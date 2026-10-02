"""Ma'lumotlar bazasi sessiyasi middleware'i.

Har bir yangilanish (update) uchun bitta `AsyncSession` ochiladi va
`data["session"]` orqali handler'larga uzatiladi. Handler muvaffaqiyatli
tugasa tranzaksiya commit qilinadi, xato bo'lsa rollback qilinadi.
"""

from __future__ import annotations

import logging
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.middlewares.common import Handler

logger = logging.getLogger(__name__)

SESSION_KEY = "session"


class DbSessionMiddleware(BaseMiddleware):
    """Sessiya ochadi, xato bo'lsa o'zgarishlarni bekor qiladi."""

    def __init__(self, session_pool: async_sessionmaker[AsyncSession]) -> None:
        self.session_pool = session_pool

    async def __call__(
        self,
        handler: Handler,
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self.session_pool() as session:
            data[SESSION_KEY] = session
            try:
                result = await handler(event, data)
            except Exception:
                await session.rollback()
                raise
            await session.commit()
            return result


__all__ = ["SESSION_KEY", "DbSessionMiddleware"]
