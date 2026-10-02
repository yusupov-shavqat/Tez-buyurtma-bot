"""Demo (soxta) katalog: bazaga namunaviy ma'lumot qo'shish va ekranlarni ko'rsatish.

Ishlatilishi (loyiha ildizidan)::

    .venv\\Scripts\\python.exe scripts\\seed_demo.py             # demo ma'lumot qo'shadi
    .venv\\Scripts\\python.exe scripts\\seed_demo.py --preview   # qo'shib, Telegram ko'rinishini chop etadi
    .venv\\Scripts\\python.exe scripts\\seed_demo.py --preview --raw
    .venv\\Scripts\\python.exe scripts\\seed_demo.py --reset     # faqat DEMO-* yozuvlarni o'chiradi

Ma'lumot `.env` dagi `DATABASE_URL` bazasiga - ya'ni bot ishlatayotgan bazaning
o'ziga yoziladi. Barcha demo mahsulotlarning artikuli `DEMO-` bilan boshlanadi,
shuning uchun `--reset` faqat shu yozuvlarni o'chiradi (haqiqiy katalogga tegmaydi).

`--preview` tarmoqqa chiqmaydi: Bot API so'rovlari `StubSession` orqali ushlab
qolinadi va ekranga «bot nima yuborardi» ko'rinishida chop etiladi. Shu sababli
uni bot tokenisiz ham ishlatish mumkin va hech kimga xabar ketmaydi.

Eslatma: mahsulot rasmi (`image_file_id`) faqat Telegram'dan olingan file_id
bilan ishlaydi, shuning uchun demo mahsulotlar rasmiz ko'rsatiladi.
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Konsol kodlashidan (cp1251/cp866) qat'i nazar emoji va kirill matnlar chiqishi uchun.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aiogram import Bot  # noqa: E402
from aiogram.client.session.base import BaseSession  # noqa: E402
from aiogram.methods import (  # noqa: E402
    AnswerCallbackQuery,
    DeleteMessage,
    EditMessageText,
    SendMessage,
    TelegramMethod,
)
from aiogram.types import (  # noqa: E402
    CallbackQuery,
    Chat,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    Update,
    User as TelegramUser,
)

from bot.config import Settings, get_settings  # noqa: E402
from bot.database.base import (  # noqa: E402
    create_engine,
    create_session_pool,
    dispose_engine,
    init_models,
)
from bot.database.enums import Unit  # noqa: E402
from bot.database.models import Product  # noqa: E402
from bot.database.repositories.catalog import (  # noqa: E402
    CategoryRepository,
    ProductRepository,
)
from bot.database.repositories.users import UserRepository  # noqa: E402
from bot.keyboards import CartCB, CatalogCB, CheckoutCB, ProductCB  # noqa: E402
from bot.locales import translate  # noqa: E402
from bot.services import CartService  # noqa: E402
from bot.utils.money import to_decimal  # noqa: E402
from main import build_dispatcher  # noqa: E402

#: Demo mahsulotlar artikuli shu qator bilan boshlanadi (`--reset` shularni o'chiradi).
SKU_PREFIX = "DEMO-"

#: `--preview` uchun namunaviy mijoz (bazada yaratiladi, `--reset` uni ham o'chiradi).
PREVIEW_CLIENT_ID = 777_000_111

#: Ekranlar qaysi tilda ko'rsatiladi.
PREVIEW_LANG = "uz"

#: (name_uz, name_ru, emoji, sort_order)
CATEGORIES: tuple[tuple[str, str, str, int], ...] = (
    ("Ichimliklar", "Напитки", "🥤", 10),
    ("Non mahsulotlari", "Хлебобулочные изделия", "🍞", 20),
    ("Sut mahsulotlari", "Молочные продукты", "🥛", 30),
    ("Shirinliklar", "Сладости", "🍫", 40),
    ("Maishiy kimyo", "Бытовая химия", "🧴", 50),
)


@dataclass(frozen=True, slots=True)
class DemoProduct:
    """Bitta demo mahsulot tavsifi (narxlar satr ko'rinishida - Decimal aniq)."""

    sku: str
    name_uz: str
    name_ru: str
    category: str
    price: str
    stock: str
    min_stock: str
    unit: Unit = Unit.PCS
    box_size: int = 1
    discount: str | None = None
    promo: bool = False
    description_uz: str | None = None
    description_ru: str | None = None


PRODUCTS: tuple[DemoProduct, ...] = (
    DemoProduct(
        "DEMO-001", "Suv «Hydrolife» 1.5L", "Вода «Hydrolife» 1.5л",
        "Ichimliklar", "5000", "240", "40",
    ),
    DemoProduct(
        "DEMO-002", "Gazlangan suv 0.5L", "Газированная вода 0.5л",
        "Ichimliklar", "4000", "120", "30",
    ),
    DemoProduct(
        "DEMO-003", "Sharbat «Bliss» 1L (olma)", "Сок «Bliss» 1л (яблоко)",
        "Ichimliklar", "12000", "60", "20",
        discount="9900", promo=True,
        description_uz="Tabiiy olma sharbati, shakar qo'shilmagan.",
        description_ru="Натуральный яблочный сок без сахара.",
    ),
    # Ataylab kam qoldiq - «📉 Kam qoldiq» bo'limi ko'rinishi uchun.
    DemoProduct(
        "DEMO-004", "Kola 1.5L", "Кола 1.5л",
        "Ichimliklar", "10000", "8", "24",
        discount="8500", promo=True,
    ),
    DemoProduct(
        "DEMO-005", "Obi non", "Лепёшка",
        "Non mahsulotlari", "4000", "60", "15",
    ),
    DemoProduct(
        "DEMO-006", "Sirkali bulochka", "Булочка с корицей",
        "Non mahsulotlari", "6500", "35", "10",
    ),
    DemoProduct(
        "DEMO-007", "Sut «MilkPro» 1L", "Молоко «MilkPro» 1л",
        "Sut mahsulotlari", "13000", "80", "20",
        unit=Unit.LITER, box_size=12,
    ),
    # Kam qoldiq
    DemoProduct(
        "DEMO-008", "Qatiq 0.5L", "Кефир 0.5л",
        "Sut mahsulotlari", "9000", "25", "30", unit=Unit.LITER,
    ),
    DemoProduct(
        "DEMO-009", "Tvorog 200g", "Творог 200г",
        "Sut mahsulotlari", "11000", "40", "10", unit=Unit.PACK,
    ),
    DemoProduct(
        "DEMO-010", "Shokolad «Kinder» 20g", "Шоколад «Kinder» 20г",
        "Shirinliklar", "14000", "150", "30", box_size=24,
    ),
    DemoProduct(
        "DEMO-011", "Pechene «Bonu» 400g", "Печенье «Bonu» 400г",
        "Shirinliklar", "18000", "50", "12",
        discount="15000", promo=True,
        description_uz="Uy sharoitida pishirilgan, 8 xil don mahsulotidan.",
        description_ru="Домашнее печенье из 8 видов зерновых.",
    ),
    DemoProduct(
        "DEMO-012", "Konfet «Chamomile»", "Карамель «Chamomile»",
        "Shirinliklar", "32000", "45", "10", unit=Unit.KG,
    ),
    DemoProduct(
        "DEMO-013", "Kir yuvish kukuni 3kg", "Стиральный порошок 3кг",
        "Maishiy kimyo", "45000", "30", "8",
        discount="39900", promo=True,
    ),
    # Kam qoldiq (3 dona)
    DemoProduct(
        "DEMO-014", "Idish yuvish geli 500ml", "Гель для посуды 500мл",
        "Maishiy kimyo", "16000", "3", "10",
    ),
    DemoProduct(
        "DEMO-015", "Salfetka (100 dona)", "Салфетки (100 шт)",
        "Maishiy kimyo", "25000", "15", "5",
        unit=Unit.BOX, box_size=100,
    ),
)



# ------------------------- Baza bilan ishlash --------------------------
async def seed_catalog(session) -> tuple[list[Product], int, int]:
    """Demo kategoriya va mahsulotlarni qo'shadi; (mahsulotlar, +yangi, ~yangilangan).

    Har bir yozuv artikul bo'yicha izlanadi: mavjud bo'lsa nomi/narxi/qoldig'i
    yangilanadi, bo'lmasa yaratiladi. Shu sababli skriptni qayta ishga tushirish
    xavfsiz - dublikat yaratilmaydi.
    """
    categories = CategoryRepository(session)
    products = ProductRepository(session)

    category_ids: dict[str, int] = {}
    for name_uz, name_ru, emoji, sort_order in CATEGORIES:
        category = await categories.get_by_name(name_uz)
        if category is None:
            category = await categories.create(
                name_uz, name_ru, emoji=emoji, sort_order=sort_order
            )
        category_ids[name_uz] = category.id

    created = updated = 0
    saved: list[Product] = []
    for index, demo in enumerate(PRODUCTS, start=1):
        product = await products.get_by_sku(demo.sku)
        if product is None:
            product = Product(sku=demo.sku)
            session.add(product)
            created += 1
        else:
            updated += 1
        product.category_id = category_ids[demo.category]
        product.name_uz = demo.name_uz
        product.name_ru = demo.name_ru
        product.price = to_decimal(demo.price)
        product.discount_price = to_decimal(demo.discount) if demo.discount else None
        product.description_uz = demo.description_uz
        product.description_ru = demo.description_ru
        product.unit = demo.unit
        product.box_size = max(int(demo.box_size), 1)
        product.stock = to_decimal(demo.stock)
        product.min_stock = to_decimal(demo.min_stock)
        product.is_promo = demo.promo
        product.is_active = True
        product.sort_order = index * 10
        saved.append(product)

    await session.commit()
    return saved, created, updated


async def reset_demo(session) -> None:
    """Faqat `DEMO-*` mahsulotlar, bo'sh qolgan demo kategoriyalar va namunaviy mijoz."""
    products = ProductRepository(session)
    categories = CategoryRepository(session)

    removed_products = await products.delete_where(Product.sku.like(f"{SKU_PREFIX}%"))
    removed_categories = 0
    for name_uz, *_ in CATEGORIES:
        category = await categories.get_by_name(name_uz)
        if category is None:
            continue
        if await products.count(Product.category_id == category.id) == 0:
            await categories.delete(category)
            removed_categories += 1

    removed_client = False
    users = UserRepository(session)
    client = await users.get_by_telegram_id(PREVIEW_CLIENT_ID)
    if client is not None:
        try:
            await session.delete(client)
            removed_client = True
        except Exception as error:  # pragma: no cover - bog'langan buyurtma bo'lsa
            print(f"Namunaviy mijoz o'chirilmadi: {error}")
    await session.commit()
    print(
        f"O'chirildi: {removed_products} mahsulot, {removed_categories} kategoriya"
        + (", 1 namunaviy mijoz." if removed_client else ".")
    )


async def report(session, title: str) -> None:
    """Bazadagi katalog holatini qisqa ko'rinishda chop etadi."""
    categories = CategoryRepository(session)
    products = ProductRepository(session)
    counts = await categories.product_counts()
    print(f"\n{title}")
    cards = await categories.list_active()
    for category in cards:
        print(
            f"  • {category.emoji} {category.name_uz} — "
            f"{counts.get(category.id, 0)} ta mahsulot"
        )
    print(
        f"  jami: {await products.count_total()} mahsulot "
        f"({await products.count_promo()} aksiyada, "
        f"{len(await products.list_low_stock())} kam qoldiq)"
    )


# ------------------------- Bot ekranlari (preview) ---------------------
#: HTML teglar (konsolda o'qish uchun olib tashlanadi).
_TAG_RE = re.compile(r"</?[a-z][^>]*>")

#: Preview uchun soxta bot tokeni - tarmoqqa chiqilmaydi.
FAKE_TOKEN = "42:" + "A" * 35


class StubSession(BaseSession):
    """Bot API so'rovlarini ushlab qoladi va ro'yxatini saqlaydi."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[TelegramMethod[Any]] = []

    async def close(self) -> None:  # pragma: no cover - yopiladigan narsa yo'q
        return None

    async def make_request(
        self, bot: Bot, method: TelegramMethod[Any], timeout: int | None = None
    ) -> Any:
        self.calls.append(method)
        return True

    async def stream_content(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        yield b""

    def clear(self) -> None:
        self.calls.clear()

    def inline_markup(self) -> InlineKeyboardMarkup | None:
        """Oxirgi yuborilgan/tahrirlangan xabarning inline klaviaturasi."""
        for call in reversed(self.calls):
            markup = getattr(call, "reply_markup", None)
            if isinstance(markup, InlineKeyboardMarkup):
                return markup
        return None


def plain(text: str) -> str:
    """HTML teglarni olib tashlaydi (konsolda o'qish uchun)."""
    return _TAG_RE.sub("", text or "").strip()


def keyboard_rows(markup: object) -> list[list[str]]:
    """Klaviatura tugmalarini matn ko'rinishida qaytaradi."""
    if isinstance(markup, InlineKeyboardMarkup):
        return [[button.text for button in row] for row in markup.inline_keyboard]
    if isinstance(markup, ReplyKeyboardMarkup):
        return [[button.text for button in row] for row in markup.keyboard]
    return []


class Transcript:
    """Bot yuborgan xabarlarni «Telegram'da qanday ko'rinadi» shaklida chop etadi."""

    def __init__(self, api: StubSession, *, raw: bool = False) -> None:
        self.api = api
        self.raw = raw
        self.step = 0

    def show(self, title: str) -> None:
        """Joriy qadamda yuborilgan barcha xabarlarni chiqaradi."""
        self.step += 1
        print(f"\n{'-' * 68}\n{self.step}) {title}\n{'-' * 68}")
        for call in self.api.calls:
            self._render(call)

    def _render(self, call: TelegramMethod[Any]) -> None:
        if isinstance(call, SendMessage):
            self._message("yangi xabar", call.text, call.reply_markup)
        elif isinstance(call, EditMessageText):
            self._message("xabar tahrirlandi", call.text, call.reply_markup)
        elif isinstance(call, AnswerCallbackQuery):
            print(f"      ⚡ tugma javobi: {call.text or '(jimgina)'}")
        elif isinstance(call, DeleteMessage):
            print("      🗑 menyu xabari o'chirildi")
        else:  # pragma: no cover - boshqa metodlar preview'da uchramaydi
            print(f"      • {type(call).__name__}")

    def _message(self, header: str, text: str | None, markup: object) -> None:
        body = (text or "") if self.raw else plain(text or "")
        print(f"\n   🤖 {header}:")
        for line in (body.splitlines() or [""]):
            print(f"      {line}")
        rows = keyboard_rows(markup)
        if rows:
            print("      ── tugmalar:")
            for row in rows:
                print("      [ " + " ]  [ ".join(row) + " ]")


def telegram_user(user_id: int) -> TelegramUser:
    return TelegramUser(
        id=user_id, is_bot=False, first_name="Demo Mijoz", language_code=PREVIEW_LANG
    )


def message_update(update_id: int, user_id: int, text: str) -> Update:
    """Foydalanuvchi matn (yoki reply tugma) yuborganini imitatsiya qiladi."""
    return Update(
        update_id=update_id,
        message=Message(
            message_id=update_id,
            date=datetime.now(tz=timezone.utc),
            chat=Chat(id=user_id, type="private"),
            from_user=telegram_user(user_id),
            text=text,
        ),
    )


def callback_update(update_id: int, user_id: int, data: str) -> Update:
    """Inline tugma bosilganini imitatsiya qiladi."""
    return Update(
        update_id=update_id,
        callback_query=CallbackQuery(
            id=str(update_id),
            from_user=telegram_user(user_id),
            chat_instance="preview",
            data=data,
            message=Message(
                message_id=update_id,
                date=datetime.now(tz=timezone.utc),
                chat=Chat(id=user_id, type="private"),
                from_user=TelegramUser(id=1, is_bot=True, first_name="Bot"),
                text="preview",
            ),
        ),
    )


def find_callback(api: StubSession, callback_type: type, action: str, **fields: Any) -> tuple[str, str]:
    """Oxirgi klaviaturadan kerakli tugmani topadi: (matn, callback data)."""
    markup = api.inline_markup()
    if markup is None:
        raise RuntimeError("oxirgi xabarda inline klaviatura yo'q")
    for row in markup.inline_keyboard:
        for button in row:
            data = button.callback_data
            if not data:
                continue
            try:
                parsed = callback_type.unpack(data)
            except (ValueError, TypeError, KeyError):
                continue
            if parsed.action != action:
                continue
            if any(getattr(parsed, name) != value for name, value in fields.items()):
                continue
            return button.text, data
    raise RuntimeError(f"«{action}» amali bo'lgan tugma topilmadi")


# ------------------------- Preview oqimi -------------------------------
async def run_preview(
    settings: Settings, session_pool: Any, products: Sequence[Product], *, raw: bool = False
) -> None:
    """Katalog oqimini tarmoqsiz «ijro etadi» va har bir ekranni chop etadi."""
    ids = {product.sku: product.id for product in products}
    promo_id = ids.get("DEMO-003")
    if promo_id is None:  # pragma: no cover - DEMO-003 ro'yxatda doim bor
        raise SystemExit("DEMO-003 topilmadi - `--seed` bilan demo ma'lumot qo'shing.")

    async with session_pool() as session:
        users = UserRepository(session)
        user, _ = await users.get_or_create(
            PREVIEW_CLIENT_ID,
            username="demo_preview",
            full_name="Demo Mijoz",
            chat_id=PREVIEW_CLIENT_ID,
        )
        if not user.has_phone:
            await users.set_phone(user, "+998900000000")
        dropped = await CartService(session, settings).clear(user.id)
        await session.commit()
    if dropped:
        print(f"(avvalgi preview'dan qolgan {dropped} savat pozitsiyasi tozalandi)")

    api = StubSession()
    bot = Bot(token=FAKE_TOKEN, session=api)
    dispatcher = build_dispatcher(settings, session_pool)
    view = Transcript(api, raw=raw)

    def tr(key: str, **kwargs: Any) -> str:
        return translate(key, PREVIEW_LANG, **kwargs)

    async def step(title: str, update: Update) -> None:
        api.clear()
        await dispatcher.feed_update(bot, update)
        view.show(title)

    catalog_label = tr("btn_catalog")
    promo_label = tr("btn_promo")
    cart_label = tr("btn_cart")

    print(f"\n{'=' * 68}\nBOT EKRANLARI — {settings.brand_name}\n{'=' * 68}")
    try:
        await step(
            "/start (mijoz allaqachon ro'yxatdan o'tgan)",
            message_update(1, PREVIEW_CLIENT_ID, "/start"),
        )
        await step(
            f"reply tugma: «{catalog_label}»",
            message_update(2, PREVIEW_CLIENT_ID, catalog_label),
        )

        category_label, data = find_callback(api, CatalogCB, "category")
        await step(
            f"kategoriya tanlandi: «{category_label}»",
            callback_update(3, PREVIEW_CLIENT_ID, data),
        )

        product_label, data = find_callback(api, ProductCB, "open", product_id=promo_id)
        await step(
            f"mahsulot kartochkasi: «{product_label}»",
            callback_update(4, PREVIEW_CLIENT_ID, data),
        )

        _, data = find_callback(api, ProductCB, "add", product_id=promo_id)
        await step("«➕ Savatga qo'shish»", callback_update(5, PREVIEW_CLIENT_ID, data))

        _, data = find_callback(api, ProductCB, "qty", value=10)
        await step(
            "miqdor tanlandi (10 dona) → savat",
            callback_update(6, PREVIEW_CLIENT_ID, data),
        )

        await step(
            f"reply tugma: «{promo_label}»",
            message_update(7, PREVIEW_CLIENT_ID, promo_label),
        )
        await step(
            f"reply tugma: «{cart_label}»",
            message_update(8, PREVIEW_CLIENT_ID, cart_label),
        )

        checkout_label, data = find_callback(api, CartCB, "checkout")
        await step(f"«{checkout_label}»", callback_update(9, PREVIEW_CLIENT_ID, data))

        delivery_label, data = find_callback(api, CheckoutCB, "delivery")
        await step(
            f"«{delivery_label}» — manzil qadami",
            callback_update(10, PREVIEW_CLIENT_ID, data),
        )
    finally:
        await bot.session.close()
        async with session_pool() as session:
            preview_user = await UserRepository(session).get_by_telegram_id(PREVIEW_CLIENT_ID)
            if preview_user is not None:
                await CartService(session, settings).clear(preview_user.id)
                await session.commit()


# ------------------------- CLI -----------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """Buyruq qatori argumentlari."""
    parser = argparse.ArgumentParser(
        description="Demo (soxta) katalog ma'lumotlarini bazaga qo'shadi.",
    )
    parser.add_argument(
        "--preview", action="store_true", help="qo'shgandan keyin bot ekranlarini chop etadi"
    )
    parser.add_argument(
        "--raw", action="store_true", help="xabarlarni HTML teglari bilan chiqaradi"
    )
    parser.add_argument(
        "--seed", action="store_true", help="demo ma'lumotni qo'shadi (standart amal)"
    )
    parser.add_argument(
        "--reset", action="store_true", help="faqat DEMO-* yozuvlarni o'chiradi"
    )
    return parser


async def main() -> None:
    """Skriptning kirish nuqtasi."""
    args = build_parser().parse_args()
    # Throttling (RATE_LIMIT_SECONDS) preview'da xalaqit beradi - nusxada 0 qilamiz.
    settings = get_settings().model_copy(update={"rate_limit_seconds": 0.0})
    engine = create_engine(settings.database_url, echo=settings.db_echo)
    await init_models(engine)
    pool = create_session_pool(engine)
    try:
        print(f"Baza: {settings.database_url}")
        if args.reset:
            async with pool() as session:
                await reset_demo(session)
            if not (args.seed or args.preview):
                async with pool() as session:
                    await report(session, "Qolgan katalog:")
                return

        async with pool() as session:
            saved, created, updated = await seed_catalog(session)
            print(
                f"Kategoriya: {len(CATEGORIES)} ta tekshirildi; mahsulot: "
                f"+{created} yangi / {updated} yangilandi."
            )
            await report(session, "Katalog holati:")

        if args.preview:
            await run_preview(settings, pool, saved, raw=args.raw)
        else:
            print("\nBotni ishga tushirib «🛍 Katalog» tugmasini bosing:")
            print("  .venv\\Scripts\\python.exe main.py")
            print("Ekranlarni terminalda ko'rish uchun: --preview (yoki --preview --raw).")
    finally:
        await dispose_engine(engine)


if __name__ == "__main__":
    asyncio.run(main())


__all__ = [
    "CATEGORIES",
    "PREVIEW_CLIENT_ID",
    "PRODUCTS",
    "SKU_PREFIX",
    "DemoProduct",
    "StubSession",
    "build_parser",
    "find_callback",
    "main",
    "report",
    "reset_demo",
    "run_preview",
    "seed_catalog",
]



