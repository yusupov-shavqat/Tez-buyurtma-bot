"""Boshlash, til tanlash va asosiy menyu handler'lari.

Handler'lar `BotContext` (`BotContextMiddleware` tayyorlaydi) orqali ishlaydi::

    async def handler(message: Message, ctx: BotContext) -> None:
        await message.answer(ctx.t("cart_empty"))

`start` router'i birinchi bo'lib ulanadi, chunki /start, til tanlash va
telefon raqami - barcha bo'limlar uchun umumiy kirish nuqtasi.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Contact, Message, ReplyKeyboardMarkup

from bot.database.enums import Language
from bot.database.repositories.users import UserRepository
from bot.handlers.common import menu_text
from bot.handlers.states import StartStates
from bot.keyboards import (
    LangCB,
    MenuCB,
    language_inline,
    main_menu,
    phone_request,
    reply_button_filter,
)
from bot.locales import normalize_language
from bot.middlewares import BotContext
from bot.services.presenters import role_label
from bot.utils.rendering import answer_callback, render
from bot.utils.text import escape
from bot.utils.validators import is_valid_phone, normalize_phone

logger = logging.getLogger(__name__)


# ------------------------- ichki yordamchilar --------------------------
def _greeting(ctx: BotContext) -> str:
    """Salomlashish matni: yangi mijozga brend, tanishga ism bilan."""
    user = ctx.user
    if user is not None and user.has_phone:
        return ctx.t("welcome_back", name=escape(user.display_name))
    return ctx.t("start_welcome", brand=escape(ctx.settings.brand_name))


def _menu_markup(ctx: BotContext) -> ReplyKeyboardMarkup:
    """Foydalanuvchi roli hisobga olingan asosiy menyu."""
    return main_menu(ctx.t, is_staff=ctx.is_staff)


async def _open_menu(
    message: Message, ctx: BotContext, state: FSMContext | None = None, *, ask_phone: bool = False
) -> None:
    """Asosiy menyuni ko'rsatadi.

    :param state: berilgan bo'lsa FSM holati ham yangilanadi (raqam bor
        bo'lsa tozalanadi, `ask_phone=True` bo'lsa kutish holati o'rnatiladi).
    :param ask_phone: raqam yo'q bo'lsa uni so'rash kerakmi (`/start` da True,
        menyuga qaytishda esa False - foydalanuvchini bezovta qilmaslik uchun).
    """
    user = ctx.user
    await message.answer(_greeting(ctx), reply_markup=_menu_markup(ctx))
    if ctx.is_staff and user is not None:
        await message.answer(
            ctx.t("admin_welcome_staff", role=role_label(ctx.t, user.role))
        )
    if user is not None and user.has_phone:
        if state is not None:
            await state.clear()
        return
    if not ask_phone:
        return
    if state is not None:
        await state.set_state(StartStates.waiting_phone)
    await message.answer(
        ctx.t("start_ask_phone"), reply_markup=phone_request(ctx.t, with_cancel=True)
    )


async def _save_phone(
    message: Message, ctx: BotContext, phone: str, state: FSMContext
) -> None:
    """Raqamni bazaga yozadi va menyuga qaytaradi."""
    if ctx.user is not None:
        await UserRepository(ctx.session).set_phone(ctx.user, phone)
    await state.clear()
    await message.answer(
        ctx.t("phone_received", phone=escape(phone)), reply_markup=_menu_markup(ctx)
    )


# ------------------------- buyruqlar -----------------------------------
async def cmd_start(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """«/start» - mijozni tanish, menyu va (kerak bo'lsa) raqam so'rash."""
    await _open_menu(message, ctx, state, ask_phone=True)


async def cmd_menu(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """«/menu» - asosiy menyuni qayta ochadi."""
    await _open_menu(message, ctx, state)


async def reply_main_menu(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """«🏠 Asosiy menyu» tugmasi."""
    await _open_menu(message, ctx, state)


async def cmd_help(message: Message, ctx: BotContext) -> None:
    """«/help» - botdan foydalanish bo'yicha qisqa ma'lumot."""
    await message.answer(ctx.t("help_text"), reply_markup=_menu_markup(ctx))


async def cmd_myid(message: Message, ctx: BotContext) -> None:
    """«/myid» - Telegram ID (operator/admin uchun foydali)."""
    await message.answer(ctx.t("my_id", id=ctx.user_id or 0))


async def cmd_cancel(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """«/cancel» - joriy qadamni to'xtatib menyuga qaytaradi."""
    await state.clear()
    await _open_menu(message, ctx, state)


# ------------------------- til tanlash ---------------------------------
async def on_main_menu(query: CallbackQuery, ctx: BotContext, state: FSMContext) -> None:
    """Inline menyudagi «🏠 Asosiy menyu» tugmasi (`MenuCB(action="main")`).

    Barcha inline ekranlarda (katalog, savat, profil, panel) shu tugma bor,
    shu sababli u asosiy menyuni qayta ochadi va inline klaviaturani olib
    tashlaydi.
    """
    await state.clear()
    await answer_callback(query)
    # Tahrirlash orqali inline klaviatura olib tashlanadi, pastki menyu esa
    # yangi xabar bilan yangilanadi (`on_language` bilan bir xil usul).
    await render(query, _greeting(ctx))
    if query.message is not None:
        await query.message.answer(
            ctx.t("start_menu_hint"), reply_markup=_menu_markup(ctx)
        )


async def cmd_language(message: Message, ctx: BotContext) -> None:
    """«/language» - til tanlash klaviaturasi."""
    await message.answer(
        ctx.t("start_language_title"), reply_markup=language_inline(ctx.t, with_cancel=True)
    )


async def on_language(
    query: CallbackQuery, callback_data: LangCB, ctx: BotContext, state: FSMContext
) -> None:
    """Til tugmasi bosildi: tilni bazaga yozadi va menyuni yangilaydi."""
    code = normalize_language(callback_data.code)
    if ctx.user is not None:
        await UserRepository(ctx.session).set_language(ctx.user, Language(code))
    ctx.language = code
    await state.clear()

    t = ctx.t
    await answer_callback(query, t("lang_changed", language=t("lang_name")))
    # Xabarni tahrirlash orqali faqat inline klaviatura olib tashlanadi,
    # pastki (reply) klaviatura esa yangi xabar bilan o'zgartiriladi.
    await render(query, _greeting(ctx))
    if query.message is not None:
        await query.message.answer(
            ctx.t("start_menu_hint"), reply_markup=_menu_markup(ctx)
        )
    logger.info("Til o'zgartirildi: user=%s -> %s", ctx.user_id, code)


# ------------------------- telefon raqami ------------------------------
async def on_contact(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """«📱 Raqamni ulashish» tugmasi orqali kelgan kontakt."""
    contact: Contact | None = message.contact
    if contact is None:  # nazariy holat
        return
    if (
        contact.user_id is not None
        and ctx.user_id is not None
        and contact.user_id != ctx.user_id
    ):
        await message.answer(ctx.t("phone_wrong_owner"), reply_markup=_menu_markup(ctx))
        return
    await _save_phone(message, ctx, normalize_phone(contact.phone_number), state)


async def cancel_phone(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """«❌ Bekor qilish» - raqam so'rashni to'xtatadi (menyu ochiq qoladi)."""
    await state.clear()
    await _open_menu(message, ctx, state)


async def on_phone_text(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """Raqam qo'lda yozilganda.

    Menyu tugmalari bu handler'ga yetib kelmaydi (`menu_text` filtri):
    tugma bosilsa o'sha bo'limning handler'i ishlaydi va holatni tozalaydi.
    """
    text = (message.text or "").strip()
    if not is_valid_phone(text):
        await message.answer(
            ctx.t("phone_invalid"), reply_markup=phone_request(ctx.t, with_cancel=True)
        )
        return
    await _save_phone(message, ctx, normalize_phone(text), state)


def build_router() -> Router:
    """Yangi `start` router yasaydi.

    Ro'yxatdan o'tkazish tartibi muhim: avval buyruqlar va menyu tugmalari,
    oxirida esa «telefon kutish» holatidagi umumiy matn handler'i turadi.
    """
    router = Router(name="start")

    # Buyruqlar va menyu tugmalari
    router.message.register(cmd_start, CommandStart())
    router.message.register(cmd_menu, Command("menu"))
    router.message.register(reply_main_menu, reply_button_filter("btn_main_menu"))
    router.message.register(cmd_help, Command("help"))
    router.message.register(cmd_myid, Command("myid"))
    router.message.register(cmd_cancel, Command("cancel"))
    router.message.register(cmd_language, Command("language"))

    # Til tanlash va inline «🏠 Asosiy menyu» (barcha inline ekranlarda bor)
    router.callback_query.register(on_main_menu, MenuCB.filter(F.action == "main"))
    router.callback_query.register(on_language, LangCB.filter(F.action == "set"))

    # Telefon raqami (faqat ro'yxatdan o'tish holatida - profil va
    # boshqa bo'limlarda raqamni o'z handler'lari qabul qiladi)
    router.message.register(on_contact, StateFilter(StartStates.waiting_phone), F.contact)
    router.message.register(
        cancel_phone,
        StateFilter(StartStates.waiting_phone),
        reply_button_filter("btn_cancel"),
    )
    router.message.register(
        on_phone_text, StateFilter(StartStates.waiting_phone), F.text, menu_text
    )
    return router


__all__ = [
    "build_router",
    "on_main_menu",
]


