"""Savat repozitoriyasi (TZ 4.4 - savat/korzina)."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.orm import joinedload

from bot.database.models import CartItem, Product
from bot.database.repositories.base import BaseRepository


class CartRepository(BaseRepository[CartItem]):
    """`cart_items` jadvali bilan ishlash."""

    model = CartItem

    # ------------------------------------------------------------------
    async def list_items(self, user_id: int) -> list[CartItem]:
        """Savat elementlari (mahsulot bilan birga) - tartib saqlanadi."""
        stmt = (
            select(CartItem)
            .options(joinedload(CartItem.product))
            .where(CartItem.user_id == user_id)
            .order_by(CartItem.id)
        )
        result = await self.session.scalars(stmt)
        return list(result)

    async def get_item(self, user_id: int, product_id: int) -> CartItem | None:
        stmt = select(CartItem).where(
            CartItem.user_id == user_id, CartItem.product_id == product_id
        )
        return await self.session.scalar(stmt)

    async def get_item_by_id(self, item_id: int) -> CartItem | None:
        stmt = (
            select(CartItem)
            .options(joinedload(CartItem.product))
            .where(CartItem.id == item_id)
        )
        return await self.session.scalar(stmt)

    async def count_items(self, user_id: int) -> int:
        return await self.count(CartItem.user_id == user_id)

    async def total_quantity(self, user_id: int) -> Decimal:
        items = await self.list_items(user_id)
        return sum((Decimal(item.quantity or 0) for item in items), Decimal("0"))

    async def positions(self, user_id: int) -> int:
        return await self.count_items(user_id)

    # ------------------------- O'zgartirish ---------------------------
    async def set_quantity(self, user_id: int, product: Product, quantity: Decimal) -> CartItem:
        """Miqdorni o'rnatadi; 0 yoki undan kam bo'lsa element o'chiriladi."""
        item = await self.get_item(user_id, product.id)
        if quantity <= 0:
            if item is not None:
                await self.delete(item)
            return None  # type: ignore[return-value]

        if item is None:
            item = CartItem(user_id=user_id, product_id=product.id, quantity=quantity)
            await self.add(item)
        else:
            item.quantity = quantity
            await self.flush()
        return item

    async def add_quantity(
        self, user_id: int, product: Product, quantity: Decimal
    ) -> CartItem | None:
        """Mavjud miqdorga qo'shadi (yig'indi qoldiqdan oshmaydi)."""
        item = await self.get_item(user_id, product.id)
        current = Decimal(item.quantity or 0) if item is not None else Decimal("0")
        target = current + Decimal(quantity)
        stock = Decimal(product.stock or 0)
        if stock > 0 and target > stock:
            target = stock
        if target <= 0:
            if item is not None:
                await self.delete(item)
            return None
        return await self.set_quantity(user_id, product, target)

    async def remove_item(self, user_id: int, product_id: int) -> bool:
        item = await self.get_item(user_id, product_id)
        if item is None:
            return False
        await self.delete(item)
        return True

    async def clear(self, user_id: int) -> int:
        """Savatni tozalaydi; o'chirilgan qatorlar soni qaytadi."""
        stmt = sa_delete(CartItem).where(CartItem.user_id == user_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return int(result.rowcount or 0)

    async def totals(self, user_id: int) -> tuple[Decimal, Decimal]:
        """(mahsulotlar yig'indisi, chegirma summasi) qaytaradi."""
        subtotal = Decimal("0")
        discount = Decimal("0")
        for item in await self.list_items(user_id):
            product = item.product
            if product is None:
                continue
            quantity = Decimal(item.quantity or 0)
            price = Decimal(product.price or 0)
            effective = Decimal(product.effective_price)
            subtotal += effective * quantity
            if price > effective:
                discount += (price - effective) * quantity
        return (
            subtotal.quantize(Decimal("0.01")),
            discount.quantize(Decimal("0.01")),
        )


__all__ = ["CartRepository"]
