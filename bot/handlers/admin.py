"""Xodimlar (boshqaruv) paneli (TZ 4.5).

Panel «🛠 Boshqaruv» reply tugmasi orqali ochiladi; router'ga
`StaffOnlyMiddleware` ulangani uchun mijozlar panelga kira olmaydi.

Bo'limlar:

    * 📊 statistika - bugungi buyurtmalar, summa va holatlar kesimi;
    * 🆕 yangi / 🚚 faol buyurtmalar - ro'yxat, kartochka, holatni almashtirish;
    * 🔍 qidiruv - buyurtma raqami bo'yicha (`AdminStates.search_order`);
    * 📉 kam qolgan mahsulotlar - `low_stock_hint` chegarasidan past qoldiq;
    * ☎️ ochiq murojaatlar - javob yozish (`AdminStates.support_reply`).

Buyurtma bo'yicha izoh yozish `AdminStates.order_reply` holatida bajariladi va
xabar to'g'ridan-to'g'ri mijozga yuboriladi.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.enums import NotificationKind, OrderStatus
from bot.handlers.common import TARGET, currency, menu_text
from bot.handlers.states import AdminStates
from bot.keyboards import (
    AdminCB,
    reply_button_filter,
    staff_cancel_inline,
    staff_menu_inline,
    staff_order_inline,
    staff_orders_inline,
    staff_status_inline,
    staff_support_inline,
    staff_text_inline,
)
from bot.middlewares import BotContext, attach_staff_filter
from bot.services import ServiceError
from bot.services.presenters import (
    low_stock_line,
    order_history_line,
    staff_order_caption,
    status_label,
    support_line,
)
from bot.utils.money import format_money
from bot.utils.rendering import answer_callback, render
from bot.utils.text import escape, format_date
from bot.utils.validators import normalize_order_number, normalize_text

logger = logging.getLogger(__name__)

#: Ro'yxat tugmalari (holatlar kesimi).
ORDER_LIST_TITLES: dict[str, str] = {
    "new_orders": "admin_orders_new",
    "active_orders": "admin_orders_active",
}

#: «Faol» hisoblanadigan holatlar (yetkazilgunga qadar).
ACTIVE_STATUSES: tuple[OrderStatus, ...] = (
    OrderStatus.NEW,
    OrderStatus.CONFIRMED,
    OrderStatus.PICKING,
    OrderStatus.ON_THE_WAY,
)

#: Buyurtma kartochkasida ko'rsatiladigan oxirgi yozuvlar soni.
HISTORY_LIMIT = 5


def _list_action(value: str | None) -> str:
    """Kartochkadan qaysi ro'yxatga qaytish kerakligi."""
    if value in ORDER_LIST_TITLES:
        return str(value)
    return "new_orders"


# ------------------------- Ekranlar ------------------------------------
async def show_panel(target: TARGET, ctx: BotContext) -> None:
    """Boshqaruv panelining asosiy menyusi (hisoblagichlar bilan)."""
    t = ctx.t
    counts = await ctx.orders.active_order_counts()
    open_requests = await ctx.support.count_open()
    text = f"{t('admin_menu_title')}\n\n{t('admin_menu_hint')}"
    await render(
        target,
        text,
        staff_menu_inline(t, new_orders=counts["new"], open_requests=open_requests),
    )


async def show_orders(
    target: TARGET, ctx: BotContext, *, page: int = 1, action: str = "new_orders"
) -> None:
    """«🆕 Yangi» / «🚚 Faol» buyurtmalar ro'yxati."""
    t = ctx.t
    key = _list_action(action)
    statuses = ACTIVE_STATUSES if key == "active_orders" else (OrderStatus.NEW,)
    items, pagination = await ctx.orders.page_by_statuses(statuses, page=page)
    if not items:
        await render(target, t("admin_orders_empty"), staff_text_inline(t))
        return
    title = t(
        "admin_orders_title",
        title=t(ORDER_LIST_TITLES[key]),
        count=pagination.total,
        page=pagination.current,
        pages=pagination.pages,
    )
    await render(
        target,
        title,
        staff_orders_inline(
            t, items, pagination, currency=currency(ctx), list_action=key
        ),
    )


async def show_order(
    target: TARGET, ctx: BotContext, order_id: int, *, action: str = "new_orders"
) -> None:
    """Buyurtma kartochkasi (oxirgi o'zgarishlar bilan)."""
    t = ctx.t
    try:
        order = await ctx.orders.get_full(order_id)
    except ServiceError as error:
        await render(target, ctx.error_text(error), staff_text_inline(t))
        return
    lines = [staff_order_caption(t, order, currency(ctx))]
    history = await ctx.orders.history(order.id)
    if history:
        lines.append("")
        lines.extend(
            order_history_line(t, entry) for entry in history[-HISTORY_LIMIT:]
        )
    await render(
        target, "\n".join(lines), staff_order_inline(t, order, list_action=_list_action(action))
    )


