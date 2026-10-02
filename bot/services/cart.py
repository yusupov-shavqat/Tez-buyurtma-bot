"""Savat servisi (TZ 4.4 - savat, miqdor, summalar, yetkazib berish narxi)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import Settings
from bot.database.enums import DeliveryType, Unit
from bot.database.models import CartItem, Product
from bot.database.repositories.cart import CartRepository
from bot.services.errors import CartEmptyError, MinAmountError, QuantityError, StockLimitError
from bot.utils.money import ZERO, round_money, to_decimal

MAX_QUANTITY = Decimal("1000")


@dataclass(slots=True)
class CartLine:
    """Savatdagi bitta pozitsiya."""

    item: CartItem
    product: Product

    @property
    def quantity(self) -> Decimal:
        return to_decimal(self.item.quantity)

    @property
    def price(self) -> Decimal:
        return to_decimal(self.product.effective_price)

    @property
    def total(self) -> Decimal:
        return round_money(self.price * self.quantity)

    @property
    def full_price(self) -> Decimal:
        return to_decimal(self.product.price)

    @property
    def saved(self) -> Decimal:
        return round_money(max(ZERO, self.full_price - self.price) * self.quantity)

    @property
    def stock(self) -> Decimal:
        return to_decimal(self.product.stock)

    @property
    def available(self) -> bool:
        return self.product.in_stock

    @property
    def step(self) -> Decimal:
        return to_decimal(self.product.unit.step, Decimal("1"))


@dataclass(slots=True)
class CartSummary:
    """Savat yakuniy hisob-kitobi."""

    lines: list[CartLine]
    subtotal: Decimal
    discount: Decimal
    delivery_fee: Decimal
    total: Decimal
    delivery_type: DeliveryType = DeliveryType.DELIVERY

    @property
    def positions(self) -> int:
        return len(self.lines)

    @property
    def is_empty(self) -> bool:
        return not self.lines

    @property
    def quantity(self) -> Decimal:
        return sum((line.quantity for line in self.lines), ZERO)


class CartService:
    """Savat bilan ishlash: qo'shish, o'zgartirish, summani hisoblash."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.cart = CartRepository(session)

    # ------------------------- O'qish ----------------------------------
    async def lines(self, user_id: int) -> list[CartLine]:
        """Faol mahsulotlardan iborat savat pozitsiyalari."""
        result: list[CartLine] = []
        for item in await self.cart.list_items(user_id):
            if item.product is None or not item.product.is_active:
                continue
            result.append(CartLine(item=item, product=item.product))
        return result

    async def count(self, user_id: int) -> int:
        """Savatdagi pozitsiyalar soni (menyu belgisida ko'rsatiladi)."""
        return await self.cart.positions(user_id)

    async def summary(
        self, user_id: int, *, delivery_type: DeliveryType = DeliveryType.DELIVERY
    ) -> CartSummary:
        """Savat summasi: subtotal, chegirma, yetkazish, jami."""
        lines = await self.lines(user_id)
        subtotal = round_money(sum((line.total for line in lines), ZERO))
        discount = round_money(sum((line.saved for line in lines), ZERO))
        fee = self.delivery_fee(subtotal, delivery_type, has_items=bool(lines))
        return CartSummary(
            lines=lines,
            subtotal=subtotal,
            discount=discount,
            delivery_fee=fee,
            total=round_money(subtotal + fee),
            delivery_type=delivery_type,
        )

    # ------------------------- Yetkazish narxi -------------------------
    def delivery_fee(
        self,
        subtotal: Decimal,
        delivery_type: DeliveryType = DeliveryType.DELIVERY,
        *,
        has_items: bool = True,
    ) -> Decimal:
        """Olib ketishda 0; yetkazishda - bepul chegaradan keyin 0."""
        if not has_items or delivery_type != DeliveryType.DELIVERY:
            return ZERO
        free_from = to_decimal(self.settings.free_delivery_from)
        if free_from > 0 and subtotal >= free_from:
            return ZERO
        return round_money(self.settings.delivery_fee)

    # ------------------------- O'zgartirish ---------------------------
    async def add(
        self, user_id: int, product: Product, quantity: Decimal | int | str = 1
    ) -> CartItem:
        """Savatga qo'shadi (mavjud miqdorga qo'shiladi)."""
        value = self.validate_quantity(product, quantity)
        item = await self.cart.add_quantity(user_id, product, value)
        if item is None:
            raise StockLimitError(key="qty_stock_limit", quantity=round_money(product.stock))
        return item

    async def set_quantity(
        self, user_id: int, product: Product, quantity: Decimal | int | str
    ) -> CartItem | None:
        """Miqdorni aniq qiymatga o'rnatadi (0 - pozitsiyani o'chiradi)."""
        value = self.validate_quantity(product, quantity, allow_zero=True)
        stock = to_decimal(product.stock)
        if value > 0 and stock > 0 and value > stock:
            value = stock
        return await self.cart.set_quantity(user_id, product, value)

    async def increase(self, user_id: int, product: Product) -> CartItem | None:
        return await self.add(user_id, product, self.step_for(product))

    async def decrease(self, user_id: int, product: Product) -> CartItem | None:
        item = await self.cart.get_item(user_id, product.id)
        if item is None:
            return None
        target = to_decimal(item.quantity) - self.step_for(product)
        return await self.cart.set_quantity(user_id, product, max(ZERO, target))

    async def remove(self, user_id: int, product_id: int) -> bool:
        return await self.cart.remove_item(user_id, product_id)

    async def clear(self, user_id: int) -> int:
        return await self.cart.clear(user_id)

    async def repeat(self, user_id: int, items: list[tuple[Product, Decimal]]) -> int:
        """Buyurtmani takrorlash: savatga qo'shilgan pozitsiyalar soni."""
        added = 0
        for product, quantity in items:
            if product is None or not product.is_active or not product.in_stock:
                continue
            await self.cart.add_quantity(user_id, product, to_decimal(quantity))
            added += 1
        return added

    # ------------------------- Tekshiruvlar ---------------------------
    def step_for(self, product: Product) -> Decimal:
        return to_decimal(product.unit.step, Decimal("1"))

    def validate_quantity(
        self,
        product: Product,
        quantity: Decimal | int | str,
        *,
        allow_zero: bool = False,
    ) -> Decimal:
        """Miqdorni tekshiradi va normallashtiradi."""
        value = to_decimal(quantity)
        if value < 0 or (value == 0 and not allow_zero):
            raise QuantityError()
        if value == 0:
            return ZERO
        if value > MAX_QUANTITY:
            raise QuantityError()
        if product.unit not in {Unit.KG, Unit.LITER} and value != value.to_integral_value():
            raise QuantityError()
        stock = to_decimal(product.stock)
        if stock <= 0 or value > stock:
            raise StockLimitError(key="qty_stock_limit", quantity=round_money(stock))
        return value

    async def validate_for_checkout(
        self, user_id: int, *, delivery_type: DeliveryType = DeliveryType.DELIVERY
    ) -> CartSummary:
        """Buyurtma berishdan oldingi to'liq tekshiruv."""
        summary = await self.summary(user_id, delivery_type=delivery_type)
        if summary.is_empty:
            raise CartEmptyError()
        for line in summary.lines:
            if not line.available or line.quantity > line.stock:
                raise StockLimitError(key="qty_stock_limit", quantity=round_money(line.stock))
        min_amount = to_decimal(self.settings.min_order_amount)
        if min_amount > 0 and summary.subtotal < min_amount:
            raise MinAmountError(amount=round_money(min_amount - summary.subtotal))
        return summary


__all__ = ["CartLine", "CartService", "CartSummary", "MAX_QUANTITY"]


