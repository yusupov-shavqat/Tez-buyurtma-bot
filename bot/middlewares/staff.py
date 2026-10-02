"""Xodimlar uchun filtr middleware'i.

Boshqaruv paneli router'lari shu middleware bilan yopiladi: mijoz
tugmani bossa yoki buyruq yuborsa, amal bajarilmaydi va foydalanuvchi
ogohlantiriladi.
"""

from __future__ import annotations

import logging
from typing import Any

from aiogram import BaseMiddleware, Router
from aiogram.types import TelegramObject

from bot.database.models import User
from bot.locales import translate
from bot.middlewares.common import Handler, answer_event
from bot.middlewares.context import CONTEXT_KEY, BotContext

logger = logging.getLogger(__name__)


class StaffOnlyMiddleware(BaseMiddleware):
    """Faqat xodim rollari uchun ruxsat beradi."""

    def __init__(self, *, alert: bool = True) -> None:
        self.alert = alert

    async def __call__(
        self,
        handler: Handler,
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        ctx: BotContext | None = data.get(CONTEXT_KEY)
        user: User | None = ctx.user if ctx is not None else data.get("user")
        if user is None or not user.is_staff:
            logger.info(
                "Xodim bo'lmagan foydalanuvchi boshqaruvga urindi: %s",
                getattr(user, "telegram_id", None),
            )
            text = (
                ctx.t("admin_staff_only")
                if ctx is not None
                else translate("admin_staff_only", data.get("lang"))
            )
            await answer_event(event, text, alert=self.alert)
            return None
        return await handler(event, data)


def attach_staff_filter(router: Router, *, alert: bool = True) -> Router:
    """Router'ning barcha hodisalariga xodim filtrini o'rnatadi."""
    middleware = StaffOnlyMiddleware(alert=alert)
    for observer in (
        router.message,
        router.callback_query,
        router.inline_query,
        router.edited_message,
    ):
        observer.middleware(middleware)
    return router


__all__ = ["StaffOnlyMiddleware", "attach_staff_filter"]
