"""Model ma'lumotlarini foydalanuvchi tilidagi matnga aylantirish.

Barcha funksiyalar birinchi argument sifatida tilga bog'langan `t`
funksiyasini oladi (qarang: `bot.locales.translator`).
"""

from __future__ import annotations

from typing import Callable

from bot.database.enums import (
    CustomerSegment,
    DeliveryType,
    OrderSource,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    Unit,
    UserRole,
)
from bot.database.models import CartItem, Order, OrderItem, Product, SupportRequest, User
from bot.utils.money import format_money, format_number, format_quantity, to_decimal
from bot.utils.text import escape, format_datetime, truncate

T = Callable[..., str]


# ------------------------- Yorliqlar -----------------------------------
def unit_label(t: T, unit: Unit | str | None) -> str:
    return t(f"unit_{str(unit or Unit.PCS)}")


def status_label(t: T, status: OrderStatus | str | None) -> str:
    return t(f"status_{str(status or OrderStatus.NEW)}")


def payment_label(t: T, method: PaymentMethod | str | None) -> str:
    return t(f"pm_{str(method or PaymentMethod.CASH)}")


def payment_status_label(t: T, status: PaymentStatus | str | None) -> str:
    return t(f"ps_{str(status or PaymentStatus.UNPAID)}")


def delivery_label(t: T, delivery_type: DeliveryType | str | None) -> str:
    return t(f"dt_{str(delivery_type or DeliveryType.DELIVERY)}")


def source_label(t: T, source: OrderSource | str | None) -> str:
    return t(f"src_{str(source or OrderSource.BOT)}")


def segment_label(t: T, segment: CustomerSegment | str | None) -> str:
    return t(f"seg_{str(segment or CustomerSegment.NEW)}")


def role_label(t: T, role: UserRole | str | None) -> str:
    return t(f"role_{str(role or UserRole.CLIENT)}")


def quantity_label(t: T, quantity: object, unit: Unit | str | None) -> str:
    return format_quantity(quantity, unit_label(t, unit))


# ------------------------- Mahsulot ------------------------------------
def product_caption(
    t: T, product: Product, lang: str, currency: str, *, show_stock: bool = True
) -> str:
    """Mahsulot kartochkasi matni (rasm ostidagi izoh)."""
    lines = [f"<b>{escape(product.localized_name(lang))}</b>"]
    lines.append(t("product_sku", sku=escape(product.sku)))
    lines.append(t("product_price", price=format_money(product.effective_price, currency)))
    if product.has_discount:
        lines.append(t("product_old_price", price=format_money(product.price, currency)))
        lines.append(t("product_discount", percent=product.discount_percent))
    box_price = product.box_price
    if box_price is not None:
        lines.append(
            t(
                "product_box",
                count=product.box_size,
                unit=unit_label(t, product.unit),
                price=format_money(box_price, currency),
            )
        )
    if show_stock:
        if not product.in_stock:
            lines.append(t("product_out_of_stock"))
        else:
            lines.append(
                t("product_stock", quantity=quantity_label(t, product.stock, product.unit))
            )
            if product.is_low_stock:
                lines.append(t("product_low_stock"))
    description = product.localized_description(lang)
    if description:
        lines.append("")
        lines.append(escape(truncate(description, 400)))
    return "\n".join(lines)


def product_button_label(product: Product, lang: str, currency: str) -> str:
    """Inline tugma uchun qisqa nom: 'Guruch — 25 000 so'm'."""
    return f"{product.localized_name(lang)} — {format_money(product.effective_price, currency)}"


# ------------------------- Savat ---------------------------------------
def cart_item_line(t: T, index: int, item: CartItem, lang: str, currency: str) -> str:
    product = item.product
    name = product.localized_name(lang) if product is not None else "—"
    unit = product.unit if product is not None else Unit.PCS
    price = product.effective_price if product is not None else 0
    return t(
        "cart_item",
        index=index,
        name=escape(name),
        quantity=quantity_label(t, item.quantity, unit),
        price=format_money(price, currency),
        total=format_money(price * item.quantity, currency),
    )


