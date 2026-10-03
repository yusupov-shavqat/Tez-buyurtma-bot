"""Vaqtinchalik smoke-test: servis qatlamining to'liq oqimi (TZ 4.4).

Ishlatilishi:  python scripts/_smoke_services.py
Testlar alohida SQLite faylida ishlaydi (`data/_smoke.db`).
"""

from __future__ import annotations

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

try:  # Windows konsolida emoji chiqarish uchun
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

if sys.flags.dev_mode or __import__("os").environ.get("SMOKE_STRICT_WARNINGS"):
    import warnings

    from sqlalchemy.exc import SAWarning

    warnings.filterwarnings("error", category=SAWarning)

from bot.config import Settings
from bot.database.base import (
    create_engine,
    create_session_pool,
    dispose_engine,
    init_models,
)
from bot.database.enums import (
    CustomerSegment,
    DeliveryType,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    Unit,
    UserRole,
)
from bot.database.models import Category, Product
from bot.database.repositories.catalog import CategoryRepository, ProductRepository
from bot.database.repositories.users import CustomerRepository, UserRepository
from bot.locales import translator
from bot.services import (
    CartService,
    CatalogService,
    CheckoutData,
    NotCancellableError,
    NotificationService,
    OrderService,
    SettingsService,
    StatusSameError,
    StatusTransitionError,
    SupportService,
    SupportTooShortError,
)
from bot.services import presenters as pr

DB_PATH = Path("data/_smoke.db")
DB_URL = "sqlite+aiosqlite:///./data/_smoke.db"

FAILURES: list[str] = []


class StubBot:
    """Tarmoqqa chiqmaydigan bot o'rnini bosuvchi (faqat send_message)."""

    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    async def send_message(self, chat_id: int, text: str, **kwargs: object) -> None:
        self.sent.append((int(chat_id), text))


def check(label: str, condition: bool, extra: object = "") -> None:
    print(f"[{'OK  ' if condition else 'FAIL'}] {label} {extra}")
    if not condition:
        FAILURES.append(label)


async def seed(session, settings: Settings):
    """Foydalanuvchi, kategoriya va mahsulotlarni yaratadi."""
    users = UserRepository(session)
    user, _ = await users.get_or_create(
        1001, username="tester", full_name="Test Mijoz", chat_id=1001
    )
    await users.get_or_create(
        9001, full_name="Admin Xodim", chat_id=9001, role=UserRole.ADMIN
    )
    category = await CategoryRepository(session).add(
        Category(name_uz="Ichimliklar", name_ru="Напитки", emoji="🥤")
    )
    products = ProductRepository(session)
    water = await products.add(
        Product(
            sku="SM-001",
            name_uz="Suv 1.5L",
            name_ru="Вода 1.5L",
            price=Decimal("5000"),
            stock=Decimal("100"),
            min_stock=Decimal("10"),
            unit=Unit.PCS,
            category_id=category.id,
        )
    )
    juice = await products.add(
        Product(
            sku="SM-002",
            name_uz="Sharbat 1L",
            name_ru="Сок 1L",
            price=Decimal("10000"),
            discount_price=Decimal("9000"),
            stock=Decimal("50"),
            min_stock=Decimal("60"),
            unit=Unit.PCS,
            is_promo=True,
            category_id=category.id,
        )
    )
    await session.commit()
    return user, category, water, juice


async def smoke_catalog_cart(session, settings: Settings, user, category, water, juice):
    """Katalog va savat servislarini tekshiradi; savat servisini qaytaradi."""
    catalog = CatalogService(session)
    cards = await catalog.category_cards()
    check("kategoriya kartalari", len(cards) == 1 and cards[0].products == 2, cards)
    page_products, pagination = await catalog.product_page(category_id=category.id)
    check("katalog sahifasi", pagination.total == 2 and len(page_products) == 2)
    found = await catalog.find_product("SM-001")
    check("artikul bo'yicha qidiruv", len(found) == 1 and found[0].id == water.id)
    promo, promo_page = await catalog.promo_page()
    check("aksiya sahifasi", promo_page.total == 1 and promo[0].id == juice.id)
    low = await catalog.low_stock()
    check("kam qoldiq ro'yxati", [item.id for item in low] == [juice.id], len(low))

    cart = CartService(session, settings)
    await cart.add(user.id, water, 3)
    await cart.add(user.id, juice, 2)
    summary = await cart.summary(user.id)
    check("savat subtotal", summary.subtotal == Decimal("33000"), summary.subtotal)
    check("savat chegirma", summary.discount == Decimal("2000"), summary.discount)
    check(
        "yetkazish narxi",
        summary.delivery_fee == Decimal("15000"),
        summary.delivery_fee,
    )
    check("savat jami", summary.total == Decimal("48000"), summary.total)
    check("savat pozitsiyalari", summary.positions == 2, summary.positions)
    return cart


