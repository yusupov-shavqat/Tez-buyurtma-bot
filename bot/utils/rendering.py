"""aiogram xabarlarini ko'rsatish yordamchilari.

Handler'larda bir xil kod takrorlanmasligi uchun: matn/rasm xabarini
qayerga yuborishni (edit / yangi xabar) avtomatik tanlaydi.
"""

from __future__ import annotations

import logging

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message, ReplyKeyboardMarkup

from bot.utils.text import strip_html

logger = logging.getLogger(__name__)

TARGET = Message | CallbackQuery
KEYBOARD = InlineKeyboardMarkup | ReplyKeyboardMarkup | None


async def safe_delete(message: Message | None) -> None:
    """Xabarni o'chirishga urinadi (xato bo'lsa jim o'tadi)."""
    if message is None:
        return
    try:
        await message.delete()
    except (TelegramBadRequest, TelegramForbiddenError):
        logger.debug("Xabarni o'chirib bo'lmadi (ehtimol eski xabar).")


async def render(
    target: TARGET,
    text: str,
    reply_markup: KEYBOARD = None,
    *,
    photo: str | None = None,
) -> Message | None:
    """Xabarni ko'rsatadi: callback bo'lsa - tahrirlaydi, aks holda yangi yuboradi."""
    if isinstance(target, CallbackQuery):
        message = target.message
        if message is None:  # juda eski callback
            return None
        return await _render_from_callback(message, text, reply_markup, photo)
    return await _send(message=target, text=text, reply_markup=reply_markup, photo=photo)


async def _render_from_callback(
    message: Message, text: str, reply_markup: KEYBOARD, photo: str | None
) -> Message | None:
    has_photo = bool(message.photo)
    if photo:
        if has_photo:
            try:
                return await message.edit_caption(caption=text, reply_markup=reply_markup)
            except TelegramBadRequest as exc:
                if "message is not modified" not in str(exc):
                    await safe_delete(message)
                    return await message.answer_photo(
                        photo, caption=text, reply_markup=reply_markup
                    )
                return message
        await safe_delete(message)
        return await message.answer_photo(photo, caption=text, reply_markup=reply_markup)

    if has_photo:
        await safe_delete(message)
        return await message.answer(text, reply_markup=reply_markup)

    try:
        return await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        error = str(exc)
        if "message is not modified" in error:
            return message
        if "there is no text in the message" in error or "no text" in error:
            await safe_delete(message)
            return await message.answer(text, reply_markup=reply_markup)
        logger.debug("edit_text xatosi: %s", error)
        return await message.answer(text, reply_markup=reply_markup)


async def _send(
    message: Message, text: str, reply_markup: KEYBOARD, photo: str | None
) -> Message:
    if photo:
        return await message.answer_photo(photo, caption=text, reply_markup=reply_markup)
    return await message.answer(text, reply_markup=reply_markup)


async def answer_callback(
    callback: CallbackQuery, text: str | None = None, *, alert: bool = False
) -> None:
    """Callback'ga javob (toast/alert) - xato bo'lsa jim o'tadi.

    Telegram toast/alert matnini HTML sifatida parse qilmaydi, shu sababli
    matn `strip_html()` orqali tozalanadi (`<b>` kabi teglar va `&amp;` kabi
    entity'lar foydalanuvchiga ko'rinib qolmasligi uchun). Xabar matnlari
    (`render`) o'zgarishsiz qoladi - ularda HTML kerak.
    """
    try:
        await callback.answer(text=strip_html(text) if text else text, show_alert=alert)
    except TelegramBadRequest:
        logger.debug("callback.answer xatosi")


__all__ = ["answer_callback", "render", "safe_delete"]