async def show_statuses(
    target: TARGET, ctx: BotContext, order_id: int, *, action: str = "new_orders"
) -> None:
    """«🔄 Holatni o'zgartirish» - ruxsat etilgan o'tishlar."""
    t = ctx.t
    try:
        order = await ctx.orders.get_full(order_id)
    except ServiceError as error:
        await render(target, ctx.error_text(error), staff_text_inline(t))
        return
    transitions = ctx.orders.allowed_transitions(order.status)
    lines = [staff_order_caption(t, order, currency(ctx)), "", t("admin_choose_status")]
    if not transitions:  # yakuniy holat - faqat kartochkaga qaytamiz
        await render(
            target,
            "\n".join(lines),
            staff_order_inline(t, order, list_action=_list_action(action)),
        )
        return
    await render(
        target,
        "\n".join(lines),
        staff_status_inline(t, order, transitions, list_action=_list_action(action)),
    )


async def show_stats(target: TARGET, ctx: BotContext) -> None:
    """📊 Bugungi statistika."""
    t = ctx.t
    data = await ctx.orders.stats()
    by_status = dict(data.get("by_status") or {})  # type: ignore[arg-type]
    money = currency(ctx)
    line = t(
        "admin_stats_line",
        orders=data.get("orders", 0),
        amount=format_money(data.get("amount"), money),
        average=format_money(data.get("average"), money),
        new=by_status.get(OrderStatus.NEW.value, 0),
        confirmed=by_status.get(OrderStatus.CONFIRMED.value, 0),
        on_the_way=by_status.get(OrderStatus.ON_THE_WAY.value, 0),
        delivered=by_status.get(OrderStatus.DELIVERED.value, 0),
        cancelled=by_status.get(OrderStatus.CANCELLED.value, 0),
    )
    text = f"{t('admin_stats_title', date=format_date(data.get('date')))}\n\n{line}"  # type: ignore[arg-type]
    await render(target, text, staff_text_inline(t))


async def show_low_stock(target: TARGET, ctx: BotContext) -> None:
    """📉 Kam qolgan mahsulotlar."""
    t = ctx.t
    products = await ctx.catalog.low_stock(limit=20)
    if not products:
        await render(target, t("admin_low_stock_empty"), staff_text_inline(t))
        return
    lines = [t("admin_low_stock_title"), ""]
    lines.extend(low_stock_line(t, product, ctx.language) for product in products)
    await render(target, "\n".join(lines), staff_text_inline(t))


async def show_support(target: TARGET, ctx: BotContext, *, page: int = 1) -> None:
    """☎️ Ochiq murojaatlar ro'yxati."""
    t = ctx.t
    items, pagination = await ctx.support.open_page(page=page)
    if not items:
        await render(target, t("admin_support_empty"), staff_text_inline(t))
        return
    lines = [t("admin_support_title", count=pagination.total), ""]
    lines.extend(support_line(t, request) for request in items)
    await render(target, "\n".join(lines), staff_support_inline(t, items, pagination))