async def smoke_orders(session, settings: Settings, cart: CartService, user, water, juice):
    """Buyurtma yaratish, holatlar zanjiri, bekor qilish va to'lovlarni tekshiradi."""
    orders = OrderService(session, settings)
    order = await orders.create_from_cart(
        user,
        CheckoutData(
            address="Toshkent, Chilonzor 1-uy",
            customer_phone="+998901112233",
            comment="Smoke test",
            delivery_type=DeliveryType.DELIVERY,
        ),
    )
    await session.flush()
    check("buyurtma raqami", order.number.startswith("ORD-"), order.number)
    check("buyurtma summasi", order.total == Decimal("48000"), order.total)
    check("buyurtma holati", str(order.status) == OrderStatus.NEW.value, order.status)
    check("buyurtma tarkibi", len(order.items) == 2, len(order.items))
    check("savat tozalandi", (await cart.summary(user.id)).is_empty)
    check("qoldiq hali kamaymadi", Decimal(str(water.stock)) == Decimal("100"), water.stock)
    check("tarix yozuvi", len(await orders.history(order.id)) == 1)

    change = await orders.change_status(order, OrderStatus.CONFIRMED, actor=user)
    check("CONFIRMED ga o'tish", change.new_status is OrderStatus.CONFIRMED)
    await session.refresh(water)
    check(
        "CONFIRMED da qoldiq o'zgarmadi",
        not change.stock_deducted and Decimal(str(water.stock)) == Decimal("100"),
        water.stock,
    )

    change = await orders.change_status(order, OrderStatus.PICKING, actor=user)
    check("PICKING da qoldiq hisobdan chiqarildi", change.stock_deducted)
    await session.refresh(water)
    check("suv qoldig'i 97", Decimal(str(water.stock)) == Decimal("97"), water.stock)

    try:
        await orders.change_status(order, OrderStatus.NEW)
        check("noto'g'ri o'tish rad etildi", False)
    except StatusTransitionError:
        check("noto'g'ri o'tish rad etildi", True)

    try:
        await orders.change_status(order, OrderStatus.PICKING)
        check("bir xil holat rad etildi", False)
    except StatusSameError:
        check("bir xil holat rad etildi", True)

    for status in (OrderStatus.ON_THE_WAY, OrderStatus.DELIVERED):
        await orders.change_status(order, status, actor=user)
    check(
        "DELIVERED holati va vaqti",
        str(order.status) == OrderStatus.DELIVERED.value
        and order.delivered_at is not None,
    )
    await session.refresh(water)
    check(
        "qayta hisobdan chiqarilmadi",
        Decimal(str(water.stock)) == Decimal("97"),
        water.stock,
    )
    await orders.mark_fully_paid(order, method=PaymentMethod.CASH)
    await session.refresh(order)
    check(
        "to'lov qayd etildi",
        Decimal(str(order.paid_amount)) == Decimal("48000")
        and str(order.payment_status) == PaymentStatus.PAID.value,
        order.paid_amount,
    )

    # Mijoz bekor qilishi: faqat NEW/CONFIRMED holatlarida
    await cart.add(user.id, water, 2)
    twice = await orders.create_from_cart(
        user,
        CheckoutData(address="Toshkent, Yunusobod 5-uy", save_address=False),
    )
    await session.flush()
    cancel = await orders.cancel_by_customer(twice, reason="Fikrim o'zgardi")
    await session.refresh(water)
    check("mijoz bekor qildi", cancel.new_status is OrderStatus.CANCELLED)
    check("sabab saqlandi", twice.cancel_reason == "Fikrim o'zgardi", twice.cancel_reason)
    check(
        "qoldiq qaytarilmadi (hisobdan chiqarilmagan)",
        Decimal(str(water.stock)) == Decimal("97"),
        water.stock,
    )

    confirmed = await orders.get_full(order.id)
    try:
        await orders.cancel_by_customer(confirmed)
        check("yetkazilgan buyurtma bekor qilinmaydi", False)
    except NotCancellableError:
        check("yetkazilgan buyurtma bekor qilinmaydi", True)

    # Qaytarish: qoldiq omborga qaytadi (faqat yo'lda/ qismiy holatlardan)
    await cart.add(user.id, water, 3)
    third = await orders.create_from_cart(
        user, CheckoutData(address="Toshkent, Mirzo Ulug'bek 7-uy", save_address=False)
    )
    await session.flush()
    await orders.change_status(third, OrderStatus.CONFIRMED, actor=user)
    await session.refresh(water)
    check("CONFIRMED da qoldiq 97", Decimal(str(water.stock)) == Decimal("97"), water.stock)
    picked = await orders.change_status(third, OrderStatus.PICKING, actor=user)
    await session.refresh(water)
    check(
        "PICKING da qoldiq 94",
        picked.stock_deducted and Decimal(str(water.stock)) == Decimal("94"),
        water.stock,
    )
    await orders.change_status(third, OrderStatus.ON_THE_WAY, actor=user)
    returned = await orders.change_status(third, OrderStatus.RETURNED, actor=user)
    await session.refresh(water)
    check(
        "qaytarishda qoldiq qaytdi",
        returned.stock_released and Decimal(str(water.stock)) == Decimal("97"),
        water.stock,
    )

    # Buyurtmani takrorlash: tarkib savatga qaytadi
    added = await orders.repeat(user.id, third)
    repeated = await cart.summary(user.id)
    check("takrorlash savatga qo'shildi", added == 1 and repeated.positions == 1, added)
    await cart.clear(user.id)

    # Segment: 3 ta yetkazilgan buyurtmadan keyin REGULAR
    for _ in range(2):
        await cart.add(user.id, water, 1)
        extra = await orders.create_from_cart(
            user, CheckoutData(address="Toshkent, test", save_address=False)
        )
        await session.flush()
        for status in (
            OrderStatus.CONFIRMED,
            OrderStatus.PICKING,
            OrderStatus.ON_THE_WAY,
            OrderStatus.DELIVERED,
        ):
            await orders.change_status(extra, status, actor=user)
    customer = await CustomerRepository(session).get_by_user_id(user.id)
    check(
        "mijoz segmenti yangilandi",
        customer is not None and str(customer.segment) == CustomerSegment.REGULAR.value,
        customer.segment if customer else None,
    )

    # Statistika va sahifalash
    stats = await orders.stats()
    check("kunlik statistika", stats["orders"] >= 4, stats["orders"])
    check("statistikada top ro'yxat", isinstance(stats["top"], list), stats["top"][:1])
    page_orders, page_info = await orders.page_for_user(user.id, page=1, per_page=2)
    check("mijoz buyurtmalari sahifasi", len(page_orders) == 2 and page_info.total >= 4)
    search = await orders.search("ORD-", limit=5)
    check("buyurtma qidiruvi", len(search) == 5, len(search))
    counts = await orders.active_order_counts()
    check("faol buyurtmalar soni", set(counts) == {"new", "active"}, counts)
    return orders


