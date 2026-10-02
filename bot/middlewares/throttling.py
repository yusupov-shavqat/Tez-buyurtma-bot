"""Tezlikni cheklash (rate limit) middleware'i.

Bir foydalanuvchi ketma-ket juda tez bosgan tugmalarni/to'xtovsiz yuborgan
xabarlarni e'tiborsiz qoldiradi. Ma'lumot xotirada (in-memory) saqlanadi -
bitta bot jarayoni uchun yetarli; bir nechta instance bo'lsa Redis kerak
bo'ladi (TZ 6-bo'lim, kelajakdagi bosqich).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.middlewares.common import Handler, acknowledge_event, event_user

logger = logging.getLogger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """So'rovlar orasidagi minimal intervalni ta'minlaydi."""

    def __init__(self, rate: float, *, max_entries: int = 10_000) -> None:
        self.rate = max(0.0, float(rate or 0.0))
        self.max_entries = max(100, int(max_entries))
        self._last_seen: dict[int, float] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    @property
    def enabled(self) -> bool:
        return self.rate > 0

    def reset(self) -> None:
        """Xotirani tozalash (testlar uchun)."""
        self._last_seen.clear()

    def _prune(self, now: float) -> None:
        ttl = max(self.rate * 10, 60.0)
        self._last_seen = {
            user_id: seen for user_id, seen in self._last_seen.items() if now - seen <= ttl
        }

    async def _is_limited(self, user_id: int, now: float) -> bool:
        async with self._lock:
            last = self._last_seen.get(user_id)
            if last is not None and now - last < self.rate:
                return True
            self._last_seen[user_id] = now
            if len(self._last_seen) > self.max_entries:
                self._prune(now)
            return False

    # ------------------------------------------------------------------
    async def __call__(
        self,
        handler: Handler,
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not self.enabled:
            return await handler(event, data)
        user = event_user(event)
        if user is None:
            return await handler(event, data)
        if await self._is_limited(user.id, time.monotonic()):
            logger.debug("Rate limit: %s", user.id)
            await acknowledge_event(event)
            return None
        return await handler(event, data)


__all__ = ["ThrottlingMiddleware"]
