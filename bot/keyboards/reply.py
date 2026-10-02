"""Reply (pastki) klaviaturalar.

Tugma matnlari tarjima kalitlaridan olinadi. Handler'lar tilga bog'liq
bo'lmasligi uchun `reply_button_filter("btn_catalog")` yordamchisidan
foydalanadi - u barcha tillardagi variantlarni bitta filtrga birlashtiradi.
"""

from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from bot.locales import TRANSLATIONS, TranslateFn

#: Asosiy menyu tugmalari (tartibi muhim - qatorlarga bo'linadi).
MAIN_MENU_ROWS: tuple[tuple[str, ...], ...] = (
    ("btn_catalog", "btn_cart"),
    ("btn_orders", "btn_profile"),
    ("btn_promo", "btn_support"),
)

#: Xodimlar uchun qo'shimcha qator.
STAFF_ROW: tuple[str, ...] = ("btn_admin",)


def button_texts(key: str) -> tuple[str, ...]:
    """Barcha tillardagi tugma matnlari (takrorlanmagan holda)."""
    texts: list[str] = []
    for messages in TRANSLATIONS.values():
        value = messages.get(key)
        if value and value not in texts:
            texts.append(value)
    return tuple(texts)


class ReplyButtonFilter(BaseFilter):
    """Reply tugma bosilishini barcha tillarda tanib oluvchi filtr.

    Tugma matni tillarga qarab har xil bo'lgani uchun bitta filtrda barcha
    variantlar saqlanadi - handler'lar faqat kalit bilan ishlaydi.
    """

    __slots__ = ("ignore_case", "texts")

    def __init__(self, *texts: str, ignore_case: bool = False) -> None:
        self.ignore_case = ignore_case
        self.texts = frozenset(text.casefold() for text in texts) if ignore_case else frozenset(texts)

    async def __call__(self, message: Message) -> bool:
        text = message.text
        if text is None:
            return False
        return (text.casefold() if self.ignore_case else text) in self.texts

    def _signature_to_string(self, *args: object, **kwargs: object) -> str:
        return f"ReplyButtonFilter({', '.join(sorted(self.texts))}, ignore_case={self.ignore_case})"


def reply_button_filter(key: str, *, ignore_case: bool = False) -> ReplyButtonFilter:
    """Reply tugma bosilishini barcha tillarda tanib oluvchi filtr.

    Ishlatilishi::

        @router.message(reply_button_filter("btn_catalog"))
        async def open_catalog(...): ...
    """
    return ReplyButtonFilter(*button_texts(key), ignore_case=ignore_case)


def _button(text: str) -> KeyboardButton:
    return KeyboardButton(text=text)


def main_menu(
    t: TranslateFn, *, is_staff: bool = False, placeholder: str | None = None
) -> ReplyKeyboardMarkup:
    """Asosiy menyu klaviaturasi (xodimlar uchun qo'shimcha tugma bilan)."""
    rows: list[list[KeyboardButton]] = [
        [_button(t(key)) for key in row] for row in MAIN_MENU_ROWS
    ]
    if is_staff:
        rows.append([_button(t(key)) for key in STAFF_ROW])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder=placeholder or t("start_menu_hint"),
    )


def phone_request(t: TranslateFn, *, with_cancel: bool = False) -> ReplyKeyboardMarkup:
    """Telefon raqamini ulashish klaviaturasi."""
    rows = [[KeyboardButton(text=t("btn_share_phone"), request_contact=True)]]
    if with_cancel:
        rows.append([_button(t("btn_cancel"))])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def location_request(t: TranslateFn, *, with_cancel: bool = True) -> ReplyKeyboardMarkup:
    """Lokatsiya yuborish klaviaturasi (yetkazish manzili uchun)."""
    rows = [[KeyboardButton(text=t("btn_send_location"), request_location=True)]]
    if with_cancel:
        rows.append([_button(t("btn_cancel"))])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def cancel_keyboard(t: TranslateFn) -> ReplyKeyboardMarkup:
    """Faqat «Bekor qilish» tugmasi (FSM qadamlarida)."""
    return ReplyKeyboardMarkup(
        keyboard=[[_button(t("btn_cancel"))]], resize_keyboard=True
    )


def skip_or_cancel(t: TranslateFn) -> ReplyKeyboardMarkup:
    """Izoh qadamida: «O'tkazib yuborish» va «Bekor qilish»."""
    return ReplyKeyboardMarkup(
        keyboard=[[_button(t("btn_skip"))], [_button(t("btn_cancel"))]],
        resize_keyboard=True,
    )


def main_only(t: TranslateFn) -> ReplyKeyboardMarkup:
    """Faqat «Asosiy menyu» tugmasi."""
    return ReplyKeyboardMarkup(
        keyboard=[[_button(t("btn_main_menu"))]], resize_keyboard=True
    )


__all__ = [
    "MAIN_MENU_ROWS",
    "STAFF_ROW",
    "ReplyButtonFilter",
    "button_texts",
    "cancel_keyboard",
    "location_request",
    "main_menu",
    "main_only",
    "phone_request",
    "reply_button_filter",
    "skip_or_cancel",
]
