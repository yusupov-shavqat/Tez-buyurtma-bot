"""Buyurtma servisi (TZ 4.1.6 / 4.4).

Mas'uliyat:
* savatdan buyurtma yaratish (snapshot narxlar, yetkazish narxi, raqam);
* holatlar zanjiri (state machine) va ombor qoldig'i harakati;
* mijoz statistikasi va segment yangilanishi;
* buyurtmani takrorlash, to'lovlarni qayd etish.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import Settings
from bot.database.enums import (
    CustomerSegment,
    DeliveryType,
    OrderSource,
    OrderStatus,
    PaymentMethod,
    PaymentProvider,
    PaymentStatus,
)
from bot.database.models import Order, User
from bot.database.repositories.catalog import ProductRepository
from bot.database.repositories.orders import OrderRepository
from bot.database.repositories.users import CustomerRepository, UserRepository
from bot.services.cart import CartService
from bot.services.errors import (
    AddressRequiredError,
    NotFoundError,
    NotCancellableError,
    StatusSameError,
    StatusTransitionError,
)
from bot.utils.money import ZERO, round_money, to_decimal
from bot.utils.pagination import Pagination, paginate

#: TZ 4.1.6: ruxsat etilgan holat o'tishlari.
TRANSITIONS: dict[OrderStatus, tuple[OrderStatus, ...]] = {
    OrderStatus.NEW: (OrderStatus.CONFIRMED, OrderStatus.CANCELLED),
    OrderStatus.CONFIRMED: (OrderStatus.PICKING, OrderStatus.CANCELLED),
    OrderStatus.PICKING: (
        OrderStatus.ON_THE_WAY,
        OrderStatus.DELIVERED,
        OrderStatus.CANCELLED,
    ),
    OrderStatus.ON_THE_WAY: (
        OrderStatus.DELIVERED,
        OrderStatus.PARTIALLY_DELIVERED,
        OrderStatus.RETURNED,
    ),
    OrderStatus.PARTIALLY_DELIVERED: (OrderStatus.DELIVERED, OrderStatus.RETURNED),
    OrderStatus.DELIVERED: (),
    OrderStatus.CANCELLED: (),
    OrderStatus.RETURNED: (),
}

#: Mijoz o'zi bekor qila oladigan holatlar.
CUSTOMER_CANCELLABLE: tuple[OrderStatus, ...] = (OrderStatus.NEW, OrderStatus.CONFIRMED)

#: Ombor qoldig'i qaytariladigan holatlar.
STOCK_RELEASE_STATUSES: frozenset[OrderStatus] = frozenset(
    {OrderStatus.CANCELLED, OrderStatus.RETURNED}
)

#: Mijoz segmenti chegaralari (yetkazilgan buyurtmalar soni).
REGULAR_FROM = 3
VIP_FROM = 10


@dataclass(slots=True)
class CheckoutData:
    """Buyurtma berish FSM yakunidagi ma'lumotlar."""

    delivery_type: DeliveryType = DeliveryType.DELIVERY
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    delivery_time: str | None = None
    comment: str | None = None
    payment_method: PaymentMethod = PaymentMethod.CASH
    customer_name: str | None = None
    customer_phone: str | None = None
    source: OrderSource = OrderSource.BOT
    save_address: bool = True


@dataclass(slots=True)
class StatusChange:
    """Holat o'zgarishi natijasi (xabar yuborish uchun bayroqlar bilan)."""

    order: Order
    old_status: OrderStatus
    new_status: OrderStatus
    stock_deducted: bool = False
    stock_released: bool = False

    @property
    def is_cancelled(self) -> bool:
        return self.new_status in STOCK_RELEASE_STATUSES

    @property
    def is_delivered(self) -> bool:
        return self.new_status in {
            OrderStatus.DELIVERED,
            OrderStatus.PARTIALLY_DELIVERED,
        }


