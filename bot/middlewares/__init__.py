"""Middleware'lar to'plami (TZ 4.4 - handler'lardan oldingi qatlam).

Ulanish tartibi (`register_middlewares`):
    1. ThrottlingMiddleware   - tez-tez kelgan so'rovlarni to'xtatadi;
    2. DbSessionMiddleware    - bitta yangilanish uchun bitta sessiya;
    3. I18nMiddleware         - til va `t()` ni tayyorlaydi;
    4. BotContextMiddleware  - foydalanuvchi + mijoz + servislar (`ctx`).

Handler'lar `BotContext` ni shunday oladi:

    from bot.middlewares import BotContext

    async def handler(message: Message, ctx: BotContext) -> None:
        await message.answer(ctx.t("cart_empty"))
"""

from __future__ import annotations

from aiogram import Dispatcher
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.config import Settings
from bot.middlewares.common import (
    Handler,
    acknowledge_event,
    answer_event,
    event_chat_id,
    event_user,
    inner_event,
)
from bot.middlewares.context import CONTEXT_KEY, BotContext, BotContextMiddleware
from bot.middlewares.db import SESSION_KEY, DbSessionMiddleware
from bot.middlewares.i18n import I18nMiddleware, language_of, resolve_language, text_of
from bot.middlewares.staff import StaffOnlyMiddleware, attach_staff_filter
from bot.middlewares.throttling import ThrottlingMiddleware


def register_middlewares(
    dispatcher: Dispatcher,
    session_pool: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Dispatcher'ga tashqi middleware'larni ketma-ket ulaydi.

    aiogram o'zi `ErrorsMiddleware`, `UserContextMiddleware`,
    `FSMContextMiddleware` larni allaqachon ulagan bo'ladi - shu sababli
    ushbu middleware'lar ro'yxatning oxiriga qo'shiladi.
    """
    dispatcher.update.outer_middleware(ThrottlingMiddleware(settings.rate_limit_seconds))
    dispatcher.update.outer_middleware(DbSessionMiddleware(session_pool))
    dispatcher.update.outer_middleware(I18nMiddleware(settings))
    dispatcher.update.outer_middleware(BotContextMiddleware(settings))


__all__ = [
    "CONTEXT_KEY",
    "SESSION_KEY",
    "BotContext",
    "BotContextMiddleware",
    "DbSessionMiddleware",
    "Handler",
    "I18nMiddleware",
    "StaffOnlyMiddleware",
    "ThrottlingMiddleware",
    "acknowledge_event",
    "answer_event",
    "attach_staff_filter",
    "event_chat_id",
    "event_user",
    "inner_event",
    "language_of",
    "register_middlewares",
    "resolve_language",
    "text_of",
]
