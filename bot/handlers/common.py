"""Handler'lar uchun umumiy yordamchilar.

Handler'lar bir xil kodni takrorlamasligi uchun:

    * ``menu_markup`` / ``restore_menu`` - asosiy menyu reply klaviaturasi;
    * ``cart_text`` / ``cart_screen`` / ``show_cart`` - savat ekrani;
    * ``menu_text`` - menyu tugmasi yoki buyruq bo'lmagan matn filtri
      (FSM qadamlarida tugma bosilishi matn sifatida qabul qilinmasligi uchun);
    * ``ask_phone`` - raqam bo'lmasa uni so'rash.
"""

from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message, ReplyKeyboardMarkup

from bot.handlers.states import StartStates
from bot.keyboards import (
    MAIN_MENU_ROWS,
    STAFF_ROW,
    button_texts,
    cart_inline,
    empty_cart_inline,
    main_menu,
    phone_request,
)
from bot.middlewares import BotContext
from bot.services import CartSummary
from bot.services.presenters import cart_item_line, discount_line
from bot.utils.money import format_money
from bot.utils.rendering import render

TARGET = Message | CallbackQuery

#: FSM qadamlarida ham menyuga chiqish mumkin bo'lgan tugmalar.
MENU_BUTTON_KEYS: tuple[str, ...] = (
    tuple(key for row in MAIN_MENU_ROWS for key in row)
    + STAFF_ROW
    + ("btn_main_menu", "btn_cancel", "btn_skip", "btn_share_phone", "btn_send_location")
)


def _menu_button_texts() -> frozenset[str]:
    """Barcha tillardagi menyu tugmalari matnlari (kichik harflarda)."""
    texts: set[str] = set()
    for key in MENU_BUTTON_KEYS:
        texts.update(text.casefold() for text in button_texts(key))
    return frozenset(texts)


MENU_BUTTON_TEXTS = _menu_button_texts()


class MenuTextFilter(BaseFilter):
    """Menyu tugmasi yoki buyruq bo'lmagan matnni tanlaydi.

    FSM qadamida (masalan, manzil kiritishda) foydalanuvchi pastdagi menyu
    tugmasini bossa, xabar matn sifatida qabul qilinmaydi - o'sha tugmaning
    bo'limi ishlaydi va holat tozalanadi.
    """

    __slots__ = ()

    async def __call__(self, message: Message) -> bool:
        text = (message.text or "").strip()
        if not text or text.startswith("/"):
            return False
        return text.casefold() not in MENU_BUTTON_TEXTS

    def _signature_to_string(self, *args: object, **kwargs: object) -> str:
        return "MenuTextFilter()"


#: Tayyor filtr nusxasi (router'larda shu nom bilan ishlatiladi).
menu_text = MenuTextFilter()


# ------------------------- Menyu ---------------------------------------
def currency(ctx: BotContext) -> str:
    """Hisob-kitoblarda ishlatiladigan valyuta."""
    return ctx.settings.currency


def menu_markup(ctx: BotContext) -> ReplyKeyboardMarkup:
    """Foydalanuvchi roli hisobga olingan asosiy menyu."""
    return main_menu(ctx.t, is_staff=ctx.is_staff)


async def restore_menu(target: TARGET, ctx: BotContext) -> None:
    """Asosiy menyu reply klaviaturasini qaytaradi (inline ekrandan keyin).

    Reply klaviaturani faqat yangi xabar bilan o'zgartirish mumkin - shu
    sababli qisqa eslatma xabari yuboriladi.
    """
    message = target if isinstance(target, Message) else target.message
    if message is None:  # juda eski callback
        return
    await message.answer(ctx.t("start_menu_hint"), reply_markup=menu_markup(ctx))


async def ask_phone(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """Telefon raqamini so'raydi (buyurtma berishdan oldin majburiy)."""
    await state.set_state(StartStates.waiting_phone)
    await message.answer(
        ctx.t("start_ask_phone"), reply_markup=phone_request(ctx.t, with_cancel=True)
    )


# ------------------------- Savat ---------------------------------------
def cart_text(ctx: BotContext, summary: CartSummary) -> str:
    """Savat ekrani matni: pozitsiyalar + yakuniy hisob-kitob."""
    if summary.is_empty:
        return ctx.t("cart_empty")
    t = ctx.t
    money = ctx.settings.currency
    lines = [t("cart_title", count=summary.positions), ""]
    for index, line in enumerate(summary.lines, start=1):
        lines.append(cart_item_line(t, index, line.item, ctx.language, money))
    lines.append("")
    lines.append(
        t(
            "cart_summary",
            subtotal=format_money(summary.subtotal, money),
            discount=discount_line(t, summary.discount, money),
            delivery=format_money(summary.delivery_fee, money),
            total=format_money(summary.total, money),
        )
    )
    return "\n".join(lines)


async def cart_screen(ctx: BotContext) -> tuple[str, InlineKeyboardMarkup]:
    """Savat ekranining matni va klaviaturasi (kerak bo'lsa yangilangan)."""
    summary = await ctx.cart.summary(ctx.user.id)
    if summary.is_empty:
        return ctx.t("cart_empty"), empty_cart_inline(ctx.t)
    return cart_text(ctx, summary), cart_inline(
        ctx.t, summary, lang=ctx.language, currency=ctx.settings.currency
    )


async def show_cart(target: TARGET, ctx: BotContext) -> None:
    """Savat ekranini ko'rsatadi (callback bo'lsa xabarni tahrirlaydi)."""
    text, markup = await cart_screen(ctx)
    await render(target, text, markup)


__all__ = [
    "MENU_BUTTON_KEYS",
    "MENU_BUTTON_TEXTS",
    "MenuTextFilter",
    "TARGET",
    "ask_phone",
    "cart_screen",
    "cart_text",
    "currency",
    "menu_markup",
    "menu_text",
    "restore_menu",
    "show_cart",
]