async def smoke_support_settings(session, settings: Settings, user, orders):
    """Qo'llab-quvvatlash va sozlamalar servislarini tekshiradi."""
    support = SupportService(session)
    try:
        await support.create(user, "sal")
        check("qisqa murojaat rad etildi", False)
    except SupportTooShortError:
        check("qisqa murojaat rad etildi", True)

    request = await support.create(user, "Buyurtmam qachon yetib keladi?")
    check("murojaat yaratildi", request.id is not None and request.user is not None)
    items, pagination = await support.open_page(page=1, per_page=5)
    check("ochiq murojaatlar", pagination.total == 1 and len(items) == 1)
    answered = await support.answer(request.id, "Bugun 18:00 gacha yetkaziladi.", actor=user)
    check("javob saqlandi", answered.answer is not None and answered.answered_at is not None)
    check("ochiq murojaatlar bo'shadi", await support.count_open() == 0)
    await support.close(answered)
    check("murojaat yopildi", str(answered.status) == "closed", answered.status)

    config = SettingsService(session, settings)
    values = await config.all()
    check("sozlamalar to'plami", values["order_prefix"] == "ORD" and "working_hours" in values)
    await config.set("working_hours", "10:00-20:00")
    fresh = SettingsService(session, settings)
    check("sozlama saqlandi", await fresh.get("working_hours") == "10:00-20:00")
    check(
        "narx sozlamalari Decimal",
        await config.delivery_fee() == Decimal("15000"),
        await config.delivery_fee(),
    )
    info = await config.info()
    check("ma'lumot bo'limi", info["brand_name"] and info["working_hours"])


