"""Ko'p tillilik (i18n) moduli.

Ishlatilishi:
    from bot.locales import translate, translator

    translate("cart_empty", lang="ru")
    t = translator("uz")
    t("qty_added", quantity="5 dona")
"""

from __future__ import annotations

from typing import Callable

from bot.locales.ru import MESSAGES as RU_MESSAGES
from bot.locales.uz import MESSAGES as UZ_MESSAGES

TRANSLATIONS: dict[str, dict[str, str]] = {
    "uz": UZ_MESSAGES,
    "ru": RU_MESSAGES,
}

DEFAULT_LANGUAGE = "uz"
FALLBACK_LANGUAGE = "uz"

LANGUAGE_TITLES: dict[str, str] = {
    "uz": "🇺🇿 O'zbekcha",
    "ru": "🇷🇺 Русский",
}

TranslateFn = Callable[..., str]


def available_languages() -> tuple[str, ...]:
    return tuple(TRANSLATIONS)


def normalize_language(language: str | None) -> str:
    """'ru-RU' -> 'ru'; noma'lum til -> standart til."""
    if not language:
        return DEFAULT_LANGUAGE
    code = str(language).strip().lower().replace("_", "-").split("-")[0]
    return code if code in TRANSLATIONS else DEFAULT_LANGUAGE


def has_language(language: str | None) -> bool:
    return bool(language) and str(language).strip().lower().split("-")[0] in TRANSLATIONS


def is_known_key(key: str) -> bool:
    """Barcha tillarda kalit mavjudligini tekshiradi (testlar uchun)."""
    return all(key in messages for messages in TRANSLATIONS.values())


def translate(key: str, lang: str | None = None, **kwargs: object) -> str:
    """Kalit bo'yicha matnni qaytaradi va {param} larni to'ldiradi."""
    language = normalize_language(lang)
    messages = TRANSLATIONS.get(language, {})
    text = messages.get(key)
    if text is None:
        text = TRANSLATIONS[FALLBACK_LANGUAGE].get(key)
    if text is None:
        return key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def translator(lang: str | None) -> TranslateFn:
    """Tilga bog'langan tarjima funksiyasi."""
    language = normalize_language(lang)

    def _t(key: str, **kwargs: object) -> str:
        return translate(key, language, **kwargs)

    return _t


__all__ = [
    "DEFAULT_LANGUAGE",
    "FALLBACK_LANGUAGE",
    "LANGUAGE_TITLES",
    "TRANSLATIONS",
    "TranslateFn",
    "available_languages",
    "has_language",
    "is_known_key",
    "normalize_language",
    "translate",
    "translator",
]