# ------------------------- Kirish nuqtalari ----------------------------
async def open_admin(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """«🛠 Boshqaruv» reply tugmasi (faqat xodimlar)."""
    await state.clear()
    await show_panel(message, ctx)


async def on_admin(
    query: CallbackQuery, ctx: BotContext, callback_data: AdminCB, state: FSMContext
) -> None:
    """Panel tugmalari (barcha bo'limlar va navigatsiya)."""
    action = callback_data.action
    if action == "status_set":  # natija toast ko'rinishida ko'rsatiladi
        await set_status(query, ctx, callback_data)
        return
    await answer_callback(query)
    if action == "stats":
        await state.clear()
        await show_stats(query, ctx)
        return
    if action in ORDER_LIST_TITLES:
        await state.clear()
        await show_orders(query, ctx, page=callback_data.page, action=action)
        return
    if action == "order":
        await state.clear()
        await show_order(
            query, ctx, callback_data.order_id, action=_list_action(callback_data.value)
        )
        return
    if action == "status":
        await show_statuses(
            query, ctx, callback_data.order_id, action=_list_action(callback_data.value)
        )
        return
    if action == "reply":
        await start_reply(query, ctx, state, callback_data)
        return
    if action == "search":
        await ask_search(query, ctx, state)
        return
    if action == "low_stock":
        await state.clear()
        await show_low_stock(query, ctx)
        return
    if action == "support":
        await state.clear()
        await show_support(query, ctx, page=callback_data.page)
        return
    await state.clear()  # menu | back
    await show_panel(query, ctx)


async def set_status(
    query: CallbackQuery, ctx: BotContext, callback_data: AdminCB
) -> None:
    """Holatni almashtiradi va mijozga xabar yuboradi."""
    t = ctx.t
    try:
        order = await ctx.orders.get_full(callback_data.order_id)
    except ServiceError as error:
        await answer_callback(query, ctx.error_text(error), alert=True)
        return
    try:
        changed = await ctx.orders.change_status(
            order, callback_data.value, actor=ctx.user
        )
    except ServiceError as error:  # StatusSameError / StatusTransitionError
        await answer_callback(query, ctx.error_text(error), alert=True)
        return
    await answer_callback(
        query,
        t(
            "admin_status_changed",
            number=escape(order.number),
            status=status_label(t, changed.new_status),
        ),
    )
    await ctx.notifications.status_changed(order, changed.new_status)
    logger.info(
        "Holat o'zgardi: %s -> %s (xodim=%s)",
        order.number,
        changed.new_status.value,
        ctx.user_id,
    )
    await show_order(query, ctx, order.id, action=_list_action(callback_data.value))


async def ask_search(target: TARGET, ctx: BotContext, state: FSMContext) -> None:
    """🔍 Buyurtma raqamini kiritishni so'raydi."""
    await state.set_state(AdminStates.search_order)
    example = f"{ctx.settings.order_prefix}-000001"
    prompt = ctx.t("admin_search_prompt", example=escape(example))
    markup = staff_cancel_inline(ctx.t)
    if isinstance(target, Message):
        await target.answer(prompt, reply_markup=markup)
        return
    if target.message is not None:  # callback xabari mavjud bo'lsa
        await target.message.answer(prompt, reply_markup=markup)


async def start_reply(
    query: CallbackQuery, ctx: BotContext, state: FSMContext, callback_data: AdminCB
) -> None:
    """✍️ Javob/izoh yozish holatini o'rnatadi (murojaat yoki buyurtma)."""
    t = ctx.t
    if callback_data.request_id:
        await state.set_state(AdminStates.support_reply)
        await state.update_data(request_id=callback_data.request_id)
        await render(
            query,
            t("admin_reply_prompt", id=callback_data.request_id),
            staff_cancel_inline(t),
        )
        return
    await state.set_state(AdminStates.order_reply)
    await state.update_data(order_id=callback_data.order_id)
    await render(query, t("admin_note_prompt"), staff_cancel_inline(t))


async def on_search_text(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """🔍 Buyurtma raqami kiritildi."""
    t = ctx.t
    raw = (message.text or "").strip()
    number = normalize_order_number(raw, ctx.settings.order_prefix)
    await state.clear()
    try:
        order = await ctx.orders.get_by_number(number)
    except ServiceError:
        await message.answer(
            t("admin_search_not_found", query=escape(raw)), reply_markup=staff_text_inline(t)
        )
        return
    await show_order(message, ctx, order.id)


async def on_support_reply_text(
    message: Message, ctx: BotContext, state: FSMContext
) -> None:
    """☎️ Murojaatga javob: saqlanadi va mijozga yuboriladi."""
    t = ctx.t
    data = dict(await state.get_data())
    request_id = int(data.get("request_id") or 0)
    text = normalize_text(message.text, max_length=1000)
    try:
        request = await ctx.support.answer(request_id, text, actor=ctx.user)
    except ServiceError as error:
        await message.answer(ctx.error_text(error), reply_markup=staff_text_inline(t))
        return
    await state.clear()
    sent = await ctx.notifications.support_answered(request)
    logger.info("Murojaatga javob: #%s (xodim=%s)", request.id, ctx.user_id)
    await message.answer(
        t("admin_reply_sent") if sent else t("admin_reply_failed"),
        reply_markup=staff_text_inline(t),
    )


async def on_order_reply_text(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """✍️ Buyurtma bo'yicha izoh mijozga yuboriladi."""
    t = ctx.t
    data = dict(await state.get_data())
    order_id = int(data.get("order_id") or 0)
    text = normalize_text(message.text, max_length=1000)
    try:
        order = await ctx.orders.get_full(order_id)
    except ServiceError as error:
        await message.answer(ctx.error_text(error), reply_markup=staff_text_inline(t))
        return
    sent = await ctx.notifications.send_to_user(
        await ctx.notifications.order_user(order),
        text,
        kind=NotificationKind.ORDER_STATUS,
        order_id=order.id,
    )
    await state.clear()
    logger.info("Buyurtma izohi yuborildi: %s (xodim=%s)", order.number, ctx.user_id)
    await message.answer(
        t("admin_reply_sent") if sent else t("admin_reply_failed"),
        reply_markup=staff_text_inline(t),
    )


def build_router() -> Router:
    """Yangi `admin` router yasaydi (faqat xodimlar uchun)."""
    router = Router(name="admin")

    router.message.register(open_admin, reply_button_filter("btn_admin"))
    router.message.register(
        on_search_text, StateFilter(AdminStates.search_order), F.text, menu_text
    )
    router.message.register(
        on_support_reply_text, StateFilter(AdminStates.support_reply), F.text, menu_text
    )
    router.message.register(
        on_order_reply_text, StateFilter(AdminStates.order_reply), F.text, menu_text
    )

    router.callback_query.register(on_admin, AdminCB.filter())

    # Mijozlar panelga kira olmasligi uchun router'ga filtr o'rnatiladi.
    attach_staff_filter(router)
    return router


__all__ = [
    "ACTIVE_STATUSES",
    "HISTORY_LIMIT",
    "ORDER_LIST_TITLES",
    "ask_search",
    "build_router",
    "on_admin",
    "open_admin",
    "set_status",
    "show_low_stock",
    "show_order",
    "show_orders",
    "show_panel",
    "show_stats",
    "show_statuses",
    "show_support",
    "start_reply",
]
