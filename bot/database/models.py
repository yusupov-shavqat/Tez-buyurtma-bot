"""TZ 8-bo'lim - ma'lumotlar modeli (SQLAlchemy 2.0 uslubida).

Jadvallar:
  User / Customer / Address      -> foydalanuvchi va CRM
  Category / Product             -> katalog
  CartItem                       -> savat
  Order / OrderItem / History    -> buyurtmalar
  Payment                        -> to'lovlar va qarzdorlik
  SupportRequest                 -> qo'llab-quvvatlash
  NotificationLog / Setting      -> xizmat jadvallari
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.base import Base
from bot.database.enums import (
    CustomerSegment,
    DeliveryType,
    Language,
    NotificationKind,
    OrderSource,
    OrderStatus,
    PaymentMethod,
    PaymentProvider,
    PaymentStatus,
    SupportStatus,
    Unit,
    UserRole,
)

MONEY = Numeric(14, 2)
QUANTITY = Numeric(14, 3)
CENTS = Decimal("0.01")


def utcnow() -> datetime:
    """Naive UTC vaqti - SQLite va PostgreSQL uchun bir xil xatti-harakat."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def enum_column(enum_cls: type[StrEnum]) -> SAEnum:
    """Enum'ni VARCHAR sifatida saqlaydi (qiymatlar bilan; migratsiya oson)."""
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=32,
        validate_strings=True,
        values_callable=lambda members: [member.value for member in members],
    )


def money(value: Any = 0) -> Decimal:
    """Pul qiymatini 2 xonaga yaxlitlaydi."""
    return Decimal(str(value)).quantize(CENTS, rounding=ROUND_HALF_UP)


