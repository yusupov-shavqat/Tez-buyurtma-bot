"""Middleware'lar uchun umumiy yordamchilar.

Har bir middleware `Update` ham, ichki hodisa (message/callback_query) ham
kelishi mumkin - shu sababli hodisadan foydalanuvchi, chat ID va javob
yuborish uchun bir xil funksiyalar ishlatiladi.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram.exceptions import TelegramAPIError
from aiogram.types import (
    CallbackQuery,
    Message,
    TelegramObject,
    Update,
    User as TelegramUser,
)

from bot.utils.text import strip_html

logger = logging.getLogger(__name__)

#: Middleware ichida chaqiriladigan keyingi handler turi.
Handler = Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]]


def inner_event(event: TelegramObject) -> TelegramObject | None:
    """`Update` berilgan bo'lsa ichidagi hodisani qaytaradi."""
    if not isinstance(event, Update):
        return event
    try:
        return event.event
    except Exception:  # UpdateTypeLookupError - noma'lum turdagi yangilanish
        return None


def event_user(event: TelegramObject) -> TelegramUser | None:
    """Hodisa muallifi (Telegram foydalanuvchisi)."""
    user = getattr(inner_event(event), "from_user", None)
    return user if isinstance(user, TelegramUser) else None


def event_chat_id(event: TelegramObject) -> int | None:
    """Hodisa bo'lib o'tgan chat ID (shaxsiy chat uchun foydalanuvchi ID)."""
    inner = inner_event(event)
    if isinstance(inner, Message):
        return int(inner.chat.id)
    if isinstance(inner, CallbackQuery) and isinstance(inner.message, Message):
        return int(inner.message.chat.id)
    chat = getattr(inner, "chat", None)
    chat_id = getattr(chat, "id", None)
    return int(chat_id) if chat_id is not None else None


async def answer_event(event: TelegramObject, text: str, *, alert: bool = False) -> bool:
    """Foydalanuvchiga qisqa javob yuboradi (xabar yoki callback oynasi).

    Callback (toast/alert) matnida HTML parse qilinmaydi - shu sababli u
    `strip_html()` orqali tozalanadi, oddiy xabarda esa HTML saqlanadi.
    """
    inner = inner_event(event)
    try:
        if isinstance(inner, CallbackQuery):
            await inner.answer(strip_html(text), show_alert=alert)
            return True
        if isinstance(inner, Message):
            await inner.answer(text)
            return True
    except TelegramAPIError as error:  # foydalanuvchi chatni yopgan bo'lishi mumkin
        logger.warning("Javob yuborilmadi: %s", error)
    return False


async def acknowledge_event(event: TelegramObject) -> None:
    """Callback tugmasidagi 'yuklanmoqda' belgisini o'chiradi."""
    inner = inner_event(event)
    if not isinstance(inner, CallbackQuery):
        return
    try:
        await inner.answer()
    except TelegramAPIError as error:
        logger.debug("Callback tasdiqlanmadi: %s", error)


__all__ = [
    "Handler",
    "acknowledge_event",
    "answer_event",
    "event_chat_id",
    "event_user",
    "inner_event",
]
