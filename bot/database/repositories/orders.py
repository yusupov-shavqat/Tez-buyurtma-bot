"""Buyurtmalar repozitoriyasi (TZ 4.1.6 / 4.4)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from bot.database.enums import (
    DeliveryType,
    OrderSource,
    OrderStatus,
    PaymentMethod,
    PaymentProvider,
    PaymentStatus,
    Unit,
)
from bot.database.models import NotificationLog, Order, OrderItem, OrderStatusHistory, Payment, User
from bot.database.repositories.base import BaseRepository

MONEY_STEP = Decimal("0.01")


class OrderRepository(BaseRepository[Order]):
    """`orders`, `order_items`, `order_status_history`, `payments`."""

    model = Order

    # ------------------------- O'qish ---------------------------------
    async def get_by_number(self, number: str) -> Order | None:
        stmt = select(Order).where(func.upper(Order.number) == number.strip().upper())
        return await self.session.scalar(stmt)

    async def get_full(self, order_id: int) -> Order | None:
        """Buyurtma: satrlar, holat tarixi, to'lovlar, foydalanuvchi bilan birga."""
        stmt = (
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.status_history),
                selectinload(Order.payments),
                selectinload(Order.user),
            )
            .where(Order.id == order_id)
        )
        return await self.session.scalar(stmt)

    async def get_full_by_number(self, number: str) -> Order | None:
        stmt = (
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.status_history),
                selectinload(Order.payments),
                selectinload(Order.user),
            )
            .where(func.upper(Order.number) == number.strip().upper())
        )
        return await self.session.scalar(stmt)

    async def list_for_user(
        self, user_id: int, *, offset: int = 0, limit: int = 5
    ) -> list[Order]:
        stmt = (
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.user_id == user_id)
            .order_by(Order.id.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return list(result)

    async def count_for_user(self, user_id: int) -> int:
        return await self.count(Order.user_id == user_id)

    async def list_by_statuses(
        self,
        statuses: tuple[OrderStatus, ...] | list[OrderStatus],
        *,
        offset: int = 0,
        limit: int = 5,
        newest_first: bool = True,
    ) -> list[Order]:
        values = [str(status) for status in statuses]
        stmt = select(Order).where(Order.status.in_(values))
        stmt = stmt.order_by(Order.id.desc() if newest_first else Order.id)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.scalars(stmt)
        return list(result)

    async def count_by_statuses(
        self, statuses: tuple[OrderStatus, ...] | list[OrderStatus]
    ) -> int:
        return await self.count(Order.status.in_([str(status) for status in statuses]))

    async def search(self, query: str, *, limit: int = 10) -> list[Order]:
        """Raqam, mijoz ismi yoki telefon raqami bo'yicha qidiruv (xodimlar uchun)."""
        pattern = f"%{query.strip()}%"
        stmt = (
            select(Order)
            .where(
                or_(
                    Order.number.ilike(pattern),
                    Order.customer_name.ilike(pattern),
                    Order.customer_phone.ilike(pattern),
                )
            )
            .order_by(Order.id.desc())
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return list(result)

    # ------------------------- Raqam generatsiyasi ---------------------
    async def next_number(self, prefix: str = "ORD", *, day: date | None = None) -> str:
        """Kunlik tartib raqamli hujjat raqami: ORD-260927-0001."""
        today = day or datetime.utcnow().date()
        start = datetime(today.year, today.month, today.day)
        end = start + timedelta(days=1)
        sequence = await self.count(Order.created_at >= start, Order.created_at < end) + 1
        while True:
            number = f"{prefix}-{today:%y%m%d}-{sequence:04d}"
            if not await self.exists(Order.number == number):
                return number
            sequence += 1

    # ------------------------- Yaratish --------------------------------
    async def create(
        self,
        *,
        user_id: int,
        number: str,
        customer_id: int | None = None,
        courier_id: int | None = None,
        source: OrderSource = OrderSource.BOT,
        status: OrderStatus = OrderStatus.NEW,
        delivery_type: DeliveryType = DeliveryType.DELIVERY,
        payment_method: PaymentMethod = PaymentMethod.CASH,
        payment_status: PaymentStatus = PaymentStatus.UNPAID,
        address: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        delivery_time: str | None = None,
        customer_name: str | None = None,
        customer_phone: str | None = None,
        comment: str | None = None,
        subtotal: Decimal = Decimal("0"),
        discount_total: Decimal = Decimal("0"),
        delivery_fee: Decimal = Decimal("0"),
        total: Decimal = Decimal("0"),
    ) -> Order:
        order = Order(
            user_id=user_id,
            number=number,
            customer_id=customer_id,
            courier_id=courier_id,
            source=source,
            status=status,
            delivery_type=delivery_type,
            payment_method=payment_method,
            payment_status=payment_status,
            address=address,
            latitude=latitude,
            longitude=longitude,
            delivery_time=delivery_time,
            customer_name=customer_name,
            customer_phone=customer_phone,
            comment=comment,
            subtotal=subtotal.quantize(MONEY_STEP),
            discount_total=discount_total.quantize(MONEY_STEP),
            delivery_fee=delivery_fee.quantize(MONEY_STEP),
            total=total.quantize(MONEY_STEP),
        )
        return await self.add(order)

    async def add_item(
        self,
        order: Order,
        *,
        name: str,
        quantity: Decimal,
        unit_price: Decimal,
        total: Decimal,
        product_id: int | None = None,
        sku: str | None = None,
        unit: Unit = Unit.PCS,
        box_size: int = 1,
        discount: Decimal = Decimal("0"),
    ) -> OrderItem:
        item = OrderItem(
            order_id=order.id,
            product_id=product_id,
            name=name[:255],
            sku=sku,
            unit=unit,
            box_size=max(int(box_size or 1), 1),
            quantity=quantity,
            unit_price=unit_price.quantize(MONEY_STEP),
            discount=discount.quantize(MONEY_STEP),
            total=total.quantize(MONEY_STEP),
        )
        return await self.add(item)

    async def add_history(
        self,
        order: Order,
        to_status: OrderStatus,
        *,
        from_status: OrderStatus | None = None,
        changed_by_id: int | None = None,
        note: str | None = None,
    ) -> OrderStatusHistory:
        entry = OrderStatusHistory(
            order_id=order.id,
            from_status=from_status if from_status is not None else order.status,
            to_status=to_status,
            changed_by_id=changed_by_id,
            note=note[:512] if note else None,
        )
        return await self.add(entry)

    async def get_history(self, order_id: int) -> list[OrderStatusHistory]:
        stmt = (
            select(OrderStatusHistory)
            .where(OrderStatusHistory.order_id == order_id)
            .order_by(OrderStatusHistory.id)
        )
        result = await self.session.scalars(stmt)
        return list(result)

    # ------------------------- Holat / to'lov --------------------------
    async def update_status(
        self,
        order: Order,
        new_status: OrderStatus,
        *,
        changed_by_id: int | None = None,
        note: str | None = None,
    ) -> Order:
        """Holatni almashtiradi va tarixga yozadi (o'tish qoidalari - servisda)."""
        old_status = order.status
        order.status = new_status
        now = datetime.utcnow()
        if new_status is OrderStatus.CONFIRMED and order.confirmed_at is None:
            order.confirmed_at = now
        if new_status is OrderStatus.DELIVERED and order.delivered_at is None:
            order.delivered_at = now
        if new_status in {OrderStatus.CANCELLED, OrderStatus.RETURNED}:
            order.cancelled_at = now
        await self.add_history(
            order,
            new_status,
            from_status=old_status,
            changed_by_id=changed_by_id,
            note=note,
        )
        await self.flush()
        return order

    async def set_manager_comment(self, order: Order, comment: str) -> Order:
        order.manager_comment = comment
        await self.flush()
        return order

    async def set_cancel_reason(self, order: Order, reason: str | None) -> Order:
        order.cancel_reason = reason
        await self.flush()
        return order

    async def add_payment(
        self,
        order: Order,
        *,
        amount: Decimal,
        method: PaymentMethod,
        provider: PaymentProvider = PaymentProvider.MANUAL,
        external_id: str | None = None,
        comment: str | None = None,
        mark_paid: bool = True,
    ) -> Payment:
        """To'lov yozuvi qo'shadi va buyurtmaning to'lov holatini yangilaydi."""
        payment = Payment(
            order_id=order.id,
            customer_id=order.customer_id,
            amount=amount.quantize(MONEY_STEP),
            method=method,
            status=PaymentStatus.PAID if mark_paid else PaymentStatus.UNPAID,
            provider=provider,
            external_id=external_id,
            comment=comment,
            paid_at=datetime.utcnow() if mark_paid else None,
        )
        await self.add(payment)
        if mark_paid:
            order.paid_amount = (Decimal(order.paid_amount or 0) + amount).quantize(MONEY_STEP)
            if order.paid_amount >= Decimal(order.total or 0):
                order.payment_status = PaymentStatus.PAID
            elif order.paid_amount > 0:
                order.payment_status = PaymentStatus.PARTIAL
            await self.flush()
        return payment

    # ------------------------- Statistika ------------------------------
    async def stats_for_period(self, start: datetime, end: datetime) -> dict[str, object]:
        """Davr bo'yicha statistika: buyurtmalar soni, summa, holatlar kesimi."""
        criteria = (Order.created_at >= start, Order.created_at < end)
        count = await self.count(*criteria)
        total = await self.session.scalar(
            select(func.coalesce(func.sum(Order.total), 0)).where(*criteria)
        )
        amount = Decimal(str(total or 0)).quantize(MONEY_STEP)
        rows = (
            await self.session.execute(
                select(Order.status, func.count()).where(*criteria).group_by(Order.status)
            )
        ).all()
        by_status = {str(status): int(value) for status, value in rows}
        return {
            "orders": count,
            "amount": amount,
            "average": (amount / count).quantize(MONEY_STEP) if count else Decimal("0"),
            "by_status": by_status,
        }

    async def top_products(
        self, start: datetime, end: datetime, limit: int = 5
    ) -> list[tuple[str, Decimal]]:
        """Eng ko'p sotilgan mahsulotlar (nom, miqdor)."""
        stmt = (
            select(OrderItem.name, func.sum(OrderItem.quantity))
            .join(Order, Order.id == OrderItem.order_id)
            .where(Order.created_at >= start, Order.created_at < end)
            .group_by(OrderItem.name)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return [(str(name), Decimal(str(quantity or 0))) for name, quantity in rows]

    async def list_customer_ids_with_orders(self, statuses: list[OrderStatus]) -> list[int]:
        """Berilgan holatlardagi buyurtmalari bor foydalanuvchi ID lari."""
        stmt = (
            select(Order.user_id)
            .where(Order.status.in_([str(status) for status in statuses]))
            .distinct()
        )
        result = await self.session.scalars(stmt)
        return list(result)

    async def count_delivered_for_user(self, user_id: int) -> int:
        return await self.count(
            Order.user_id == user_id, Order.status == OrderStatus.DELIVERED
        )


class NotificationLogRepository(BaseRepository[NotificationLog]):
    """`notification_logs` jadvali - yuborilgan xabarlar jurnali."""

    model = NotificationLog

    async def log(
        self,
        *,
        kind,
        text: str,
        user_id: int | None = None,
        order_id: int | None = None,
        is_success: bool = True,
        error: str | None = None,
    ) -> NotificationLog:
        entry = NotificationLog(
            user_id=user_id,
            order_id=order_id,
            kind=kind,
            text=text[:4000],
            is_success=is_success,
            error=error[:255] if error else None,
        )
        return await self.add(entry)


__all__ = ["NotificationLogRepository", "OrderRepository"]


