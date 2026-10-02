"""Xodimlar (boshqaruv) paneli uchun inline klaviaturalar.

Panel «🛠 Boshqaruv» reply tugmasi orqali ochiladi, qolgan navigatsiya
butunlay inline (`AdminCB`) orqali amalga oshiriladi.
"""

from __future__ import annotations

from typing import Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.database.enums import OrderStatus
from bot.database.models import Order, SupportRequest
from bot.keyboards.callbacks import AdminCB
from bot.keyboards.inline import (
    button,
    keyboard,
    main_menu_row,
    nav_row,
    pagination_row,
)
from bot.locales import TranslateFn
from bot.services.presenters import status_label
from bot.utils.money import format_money
from bot.utils.pagination import Pagination
from bot.utils.text import truncate

#: Holat tugmalari qatoridagi tugmalar soni.
STATUS_COLUMNS = 2


def back_row_menu(t: TranslateFn) -> list[InlineKeyboardButton]:
    """«⬅️ Orqaga» + «🏠 Asosiy menyu» qatori."""
    return nav_row(t, AdminCB(action="menu"))


def staff_menu_inline(
    t: TranslateFn, *, new_orders: int = 0, open_requests: int = 0
) -> InlineKeyboardMarkup:
    """Boshqaruv panelining asosiy menyusi."""
    return keyboard(
        [
            [
                button(t("btn_admin_stats"), AdminCB(action="stats")),
                button(
                    t("btn_admin_new_orders", count=new_orders),
                    AdminCB(action="new_orders"),
                ),
            ],
            [
                button(t("btn_admin_active_orders"), AdminCB(action="active_orders")),
                button(t("btn_admin_search_order"), AdminCB(action="search")),
            ],
            [
                button(t("btn_admin_low_stock"), AdminCB(action="low_stock")),
                button(
                    t("btn_admin_support", count=open_requests),
                    AdminCB(action="support"),
                ),
            ],
            main_menu_row(t),
        ]
    )



def staff_orders_inline(
    t: TranslateFn,
    orders: Sequence[Order],
    pagination: Pagination,
    *,
    currency: str = "so'm",
    list_action: str = "new_orders",
) -> InlineKeyboardMarkup:
    """Xodim uchun buyurtmalar ro'yxati (holat va summa bilan)."""
    rows: list[list[InlineKeyboardButton]] = [
        [
            button(
                truncate(
                    f"{order.number} — {format_money(order.total, currency)} — "
                    f"{status_label(t, order.status)}",
                    60,
                ),
                AdminCB(action="order", order_id=order.id, value=list_action),
            )
        ]
        for order in orders
    ]
    rows.append(
        pagination_row(
            t,
            pagination,
            prev_cb=AdminCB(action=list_action, page=pagination.prev_page),
            next_cb=AdminCB(action=list_action, page=pagination.next_page),
        )
    )
    rows.append(back_row_menu(t))
    return keyboard(rows)


def staff_order_inline(
    t: TranslateFn, order: Order, *, list_action: str = "new_orders"
) -> InlineKeyboardMarkup:
    """Xodim uchun buyurtma kartochkasi tugmalari."""
    return keyboard(
        [
            [
                button(
                    t("btn_admin_change_status"),
                    AdminCB(action="status", order_id=order.id, value=list_action),
                )
            ],
            [
                button(
                    t("btn_admin_reply", id=order.id),
                    AdminCB(action="reply", order_id=order.id),
                )
            ],
            back_row_menu(t),
        ]
    )


def staff_status_inline(
    t: TranslateFn,
    order: Order,
    transitions: Sequence[OrderStatus],
    *,
    list_action: str = "new_orders",
) -> InlineKeyboardMarkup:
    """Ruxsat etilgan holat o'tishlari (zanjir bo'yicha)."""
    rows: list[list[InlineKeyboardButton]] = []
    current: list[InlineKeyboardButton] = []
    for status in transitions:
        current.append(
            button(
                status_label(t, status),
                AdminCB(
                    action="status_set",
                    order_id=order.id,
                    value=status.value,
                ),
            )
        )
        if len(current) == STATUS_COLUMNS:
            rows.append(current)
            current = []
    if current:
        rows.append(current)
    rows.append(
        [
            button(
                t("btn_back"),
                AdminCB(action="order", order_id=order.id, value=list_action),
            )
        ]
    )
    rows.append(back_row_menu(t))
    return keyboard(rows)


def staff_support_inline(
    t: TranslateFn,
    requests: Sequence[SupportRequest],
    pagination: Pagination,
    *,
    list_action: str = "support",
) -> InlineKeyboardMarkup:
    """Qo'llab-quvvatlash so'rovlari: har biriga javob tugmasi."""
    rows: list[list[InlineKeyboardButton]] = [
        [
            button(
                t("btn_admin_reply", id=request.id),
                AdminCB(action="reply", request_id=request.id),
            )
        ]
        for request in requests
    ]
    rows.append(
        pagination_row(
            t,
            pagination,
            prev_cb=AdminCB(action=list_action, page=pagination.prev_page),
            next_cb=AdminCB(action=list_action, page=pagination.next_page),
        )
    )
    rows.append(back_row_menu(t))
    return keyboard(rows)


def staff_text_inline(t: TranslateFn) -> InlineKeyboardMarkup:
    """Faqat matndan iborat ekranlar (statistika, qoldiq) uchun klaviatura."""
    return keyboard([back_row_menu(t)])


def staff_cancel_inline(t: TranslateFn) -> InlineKeyboardMarkup:
    """Matn kiritish (qidiruv/javob) jarayonini bekor qilish."""
    return keyboard([[button(t("btn_cancel"), AdminCB(action="menu"))]])


__all__ = [
    "STATUS_COLUMNS",
    "back_row_menu",
    "staff_cancel_inline",
    "staff_menu_inline",
    "staff_order_inline",
    "staff_orders_inline",
    "staff_status_inline",
    "staff_support_inline",
    "staff_text_inline",
]
