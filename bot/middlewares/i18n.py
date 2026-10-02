"""Til (i18n) middleware'i.

Til quyidagi tartibda aniqlanadi:
    1. bazadagi foydalanuvchi tili (UserContextMiddleware o'rnatadi),
    2. Telegram profili (`language_code`),
    3. `DEFAULT_LANGUAGE` sozlamasi.

`data` ichiga quyidagilar yoziladi:
    data["lang"]         - tanlangan til kodi ("uz" / "ru")
    data["t"]            - shu tilga bog'langan tarjima funksiyasi
    data["telegram_lang"]- Telegram profilidan olingan til
"""

from __future__ import annotations

import logging
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.config import Settings
from bot.locales import has_language, normalize_language, translate, translator
from bot.middlewares.common import Handler, event_user

logger = logging.getLogger(__name__)


def resolve_language(language: str | None, fallback: str | None = None) -> str:
    """Tilni aniqlaydi; noto'g'ri yoki bo'sh qiymatda standart tilga qaytadi."""
    if has_language(language):
        return normalize_language(language)
    if has_language(fallback):
        return normalize_language(fallback)
    return normalize_language(None)


class I18nMiddleware(BaseMiddleware):
    """`data["lang"]` va `data["t"]` ni to'ldiradi."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def __call__(
        self,
        handler: Handler,
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = event_user(event)
        telegram_language = resolve_language(
            getattr(user, "language_code", None), self.settings.default_language
        )
        data["telegram_lang"] = telegram_language
        language = data.get("lang")
        if not has_language(language):
            language = telegram_language
        data["lang"] = language
        data["t"] = translator(language)
        return await handler(event, data)


def language_of(data: dict[str, Any], key: str = "lang") -> str:
    """`data` ichidagi tilni xavfsiz o'qiydi (standart - o'zbekcha)."""
    return resolve_language(data.get(key))


def text_of(key: str, data: dict[str, Any], **kwargs: object) -> str:
    """`data` dagi tilga mos matnni qaytaradi."""
    return translate(key, language_of(data), **kwargs)


__all__ = [
    "I18nMiddleware",
    "language_of",
    "resolve_language",
    "text_of",
]
