"""Mijoz uchun inline klaviaturalar (katalog, savat, buyurtma, profil...).

Barcha funksiyalar birinchi argument sifatida tilga bog'langan `t`
funksiyasini oladi (qarang: `bot.locales.translator`), mahsulot nomlari
uchun esa `lang` kalit so'zi uzatiladi.
"""

from __future__ import annotations

from typing import Iterable, Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.database.enums import PaymentMethod
from bot.database.models import Address, Order, Product
from bot.keyboards.callbacks import (
    CartCB,
    CatalogCB,
    CheckoutCB,
    LangCB,
    MenuCB,
    OrderCB,
    ProductCB,
    ProfileCB,
    SupportCB,
)
from bot.locales import LANGUAGE_TITLES, TranslateFn, available_languages
from bot.services.cart import CartLine, CartSummary
from bot.services.catalog import CategoryCard
from bot.services.presenters import product_button_label, status_label, unit_label
from bot.utils.money import format_money, format_quantity
from bot.utils.pagination import Pagination
from bot.utils.text import truncate

#: Bir sahifada ko'rsatiladigan manzillar soni.
MAX_ADDRESS_BUTTONS = 5

#: Miqdor tanlash tugmalari (o'lchov birligi qadamiga ko'paytiriladi).
QUANTITY_STEPS: tuple[int, ...] = (1, 2, 3, 5, 10)

#: Yetkazish vaqti variantlari: (callback qiymati, tarjima kaliti).
TIME_SLOTS: tuple[tuple[str, str], ...] = (
    ("asap", "btn_time_asap"),
    ("today_am", "btn_time_today_am"),
    ("today_pm", "btn_time_today_pm"),
    ("tomorrow", "btn_time_tomorrow"),
)

#: Kategoriya tugmalari uchun qatordagi tugmalar soni.
CATEGORY_COLUMNS = 2


# ------------------------- Asosiy yordamchilar -------------------------
def button(text: str, callback: object) -> InlineKeyboardButton:
    """Matn + callback data dan tugma yasaydi."""
    pack = getattr(callback, "pack")
    return InlineKeyboardButton(text=text, callback_data=pack())


