"""Katalog: kategoriyalar, mahsulotlar, aksiya va qidiruv (TZ 4.4).

Bo'lim ikki xil kirish nuqtasiga ega:

    * «🛍 Katalog» / «🔥 Aksiyalar» reply tugmalari va /catalog buyrug'i;
    * `MenuCB` (inline «🏠 Asosiy menyu» qatoridan qaytish) va
      `CatalogCB` (kategoriya, sahifalash, aksiya, qidiruv).

Mahsulotni savatga qo'shish ham shu modulda: miqdor tayyor variantlardan
(`ProductCB(action="qty")`) yoki qo'lda (`CartStates.quantity`) olinadi.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.handlers.common import TARGET, currency, menu_text, show_cart
from bot.handlers.states import CartStates, CatalogStates
from bot.keyboards import (
    CatalogCB,
    MenuCB,
    ProductCB,
    cancel_keyboard,
    categories_inline,
    main_menu_only,
    product_inline,
    products_inline,
    quantity_inline,
    reply_button_filter,
)
from bot.middlewares import BotContext
from bot.services import ServiceError
from bot.services.presenters import product_caption, unit_label
from bot.utils.money import format_quantity, parse_decimal
from bot.utils.rendering import answer_callback, render
from bot.utils.text import escape
from bot.utils.validators import normalize_text

logger = logging.getLogger(__name__)

#: Mahsulot kartochkasidagi «⬅️ Orqaga» qayerga qaytaradi.
BACK_TO_CATEGORIES = CatalogCB(action="categories")


async def _notify_error(target: TARGET, ctx: BotContext, error: ServiceError) -> None:
    """Servis xatosini toast yoki matn ko'rinishida ko'rsatadi."""
    text = ctx.error_text(error)
    if isinstance(target, CallbackQuery):
        await answer_callback(target, text, alert=True)
        return
    await render(target, text, main_menu_only(ctx.t))


def _quantity_text(ctx: BotContext, product, quantity) -> str:
    """«Savatga qo'shildi» matni (HTML ko'rinishida)."""
    return ctx.t(
        "qty_added", quantity=format_quantity(quantity, unit_label(ctx.t, product.unit))
    )


# ------------------------- Ekranlar ------------------------------------
async def show_categories(target: TARGET, ctx: BotContext) -> None:
    """Kategoriyalar ro'yxati (aksiya va qidiruv tugmalari bilan)."""
    cards = await ctx.catalog.category_cards()
    if not cards:
        await render(target, ctx.t("catalog_empty"), main_menu_only(ctx.t))
        return
    await render(
        target, ctx.t("catalog_title"), categories_inline(ctx.t, cards, lang=ctx.language)
    )


async def show_category(
    target: TARGET, ctx: BotContext, *, category_id: int, page: int = 1
) -> None:
    """Kategoriyadagi mahsulotlar (sahifalash bilan)."""
    t = ctx.t
    try:
        category = await ctx.catalog.get_category(category_id)
    except ServiceError as error:
        await render(target, ctx.error_text(error), main_menu_only(t))
        return
    products, pagination = await ctx.catalog.product_page(
        category_id=category.id, page=page, per_page=ctx.settings.products_per_page
    )
    if not products:
        await render(target, t("catalog_products_empty"), main_menu_only(t))
        return
    text = t(
        "catalog_products_title",
        emoji=category.emoji,
        category=escape(category.localized_name(ctx.language)),
        page=pagination.current,
        pages=pagination.pages,
    )
    markup = products_inline(
        t,
        products,
        pagination,
        back_cb=CatalogCB(action="categories"),
        lang=ctx.language,
        currency=currency(ctx),
        prev_cb=CatalogCB(
            action="category", category_id=category.id, page=pagination.prev_page
        ),
        next_cb=CatalogCB(
            action="category", category_id=category.id, page=pagination.next_page
        ),
    )
    await render(target, text, markup)


async def show_promo(target: TARGET, ctx: BotContext, *, page: int = 1) -> None:
    """Aksiyadagi (chegirmali) mahsulotlar."""
    t = ctx.t
    products, pagination = await ctx.catalog.promo_page(
        page=page, per_page=ctx.settings.products_per_page
    )
    if not products:
        await render(target, t("catalog_promo_empty"), main_menu_only(t))
        return
    markup = products_inline(
        t,
        products,
        pagination,
        back_cb=CatalogCB(action="categories"),
        lang=ctx.language,
        currency=currency(ctx),
        prev_cb=CatalogCB(action="promo", page=pagination.prev_page),
        next_cb=CatalogCB(action="promo", page=pagination.next_page),
    )
    await render(target, t("catalog_promo_title"), markup)


