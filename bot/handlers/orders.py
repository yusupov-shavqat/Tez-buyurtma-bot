"""Mijoz buyurtmalari: ro'yxat, kartochka, bekor qilish, takrorlash (TZ 4.4).

Mijoz faqat o'z buyurtmalarini ko'radi (`OrderService.get_for_user`), bekor
qilish esa faqat «Yangi» va «Tasdiqlangan» holatlarida mumkin.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.enums import NotificationKind
from bot.database.models import Order
from bot.handlers.common import TARGET, cart_screen, currency
from bot.keyboards import (
    MenuCB,
    OrderCB,
    main_menu_only,
    order_cancel_confirm_inline,
    order_detail_inline,
    orders_inline,
    reply_button_filter,
)
from bot.middlewares import BotContext
from bot.services import ServiceError
from bot.services.presenters import order_caption, order_history_line
from bot.utils.rendering import answer_callback, render
from bot.utils.text import escape

logger = logging.getLogger(__name__)


async def _order(ctx: BotContext, order_id: int | None) -> Order:
    """Mijozning buyurtmasini oladi (boshqaning buyurtmasi - topilmaydi)."""
    return await ctx.orders.get_for_user(ctx.user.id, order_id)


async def _fail(query: CallbackQuery, ctx: BotContext, error: ServiceError) -> None:
    await answer_callback(query, ctx.error_text(error), alert=True)


# ------------------------- Ekranlar ------------------------------------
async def show_orders(target: TARGET, ctx: BotContext, *, page: int = 1) -> None:
    """«📦 Buyurtmalarim» ro'yxati (sahifalash bilan)."""
    t = ctx.t
    orders, pagination = await ctx.orders.page_for_user(ctx.user.id, page=page)
    if not orders:
        await render(target, t("orders_empty"), main_menu_only(t))
        return
    markup = orders_inline(
        t,
        orders,
        pagination,
        currency=currency(ctx),
    )
    await render(target, t("orders_title", page=pagination.current, pages=pagination.pages), markup)


async def show_order(
    target: TARGET, ctx: BotContext, order: Order, *, back_page: int = 1
) -> None:
    """Buyurtma kartochkasi (tarkibi va holatlar tarixi bilan)."""
    t = ctx.t
    text = order_caption(t, order, currency(ctx))
    history = await ctx.orders.history(order.id)
    if history:
        lines = [order_history_line(t, entry) for entry in history[-5:]]
        text = f"{text}\n\n{t('order_history_title')}\n" + "\n".join(lines)
    await render(target, text, order_detail_inline(t, order, back_page=back_page))


# ------------------------- Kirish nuqtalari ----------------------------
async def cmd_orders(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """«/orders» - buyurtmalar ro'yxati."""
    await state.clear()
    await show_orders(message, ctx)


async def open_orders(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """«📦 Buyurtmalarim» reply tugmasi."""
    await state.clear()
    await show_orders(message, ctx)


async def on_menu_orders(query: CallbackQuery, ctx: BotContext, state: FSMContext) -> None:
    """Inline menyudan «Buyurtmalarim» (`MenuCB`)."""
    await state.clear()
    await answer_callback(query)
    await show_orders(query, ctx)


# ------------------------- Ro'yxat va kartochka ------------------------
async def on_list(query: CallbackQuery, ctx: BotContext, callback_data: OrderCB) -> None:
    """Sahifalash va «⬅️ Orqaga» (ro'yxatga qaytish)."""
    await answer_callback(query)
    await show_orders(query, ctx, page=callback_data.page)


async def on_detail(query: CallbackQuery, ctx: BotContext, callback_data: OrderCB) -> None:
    """Buyurtma kartochkasini ochish."""
    try:
        order = await _order(ctx, callback_data.order_id)
    except ServiceError as error:
        await _fail(query, ctx, error)
        return
    await answer_callback(query)
    await show_order(query, ctx, order, back_page=callback_data.page)


# ------------------------- Bekor qilish --------------------------------
async def on_cancel(query: CallbackQuery, ctx: BotContext, callback_data: OrderCB) -> None:
    """«❌ Buyurtmani bekor qilish» - tasdiqlash so'raladi."""
    try:
        order = await _order(ctx, callback_data.order_id)
    except ServiceError as error:
        await _fail(query, ctx, error)
        return
    await answer_callback(query)
    if not order.is_cancellable:
        await render(query, ctx.t("order_cannot_cancel"), main_menu_only(ctx.t))
        return
    await render(
        query, ctx.t("order_cancel_prompt"), order_cancel_confirm_inline(ctx.t, order)
    )


async def on_confirm_cancel(
    query: CallbackQuery, ctx: BotContext, callback_data: OrderCB
) -> None:
    """Bekor qilishni tasdiqlash: buyurtma bekor qilinadi va xodimlar xabardor."""
    try:
        order = await _order(ctx, callback_data.order_id)
        await ctx.orders.cancel_by_customer(order)
    except ServiceError as error:
        await _fail(query, ctx, error)
        return
    t = ctx.t
    await answer_callback(query, t("order_cancelled", number=order.number))
    await ctx.notifications.notify_staff(
        t(
            "notif_order_cancelled",
            number=escape(order.number),
            reason=escape(order.cancel_reason or t("profile_unknown")),
        ),
        kind=NotificationKind.ORDER_CANCELLED,
        order_id=order.id,
    )
    logger.info("Mijoz buyurtmani bekor qildi: %s", order.number)
    await render(
        query, t("order_cancelled", number=escape(order.number)), main_menu_only(t)
    )


# ------------------------- Takrorlash ----------------------------------
async def on_repeat(query: CallbackQuery, ctx: BotContext, callback_data: OrderCB) -> None:
    """«🔁 Qaytadan buyurtma» - tarkib savatga qaytariladi."""
    try:
        order = await _order(ctx, callback_data.order_id)
        count = await ctx.orders.repeat(ctx.user.id, order)
    except ServiceError as error:
        await _fail(query, ctx, error)
        return
    if not count:
        await answer_callback(query, ctx.t("order_repeat_empty"), alert=True)
        return
    text = ctx.t("order_repeat_done", count=count)
    await answer_callback(query, text)
    cart_text, markup = await cart_screen(ctx)
    await render(query, f"{text}\n\n{cart_text}", markup)


def build_router() -> Router:
    """Yangi `orders` router yasaydi."""
    router = Router(name="orders")

    router.message.register(cmd_orders, Command("orders"))
    router.message.register(open_orders, reply_button_filter("btn_orders"))

    router.callback_query.register(on_menu_orders, MenuCB.filter(F.action == "orders"))
    router.callback_query.register(on_list, OrderCB.filter(F.action == "list"))
    router.callback_query.register(on_detail, OrderCB.filter(F.action == "detail"))
    router.callback_query.register(on_cancel, OrderCB.filter(F.action == "cancel"))
    router.callback_query.register(
        on_confirm_cancel, OrderCB.filter(F.action == "confirm_cancel")
    )
    router.callback_query.register(on_repeat, OrderCB.filter(F.action == "repeat"))
    return router


__all__ = [
    "build_router",
    "cmd_orders",
    "open_orders",
    "show_order",
    "show_orders",
]