class OrderService:
    """Buyurtmalar bilan ishlashning yagona kirish nuqtasi."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.orders = OrderRepository(session)
        self.products = ProductRepository(session)
        self.customers = CustomerRepository(session)
        self.users = UserRepository(session)
        self.cart = CartService(session, settings)

    # ------------------------- Yaratish --------------------------------
    async def create_from_cart(self, user: User, data: CheckoutData) -> Order:
        """Savatdagi mahsulotlardan buyurtma yaratadi va savatni tozalaydi."""
        address = (data.address or "").strip() or None
        if data.delivery_type is DeliveryType.DELIVERY and not address:
            raise AddressRequiredError()

        summary = await self.cart.validate_for_checkout(
            user.id, delivery_type=data.delivery_type
        )
        customer = await self.customers.get_or_create_for_user(user)

        if address and data.save_address:
            await self.customers.add_address(
                customer.id,
                address,
                latitude=data.latitude,
                longitude=data.longitude,
            )
            await self.customers.update_profile(customer, address=address)

        number = await self.orders.next_number(self.settings.order_prefix)
        lang = self.settings.default_language
        order = await self.orders.create(
            user_id=user.id,
            number=number,
            customer_id=customer.id,
            source=data.source,
            status=OrderStatus.NEW,
            delivery_type=data.delivery_type,
            payment_method=data.payment_method,
            payment_status=PaymentStatus.UNPAID,
            address=address,
            latitude=data.latitude,
            longitude=data.longitude,
            delivery_time=data.delivery_time,
            customer_name=data.customer_name or user.display_name,
            customer_phone=data.customer_phone or user.phone,
            comment=data.comment,
            subtotal=summary.subtotal,
            discount_total=summary.discount,
            delivery_fee=summary.delivery_fee,
            total=summary.total,
        )

        for line in summary.lines:
            await self.orders.add_item(
                order,
                name=line.product.localized_name(lang),
                quantity=line.quantity,
                unit_price=line.price,
                total=line.total,
                product_id=line.product.id,
                sku=line.product.sku,
                unit=line.product.unit,
                box_size=line.product.box_size,
                discount=max(ZERO, line.full_price - line.price) * line.quantity,
            )

        await self.orders.add_history(order, OrderStatus.NEW, note="Savatdan yaratildi")
        await self.cart.clear(user.id)
        await self.session.flush()
        return await self.get_full(order.id)

    # ------------------------- O'qish ----------------------------------
    async def get_full(self, order_id: int | None) -> Order:
        if order_id is None:
            raise NotFoundError()
        order = await self.orders.get_full(order_id)
        if order is None:
            raise NotFoundError()
        return order

    async def get_by_number(self, number: str) -> Order:
        order = await self.orders.get_full_by_number(number)
        if order is None:
            raise NotFoundError()
        return order

    async def get_for_user(self, user_id: int, order_id: int | None) -> Order:
        order = await self.get_full(order_id)
        if order.user_id != user_id:
            raise NotFoundError()
        return order

    async def page_for_user(
        self, user_id: int, *, page: int = 1, per_page: int | None = None
    ) -> tuple[list[Order], Pagination]:
        size = per_page or self.settings.orders_per_page
        total = await self.orders.count_for_user(user_id)
        pagination = paginate(total, page, size)
        items = await self.orders.list_for_user(
            user_id, offset=pagination.offset, limit=pagination.limit
        )
        return items, pagination

    async def page_by_statuses(
        self,
        statuses: tuple[OrderStatus, ...] | list[OrderStatus],
        *,
        page: int = 1,
        per_page: int | None = None,
    ) -> tuple[list[Order], Pagination]:
        size = per_page or self.settings.orders_per_page
        total = await self.orders.count_by_statuses(statuses)
        pagination = paginate(total, page, size)
        items = await self.orders.list_by_statuses(
            statuses, offset=pagination.offset, limit=pagination.limit
        )
        return items, pagination

    async def search(self, query: str, *, limit: int = 10) -> list[Order]:
        return await self.orders.search((query or "").strip(), limit=limit)

    async def history(self, order_id: int) -> list:
        return await self.orders.get_history(order_id)

    # ------------------------- Holatlar zanjiri ------------------------
    @staticmethod
    def allowed_transitions(status: OrderStatus | str) -> tuple[OrderStatus, ...]:
        """Shu holatdan o'tish mumkin bo'lgan holatlar ro'yxati."""
        return TRANSITIONS.get(OrderStatus(str(status)), ())

    @classmethod
    def can_customer_cancel(cls, order: Order) -> bool:
        return OrderStatus(str(order.status)) in CUSTOMER_CANCELLABLE

    async def change_status(
        self,
        order: Order,
        new_status: OrderStatus | str,
        *,
        actor: User | None = None,
        note: str | None = None,
    ) -> StatusChange:
        """Holatni almashtiradi: ombor qoldig'i va mijoz statistikasi bilan."""
        current = OrderStatus(str(order.status))
        target = OrderStatus(str(new_status))
        if target is current:
            raise StatusSameError()
        if target not in TRANSITIONS.get(current, ()):
            raise StatusTransitionError()

        changed = StatusChange(order=order, old_status=current, new_status=target)
        if target.deducts_stock and not order.stock_deducted:
            changed.stock_deducted = await self._deduct_stock(order)
        elif target in STOCK_RELEASE_STATUSES and order.stock_deducted:
            changed.stock_released = await self._release_stock(order)

        await self.orders.update_status(
            order,
            target,
            changed_by_id=actor.id if actor is not None else None,
            note=note,
        )
        if changed.is_delivered:
            await self._refresh_customer_segment(order)
        await self.session.flush()
        return changed

    async def cancel_by_customer(
        self, order: Order, reason: str | None = None
    ) -> StatusChange:
        """Mijozning o'zi bekor qilishi (faqat Yangi/Tasdiqlangan)."""
        if not self.can_customer_cancel(order):
            raise NotCancellableError()
        text = (reason or "").strip()
        if text:
            await self.orders.set_cancel_reason(order, text)
        return await self.change_status(order, OrderStatus.CANCELLED, note=text or None)

    # ------------------------- Ombor harakati --------------------------
    async def _deduct_stock(self, order: Order) -> bool:
        """Buyurtma mahsulotlarini ombordan hisobdan chiqaradi."""
        moved = await self._move_stock(order, sign=Decimal("-1"))
        order.stock_deducted = moved
        return moved

    async def _release_stock(self, order: Order) -> bool:
        """Bekor qilish/qaytarishda qoldiqni omborga qaytaradi."""
        moved = await self._move_stock(order, sign=Decimal("1"))
        order.stock_deducted = False
        return moved

    async def _move_stock(self, order: Order, *, sign: Decimal) -> bool:
        items = list(order.items or [])
        product_ids = [item.product_id for item in items if item.product_id]
        if not product_ids:
            return False
        products = await self.products.get_many(product_ids)
        moved = False
        for item in items:
            product = products.get(item.product_id) if item.product_id else None
            if product is None:
                continue
            await self.products.change_stock(product, sign * to_decimal(item.quantity))
            moved = True
        return moved

    async def _refresh_customer_segment(self, order: Order) -> None:
        """Yetkazilgan buyurtmalar soniga qarab mijoz toifasini yangilaydi."""
        customer = await self.customers.get_by_user_id(order.user_id)
        if customer is None:
            return
        delivered = await self.orders.count_delivered_for_user(order.user_id)
        if delivered >= VIP_FROM:
            segment = CustomerSegment.VIP
        elif delivered >= REGULAR_FROM:
            segment = CustomerSegment.REGULAR
        else:
            segment = CustomerSegment.NEW
        if CustomerSegment(str(customer.segment)) is not segment:
            await self.customers.set_segment(customer, segment)

    # ------------------------- Takrorlash ------------------------------
    async def repeat(self, user_id: int, order: Order) -> int:
        """Buyurtma tarkibini savatga qaytaradi; qo'shilgan pozitsiyalar soni."""
        items = [item for item in (order.items or []) if item.product_id]
        if not items:
            return 0
        products = await self.products.get_many([item.product_id for item in items])
        pairs = [
            (products[item.product_id], to_decimal(item.quantity))
            for item in items
            if item.product_id in products
        ]
        return await self.cart.repeat(user_id, pairs)

    # ------------------------- To'lovlar -------------------------------
    async def register_payment(
        self,
        order: Order,
        amount,
        *,
        method: PaymentMethod = PaymentMethod.CASH,
        provider: PaymentProvider = PaymentProvider.MANUAL,
        external_id: str | None = None,
        comment: str | None = None,
        mark_paid: bool = True,
    ) -> Order:
        """To'lovni qayd etadi va buyurtma to'lov holatini yangilaydi."""
        await self.orders.add_payment(
            order,
            amount=round_money(amount),
            method=method,
            provider=provider,
            external_id=external_id,
            comment=comment,
            mark_paid=mark_paid,
        )
        await self.session.flush()
        return order

    async def mark_fully_paid(
        self, order: Order, *, method: PaymentMethod = PaymentMethod.CASH
    ) -> Order:
        """Qolgan summani to'langan deb belgilaydi (naqd yetkazishda)."""
        remaining = round_money(to_decimal(order.total) - to_decimal(order.paid_amount))
        if remaining <= ZERO:
            return order
        return await self.register_payment(order, remaining, method=method)

    # ------------------------- Statistika ------------------------------
    @staticmethod
    def day_bounds(day: date | None = None) -> tuple[datetime, datetime]:
        """Kunning boshlanishi va tugashi (naive UTC)."""
        target = day or datetime.utcnow().date()
        start = datetime.combine(target, time.min)
        return start, start + timedelta(days=1)

    async def stats(self, day: date | None = None) -> dict[str, object]:
        """Kunlik ko'rsatkichlar (admin panel «Bugungi statistika»)."""
        start, end = self.day_bounds(day)
        data = await self.orders.stats_for_period(start, end)
        data["date"] = start
        data["top"] = await self.orders.top_products(start, end, limit=5)
        return data

    async def stats_for_period(
        self, start: datetime, end: datetime, *, with_top: bool = True
    ) -> dict[str, object]:
        data = await self.orders.stats_for_period(start, end)
        if with_top:
            data["top"] = await self.orders.top_products(start, end, limit=5)
        return data

    async def active_order_counts(self) -> dict[str, int]:
        """Yangi va faol buyurtmalar soni (admin menyu tugmalari uchun)."""
        new_count = await self.orders.count_by_statuses((OrderStatus.NEW,))
        active = await self.orders.count_by_statuses(
            (
                OrderStatus.NEW,
                OrderStatus.CONFIRMED,
                OrderStatus.PICKING,
                OrderStatus.ON_THE_WAY,
            )
        )
        return {"new": new_count, "active": active}


__all__ = [
    "CUSTOMER_CANCELLABLE",
    "CheckoutData",
    "OrderService",
    "REGULAR_FROM",
    "STOCK_RELEASE_STATUSES",
    "StatusChange",
    "TRANSITIONS",
    "VIP_FROM",
]