async def show_search(
    target: TARGET, ctx: BotContext, *, query: str, page: int = 1
) -> None:
    """Qidiruv natijalari (sahifalash bilan)."""
    t = ctx.t
    products, pagination = await ctx.catalog.search_page(
        query, page=page, per_page=ctx.settings.products_per_page
    )
    if not products:
        await render(
            target, t("catalog_search_empty", query=escape(query)), main_menu_only(t)
        )
        return
    markup = products_inline(
        t,
        products,
        pagination,
        back_cb=CatalogCB(action="categories"),
        lang=ctx.language,
        currency=currency(ctx),
        prev_cb=CatalogCB(action="search", page=pagination.prev_page),
        next_cb=CatalogCB(action="search", page=pagination.next_page),
    )
    await render(
        target,
        t("catalog_search_results", query=escape(query), count=pagination.total),
        markup,
    )


async def show_product(target: TARGET, ctx: BotContext, *, product_id: int | None) -> None:
    """Mahsulot kartochkasi (rasm bo'lsa - rasm bilan)."""
    try:
        product = await ctx.catalog.get_product(product_id)
    except ServiceError as error:
        await _notify_error(target, ctx, error)
        return
    caption = product_caption(ctx.t, product, ctx.language, currency(ctx))
    markup = product_inline(ctx.t, product, back_cb=BACK_TO_CATEGORIES)
    await render(target, caption, markup, photo=product.image_file_id)


