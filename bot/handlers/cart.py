"""Savat: pozitsiyalar, miqdor, tozalash va buyurtmaga o'tish (TZ 4.4).

Savat ekrani `bot.handlers.common.cart_screen()` orqali yasaladi, shuning
uchun katalog (mahsulot qo'shilgandan keyin) va buyurtmalar (takrorlash)
bo'limlari ham aynan shu ko'rinishdan foydalanadi.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.handlers.checkout import begin_checkout
from bot.handlers.common import show_cart
from bot.keyboards import CartCB, MenuCB, reply_button_filter
from bot.middlewares import BotContext
from bot.services import ServiceError
from bot.utils.rendering import answer_callback
from bot.utils.text import escape

logger = logging.getLogger(__name__)


async def _fail(query: CallbackQuery, ctx: BotContext, error: ServiceError) -> None:
    """Savat amalidagi xatoni toast ko'rinishida ko'rsatadi."""
    await answer_callback(query, ctx.error_text(error), alert=True)


# ------------------------- Kirish nuqtalari ----------------------------
async def cmd_cart(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """«/cart» - savatni ochadi."""
    await state.clear()
    await show_cart(message, ctx)


async def open_cart(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """«🛒 Savat» reply tugmasi."""
    await state.clear()
    await show_cart(message, ctx)


async def on_menu_cart(query: CallbackQuery, ctx: BotContext, state: FSMContext) -> None:
    """Inline menyudan «Savat» (`MenuCB`)."""
    await state.clear()
    await answer_callback(query)
    await show_cart(query, ctx)


# ------------------------- Savat amallari ------------------------------
async def on_open(query: CallbackQuery, ctx: BotContext) -> None:
    """Savatni qayta ko'rsatish (eski tugmalar uchun ham)."""
    await answer_callback(query)
    await show_cart(query, ctx)


async def on_increase(query: CallbackQuery, ctx: BotContext, callback_data: CartCB) -> None:
    """«➕» - miqdorni bir qadamga oshiradi."""
    try:
        product = await ctx.catalog.get_product(callback_data.product_id)
        await ctx.cart.increase(ctx.user.id, product)
    except ServiceError as error:
        await _fail(query, ctx, error)
        return
    await answer_callback(query)
    await show_cart(query, ctx)


async def on_decrease(query: CallbackQuery, ctx: BotContext, callback_data: CartCB) -> None:
    """«➖» - miqdorni bir qadamga kamaytiradi."""
    try:
        product = await ctx.catalog.get_product(callback_data.product_id)
        await ctx.cart.decrease(ctx.user.id, product)
    except ServiceError as error:
        await _fail(query, ctx, error)
        return
    await answer_callback(query)
    await show_cart(query, ctx)


async def on_remove(query: CallbackQuery, ctx: BotContext, callback_data: CartCB) -> None:
    """«🗑» - pozitsiyani savatdan olib tashlaydi."""
    try:
        product = await ctx.catalog.get_product(callback_data.product_id)
        await ctx.cart.remove(ctx.user.id, product.id)
    except ServiceError as error:
        await _fail(query, ctx, error)
        return
    name = escape(product.localized_name(ctx.language))
    await answer_callback(query, ctx.t("cart_removed", name=name))
    await show_cart(query, ctx)


async def on_clear(query: CallbackQuery, ctx: BotContext) -> None:
    """«🗑 Savatni tozalash»."""
    await ctx.cart.clear(ctx.user.id)
    await answer_callback(query, ctx.t("cart_cleared"))
    await show_cart(query, ctx)


async def on_checkout(query: CallbackQuery, ctx: BotContext, state: FSMContext) -> None:
    """«🚚 Buyurtma berish» - buyurtma berish oqimini boshlaydi."""
    await begin_checkout(query, ctx, state)


def build_router() -> Router:
    """Yangi `cart` router yasaydi."""
    router = Router(name="cart")

    router.message.register(cmd_cart, Command("cart"))
    router.message.register(open_cart, reply_button_filter("btn_cart"))

    router.callback_query.register(on_menu_cart, MenuCB.filter(F.action == "cart"))
    router.callback_query.register(on_open, CartCB.filter(F.action == "open"))
    router.callback_query.register(on_increase, CartCB.filter(F.action == "inc"))
    router.callback_query.register(on_decrease, CartCB.filter(F.action == "dec"))
    router.callback_query.register(on_remove, CartCB.filter(F.action == "remove"))
    router.callback_query.register(on_clear, CartCB.filter(F.action == "clear"))
    router.callback_query.register(on_checkout, CartCB.filter(F.action == "checkout"))
    return router


__all__ = [
    "build_router",
    "cmd_cart",
    "on_checkout",
    "open_cart",
]