async def smoke_notifications(session, settings: Settings, user, orders, product):
    """Bildirishnomalar: xodimlarga va mijozga xabar yuborilishi."""
    bot = StubBot()
    notify = NotificationService(bot, session, settings)
    recipient_ids = await notify.staff_chat_ids()
    check("xodim chati ID lari", sorted(recipient_ids) == [555, 9001], recipient_ids)

    order = (await orders.page_for_user(user.id, page=1, per_page=1))[0][0]
    sent_to_staff = await notify.order_created(order)
    check("yangi buyurtma xodimlarga", sent_to_staff == 2, sent_to_staff)

    ok = await notify.status_changed(order, OrderStatus.DELIVERED)
    check("mijozga holat xabari", ok and bot.sent[-1][0] == 1001, bot.sent[-1][1][:60])
    ok = await notify.order_cancelled(order, reason="Test sabab")
    check("mijozga bekor xabari", ok and "Test sabab" in bot.sent[-1][1])

    request = await SupportService(session).create(user, "Yetkazish vaqti qanday?")
    sent = await notify.support_created(request)
    check("yangi murojaat xodimlarga", sent == 2, sent)
    request = await SupportService(session).answer(request.id, "09:00 dan 19:00 gacha.", actor=user)
    ok = await notify.support_answered(request)
    check("mijozga javob xabari", ok and "19:00" in bot.sent[-1][1])

    sent = await notify.low_stock([product])
    check("kam qoldiq xabari", sent == 2, sent)
    check("jurnal yozuvlari", len(bot.sent) >= 8, len(bot.sent))

    # Mijoz izohi xodimga ko'rinishi kerak (xabarda ham, kartochkada ham).
    page, _ = await orders.page_for_user(user.id, page=1, per_page=20)
    commented = next((item for item in page if item.comment), None)
    check("izohli buyurtma topildi", commented is not None)
    if commented is not None:
        bot.sent.clear()
        await notify.order_created(commented)
        check(
            "izoh xodim xabarida",
            any("Smoke test" in text for _chat_id, text in bot.sent),
        )
        caption = pr.staff_order_caption(translator("uz"), commented, settings.currency)
        check("izoh xodim kartochkasida", "Smoke test" in caption, caption[-40:])


async def run() -> int:
    if DB_PATH.exists():
        DB_PATH.unlink()
    settings = Settings(
        bot_token="1:smoke",
        admin_ids=[9001],
        support_chat_id=555,
        min_order_amount=Decimal("1000"),
        _env_file=None,
    )
    engine = create_engine(DB_URL)
    await init_models(engine)
    pool = create_session_pool(engine)
    try:
        async with pool() as session:
            user, category, water, juice = await seed(session, settings)
            cart = await smoke_catalog_cart(
                session, settings, user, category, water, juice
            )
            orders = await smoke_orders(session, settings, cart, user, water, juice)
            await smoke_support_settings(session, settings, user, orders)
            await smoke_notifications(session, settings, user, orders, juice)
            await session.commit()
    finally:
        await dispose_engine(engine)

    print()
    if FAILURES:
        print("XATOLAR:", len(FAILURES), FAILURES)
        return 1
    print("SMOKE OK: barcha tekshiruvlar muvaffaqiyatli o'tdi.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))