def keyboard(rows: Iterable[Sequence[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    """Bo'sh qatorlarni tashlab, klaviatura yig'adi."""
    return InlineKeyboardMarkup(inline_keyboard=[list(row) for row in rows if row])


def main_menu_row(t: TranslateFn) -> list[InlineKeyboardButton]:
    return [button(t("btn_main_menu"), MenuCB(action="main"))]


def main_menu_only(t: TranslateFn) -> InlineKeyboardMarkup:
    return keyboard([main_menu_row(t)])


def back_row(t: TranslateFn, callback: object) -> list[InlineKeyboardButton]:
    return [button(t("btn_back"), callback)]


def nav_row(t: TranslateFn, back_cb: object, *, with_main: bool = True) -> list[InlineKeyboardButton]:
    """«Orqaga» (+ «Asosiy menyu») qatori."""
    row = back_row(t, back_cb)
    if with_main:
        row.extend(main_menu_row(t))
    return row


def with_page(callback: object, page: int) -> object:
    """Callback data nusxasini boshqa sahifa bilan qaytaradi.

    Sahifalash tugmalarini yasashda foydalaniladi: agar callback data ichida
    ``page`` maydoni bo'lsa (``CatalogCB``, ``OrderCB``, ``AdminCB``...), u
    yangilanadi, aks holda callback o'zgarishsiz qaytariladi.
    """
    model_copy = getattr(callback, "model_copy", None)
    if model_copy is not None and hasattr(callback, "page"):
        return model_copy(update={"page": page})
    return callback


def pagination_row(
    t: TranslateFn,
    pagination: Pagination,
    *,
    prev_cb: object,
    next_cb: object,
) -> list[InlineKeyboardButton]:
    """Sahifalash qatori (faqat mavjud yo'nalishlar ko'rsatiladi)."""
    row: list[InlineKeyboardButton] = []
    if pagination.has_prev:
        row.append(button(t("btn_prev"), prev_cb))
    if pagination.has_next:
        row.append(button(t("btn_next"), next_cb))
    return row


# ------------------------- Til tanlash --------------------------------
def language_inline(t: TranslateFn, *, with_cancel: bool = False) -> InlineKeyboardMarkup:
    """Til tanlash klaviaturasi (barcha tillar bir qatorda)."""
    row = [
        button(LANGUAGE_TITLES.get(code, code), LangCB(action="set", code=code))
        for code in available_languages()
    ]
    rows: list[list[InlineKeyboardButton]] = [row]
    if with_cancel:
        rows.append(main_menu_row(t))
    return keyboard(rows)


# ------------------------- Katalog ------------------------------------
def categories_inline(
    t: TranslateFn, cards: Sequence[CategoryCard], *, lang: str = "uz"
) -> InlineKeyboardMarkup:
    """Kategoriyalar klaviaturasi: aksiya va qidiruv tugmalari bilan."""
    rows: list[list[InlineKeyboardButton]] = []
    current: list[InlineKeyboardButton] = []
    for card in cards:
        label = card.category.button_label(lang)
        if card.products:
            label = f"{label} ({card.products})"
        current.append(
            button(label, CatalogCB(action="category", category_id=card.category.id))
        )
        if len(current) == CATEGORY_COLUMNS:
            rows.append(current)
            current = []
    if current:
        rows.append(current)
    rows.append(
        [
            button(t("btn_promo"), CatalogCB(action="promo")),
            button(t("btn_search"), CatalogCB(action="search")),
        ]
    )
    rows.append(main_menu_row(t))
    return keyboard(rows)


def products_inline(
    t: TranslateFn,
    products: Sequence[Product],
    pagination: Pagination,
    *,
    back_cb: object,
    lang: str = "uz",
    currency: str = "so'm",
    prev_cb: object | None = None,
    next_cb: object | None = None,
) -> InlineKeyboardMarkup:
    """Mahsulotlar ro'yxati + sahifalash + «Orqaga»."""
    rows: list[list[InlineKeyboardButton]] = [
        [
            button(
                truncate(product_button_label(product, lang, currency), 60),
                ProductCB(action="open", product_id=product.id),
            )
        ]
        for product in products
    ]
    rows.append(
        pagination_row(
            t,
            pagination,
            prev_cb=prev_cb or with_page(back_cb, pagination.prev_page),
            next_cb=next_cb or with_page(back_cb, pagination.next_page),
        )
    )
    rows.append(nav_row(t, back_cb))
    return keyboard(rows)


def product_inline(
    t: TranslateFn, product: Product, *, back_cb: object
) -> InlineKeyboardMarkup:
    """Mahsulot kartochkasi: savatga qo'shish va orqaga."""
    rows: list[list[InlineKeyboardButton]] = []
    if product.in_stock:
        rows.append(
            [
                button(
                    t("btn_add_to_cart"),
                    ProductCB(action="add", product_id=product.id),
                )
            ]
        )
    rows.append(nav_row(t, back_cb))
    return keyboard(rows)


def quantity_inline(
    t: TranslateFn, product: Product, *, back_cb: object | None = None
) -> InlineKeyboardMarkup:
    """Miqdor tanlash: tayyor variantlar + qo'lda kiritish."""
    step = product.step
    rows: list[list[InlineKeyboardButton]] = []
    current: list[InlineKeyboardButton] = []
    for steps in QUANTITY_STEPS:
        current.append(
            button(
                format_quantity(step * steps, unit_label(t, product.unit)),
                ProductCB(action="qty", product_id=product.id, value=steps),
            )
        )
        if len(current) == 3:
            rows.append(current)
            current = []
    if current:
        rows.append(current)
    cancel_cb = back_cb or ProductCB(action="open", product_id=product.id)
    rows.append(
        [
            button(t("btn_other_qty"), ProductCB(action="input", product_id=product.id)),
            button(t("btn_cancel"), cancel_cb),
        ]
    )
    return keyboard(rows)


# ------------------------- Savat --------------------------------------
def cart_inline(
    t: TranslateFn, summary: CartSummary, *, lang: str = "uz", currency: str = "so'm"
) -> InlineKeyboardMarkup:
    """Savat: har bir pozitsiya uchun ➖/➕, tozalash va buyurtma tugmalari."""
    rows: list[list[InlineKeyboardButton]] = [
        _cart_line_row(t, line, lang=lang, currency=currency) for line in summary.lines
    ]
    rows.append([button(t("btn_checkout"), CartCB(action="checkout"))])
    rows.append([button(t("btn_clear_cart"), CartCB(action="clear"))])
    rows.append(main_menu_row(t))
    return keyboard(rows)


def _cart_line_row(
    t: TranslateFn, line: CartLine, *, lang: str, currency: str
) -> list[InlineKeyboardButton]:
    """Bitta savat pozitsiyasi uchun tugmalar qatori.

    Miqdor bitta qadamga teng bo'lsa - «➖» o'rniga «🗑» (o'chirish) ko'rsatiladi.
    """
    product = line.product
    name = truncate(product.localized_name(lang), 22)
    quantity = format_quantity(line.quantity, unit_label(t, product.unit))
    can_remove = line.quantity <= line.step
    return [
        button(
            "🗑" if can_remove else "➖",
            CartCB(
                action="remove" if can_remove else "dec", product_id=product.id
            ),
        ),
        button(
            f"{name} — {quantity}",
            ProductCB(action="open", product_id=product.id),
        ),
        button("➕", CartCB(action="inc", product_id=product.id)),
    ]


def empty_cart_inline(t: TranslateFn) -> InlineKeyboardMarkup:
    """Bo'sh savat uchun klaviatura."""
    return keyboard(
        [
            [button(t("btn_catalog"), CatalogCB(action="categories"))],
            main_menu_row(t),
        ]
    )


# ------------------------- Buyurtma berish ----------------------------
def checkout_delivery_inline(t: TranslateFn) -> InlineKeyboardMarkup:
    """Yetkazish turi tanlash."""
    return keyboard(
        [
            [
                button(t("btn_co_delivery"), CheckoutCB(action="delivery")),
                button(t("btn_co_pickup"), CheckoutCB(action="pickup")),
            ],
            [button(t("btn_cancel"), CheckoutCB(action="cancel"))],
        ]
    )


def checkout_address_inline(
    t: TranslateFn, addresses: Sequence[Address] = ()
) -> InlineKeyboardMarkup:
    """Saqlangan manzillar + yangi manzil kiritish tugmasi."""
    rows: list[list[InlineKeyboardButton]] = []
    for address in list(addresses)[:MAX_ADDRESS_BUTTONS]:
        label = address.label or address.address
        rows.append(
            [
                button(
                    f"📍 {truncate(label, 50)}",
                    CheckoutCB(action="addr", value=str(address.id)),
                )
            ]
        )
    rows.append([button(t("btn_new_address"), CheckoutCB(action="new_address"))])
    rows.append([button(t("btn_cancel"), CheckoutCB(action="cancel"))])
    return keyboard(rows)


def checkout_time_inline(t: TranslateFn) -> InlineKeyboardMarkup:
    """Yetkazish vaqtini tanlash (2 tadan qatorlarga)."""
    rows: list[list[InlineKeyboardButton]] = []
    for index in range(0, len(TIME_SLOTS), 2):
        rows.append(
            [
                button(t(key), CheckoutCB(action="time", value=value))
                for value, key in TIME_SLOTS[index : index + 2]
            ]
        )
    rows.append([button(t("btn_cancel"), CheckoutCB(action="cancel"))])
    return keyboard(rows)


def checkout_comment_inline(t: TranslateFn) -> InlineKeyboardMarkup:
    """Izoh qadamining klaviaturasi."""
    return keyboard(
        [
            [button(t("btn_skip"), CheckoutCB(action="skip"))],
            [button(t("btn_cancel"), CheckoutCB(action="cancel"))],
        ]
    )


def checkout_payment_inline(
    t: TranslateFn, *, online: bool = False
) -> InlineKeyboardMarkup:
    """To'lov usulini tanlash."""
    rows = [
        [
            button(
                t("btn_pay_cash"),
                CheckoutCB(action="payment", value=PaymentMethod.CASH.value),
            )
        ],
        [
            button(
                t("btn_pay_card"),
                CheckoutCB(action="payment", value=PaymentMethod.CARD.value),
            ),
            button(
                t("btn_pay_transfer"),
                CheckoutCB(action="payment", value=PaymentMethod.TRANSFER.value),
            ),
        ],
    ]
    if online:
        rows.append(
            [
                button(
                    t("btn_pay_online"),
                    CheckoutCB(action="payment", value=PaymentMethod.PAYME.value),
                )
            ]
        )
    rows.append([button(t("btn_cancel"), CheckoutCB(action="cancel"))])
    return keyboard(rows)



def checkout_confirm_inline(t: TranslateFn) -> InlineKeyboardMarkup:
    """Buyurtmani tasdiqlash."""
    return keyboard(
        [
            [
                button(t("btn_confirm"), CheckoutCB(action="confirm")),
                button(t("btn_cancel"), CheckoutCB(action="cancel")),
            ],
            [button(t("btn_back"), CheckoutCB(action="back"))],
        ]
    )


# ------------------------- Buyurtmalar --------------------------------
def orders_inline(
    t: TranslateFn,
    orders: Sequence[Order],
    pagination: Pagination,
    *,
    currency: str = "so'm",
) -> InlineKeyboardMarkup:
    """Buyurtmalar ro'yxati + sahifalash + «🏠 Asosiy menyu».

    Ro'yxat bo'limning ildizi (katalog va savat kabi), shuning uchun bu yerda
    «⬅️ Orqaga» tugmasi yo'q - faqat asosiy menyuga qaytish tugmasi qoladi.
    """
    rows: list[list[InlineKeyboardButton]] = [
        [
            button(
                truncate(
                    f"{t('btn_order_detail', number=order.number)} — "
                    f"{format_money(order.total, currency)} — {status_label(t, order.status)}",
                    60,
                ),
                OrderCB(action="detail", order_id=order.id),
            )
        ]
        for order in orders
    ]
    rows.append(
        pagination_row(
            t,
            pagination,
            prev_cb=OrderCB(action="list", page=pagination.prev_page),
            next_cb=OrderCB(action="list", page=pagination.next_page),
        )
    )
    rows.append(main_menu_row(t))
    return keyboard(rows)


def order_detail_inline(
    t: TranslateFn, order: Order, *, back_page: int = 1
) -> InlineKeyboardMarkup:
    """Buyurtma kartochkasi tugmalari."""
    rows: list[list[InlineKeyboardButton]] = []
    if order.is_cancellable:
        rows.append(
            [
                button(
                    t("btn_order_cancel"),
                    OrderCB(action="cancel", order_id=order.id),
                )
            ]
        )
    rows.append(
        [button(t("btn_order_repeat"), OrderCB(action="repeat", order_id=order.id))]
    )
    rows.append(nav_row(t, OrderCB(action="list", page=back_page), with_main=True))
    return keyboard(rows)


def order_cancel_confirm_inline(t: TranslateFn, order: Order) -> InlineKeyboardMarkup:
    """«Bekor qilishni tasdiqlaysizmi?» klaviaturasi."""
    return keyboard(
        [
            [
                button(
                    t("btn_yes"),
                    OrderCB(action="confirm_cancel", order_id=order.id),
                ),
                button(t("btn_no"), OrderCB(action="detail", order_id=order.id)),
            ]
        ]
    )


# ------------------------- Profil -------------------------------------
def profile_inline(t: TranslateFn) -> InlineKeyboardMarkup:
    """Profil bo'limi tugmalari."""
    return keyboard(
        [
            [
                button(t("btn_change_phone"), ProfileCB(action="phone")),
                button(t("btn_change_language"), ProfileCB(action="language")),
            ],
            [button(t("btn_my_addresses"), ProfileCB(action="addresses"))],
            main_menu_row(t),
        ]
    )


def profile_language_inline(t: TranslateFn) -> InlineKeyboardMarkup:
    """Profildan tilni almashtirish."""
    rows = [
        [button(LANGUAGE_TITLES.get(code, code), LangCB(action="set", code=code))]
        for code in available_languages()
    ]
    rows.append(back_row(t, ProfileCB(action="open")))
    return keyboard(rows)


def addresses_inline(t: TranslateFn) -> InlineKeyboardMarkup:
    """Manzillar ro'yxati klaviaturasi."""
    return keyboard([nav_row(t, ProfileCB(action="open"))])


# ------------------------- Qo'llab-quvvatlash -------------------------
def support_inline(t: TranslateFn, *, phone_available: bool = True) -> InlineKeyboardMarkup:
    """Qo'llab-quvvatlash menyusi."""
    row = [button(t("btn_support_write"), SupportCB(action="write"))]
    if phone_available:
        row.append(button(t("btn_support_call"), SupportCB(action="call")))
    return keyboard([row, main_menu_row(t)])


__all__ = [
    "CATEGORY_COLUMNS",
    "MAX_ADDRESS_BUTTONS",
    "QUANTITY_STEPS",
    "TIME_SLOTS",
    "addresses_inline",
    "back_row",
    "button",
    "cart_inline",
    "categories_inline",
    "checkout_address_inline",
    "checkout_comment_inline",
    "checkout_confirm_inline",
    "checkout_delivery_inline",
    "checkout_payment_inline",
    "checkout_time_inline",
    "empty_cart_inline",
    "keyboard",
    "language_inline",
    "main_menu_only",
    "main_menu_row",
    "nav_row",
    "order_cancel_confirm_inline",
    "order_detail_inline",
    "orders_inline",
    "pagination_row",
    "product_inline",
    "products_inline",
    "profile_inline",
    "profile_language_inline",
    "quantity_inline",
    "support_inline",
    "with_page",
]