def order_item_line(t: T, item: OrderItem, currency: str) -> str:
    return t(
        "order_item_line",
        name=escape(item.name),
        quantity=quantity_label(t, item.quantity, item.unit),
        price=format_money(item.unit_price, currency),
        total=format_money(item.total, currency),
    )


def discount_line(t: T, discount: object, currency: str) -> str:
    """Chegirma bo'lsa - qator, aks holda bo'sh satr."""
    if to_decimal(discount) <= 0:
        return ""
    return t("cart_discount_line", discount=format_money(discount, currency))


# ------------------------- Buyurtma ------------------------------------
def order_summary_line(t: T, order: Order, currency: str, *, index: int | None = None) -> str:
    """Buyurtmalar ro'yxatidagi qator."""
    return t(
        "orders_item",
        index=index if index is not None else "",
        number=escape(order.number),
        status=status_label(t, order.status),
        date=format_datetime(order.created_at),
        total=format_money(order.total, currency),
    )


def order_caption(t: T, order: Order, currency: str, *, with_items: bool = True) -> str:
    """Mijoz uchun buyurtma kartochkasi."""
    lines = [t("order_title", number=escape(order.number))]
    lines.append(
        t(
            "order_info",
            date=format_datetime(order.created_at),
            status=status_label(t, order.status),
            total=format_money(order.total, currency),
            payment=payment_label(t, order.payment_method),
            payment_status=payment_status_label(t, order.payment_status),
        )
    )
    lines.append(
        t(
            "order_delivery_info",
            delivery_type=delivery_label(t, order.delivery_type),
            address=escape(order.address or t("profile_unknown")),
            time=escape(order.delivery_time or t("profile_unknown")),
        )
    )
    if with_items and order.items:
        lines.append("")
        lines.append(t("order_items_title"))
        for item in order.items:
            lines.append(order_item_line(t, item, currency))
    if order.comment:
        lines.append("")
        lines.append(t("order_comment", comment=escape(truncate(order.comment, 300))))
    return "\n".join(lines)


def staff_order_caption(t: T, order: Order, currency: str) -> str:
    """Xodim uchun qisqa buyurtma kartochkasi."""
    customer = order.customer_name or (order.user.display_name if order.user else None)
    return t(
        "admin_order_caption",
        number=escape(order.number),
        status=status_label(t, order.status),
        customer=escape(customer or t("profile_unknown")),
        phone=escape(order.customer_phone or t("profile_unknown")),
        total=format_money(order.total, currency),
        payment=payment_label(t, order.payment_method),
        date=format_datetime(order.created_at),
        source=source_label(t, order.source),
    )


def order_history_line(t: T, entry) -> str:
    return t(
        "order_history_line",
        date=format_datetime(entry.created_at),
        status=status_label(t, entry.to_status),
    )


# ------------------------- Qo'llab-quvvatlash / xodimlar ----------------
def support_line(t: T, request: SupportRequest) -> str:
    user = request.user
    name = user.display_name if user is not None else t("profile_unknown")
    phone = (user.phone if user is not None else None) or t("profile_unknown")
    return t(
        "admin_support_line",
        id=request.id,
        date=format_datetime(request.created_at),
        user=escape(name),
        phone=escape(phone),
        message=escape(truncate(request.message, 600)),
    )


def staff_line(t: T, user: User) -> str:
    return f"• {escape(user.display_name)} — {role_label(t, user.role)} ({user.telegram_id})"


def low_stock_line(t: T, product: Product, lang: str) -> str:
    return t(
        "admin_low_stock_line",
        name=escape(product.localized_name(lang)),
        stock=format_number(product.stock),
        min_stock=format_number(product.min_stock),
    )


__all__ = [
    "T",
    "cart_item_line",
    "delivery_label",
    "discount_line",
    "low_stock_line",
    "order_caption",
    "order_history_line",
    "order_item_line",
    "order_summary_line",
    "payment_label",
    "payment_status_label",
    "product_button_label",
    "product_caption",
    "quantity_label",
    "role_label",
    "segment_label",
    "source_label",
    "staff_line",
    "staff_order_caption",
    "status_label",
    "support_line",
    "unit_label",
]