class TimestampMixin:
    """created_at / updated_at maydonlari."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )


class User(Base, TimestampMixin):
    """Bot foydalanuvchisi: mijoz yoki xodim (TZ 2-bo'lim)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    language: Mapped[Language] = mapped_column(
        enum_column(Language), default=Language.UZ, nullable=False
    )
    role: Mapped[UserRole] = mapped_column(
        enum_column(UserRole), default=UserRole.CLIENT, nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    customer: Mapped[Customer | None] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    cart_items: Mapped[list[CartItem]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    orders: Mapped[list[Order]] = relationship(
        back_populates="user", foreign_keys="Order.user_id"
    )
    support_requests: Mapped[list[SupportRequest]] = relationship(
        back_populates="user", foreign_keys="SupportRequest.user_id"
    )

    # ------------------------------------------------------------------
    @property
    def display_name(self) -> str:
        if self.full_name:
            return self.full_name
        if self.username:
            return f"@{self.username}"
        return f"ID {self.telegram_id}"

    @property
    def is_staff(self) -> bool:
        return self.role.is_staff

    @property
    def has_phone(self) -> bool:
        return bool(self.phone)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} tg={self.telegram_id} role={self.role}>"


class Customer(Base, TimestampMixin):
    """Mijoz kartochkasi (CRM qismi - TZ 4.1.4)."""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    segment: Mapped[CustomerSegment] = mapped_column(
        enum_column(CustomerSegment), default=CustomerSegment.NEW, nullable=False
    )
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(512), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    credit_limit: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    debt_amount: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship(back_populates="customer")
    addresses: Mapped[list[Address]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )


class Address(Base, TimestampMixin):
    """Mijozning saqlangan manzillari."""

    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    address: Mapped[str] = mapped_column(String(512), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    customer: Mapped[Customer] = relationship(back_populates="addresses")


class Category(Base, TimestampMixin):
    """Mahsulot kategoriyasi (TZ 4.1.2 - kategoriyalar)."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name_uz: Mapped[str] = mapped_column(String(128), nullable=False)
    name_ru: Mapped[str] = mapped_column(String(128), nullable=False)
    emoji: Mapped[str] = mapped_column(String(8), default="", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    products: Mapped[list[Product]] = relationship(back_populates="category")

    def localized_name(self, lang: str = "uz") -> str:
        if str(lang).startswith("ru") and self.name_ru:
            return self.name_ru
        return self.name_uz

    def button_label(self, lang: str = "uz") -> str:
        return f"{self.emoji} {self.localized_name(lang)}".strip()


class Product(Base, TimestampMixin):
    """Mahsulot (TZ 4.1.2): narxlar, o'lchov birligi, qadoqlash, qoldiq."""

    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("sku", name="uq_products_sku"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    name_uz: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ru: Mapped[str] = mapped_column(String(255), nullable=False)
    description_uz: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    discount_price: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    wholesale_price: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    unit: Mapped[Unit] = mapped_column(enum_column(Unit), default=Unit.PCS, nullable=False)
    box_size: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    stock: Mapped[Decimal] = mapped_column(QUANTITY, default=Decimal("0"), nullable=False)
    min_stock: Mapped[Decimal] = mapped_column(QUANTITY, default=Decimal("0"), nullable=False)
    image_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_promo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    category: Mapped[Category | None] = relationship(back_populates="products")

    # ------------------------------------------------------------------
    def localized_name(self, lang: str = "uz") -> str:
        if str(lang).startswith("ru") and self.name_ru:
            return self.name_ru
        return self.name_uz

    def localized_description(self, lang: str = "uz") -> str | None:
        if str(lang).startswith("ru"):
            return self.description_ru or self.description_uz
        return self.description_uz

    @property
    def has_discount(self) -> bool:
        return (
            self.discount_price is not None
            and self.discount_price > 0
            and self.discount_price < self.price
        )

    @property
    def effective_price(self) -> Decimal:
        """Mijoz uchun amaldagi narx (chegirma bo'lsa - chegirmali narx)."""
        if self.has_discount and self.discount_price is not None:
            return money(self.discount_price)
        return money(self.price)

    @property
    def discount_percent(self) -> int:
        if not self.has_discount or not self.price:
            return 0
        ratio = (Decimal(1) - self.effective_price / money(self.price)) * 100
        return int(ratio.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    @property
    def in_stock(self) -> bool:
        return Decimal(self.stock or 0) > 0

    @property
    def is_low_stock(self) -> bool:
        return Decimal(self.stock or 0) <= Decimal(self.min_stock or 0)

    @property
    def step(self) -> Decimal:
        """Savatdagi +/- qadami (quti uchun box_size, kg/litr uchun 0.5)."""
        if self.unit is Unit.BOX:
            return Decimal(max(self.box_size, 1))
        return Decimal(self.unit.step)

    @property
    def box_price(self) -> Decimal | None:
        if self.box_size and self.box_size > 1:
            return money(self.effective_price * self.box_size)
        return None


class CartItem(Base, TimestampMixin):
    """Mijoz savati (TZ 4.4 - savat/korzina)."""

    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_cart_user_product"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    quantity: Mapped[Decimal] = mapped_column(QUANTITY, default=Decimal("1"), nullable=False)

    user: Mapped[User] = relationship(back_populates="cart_items")
    product: Mapped[Product] = relationship(lazy="selectin")


class Order(Base, TimestampMixin):
    """Buyurtma (TZ 4.1.6 / 4.4 - buyurtma berish va holatlar zanjiri)."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    courier_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    source: Mapped[OrderSource] = mapped_column(
        enum_column(OrderSource), default=OrderSource.BOT, nullable=False
    )
    status: Mapped[OrderStatus] = mapped_column(
        enum_column(OrderStatus), default=OrderStatus.NEW, nullable=False, index=True
    )
    delivery_type: Mapped[DeliveryType] = mapped_column(
        enum_column(DeliveryType), default=DeliveryType.DELIVERY, nullable=False
    )
    payment_method: Mapped[PaymentMethod] = mapped_column(
        enum_column(PaymentMethod), default=PaymentMethod.CASH, nullable=False
    )
    payment_status: Mapped[PaymentStatus] = mapped_column(
        enum_column(PaymentStatus), default=PaymentStatus.UNPAID, nullable=False
    )

    address: Mapped[str | None] = mapped_column(String(512), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    delivery_time: Mapped[str | None] = mapped_column(String(128), nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    manager_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)

    subtotal: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    discount_total: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    delivery_fee: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    total: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    stock_deducted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[User] = relationship(back_populates="orders", foreign_keys=[user_id])


    courier: Mapped[User | None] = relationship(foreign_keys=[courier_id])
    customer: Mapped[Customer | None] = relationship()
    items: Mapped[list[OrderItem]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderItem.id"
    )
    status_history: Mapped[list[OrderStatusHistory]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderStatusHistory.id",
    )
    payments: Mapped[list[Payment]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="Payment.id"
    )

    # ------------------------------------------------------------------
    @property
    def is_cancellable(self) -> bool:
        """Mijoz faqat tasdiqlangunga qadar bekor qila oladi (TZ 4.1.6)."""
        return self.status in {OrderStatus.NEW, OrderStatus.CONFIRMED}

    @property
    def is_paid(self) -> bool:
        return self.payment_status is PaymentStatus.PAID

    @property
    def positions(self) -> int:
        return len(self.items) if self.items else 0

    @property
    def items_total_quantity(self) -> Decimal:
        total = Decimal("0")
        for item in self.items or []:
            total += Decimal(item.quantity or 0)
        return total

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Order {self.number} status={self.status} total={self.total}>"


class OrderItem(Base, TimestampMixin):
    """Buyurtma satri (mahsulot ma'lumotlari snapshot sifatida saqlanadi)."""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(64), nullable=True)
    unit: Mapped[Unit] = mapped_column(enum_column(Unit), default=Unit.PCS, nullable=False)
    box_size: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(QUANTITY, default=Decimal("0"), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    discount: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    total: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped[Product | None] = relationship()

    def localized_name(self, lang: str = "uz") -> str:
        return self.name

    def __repr__(self) -> str:  # pragma: no cover
        return f"<OrderItem {self.name} x{self.quantity} = {self.total}>"


class OrderStatusHistory(Base):
    """Buyurtma holati o'zgarishlari tarixi (audit - TZ 7-bo'lim)."""

    __tablename__ = "order_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    from_status: Mapped[OrderStatus | None] = mapped_column(enum_column(OrderStatus), nullable=True)
    to_status: Mapped[OrderStatus] = mapped_column(enum_column(OrderStatus), nullable=False)
    changed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    order: Mapped[Order] = relationship(back_populates="status_history")
    changed_by: Mapped[User | None] = relationship()


class Payment(Base, TimestampMixin):
    """To'lov / qarzdorlik harakati (TZ 4.1.8)."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    amount: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        enum_column(PaymentMethod), default=PaymentMethod.CASH, nullable=False
    )
    status: Mapped[PaymentStatus] = mapped_column(
        enum_column(PaymentStatus), default=PaymentStatus.UNPAID, nullable=False
    )
    provider: Mapped[PaymentProvider] = mapped_column(
        enum_column(PaymentProvider), default=PaymentProvider.MANUAL, nullable=False
    )
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    comment: Mapped[str | None] = mapped_column(String(512), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    order: Mapped[Order | None] = relationship(back_populates="payments")
    customer: Mapped[Customer | None] = relationship()


class SupportRequest(Base, TimestampMixin):
    """Mijozning qo'llab-quvvatlash so'rovi (TZ 4.4 - operator bilan bog'lanish)."""

    __tablename__ = "support_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SupportStatus] = mapped_column(
        enum_column(SupportStatus), default=SupportStatus.OPEN, nullable=False, index=True
    )
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    answered_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    answered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[User] = relationship(back_populates="support_requests", foreign_keys=[user_id])
    answered_by: Mapped[User | None] = relationship(foreign_keys="SupportRequest.answered_by_id")
    order: Mapped[Order | None] = relationship()


class NotificationLog(Base):
    """Yuborilgan bildirishnomalar jurnali (TZ 7-bo'lim - loglar)."""

    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    kind: Mapped[NotificationKind] = mapped_column(enum_column(NotificationKind), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class Setting(Base, TimestampMixin):
    """Tizim sozlamalari (kalit-qiymat): ish vaqti, aloqa raqami va h.k."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(1024), default="", nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)


__all__ = [
    "Address",
    "CartItem",
    "Category",
    "Customer",
    "NotificationLog",
    "Order",
    "OrderItem",
    "OrderStatusHistory",
    "Payment",
    "Product",
    "Setting",
    "SupportRequest",
    "User",
    "money",
    "utcnow",
]





