"""Qo'llab-quvvatlash bo'limi (TZ 4.4).

Mijoz «☎️ Yordam» tugmasi yoki inline menyu (`MenuCB(action="support")`)
orqali kiradi va ikkita imkoniyatga ega:

    * ✍️ operatorga yozish - matn `SupportStates.message` holatida olinadi,
      servis orqali saqlanadi va xodimlarga bildirishnoma yuboriladi;
    * 📞 qo'llab-quvvatlash raqami - sozlamalardan olinadi (`settings`).

Raqam kiritilmagan bo'lsa «call» tugmasi umuman ko'rsatilmaydi.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.handlers.common import TARGET, menu_markup, menu_text, restore_menu
from bot.handlers.states import SupportStates
from bot.keyboards import (
    MenuCB,
    SupportCB,
    cancel_keyboard,
    main_menu_only,
    reply_button_filter,
    support_inline,
)
from bot.middlewares import BotContext
from bot.services import ServiceError
from bot.utils.rendering import answer_callback, render
from bot.utils.text import escape
from bot.utils.validators import normalize_text

logger = logging.getLogger(__name__)


# ------------------------- Yordamchilar -------------------------------
async def _support_phone(ctx: BotContext) -> str | None:
    """Sozlamalardagi qo'llab-quvvatlash raqami (bo'lmasa - `None`)."""
    info = await ctx.settings_service.info()
    phone = (info.get("support_phone") or "").strip()
    if not phone or phone == ctx.t("profile_unknown"):
        return None
    return phone


# ------------------------- Ekranlar ------------------------------------
async def show_menu(target: TARGET, ctx: BotContext) -> None:
    """«☎️ Yordam» menyusi."""
    phone = await _support_phone(ctx)
    await render(
        target, ctx.t("support_menu"), support_inline(ctx.t, phone_available=phone is not None)
    )


async def show_call(target: TARGET, ctx: BotContext) -> None:
    """«📞 Qo'ng'iroq qilish» - raqamni ko'rsatadi."""
    phone = await _support_phone(ctx)
    if phone is None:
        await render(target, ctx.t("support_call_missing"), main_menu_only(ctx.t))
        return
    await render(
        target, ctx.t("support_call_info", phone=escape(phone)), main_menu_only(ctx.t)
    )


async def ask_message(target: TARGET, ctx: BotContext, state: FSMContext) -> None:
    """Murojaat matnini kutish holatini o'rnatadi."""
    await state.set_state(SupportStates.message)
    prompt = ctx.t("support_ask")
    markup = cancel_keyboard(ctx.t)
    if isinstance(target, Message):
        await target.answer(prompt, reply_markup=markup)
        return
    if target.message is not None:  # callback xabari mavjud bo'lsa
        await target.message.answer(prompt, reply_markup=markup)


# ------------------------- Kirish nuqtalari ----------------------------
async def open_support(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """«☎️ Yordam» reply tugmasi."""
    await state.clear()
    await show_menu(message, ctx)


async def on_menu_support(query: CallbackQuery, ctx: BotContext, state: FSMContext) -> None:
    """Inline menyudan «Yordam» (`MenuCB`)."""
    await state.clear()
    await answer_callback(query)
    await show_menu(query, ctx)


async def on_support(
    query: CallbackQuery, ctx: BotContext, callback_data: SupportCB, state: FSMContext
) -> None:
    """Qo'llab-quvvatlash tugmalari."""
    action = callback_data.action
    if action == "write":
        await answer_callback(query)
        await ask_message(query, ctx, state)
        return
    if action == "call":
        await answer_callback(query)
        await show_call(query, ctx)
        return
    await answer_callback(query)
    await show_menu(query, ctx)


async def on_support_text(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """Murojaat matni kiritildi: saqlanadi va xodimlarga yuboriladi."""
    text = normalize_text(message.text, max_length=1000)
    try:
        request = await ctx.support.create(ctx.user, text)
    except ServiceError as error:
        await message.answer(ctx.error_text(error), reply_markup=menu_markup(ctx))
        return
    await state.clear()
    await ctx.notifications.support_created(request)
    await message.answer(
        ctx.t("support_sent", id=request.id), reply_markup=menu_markup(ctx)
    )
    logger.info("Yangi murojaat: #%s (user=%s)", request.id, ctx.user_id)


async def cancel_support(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """«❌ Bekor qilish» - murojaat yozish to'xtatiladi."""
    await state.clear()
    await restore_menu(message, ctx)


def build_router() -> Router:
    """Yangi `support` router yasaydi."""
    router = Router(name="support")

    router.message.register(open_support, reply_button_filter("btn_support"))

    router.callback_query.register(on_menu_support, MenuCB.filter(F.action == "support"))
    router.callback_query.register(on_support, SupportCB.filter())

    router.message.register(
        cancel_support, StateFilter(SupportStates.message), reply_button_filter("btn_cancel")
    )
    router.message.register(
        on_support_text, StateFilter(SupportStates.message), F.text, menu_text
    )
    return router


__all__ = [
    "ask_message",
    "build_router",
    "cancel_support",
    "on_menu_support",
    "open_support",
    "show_call",
    "show_menu",
]
