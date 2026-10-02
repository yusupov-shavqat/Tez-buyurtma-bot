"""Katalog repozitoriylari: kategoriyalar va mahsulotlar (TZ 4.1.2)."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, or_, select

from bot.database.enums import Unit
from bot.database.models import Category, Product
from bot.database.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    """`categories` jadvali."""

    model = Category

    async def list_active(self) -> list[Category]:
        stmt = (
            select(Category)
            .where(Category.is_active.is_(True))
            .order_by(Category.sort_order, Category.id)
        )
        result = await self.session.scalars(stmt)
        return list(result)

    async def list_all_ordered(self) -> list[Category]:
        stmt = select(Category).order_by(Category.sort_order, Category.id)
        result = await self.session.scalars(stmt)
        return list(result)

    async def get_by_name(self, name: str) -> Category | None:
        stmt = select(Category).where(
            or_(Category.name_uz.ilike(name), Category.name_ru.ilike(name))
        )
        return await self.session.scalar(stmt)

    async def create(
        self,
        name_uz: str,
        name_ru: str,
        *,
        emoji: str = "",
        sort_order: int = 100,
        parent_id: int | None = None,
    ) -> Category:
        category = Category(
            name_uz=name_uz,
            name_ru=name_ru,
            emoji=emoji,
            sort_order=sort_order,
            parent_id=parent_id,
        )
        return await self.add(category)

    async def product_counts(self) -> dict[int, int]:
        """Kategoriya bo'yicha faol mahsulotlar soni."""
        stmt = (
            select(Product.category_id, func.count())
            .where(Product.is_active.is_(True), Product.category_id.is_not(None))
            .group_by(Product.category_id)
        )
        rows = (await self.session.execute(stmt)).all()
        return {int(category_id): int(total) for category_id, total in rows}


class ProductRepository(BaseRepository[Product]):
    """`products` jadvali: qidiruv, sahifalash, qoldiq harakati."""

    model = Product

    # ------------------------- O'qish ---------------------------------
    async def list_active(
        self,
        *,
        category_id: int | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Product]:
        stmt = select(Product).where(Product.is_active.is_(True))
        if category_id is not None:
            stmt = stmt.where(Product.category_id == category_id)
        stmt = stmt.order_by(Product.sort_order, Product.id).offset(offset).limit(limit)
        result = await self.session.scalars(stmt)
        return list(result)

    async def count_active(self, category_id: int | None = None) -> int:
        criteria = [Product.is_active.is_(True)]
        if category_id is not None:
            criteria.append(Product.category_id == category_id)
        return await self.count(*criteria)

    async def search(self, query: str, *, offset: int = 0, limit: int = 20) -> list[Product]:
        """Nomi, artikuli yoki shtrix-kodi bo'yicha qidiruv."""
        stmt = (
            select(Product)
            .where(Product.is_active.is_(True), *self._search_criteria(query))
            .order_by(Product.sort_order, Product.id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return list(result)

    async def count_search(self, query: str) -> int:
        return await self.count(Product.is_active.is_(True), *self._search_criteria(query))

    @staticmethod
    def _search_criteria(query: str) -> list:
        pattern = f"%{query.strip()}%"
        return [
            or_(
                Product.name_uz.ilike(pattern),
                Product.name_ru.ilike(pattern),
                Product.sku.ilike(pattern),
                Product.barcode.ilike(pattern),
            )
        ]

    async def list_promo(self, *, offset: int = 0, limit: int = 20) -> list[Product]:
        stmt = (
            select(Product)
            .where(
                Product.is_active.is_(True),
                Product.is_promo.is_(True),
                Product.discount_price.is_not(None),
            )
            .order_by(Product.sort_order, Product.id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return list(result)

    async def count_promo(self) -> int:
        return await self.count(
            Product.is_active.is_(True),
            Product.is_promo.is_(True),
            Product.discount_price.is_not(None),
        )

    async def list_low_stock(self, *, limit: int = 50) -> list[Product]:
        """Qoldig'i minimal chegaradan past yoki teng mahsulotlar."""
        stmt = (
            select(Product)
            .where(Product.is_active.is_(True), Product.stock <= Product.min_stock)
            .order_by(Product.stock, Product.id)
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return list(result)

    async def get_many(self, product_ids: list[int]) -> dict[int, Product]:
        if not product_ids:
            return {}
        stmt = select(Product).where(Product.id.in_(product_ids))
        result = await self.session.scalars(stmt)
        return {product.id: product for product in result}

    async def get_by_sku(self, sku: str) -> Product | None:
        stmt = select(Product).where(Product.sku == sku)
        return await self.session.scalar(stmt)

    async def get_by_barcode(self, barcode: str) -> Product | None:
        stmt = select(Product).where(Product.barcode == barcode)
        return await self.session.scalar(stmt)

    # ------------------------- Ombor harakati -------------------------
    async def change_stock(self, product: Product, delta: Decimal) -> Decimal:
        """Qoldiqni o'zgartiradi va yangi qiymatni qaytaradi (0 dan pastga tushmaydi)."""
        new_value = Decimal(product.stock or 0) + Decimal(delta)
        if new_value < 0:
            new_value = Decimal("0")
        product.stock = new_value
        await self.flush()
        return product.stock

    async def set_stock(self, product: Product, value: Decimal) -> Decimal:
        product.stock = max(Decimal("0"), Decimal(value))
        await self.flush()
        return product.stock

    # ------------------------- CRUD (admin/seed) ----------------------
    async def create(
        self,
        sku: str,
        name_uz: str,
        name_ru: str,
        *,
        category_id: int | None = None,
        price: Decimal = Decimal("0"),
        discount_price: Decimal | None = None,
        description_uz: str | None = None,
        description_ru: str | None = None,
        barcode: str | None = None,
        unit: Unit | None = None,
        box_size: int = 1,
        stock: Decimal = Decimal("0"),
        min_stock: Decimal = Decimal("0"),
        is_promo: bool = False,
        sort_order: int = 100,
    ) -> Product:
        product = Product(
            sku=sku,
            name_uz=name_uz,
            name_ru=name_ru,
            category_id=category_id,
            price=price,
            discount_price=discount_price,
            description_uz=description_uz,
            description_ru=description_ru,
            barcode=barcode,
            unit=unit or Unit.PCS,
            box_size=max(int(box_size), 1),
            stock=stock,
            min_stock=min_stock,
            is_promo=is_promo,
            sort_order=sort_order,
        )
        return await self.add(product)

    async def count_total(self) -> int:
        return await self.count()


__all__ = ["CategoryRepository", "ProductRepository"]


