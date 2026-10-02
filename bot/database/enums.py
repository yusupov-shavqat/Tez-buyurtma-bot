"""Tizimda ishlatiladigan enum (sanab o'tilgan) qiymatlar.

Barchasi `StrEnum` - bazada matn ko'rinishida saqlanadi, bu keyinchalik
PostgreSQL'ga migratsiya qilishni osonlashtiradi.
"""

from __future__ import annotations

from enum import StrEnum


class Language(StrEnum):
    UZ = "uz"
    RU = "ru"

    @property
    def label(self) -> str:
        return {"uz": "O'zbekcha", "ru": "Русский"}.get(self.value, self.value)


class UserRole(StrEnum):
    """TZ 2-bo'lim: foydalanuvchi rollari."""

    CLIENT = "client"
    OPERATOR = "operator"
    WAREHOUSE = "warehouse"
    MANAGER = "manager"
    ADMIN = "admin"

    @property
    def is_staff(self) -> bool:
        return self is not UserRole.CLIENT


STAFF_ROLES: tuple[UserRole, ...] = (
    UserRole.OPERATOR,
    UserRole.WAREHOUSE,
    UserRole.MANAGER,
    UserRole.ADMIN,
)


class CustomerSegment(StrEnum):
    NEW = "new"
    REGULAR = "regular"
    VIP = "vip"


class Unit(StrEnum):
    """O'lchov birliklari (TZ 4.1.2)."""

    PCS = "pcs"
    BOX = "box"
    PACK = "pack"
    KG = "kg"
    LITER = "liter"

    @property
    def step(self) -> str:
        """Savatda +/- tugmasi uchun qadam."""
        return {
            Unit.KG: "0.5",
            Unit.LITER: "0.5",
        }.get(self, "1")


class OrderSource(StrEnum):
    BOT = "bot"
    AGENT = "agent"
    ADMIN = "admin"
    PHONE = "phone"


class OrderStatus(StrEnum):
    """TZ 4.1.6: Yangi -> Tasdiqlangan -> Yig'ilmoqda -> Yo'lda -> Yetkazildi."""

    NEW = "new"
    CONFIRMED = "confirmed"
    PICKING = "picking"
    ON_THE_WAY = "on_the_way"
    DELIVERED = "delivered"
    PARTIALLY_DELIVERED = "partially_delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"

    @property
    def is_final(self) -> bool:
        return self in {
            OrderStatus.DELIVERED,
            OrderStatus.PARTIALLY_DELIVERED,
            OrderStatus.CANCELLED,
            OrderStatus.RETURNED,
        }

    @property
    def is_active(self) -> bool:
        return not self.is_final

    @property
    def deducts_stock(self) -> bool:
        """Shu holatga o'tganda ombor qoldig'i hisobdan chiqariladi."""
        return self in {OrderStatus.PICKING, OrderStatus.ON_THE_WAY, OrderStatus.DELIVERED}


class DeliveryType(StrEnum):
    DELIVERY = "delivery"
    PICKUP = "pickup"


class PaymentMethod(StrEnum):
    CASH = "cash"
    TRANSFER = "transfer"
    CARD = "card"
    PAYME = "payme"
    CLICK = "click"


ONLINE_PAYMENT_METHODS: tuple[PaymentMethod, ...] = (
    PaymentMethod.PAYME,
    PaymentMethod.CLICK,
)


class PaymentStatus(StrEnum):
    UNPAID = "unpaid"
    PARTIAL = "partial"
    PAID = "paid"
    REFUNDED = "refunded"


class PaymentProvider(StrEnum):
    MANUAL = "manual"
    PAYME = "payme"
    CLICK = "click"


class SupportStatus(StrEnum):
    OPEN = "open"
    ANSWERED = "answered"
    CLOSED = "closed"


class NotificationKind(StrEnum):
    ORDER_CREATED = "order_created"
    ORDER_STATUS = "order_status"
    ORDER_CANCELLED = "order_cancelled"
    SUPPORT = "support"
    SUPPORT_REPLY = "support_reply"
    LOW_STOCK = "low_stock"
    BROADCAST = "broadcast"


__all__ = [
    "CustomerSegment",
    "DeliveryType",
    "Language",
    "NotificationKind",
    "ONLINE_PAYMENT_METHODS",
    "OrderSource",
    "OrderStatus",
    "PaymentMethod",
    "PaymentProvider",
    "PaymentStatus",
    "STAFF_ROLES",
    "SupportStatus",
    "Unit",
    "UserRole",
]
