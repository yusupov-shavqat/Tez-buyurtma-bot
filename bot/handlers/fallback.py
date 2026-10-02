"""Zaxira (fallback) handler'lar.

Router eng oxirida ulanadi - shu sababli u «qolgan hamma narsani» qabul
qiladi va foydalanuvchini asosiy menyuga qaytaradi.
"""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import CallbackQuery, Message

from bot.keyboards import main_menu
from bot.middlewares import BotContext
from bot.utils.rendering import answer_callback

logger = logging.getLogger(__name__)


async def unknown_callback(query: CallbackQuery, ctx: BotContext) -> None:
    """Eski yoki noma'lum inline tugma - «yuklanmoqda» belgisini o'chiradi."""
    logger.debug("Noma'lum callback: %r (user=%s)", query.data, ctx.user_id)
    await answer_callback(query, ctx.t("unknown_message"))


async def unknown_message(message: Message, ctx: BotContext) -> None:
    """Boshqa turdagi xabarlar - foydalanuvchini menyuga qaytaradi."""
    logger.debug("Noma'lum xabar turi: %s (user=%s)", message.content_type, ctx.user_id)
    await message.answer(
        ctx.t("unknown_message"),
        reply_markup=main_menu(ctx.t, is_staff=ctx.is_staff),
    )


def build_router() -> Router:
    """Yangi fallback router yasaydi (har bir dispatcher uchun alohida nusxa)."""
    router = Router(name="fallback")
    router.callback_query.register(unknown_callback)
    router.message.register(unknown_message)
    return router


__all__ = ["build_router", "unknown_callback", "unknown_message"]