# ------------------------- Buyruqlar va reply tugmalar -----------------
async def cmd_catalog(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """«/catalog» - katalogni ochadi."""
    await state.clear()
    await show_categories(message, ctx)


async def cmd_promo(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """«/promo» - aksiyadagi mahsulotlar."""
    await state.clear()
    await show_promo(message, ctx)


async def open_catalog(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """«🛍 Katalog» reply tugmasi."""
    await state.clear()
    await show_categories(message, ctx)


async def open_promo(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """«🔥 Aksiyalar» reply tugmasi."""
    await state.clear()
    await show_promo(message, ctx)


async def cancel_state(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """«❌ Bekor qilish» - qadamni to'xtatib katalogga qaytaradi."""
    await state.clear()
    await show_categories(message, ctx)


# ------------------------- Inline navigatsiya --------------------------
async def on_menu_catalog(query: CallbackQuery, ctx: BotContext, state: FSMContext) -> None:
    """Inline menyudan «Katalog» (`MenuCB`)."""
    await state.clear()
    await answer_callback(query)
    await show_categories(query, ctx)


async def on_promo_menu(query: CallbackQuery, ctx: BotContext, state: FSMContext) -> None:
    """Inline menyudan «Aksiyalar» (`MenuCB`)."""
    await state.clear()
    await answer_callback(query)
    await show_promo(query, ctx)


async def on_categories(query: CallbackQuery, ctx: BotContext) -> None:
    """«⬅️ Orqaga» - kategoriyalar ro'yxatiga qaytish."""
    await answer_callback(query)
    await show_categories(query, ctx)


async def on_category(query: CallbackQuery, ctx: BotContext, callback_data: CatalogCB) -> None:
    """Kategoriya tanlandi (yoki sahifasi almashtirildi)."""
    await answer_callback(query)
    await show_category(
        query, ctx, category_id=callback_data.category_id, page=callback_data.page
    )


async def on_promo(query: CallbackQuery, ctx: BotContext, callback_data: CatalogCB) -> None:
    """Aksiya sahifasi."""
    await answer_callback(query)
    await show_promo(query, ctx, page=callback_data.page)

# ------------------------- Qidiruv -------------------------------------
async def on_search(
    query: CallbackQuery, ctx: BotContext, callback_data: CatalogCB, state: FSMContext
) -> None:
    """«🔍 Qidiruv» tugmasi yoki natijalarning keyingi sahifasi."""
    await answer_callback(query)
    data = await state.get_data()
    saved = str(data.get("query") or "")
    if callback_data.page > 1 and saved:
        await show_search(query, ctx, query=saved, page=callback_data.page)
        return
    await state.set_state(CatalogStates.search)
    await state.update_data(query=None)
    await render(query, ctx.t("catalog_search_prompt"), main_menu_only(ctx.t))


async def on_search_text(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """Qidiruv so'rovi matn ko'rinishida kelganda."""
    query = normalize_text(message.text, max_length=100)
    if len(query) < 2:
        await message.answer(ctx.t("catalog_search_prompt"))
        return
    await state.update_data(query=query)
    await show_search(message, ctx, query=query)


# ------------------------- Mahsulot kartochkasi ------------------------
async def on_product(query: CallbackQuery, ctx: BotContext, callback_data: ProductCB) -> None:
    """Mahsulot kartochkasini ochish (katalog yoki savatdan)."""
    await answer_callback(query)
    await show_product(query, ctx, product_id=callback_data.product_id)


async def on_add(query: CallbackQuery, ctx: BotContext, callback_data: ProductCB) -> None:
    """«➕ Savatga qo'shish» - miqdor tanlash ekranini ochadi."""
    try:
        product = await ctx.catalog.get_product(callback_data.product_id)
    except ServiceError as error:
        await _notify_error(query, ctx, error)
        return
    await answer_callback(query)
    await render(
        query,
        ctx.t("add_qty_prompt"),
        quantity_inline(
            ctx.t, product, back_cb=ProductCB(action="open", product_id=product.id)
        ),
    )


async def on_quantity(
    query: CallbackQuery, ctx: BotContext, callback_data: ProductCB
) -> None:
    """Tayyor miqdor tanlandi: savatga qo'shadi va savatni ko'rsatadi."""
    try:
        product = await ctx.catalog.get_product(callback_data.product_id)
        quantity = ctx.cart.validate_quantity(
            product, ctx.cart.step_for(product) * max(callback_data.value, 1)
        )
        await ctx.cart.add(ctx.user.id, product, quantity)
    except ServiceError as error:
        await _notify_error(query, ctx, error)
        return
    await answer_callback(query, _quantity_text(ctx, product, quantity))
    await show_cart(query, ctx)


async def on_quantity_input(
    query: CallbackQuery, ctx: BotContext, callback_data: ProductCB, state: FSMContext
) -> None:
    """«✏️ Boshqa miqdor» - miqdorni qo'lda kiritishni so'raydi."""
    await answer_callback(query)
    await state.set_state(CartStates.quantity)
    await state.update_data(product_id=callback_data.product_id)
    if query.message is not None:
        await query.message.answer(
            ctx.t("add_qty_input_prompt"), reply_markup=cancel_keyboard(ctx.t)
        )


async def on_quantity_text(message: Message, ctx: BotContext, state: FSMContext) -> None:
    """Qo'lda kiritilgan miqdorni savatga qo'shadi."""
    data = await state.get_data()
    try:
        product = await ctx.catalog.get_product(data.get("product_id"))
        quantity = ctx.cart.validate_quantity(product, parse_decimal(message.text))
        await ctx.cart.add(ctx.user.id, product, quantity)
    except ValueError:
        await message.answer(ctx.t("qty_invalid"), reply_markup=cancel_keyboard(ctx.t))
        return
    except ServiceError as error:
        await message.answer(ctx.error_text(error), reply_markup=cancel_keyboard(ctx.t))
        return
    await state.clear()
    await message.answer(_quantity_text(ctx, product, quantity))
    await show_cart(message, ctx)


def build_router() -> Router:
    """Yangi `catalog` router yasaydi."""
    router = Router(name="catalog")

    # Buyruqlar va reply tugmalar
    router.message.register(cmd_catalog, Command("catalog"))
    router.message.register(cmd_promo, Command("promo"))
    router.message.register(open_catalog, reply_button_filter("btn_catalog"))
    router.message.register(open_promo, reply_button_filter("btn_promo"))

    # Matn kutadigan qadamlar (menyu tugmalari bu yerga tushmaydi)
    router.message.register(
        cancel_state,
        StateFilter(CatalogStates.search, CartStates.quantity),
        reply_button_filter("btn_cancel"),
    )
    router.message.register(
        on_search_text, StateFilter(CatalogStates.search), F.text, menu_text
    )
    router.message.register(
        on_quantity_text, StateFilter(CartStates.quantity), F.text, menu_text
    )

    # Inline navigatsiya
    router.callback_query.register(on_menu_catalog, MenuCB.filter(F.action == "catalog"))
    router.callback_query.register(on_promo_menu, MenuCB.filter(F.action == "promo"))
    router.callback_query.register(on_categories, CatalogCB.filter(F.action == "categories"))
    router.callback_query.register(on_category, CatalogCB.filter(F.action == "category"))
    router.callback_query.register(on_promo, CatalogCB.filter(F.action == "promo"))
    router.callback_query.register(on_search, CatalogCB.filter(F.action == "search"))
    router.callback_query.register(on_product, ProductCB.filter(F.action == "open"))
    router.callback_query.register(on_add, ProductCB.filter(F.action == "add"))
    router.callback_query.register(on_quantity, ProductCB.filter(F.action == "qty"))
    router.callback_query.register(on_quantity_input, ProductCB.filter(F.action == "input"))
    return router


__all__ = [
    "build_router",
    "cancel_state",
    "open_catalog",
    "open_promo",
    "show_categories",
    "show_category",
    "show_product",
    "show_promo",
    "show_search",
]

