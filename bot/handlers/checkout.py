"""Buyurtma berish oqimi (TZ 4.4).

Qadamlar:

    1. savatni tekshirish (bo'sh emas, minimal summa, qoldiq) va telefon;
    2. yetkazish turi (yetkazib berish / o'zi olib ketish);
    3. manzil - saqlangan manzillardan, matn yoki lokatsiya orqali;
    4. yetkazish vaqti;
    5. izoh (ixtiyoriy);
    6. to'lov usuli;
    7. tasdiqlash - buyurtma yaratiladi va xodimlarga xabar yuboriladi.

Barcha qadamlar `CheckoutCB` orqali boshqariladi; matn kutadigan qadamlar
(`CheckoutStates.address`, `CheckoutStates.comment`) FSM holatida turadi.
Tasdiqlash ekranidagi «⬅️ Orqaga» (`CheckoutCB(action="back")`) to'lov usulini
tanlash qadamiga qaytaradi.

Eslatma: onlayn to'lov (Payme/Click) hali ulanmagan - shu sababli
`checkout_payment_inline` faqat naqd/karta/o'tkazma variantlarini ko'rsatadi.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.enums import DeliveryType, OrderSource, PaymentMethod
from bot.database.models import Address
from bot.database.repositories.users import CustomerRepository
from bot.handlers.common import TARGET, ask_phone, currency, menu_markup, menu_text, restore_menu
from bot.handlers.states import CHECKOUT_STATES, CheckoutStates
from bot.keyboards import (
    TIME_SLOTS,
    CheckoutCB,
    checkout_address_inline,
    checkout_comment_inline,
    checkout_confirm_inline,
    checkout_delivery_inline,
    checkout_payment_inline,
    checkout_time_inline,
    empty_cart_inline,
    location_request,
    main_menu_only,
    order_detail_inline,
    reply_button_filter,
    staff_order_inline,
)
from bot.locales import translator
from bot.middlewares import BotContext
from bot.services import CartEmptyError, CheckoutData, ServiceError
from bot.services.presenters import (
    delivery_label,
    discount_line,
    payment_label,
    unit_label,
)
from bot.utils.money import format_money, format_quantity
from bot.utils.rendering import answer_callback, render
from bot.utils.text import escape
from bot.utils.validators import normalize_text

logger = logging.getLogger(__name__)

#: Onlayn to'lov havolalari ulangunga qadar faqat oflayn usullar ko'rsatiladi.
ONLINE_PAYMENT_READY = False


# ------------------------- Yordamchilar -------------------------------
async def _finish(
    target: TARGET, ctx: BotContext, state: FSMContext, text: str, markup: object = None
) -> None:
    """Oqimni tugatadi: holatni tozalaydi, xabar yuboradi, menyuni qaytaradi."""
    await state.clear()
    await render(target, text, markup or main_menu_only(ctx.t))
    await restore_menu(target, ctx)


async def _addresses(ctx: BotContext) -> list[Address]:
    """Mijozning saqlangan manzillari."""
    if ctx.customer is None:
        return []
    return await CustomerRepository(ctx.session).list_addresses(ctx.customer.id)


def _delivery_type(data: dict[str, object]) -> DeliveryType:
    return DeliveryType(str(data.get("delivery_type") or DeliveryType.DELIVERY.value))


def _payment_method(data: dict[str, object]) -> PaymentMethod:
    return PaymentMethod(str(data.get("payment_method") or PaymentMethod.CASH.value))


def _slot_label(ctx: BotContext, value: str) -> str:
    """Yetkazish vaqti tugmasining tarjima qilingan matni."""
    for slot, key in TIME_SLOTS:
        if slot == value:
            return ctx.t(key)
    return value


async def begin_checkout(target: TARGET, ctx: BotContext, state: FSMContext) -> None:
    """Buyurtma berish oqimini boshlaydi (savatdan «🚚 Buyurtma berish»)."""
    try:
        await ctx.cart.validate_for_checkout(ctx.user.id)
    except ServiceError as error:
        text = ctx.error_text(error)
        if isinstance(target, CallbackQuery):
            await answer_callback(target, text, alert=True)
        markup = (
            empty_cart_inline(ctx.t)
            if isinstance(error, CartEmptyError)
            else main_menu_only(ctx.t)
        )
        await render(target, text, markup)
        return

    if not ctx.user.has_phone:
        if isinstance(target, CallbackQuery):
            await answer_callback(target)
            if target.message is not None:
                await ask_phone(target.message, ctx, state)
        else:
            await ask_phone(target, ctx, state)
        return

    await state.clear()
    await state.update_data(
        delivery_type=DeliveryType.DELIVERY.value,
        address=None,
        latitude=None,
        longitude=None,
        delivery_time=None,
        comment=None,
        payment_method=PaymentMethod.CASH.value,
    )
    await render(target, ctx.t("co_delivery_title"), checkout_delivery_inline(ctx.t))


# ------------------------- Ekranlar ------------------------------------
async def _show_address(target: TARGET, ctx: BotContext, state: FSMContext) -> None:
    """Manzil qadami: saqlangan manzillar + matn/lokatsiya kutish."""
    await state.set_state(CheckoutStates.address)
    addresses = await _addresses(ctx)
    text = ctx.t("co_saved_addresses") if addresses else ctx.t("co_ask_address")
    await render(target, text, checkout_address_inline(ctx.t, addresses))
    if isinstance(target, CallbackQuery) and target.message is not None:
        # Reply klaviaturani (lokatsiya) faqat yangi xabar bilan o'zgartirish mumkin.
        await target.message.answer(
            ctx.t("co_ask_address"), reply_markup=location_request(ctx.t)
        )


async def _show_time(target: TARGET, ctx: BotContext, state: FSMContext) -> None:
    """Yetkazish vaqtini tanlash qadami."""
    data = dict(await state.get_data())
    if _delivery_type(data) is DeliveryType.PICKUP:
        info = await ctx.settings_service.info()
        address = str(info.get("pickup_address") or "")
        head = (
            ctx.t(
                "co_pickup_address",
                address=escape(address),
                hours=escape(str(info.get("working_hours") or "")),
            )
            if address and address != "—"
            else ctx.t("co_pickup_missing")
        )
        text = f"{head}\n\n{ctx.t('co_ask_time')}"
    else:
        text = ctx.t("co_ask_time")
    await render(target, text, checkout_time_inline(ctx.t))
    if isinstance(target, Message):
        # Manzil qadamida reply klaviatura o'zgargan bo'ladi - menyuni qaytaramiz.
        await restore_menu(target, ctx)


async def _show_comment(target: TARGET, ctx: BotContext, state: FSMContext) -> None:
    """Izoh qadami (matn kiritish yoki «⏭ O'tkazib yuborish»)."""
    await state.set_state(CheckoutStates.comment)
    await render(target, ctx.t("co_ask_comment"), checkout_comment_inline(ctx.t))


async def _show_payment(target: TARGET, ctx: BotContext, state: FSMContext) -> None:
    """To'lov usulini tanlash qadami."""
    await state.set_state(None)
    await render(
        target,
        ctx.t("co_choose_payment"),
        checkout_payment_inline(ctx.t, online=ONLINE_PAYMENT_READY),
    )


async def _show_confirm(target: TARGET, ctx: BotContext, state: FSMContext) -> None:
    """Tasdiqlashdan oldingi yakuniy ko'rinish."""
    await state.set_state(None)
    data = dict(await state.get_data())
    summary = await ctx.cart.summary(ctx.user.id, delivery_type=_delivery_type(data))
    if summary.is_empty:
        await _finish(target, ctx, state, ctx.t("cart_empty"))
        return
    await render(target, _confirm_text(ctx, data, summary), checkout_confirm_inline(ctx.t))


def _confirm_text(ctx: BotContext, data: dict[str, object], summary) -> str:
    """Buyurtma tarkibi: pozitsiyalar, summalar va yetkazish ma'lumotlari."""
    t = ctx.t
    money = currency(ctx)
    lines = [t("co_summary_title"), ""]
    for line in summary.lines:
        lines.append(
            t(
                "co_summary_item",
                name=escape(line.product.localized_name(ctx.language)),
                quantity=format_quantity(line.quantity, unit_label(t, line.product.unit)),
                price=format_money(line.price, money),
                total=format_money(line.total, money),
            )
        )
    lines.append("")
    lines.append(
        t(
            "co_summary_info",
            subtotal=format_money(summary.subtotal, money),
            discount=discount_line(t, summary.discount, money),
            delivery=format_money(summary.delivery_fee, money),
            total=format_money(summary.total, money),
            delivery_type=delivery_label(t, _delivery_type(data)),
            address=escape(data.get("address") or t("dt_pickup")),
            time=escape(data.get("delivery_time") or t("profile_unknown")),
            payment=payment_label(t, _payment_method(data)),
        )
    )
    lines.append("")
    lines.append(t("co_confirm_ask"))
    return "\n".join(lines)


# ------------------------- Qadam handler'lari --------------------------
async def on_delivery(query: CallbackQuery, ctx: BotContext, state: FSMContext) -> None:
    """«🚚 Yetkazib berish» tanlandi."""
    await state.update_data(delivery_type=DeliveryType.DELIVERY.value)
    await answer_callback(query)
    await _show_address(query, ctx, state)


async def on_pickup(query: CallbackQuery, ctx: BotContext, state: FSMContext) -> None:
    """«🏬 O'zi olib ketish» tanlandi - manzil so'ralmaydi."""
    await state.update_data(
        delivery_type=DeliveryType.PICKUP.value,
        address=None,
        latitude=None,
        longitude=None,
    )
    await answer_callback(query)
    await _show_time(query, ctx, state)


async def on_saved_address(
    query: CallbackQuery, ctx: BotContext, callback_data: CheckoutCB, state: FSMContext
) -> None:
    """Saqlangan manzillardan biri tanlandi."""
    value = callback_data.value
    address_id = int(value) if value.isdigit() else 0
    addresses = await _addresses(ctx)
    address = next((item for item in addresses if item.id == address_id), None)
    if address is None:
        await answer_callback(query, ctx.t("error_stale"), alert=True)
        return
    await state.update_data(
        address=address.address, latitude=address.latitude, longitude=address.longitude
    )
    await answer_callback(query, ctx.t("co_address_saved"))
    await _show_time(query, ctx, state)


async def on_new_address(query: CallbackQuery, ctx: BotContext, state: FSMContext) -> None:
    """«✍️ Yangi manzil» / «📍 Lokatsiya» - matn yoki lokatsiya kutadi."""
    await answer_callback(query)
    if query.message is not None:
        await query.message.answer(
            ctx.t("co_ask_address"), reply_markup=location_request(ctx.t)
        )


async def on_address_text(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """Manzil matn ko'rinishida kelganda."""
    text = normalize_text(message.text, max_length=500)
    if not text:
        await message.answer(
            ctx.t("co_address_required"), reply_markup=location_request(ctx.t)
        )
        return
    await state.update_data(address=text, latitude=None, longitude=None)
    await _show_time(message, ctx, state)


async def on_address_location(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """Lokatsiya yuborilganda (koordinatalar manzil sifatida saqlanadi)."""
    location = message.location
    if location is None:  # nazariy holat
        return
    coords = f"{location.latitude:.5f}, {location.longitude:.5f}"
    await state.update_data(
        address=f"📍 {coords}",
        latitude=location.latitude,
        longitude=location.longitude,
    )
    await _show_time(message, ctx, state)


async def on_time(
    query: CallbackQuery, ctx: BotContext, callback_data: CheckoutCB, state: FSMContext
) -> None:
    """Yetkazish vaqti tanlandi."""
    await state.update_data(delivery_time=_slot_label(ctx, callback_data.value))
    await answer_callback(query)
    await _show_comment(query, ctx, state)


async def on_comment_text(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """Izoh matni kiritildi."""
    comment = normalize_text(message.text, max_length=500)
    await state.update_data(comment=comment or None)
    await _show_payment(message, ctx, state)


async def on_skip(query: CallbackQuery, ctx: BotContext, state: FSMContext) -> None:
    """«⏭ O'tkazib yuborish» - izohsiz davom etadi."""
    await state.update_data(comment=None)
    await answer_callback(query)
    await _show_payment(query, ctx, state)


async def on_payment(
    query: CallbackQuery, ctx: BotContext, callback_data: CheckoutCB, state: FSMContext
) -> None:
    """To'lov usuli tanlandi (tasdiqlashdan «⬅️ Orqaga» ham shu yerga keladi)."""
    try:
        method = PaymentMethod(callback_data.value)
    except ValueError:
        method = PaymentMethod.CASH
    await state.update_data(payment_method=method.value)
    await answer_callback(query)
    await _show_confirm(query, ctx, state)


async def on_back(query: CallbackQuery, ctx: BotContext, state: FSMContext) -> None:
    """«⬅️ Orqaga» - tasdiqlash ekranidan to'lov usulini tanlash qadamiga qaytadi."""
    await answer_callback(query)
    await _show_payment(query, ctx, state)


async def on_cancel(query: CallbackQuery, ctx: BotContext, state: FSMContext) -> None:
    """«❌ Bekor qilish» - oqim to'xtatiladi, savat saqlanib qoladi."""
    await _finish(query, ctx, state, ctx.t("co_cancelled"))


async def on_cancel_text(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """Reply «❌ Bekor qilish» tugmasi (manzil/izoh qadamida)."""
    await state.clear()
    await message.answer(ctx.t("co_cancelled"), reply_markup=menu_markup(ctx))


async def on_confirm(query: CallbackQuery, ctx: BotContext, state: FSMContext) -> None:
    """Buyurtmani tasdiqlash: yaratish va xodimlarga xabar yuborish."""
    data = dict(await state.get_data())
    options = CheckoutData(
        delivery_type=_delivery_type(data),
        address=data.get("address"),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        delivery_time=data.get("delivery_time"),
        comment=data.get("comment"),
        payment_method=_payment_method(data),
        customer_name=ctx.user.display_name,
        customer_phone=ctx.user.phone,
        source=OrderSource.BOT,
        save_address=True,
    )
    try:
        order = await ctx.orders.create_from_cart(ctx.user, options)
    except ServiceError as error:
        text = ctx.error_text(error)
        await answer_callback(query, text, alert=True)
        await _finish(query, ctx, state, text)
        return

    money = format_money(order.total, currency(ctx))
    summary = ctx.t("co_created", number=escape(order.number), total=money)
    await answer_callback(query, ctx.t("co_created", number=order.number, total=money))
    await ctx.notifications.order_created(
        order, markup=staff_order_inline(translator("uz"), order, list_action="new_orders")
    )
    logger.info("Buyurtma yaratildi: %s (foydalanuvchi=%s)", order.number, ctx.user_id)
    await _finish(query, ctx, state, summary, order_detail_inline(ctx.t, order))


def build_router() -> Router:
    """Yangi `checkout` router yasaydi."""
    router = Router(name="checkout")

    router.callback_query.register(on_cancel, CheckoutCB.filter(F.action == "cancel"))
    router.callback_query.register(on_back, CheckoutCB.filter(F.action == "back"))
    router.callback_query.register(on_delivery, CheckoutCB.filter(F.action == "delivery"))
    router.callback_query.register(on_pickup, CheckoutCB.filter(F.action == "pickup"))
    router.callback_query.register(on_saved_address, CheckoutCB.filter(F.action == "addr"))
    router.callback_query.register(
        on_new_address, CheckoutCB.filter(F.action.in_({"new_address", "location"}))
    )
    router.callback_query.register(on_time, CheckoutCB.filter(F.action == "time"))
    router.callback_query.register(on_skip, CheckoutCB.filter(F.action == "skip"))
    router.callback_query.register(on_payment, CheckoutCB.filter(F.action == "payment"))
    router.callback_query.register(on_confirm, CheckoutCB.filter(F.action == "confirm"))

    # Matn/lokatsiya kutadigan qadamlar (reply «Bekor qilish» birinchi turadi)
    router.message.register(
        on_cancel_text, StateFilter(*CHECKOUT_STATES), reply_button_filter("btn_cancel")
    )
    router.message.register(on_address_location, StateFilter(CheckoutStates.address), F.location)
    router.message.register(
        on_address_text, StateFilter(CheckoutStates.address), F.text, menu_text
    )
    router.message.register(
        on_comment_text, StateFilter(CheckoutStates.comment), F.text, menu_text
    )
    return router


__all__ = [
    "ONLINE_PAYMENT_READY",
    "begin_checkout",
    "build_router",
    "on_back",
    "on_cancel",
    "on_confirm",
]



