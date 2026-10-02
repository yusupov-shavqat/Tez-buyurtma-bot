"""Katalog servisi (TZ 4.4 - katalog, qidiruv, aksiyalar)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Category, Product
from bot.database.repositories.catalog import CategoryRepository, ProductRepository
from bot.services.errors import NotFoundError
from bot.utils.pagination import Pagination, paginate


@dataclass(slots=True)
class CategoryCard:
    """Kategoriya + undagi mahsulotlar soni (inline tugma uchun)."""

    category: Category
    products: int

    def label(self, lang: str) -> str:
        return self.category.button_label(lang)


class CatalogService:
    """Kategoriya va mahsulotlar bilan ishlash."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.categories = CategoryRepository(session)
        self.products = ProductRepository(session)

    # ------------------------- Kategoriyalar ---------------------------
    async def category_cards(self) -> list[CategoryCard]:
        """Faol kategoriyalar va mahsulotlar soni (katalog menyusi uchun)."""
        categories = await self.categories.list_active()
        counts = await self.categories.product_counts()
        return [CategoryCard(category=item, products=counts.get(item.id, 0)) for item in categories]

    async def get_category(self, category_id: int | None) -> Category:
        if category_id is None:
            raise NotFoundError()
        category = await self.categories.get(category_id)
        if category is None:
            raise NotFoundError()
        return category

    # ------------------------- Mahsulotlar -----------------------------
    async def product_page(
        self,
        *,
        category_id: int | None = None,
        page: int = 1,
        per_page: int = 5,
    ) -> tuple[list[Product], Pagination]:
        total = await self.products.count_active(category_id)
        pagination = paginate(total, page, per_page)
        products = await self.products.list_active(
            category_id=category_id, offset=pagination.offset, limit=pagination.limit
        )
        return products, pagination

    async def promo_page(
        self, *, page: int = 1, per_page: int = 5
    ) -> tuple[list[Product], Pagination]:
        total = await self.products.count_promo()
        pagination = paginate(total, page, per_page)
        products = await self.products.list_promo(
            offset=pagination.offset, limit=pagination.limit
        )
        return products, pagination

    async def search_page(
        self, query: str, *, page: int = 1, per_page: int = 5
    ) -> tuple[list[Product], Pagination]:
        total = await self.products.count_search(query)
        pagination = paginate(total, page, per_page)
        products = await self.products.search(
            query, offset=pagination.offset, limit=pagination.limit
        )
        return products, pagination

    async def get_product(self, product_id: int | None) -> Product:
        if product_id is None:
            raise NotFoundError()
        product = await self.products.get(product_id)
        if product is None or not product.is_active:
            raise NotFoundError()
        return product

    async def find_product(self, query: str) -> list[Product]:
        """Aniq artikul/shtrix-kod yoki nomi bo'yicha qidiruv."""
        text = (query or "").strip()
        if not text:
            return []
        exact = await self.products.get_by_sku(text.upper())
        if exact is None:
            exact = await self.products.get_by_barcode(text)
        if exact is not None and exact.is_active:
            return [exact]
        return await self.products.search(text, limit=10)

    async def low_stock(self, *, limit: int = 20) -> list[Product]:
        return await self.products.list_low_stock(limit=limit)

    async def change_stock(self, product: Product, delta) -> None:
        await self.products.change_stock(product, delta)


__all__ = ["CatalogService", "CategoryCard"]
