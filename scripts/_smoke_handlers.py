"""Handler qatlami smoke-testi: haqiqiy bot tokenisiz /start oqimini tekshiradi.

Bot API so'rovlari `StubSession` orqali ushlanadi (tarmoqqa chiqilmaydi),
baza esa `data/_smoke_handlers.db` faylida yaratiladi.

Ishlatilishi::

    .venv\\Scripts\\python.exe scripts\\_smoke_handlers.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Konsol kodlashidan (cp1251/cp866) qat'i nazar emoji va kirill matnlar chiqishi uchun.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


from aiogram import Bot, Dispatcher  # noqa: E402
from aiogram.client.session.base import BaseSession  # noqa: E402
from aiogram.methods import (  # noqa: E402
    AnswerCallbackQuery,
    EditMessageText,
    GetMe,
    SendMessage,
    SetMyCommands,
    TelegramMethod,
)
from aiogram.types import (  # noqa: E402
    CallbackQuery,
    Chat,
    Contact,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    Update,
    User as TelegramUser,
)
from sqlalchemy.ext.asyncio import AsyncEngine  # noqa: E402

from bot.config import Settings  # noqa: E402
from bot.database.base import (  # noqa: E402
    create_engine,
    create_session_pool,
    dispose_engine,
    init_models,
)
from bot.database.enums import Language, PaymentMethod, UserRole  # noqa: E402
from bot.database.repositories.catalog import (  # noqa: E402
    CategoryRepository,
    ProductRepository,
)
from bot.database.repositories.support import SupportRepository  # noqa: E402
from bot.database.repositories.users import UserRepository  # noqa: E402
from bot.keyboards import (  # noqa: E402
    AdminCB,
    CatalogCB,
    CheckoutCB,
    LangCB,
    MenuCB,
    ProfileCB,
    SupportCB,
)
from bot.locales import translate  # noqa: E402
from bot.services import CartService  # noqa: E402
from bot.services.presenters import role_label  # noqa: E402
from bot.utils.money import round_money  # noqa: E402
from bot.utils.text import escape, format_date, strip_html  # noqa: E402
import main as main_module  # noqa: E402
from main import build_dispatcher  # noqa: E402

DB_PATH = Path("data/_smoke_handlers.db")
DB_URL = "sqlite+aiosqlite:///./data/_smoke_handlers.db"
BRAND = "Smoke Do'kon"
CLIENT = 1001
OTHER = 2002
STAFF = 9001

#: Dispatcher'ga ulanishi kutilayotgan router'lar (tartib - muhim: fallback oxirida).
EXPECTED_ROUTERS = (
    "start",
    "catalog",
    "cart",
    "checkout",
    "orders",
    "profile",
    "support",
    "admin",
    "fallback",
)

FAILURES: list[str] = []


class StubSession(BaseSession):
    """Bot API so'rovlarini ushlab qoladi (tarmoqqa chiqmaydi)."""

    def __init__(self, responses: dict[type, Any] | None = None) -> None:
        super().__init__()
        self.calls: list[TelegramMethod[Any]] = []
        self.responses: dict[type, Any] = responses or {}

    async def close(self) -> None:  # pragma: no cover - yopadigan narsa yo'q
        return None

    async def make_request(
        self, bot: Bot, method: TelegramMethod[Any], timeout: int | None = None
    ) -> Any:
        self.calls.append(method)
        for method_type, value in self.responses.items():
            if isinstance(method, method_type):
                return value
        return True

    async def stream_content(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        yield b""

    def of(self, method_type: type) -> list[Any]:
        return [call for call in self.calls if isinstance(call, method_type)]

    def clear(self) -> None:
        self.calls.clear()


def check(label: str, condition: bool, extra: object = "") -> None:
    print(f"[{'OK  ' if condition else 'FAIL'}] {label} {extra}")
    if not condition:
        FAILURES.append(label)


def button_labels(markup: InlineKeyboardMarkup | None) -> list[str]:
    """Klaviaturadagi barcha tugma matnlarini qaytaradi."""
    if markup is None:
        return []
    return [button.text for row in markup.inline_keyboard for button in row]


def find_button(markup: InlineKeyboardMarkup | None, text: str) -> str | None:
    """Klaviaturadan matni bo'yicha tugma callback data'sini topadi."""
    if markup is None:
        return None
    for row in markup.inline_keyboard:
        for button in row:
            if button.text == text:
                return button.callback_data
    return None


def clean_db(db_path: Path) -> None:
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(db_path) + suffix)
        if candidate.exists():
            candidate.unlink()


def telegram_user(user_id: int, language_code: str | None) -> TelegramUser:
    return TelegramUser(
        id=user_id, is_bot=False, first_name=f"User {user_id}", language_code=language_code
    )


def message_update(
    update_id: int,
    user_id: int,
    text: str | None = None,
    *,
    language_code: str | None = "uz",
    contact: Contact | None = None,
) -> Update:
    return Update(
        update_id=update_id,
        message=Message(
            message_id=update_id,
            date=datetime.now(tz=timezone.utc),
            chat=Chat(id=user_id, type="private"),
            from_user=telegram_user(user_id, language_code),
            text=text,
            contact=contact,
        ),
    )


def callback_update(
    update_id: int, user_id: int, data: str, *, language_code: str | None = "uz"
) -> Update:
    return Update(
        update_id=update_id,
        callback_query=CallbackQuery(
            id=str(update_id),
            from_user=telegram_user(user_id, language_code),
            chat_instance="smoke",
            data=data,
            message=Message(
                message_id=update_id,
                date=datetime.now(tz=timezone.utc),
                chat=Chat(id=user_id, type="private"),
                from_user=TelegramUser(id=999, is_bot=True, first_name="SmokeBot"),
                text="menu",
            ),
        ),
    )


async def feed_callback(
    dispatcher: Dispatcher,
    bot: Bot,
    api: StubSession,
    update_id: int,
    user_id: int,
    data: str,
) -> None:
    """Callback'ni yuboradi va oldingi chaqiruvlar jurnalini tozalaydi."""
    api.clear()
    await dispatcher.feed_update(bot, callback_update(update_id, user_id, data))


async def finish(engine: AsyncEngine) -> None:
    """Bazani yopadi, yakuniy hisobotni chop etadi va kerak bo'lsa xato kodini qaytaradi."""
    await dispose_engine(engine)
    print("=" * 64)
    if FAILURES:
        print(f"XATO: {len(FAILURES)} ta tekshiruv muvaffaqiyatsiz:")
        for label in FAILURES:
            print("  -", label)
        raise SystemExit(1)
    print("Barcha tekshiruvlar muvaffaqiyatli o'tdi ✅")


async def main() -> None:
    clean_db(DB_PATH)

    settings = Settings(
        database_url=DB_URL,
        admin_ids=[STAFF],
        rate_limit_seconds=0.0,
        brand_name=BRAND,
    )
    engine = create_engine(DB_URL)
    await init_models(engine)
    pool = create_session_pool(engine)
    api = StubSession()
    bot = Bot(token="42:" + "A" * 35, session=api)
    dispatcher = build_dispatcher(settings, pool)

    check(
        "router'lar ulandi (start + bo'limlar + fallback)",
        tuple(router.name for router in dispatcher.sub_routers) == EXPECTED_ROUTERS,
        [router.name for router in dispatcher.sub_routers],
    )
    check(
        "resolve_used_update_types() ishlaydi",
        bool(dispatcher.resolve_used_update_types()),
        dispatcher.resolve_used_update_types(),
    )
    second = build_dispatcher(settings, pool)
    check(
        "dispatcher qayta qurilishi mumkin (router'lar yangi nusxada)",
        tuple(r.name for r in second.sub_routers) == EXPECTED_ROUTERS
        and all(
            first is not other
            for first, other in zip(dispatcher.sub_routers, second.sub_routers)
        ),
    )

    # ---------------- 1. /start: yangi mijoz ----------------------------
    await dispatcher.feed_update(bot, message_update(1, CLIENT, "/start"))
    sent = api.of(SendMessage)
    check("1) /start: 2 ta xabar (salom + raqam so'rash)", len(sent) == 2, len(sent))
    check(
        "1) /start: brend bilan salomlashish",
        bool(sent) and sent[0].text == translate("start_welcome", "uz", brand=BRAND),
        sent[0].text[:40] if sent else "",
    )
    check(
        "1) /start: asosiy menyu reply klaviaturasi",
        bool(sent)
        and isinstance(sent[0].reply_markup, ReplyKeyboardMarkup)
        and sent[0].reply_markup.keyboard[0][0].text == translate("btn_catalog", "uz"),
    )
    check(
        "1) /start: kontakt tugmasi va «Bekor qilish»",
        len(sent) == 2
        and sent[1].text == translate("start_ask_phone", "uz")
        and sent[1].reply_markup.keyboard[0][0].request_contact is True
        and sent[1].reply_markup.keyboard[-1][0].text == translate("btn_cancel", "uz"),
    )

    async with pool() as session:
        saved = await UserRepository(session).get_with_customer(CLIENT)
    check(
        "1) baza: foydalanuvchi + mijoz kartochkasi yaratildi",
        saved is not None and saved.customer is not None,
    )
    check("1) baza: telefon hali yo'q", saved is not None and not saved.has_phone)

    # ---------------- 2. Noto'g'ri matn ---------------------------------
    api.clear()
    await dispatcher.feed_update(bot, message_update(2, CLIENT, "salom"))
    sent = api.of(SendMessage)
    check(
        "2) raqam kutish holatida noto'g'ri matn ogohlantirildi",
        len(sent) == 1 and sent[0].text == translate("phone_invalid", "uz"),
        [m.text for m in sent],
    )

    # ---------------- 3. Boshqa odamning kontaktі ------------------------
    api.clear()
    await dispatcher.feed_update(
        bot,
        message_update(
            3,
            CLIENT,
            contact=Contact(
                phone_number="+998900000000", first_name="Boshqa", user_id=OTHER
            ),
        ),
    )
    sent = api.of(SendMessage)
    check(
        "3) boshqa odamning kontaktі rad etildi",
        len(sent) == 1 and sent[0].text == translate("phone_wrong_owner", "uz"),
        [m.text for m in sent],
    )

    # ---------------- 4. Raqamni matn bilan yuborish --------------------
    api.clear()
    await dispatcher.feed_update(bot, message_update(4, CLIENT, "90 123 45 67"))
    sent = api.of(SendMessage)
    check(
        "4) matn bilan raqam qabul qilindi (+998 formatida)",
        len(sent) == 1
        and sent[0].text == translate("phone_received", "uz", phone="+998901234567"),
        [m.text for m in sent],
    )
    async with pool() as session:
        saved = await UserRepository(session).get_with_customer(CLIENT)
    check(
        "4) baza: raqam saqlandi",
        saved is not None and saved.phone == "+998901234567",
        getattr(saved, "phone", None),
    )

    # ---------------- 5. Holat tozalandi + katalog bo'limi ---------------
    api.clear()
    await dispatcher.feed_update(
        bot, message_update(5, CLIENT, translate("btn_catalog", "uz"))
    )
    sent = api.of(SendMessage)
    check(
        "5) raqamdan keyin holat tozalandi (katalog bo'limi javob berdi)",
        len(sent) == 1 and sent[0].text == translate("catalog_empty", "uz"),
        [m.text for m in sent],
    )

    # ---------------- 6. /help ------------------------------------------
    api.clear()
    await dispatcher.feed_update(bot, message_update(6, CLIENT, "/help"))
    sent = api.of(SendMessage)
    check(
        "6) /help: yordam matni (foydalanuvchi tilida)",
        len(sent) == 1 and sent[0].text == translate("help_text", "uz"),
        sent[0].text[:40] if sent else "",
    )
    check(
        "6) /help: menyu klaviaturasi birga yuborildi",
        len(sent) == 1 and isinstance(sent[0].reply_markup, ReplyKeyboardMarkup),
    )

    # ---------------- 7. /myid ------------------------------------------
    api.clear()
    await dispatcher.feed_update(bot, message_update(7, CLIENT, "/myid"))
    sent = api.of(SendMessage)
    check(
        "7) /myid: Telegram ID ko'rsatildi",
        len(sent) == 1 and sent[0].text == translate("my_id", "uz", id=CLIENT),
        sent[0].text if sent else "",
    )

    # ---------------- 8. /language --------------------------------------
    api.clear()
    await dispatcher.feed_update(bot, message_update(8, CLIENT, "/language"))
    sent = api.of(SendMessage)
    markup = sent[0].reply_markup if sent else None
    check(
        "8) /language: til tanlash klaviaturasi",
        len(sent) == 1 and sent[0].text == translate("start_language_title", "uz"),
    )
    check(
        "8) /language: ru tugmasining callback ma'lumoti",
        markup is not None
        and markup.inline_keyboard[0][1].callback_data
        == LangCB(action="set", code="ru").pack(),
        getattr(markup.inline_keyboard[0][1], "callback_data", None) if markup else None,
    )

    # ---------------- 9. Tilni almashtirish (callback) ------------------
    name = saved.display_name if saved is not None else ""
    api.clear()
    await dispatcher.feed_update(
        bot, callback_update(9, CLIENT, LangCB(action="set", code="ru").pack())
    )
    answers = api.of(AnswerCallbackQuery)
    check(
        "9) til: toast «Til o'zgartirildi» (ruscha, HTML tegsiz)",
        bool(answers)
        and answers[0].text
        == strip_html(
            translate("lang_changed", "ru", language=translate("lang_name", "ru"))
        ),
        [a.text for a in answers],
    )
    edited = api.of(EditMessageText)
    check(
        "9) til: xabar ruscha salomlashishga o'zgartirildi",
        bool(edited) and edited[0].text == translate("welcome_back", "ru", name=name),
        edited[0].text if edited else "",
    )
    sent = api.of(SendMessage)
    check(
        "9) til: ruscha reply klaviatura yangi xabar bilan yuborildi",
        len(sent) == 1
        and sent[0].text == translate("start_menu_hint", "ru")
        and isinstance(sent[0].reply_markup, ReplyKeyboardMarkup)
        and sent[0].reply_markup.keyboard[0][0].text == translate("btn_catalog", "ru"),
        [m.text for m in sent],
    )
    async with pool() as session:
        after = await UserRepository(session).get_by_telegram_id(CLIENT)
    check(
        "9) baza: til «ru» bo'lib saqlandi",
        after is not None and after.language == Language.RU,
        getattr(after, "language", None),
    )

    # ---------------- 10. Til saqlandi + raqam qayta so'ralmaydi --------
    api.clear()
    await dispatcher.feed_update(bot, message_update(10, CLIENT, "/start"))
    sent = api.of(SendMessage)
    check(
        "10) /start: ruscha salomlashish (til bazadan olindi)",
        len(sent) == 1 and sent[0].text == translate("welcome_back", "ru", name=name),
        [m.text for m in sent],
    )

    # ---------------- 11. Noma'lum callback -----------------------------
    api.clear()
    await dispatcher.feed_update(bot, callback_update(11, CLIENT, "nomalum:1"))
    check("11) noma'lum callback: «yuklanmoqda» to'xtatildi", bool(api.of(AnswerCallbackQuery)))

    # ---------------- 12. Xodim (admin) ---------------------------------
    api.clear()
    await dispatcher.feed_update(bot, message_update(12, STAFF, "/start"))
    sent = api.of(SendMessage)
    check("12) xodim: 3 ta xabar (salom + rejim + raqam)", len(sent) == 3, len(sent))
    check(
        "12) xodim: menyuda «Boshqaruv» qatori",
        len(sent) == 3
        and sent[0].reply_markup.keyboard[-1][0].text == translate("btn_admin", "uz"),
    )
    staff_role = role_label(lambda key: translate(key, "uz"), UserRole.ADMIN)
    check(
        "12) xodim: rol nomi bilan xabar",
        len(sent) == 3
        and sent[1].text == translate("admin_welcome_staff", "uz", role=staff_role),
        sent[1].text if len(sent) == 3 else "",
    )
    async with pool() as session:
        staff_user = await UserRepository(session).get_by_telegram_id(STAFF)
    check(
        "12) baza: admin roli berildi",
        staff_user is not None and staff_user.role is UserRole.ADMIN,
        getattr(staff_user, "role", None),
    )

    # ---------------- 13. «Bekor qilish» bilan raqam so'rashni to'xtatish
    api.clear()
    await dispatcher.feed_update(bot, message_update(13, 3003, "/start"))
    check(
        "13) yangi mijoz: salom + raqam so'rash",
        len(api.of(SendMessage)) == 2,
        len(api.of(SendMessage)),
    )
    api.clear()
    await dispatcher.feed_update(bot, message_update(14, 3003, translate("btn_cancel", "uz")))
    sent = api.of(SendMessage)
    check(
        "13) «Bekor qilish»: menyu ochildi, raqam qayta so'ralmadi",
        len(sent) == 1 and sent[0].text == translate("start_welcome", "uz", brand=BRAND),
        [m.text for m in sent],
    )
    api.clear()
    await dispatcher.feed_update(bot, message_update(15, 3003, "salom"))
    sent = api.of(SendMessage)
    check(
        "13) «Bekor qilish» dan keyin holat tozalandi (fallback javobi)",
        len(sent) == 1 and sent[0].text == translate("unknown_message", "uz"),
        [m.text for m in sent],
    )


    # ---------------- 14. Bo'limlarga kirish (reply tugmalari) -----------
    api.clear()
    await dispatcher.feed_update(
        bot, callback_update(16, CLIENT, LangCB(action="set", code="uz").pack())
    )
    check(
        "14) til «uz» ga qaytarildi (keyingi tekshiruvlar o'zbekcha)",
        bool(api.of(EditMessageText)),
    )

    api.clear()
    await dispatcher.feed_update(
        bot, message_update(17, CLIENT, translate("btn_cart", "uz"))
    )
    sent = api.of(SendMessage)
    check(
        "14) «🛒 Savat»: bo'sh savat ekrani (cart router ulandi)",
        len(sent) == 1 and sent[0].text == translate("cart_empty", "uz"),
        [m.text for m in sent],
    )
    markup = sent[0].reply_markup if sent else None
    check(
        "14) bo'sh savatda «🏠 Asosiy menyu» inline tugmasi bor",
        isinstance(markup, InlineKeyboardMarkup)
        and any(
            btn.callback_data == MenuCB(action="main").pack()
            for row in markup.inline_keyboard
            for btn in row
        ),
        markup.inline_keyboard if markup is not None else None,
    )

    api.clear()
    await dispatcher.feed_update(
        bot, callback_update(18, CLIENT, MenuCB(action="main").pack())
    )
    edited = api.of(EditMessageText)
    sent = api.of(SendMessage)
    check(
        "14) inline «🏠 Asosiy menyu» (`MenuCB(action=\"main\")`) ishlaydi",
        bool(api.of(AnswerCallbackQuery))
        and len(edited) == 1
        and len(sent) == 1
        and sent[0].text == translate("start_menu_hint", "uz")
        and isinstance(sent[0].reply_markup, ReplyKeyboardMarkup),
        [m.text for m in sent],
    )

    api.clear()
    await dispatcher.feed_update(
        bot, message_update(19, CLIENT, translate("btn_orders", "uz"))
    )
    sent = api.of(SendMessage)
    check(
        "14) «📦 Buyurtmalarim»: bo'sh ro'yxat (orders router ulandi)",
        len(sent) == 1 and sent[0].text == translate("orders_empty", "uz"),
        [m.text for m in sent],
    )

    api.clear()
    await dispatcher.feed_update(
        bot, message_update(20, CLIENT, translate("btn_promo", "uz"))
    )
    sent = api.of(SendMessage)
    check(
        "14) «🔥 Aksiyalar»: bo'sh aksiya ekrani (catalog router)",
        len(sent) == 1 and sent[0].text == translate("catalog_promo_empty", "uz"),
        [m.text for m in sent],
    )

    # ---------------- 15. Profil bo'limi ---------------------------------
    api.clear()
    await dispatcher.feed_update(
        bot, message_update(21, CLIENT, translate("btn_profile", "uz"))
    )
    sent = api.of(SendMessage)
    check(
        "15) «👤 Profil»: kartochka va inline klaviatura (profile router)",
        len(sent) == 1
        and translate("profile_title", "uz") in sent[0].text
        and translate("profile_phone", "uz", value="+998901234567") in sent[0].text
        and isinstance(sent[0].reply_markup, InlineKeyboardMarkup),
        [m.text for m in sent],
    )
    markup = sent[0].reply_markup if sent else None
    check(
        "15) profil tugmalari (telefon / manzillar)",
        isinstance(markup, InlineKeyboardMarkup)
        and any(
            btn.callback_data in {
                ProfileCB(action="phone").pack(),
                ProfileCB(action="addresses").pack(),
            }
            for row in markup.inline_keyboard
            for btn in row
        ),
    )

    api.clear()
    await dispatcher.feed_update(
        bot, callback_update(22, CLIENT, ProfileCB(action="phone").pack())
    )
    sent = api.of(SendMessage)
    check(
        "15) «📱 Telefonni o'zgartirish»: kontakt klaviaturasi bilan so'raldi",
        len(sent) == 1
        and sent[0].text == translate("profile_phone_prompt", "uz")
        and isinstance(sent[0].reply_markup, ReplyKeyboardMarkup)
        and sent[0].reply_markup.keyboard[0][0].request_contact is True,
        [m.text for m in sent],
    )

    api.clear()
    await dispatcher.feed_update(bot, message_update(23, CLIENT, "90 111 22 33"))
    sent = api.of(SendMessage)
    check(
        "15) profil orqali raqam yangilandi va kartochka qayta ko'rsatildi",
        len(sent) == 2
        and sent[0].text == translate("profile_phone_updated", "uz")
        and translate("profile_phone", "uz", value="+998901112233") in sent[1].text,
        [m.text for m in sent],
    )
    async with pool() as session:
        updated = await UserRepository(session).get_by_telegram_id(CLIENT)
    check(
        "15) baza: yangi raqam saqlandi",
        updated is not None and updated.phone == "+998901112233",
        getattr(updated, "phone", None),
    )

    api.clear()
    await dispatcher.feed_update(
        bot, callback_update(24, CLIENT, ProfileCB(action="addresses").pack())
    )
    edited = api.of(EditMessageText)
    check(
        "15) «📍 Manzillarim»: saqlangan manzil yo'qligi haqida xabar",
        bool(edited) and edited[0].text == translate("profile_addresses_empty", "uz"),
        edited[0].text if edited else "",
    )

    api.clear()
    await dispatcher.feed_update(
        bot, callback_update(25, CLIENT, ProfileCB(action="open").pack())
    )
    edited = api.of(EditMessageText)
    check(
        "15) «⬅️ Orqaga»: profil kartochkasiga qaytish",
        bool(edited) and translate("profile_title", "uz") in edited[0].text,
        edited[0].text if edited else "",
    )

    # ---------------- 16. Qo'llab-quvvatlash -----------------------------
    api.clear()
    await dispatcher.feed_update(
        bot, message_update(26, CLIENT, translate("btn_support", "uz"))
    )
    sent = api.of(SendMessage)
    check(
        "16) «☎️ Yordam»: menyu va inline klaviatura (support router)",
        len(sent) == 1
        and sent[0].text == translate("support_menu", "uz")
        and isinstance(sent[0].reply_markup, InlineKeyboardMarkup),
        [m.text for m in sent],
    )

    api.clear()
    await dispatcher.feed_update(
        bot, callback_update(27, CLIENT, SupportCB(action="call").pack())
    )
    edited = api.of(EditMessageText)
    # Qo'llab-quvvatlash raqami `.env` dan kelishi mumkin - ikkala holat ham qabul qilinadi.
    expected_call = (
        translate("support_call_info", "uz", phone=escape(settings.support_phone))
        if settings.support_phone
        else translate("support_call_missing", "uz")
    )
    check(
        "16) «📞 Telefon orqali»: raqam yoki yo'qligi haqida xabar",
        bool(edited) and edited[0].text == expected_call,
        edited[0].text if edited else "",
    )

    api.clear()
    await dispatcher.feed_update(
        bot, callback_update(28, CLIENT, SupportCB(action="write").pack())
    )
    sent = api.of(SendMessage)
    check(
        "16) «✍️ Operatorga yozish»: matn kutilmoqda",
        len(sent) == 1
        and sent[0].text == translate("support_ask", "uz")
        and isinstance(sent[0].reply_markup, ReplyKeyboardMarkup),
        [m.text for m in sent],
    )

    api.clear()
    await dispatcher.feed_update(bot, message_update(29, CLIENT, "Buyurtmam qayerda?"))
    sent = api.of(SendMessage)
    check(
        "16) murojaat saqlandi: xodimga bildirishnoma + mijozga tasdiq",
        len(sent) == 2
        and sent[0].chat_id == STAFF
        and "Buyurtmam qayerda?" in sent[0].text
        and sent[1].chat_id == CLIENT
        and sent[1].text == translate("support_sent", "uz", id=1),
        [(m.chat_id, m.text[:40]) for m in sent],
    )
    async with pool() as session:
        request = await SupportRepository(session).get(1)
    check(
        "16) baza: murojaat ochiq holda saqlandi",
        request is not None and request.user_id is not None,
        getattr(request, "id", None),
    )

    # ---------------- 17. Xodimlar paneli --------------------------------
    api.clear()
    await dispatcher.feed_update(
        bot, message_update(30, STAFF, translate("btn_admin", "uz"))
    )
    sent = api.of(SendMessage)
    check(
        "17) «🛠 Boshqaruv»: panel va hisoblagichlar (admin router)",
        len(sent) == 1
        and sent[0].text.startswith(translate("admin_menu_title", "uz"))
        and isinstance(sent[0].reply_markup, InlineKeyboardMarkup),
        [m.text for m in sent],
    )

    api.clear()
    await dispatcher.feed_update(
        bot, callback_update(31, STAFF, AdminCB(action="low_stock").pack())
    )
    edited = api.of(EditMessageText)
    check(
        "17) «📉 Kam qoldiq»: mahsulot yo'qligi haqida xabar",
        bool(edited) and edited[0].text == translate("admin_low_stock_empty", "uz"),
        edited[0].text if edited else "",
    )

    api.clear()
    await dispatcher.feed_update(
        bot, callback_update(32, STAFF, AdminCB(action="stats").pack())
    )
    edited = api.of(EditMessageText)
    check(
        "17) «📊 Bugungi statistika»: hisobot ko'rsatildi",
        bool(edited)
        and edited[0].text.startswith(
            translate(
                "admin_stats_title",
                "uz",
                date=format_date(datetime.now(tz=timezone.utc)),
            )
        ),
        edited[0].text.splitlines()[:1] if edited else "",
    )

    api.clear()
    await dispatcher.feed_update(
        bot, callback_update(33, STAFF, AdminCB(action="support").pack())
    )
    edited = api.of(EditMessageText)
    check(
        "17) «☎️ Murojaatlar»: mijoz murojaati ro'yxatda",
        bool(edited)
        and translate("admin_support_title", "uz", count=1) in edited[0].text
        and "Buyurtmam qayerda?" in edited[0].text,
        edited[0].text if edited else "",
    )

    api.clear()
    await dispatcher.feed_update(
        bot,
        callback_update(34, STAFF, AdminCB(action="reply", request_id=1).pack()),
    )
    edited = api.of(EditMessageText)
    check(
        "17) «✍️ Javob berish»: matn so'raldi",
        bool(edited)
        and edited[0].text == translate("admin_reply_prompt", "uz", id=1),
        edited[0].text if edited else "",
    )

    api.clear()
    await dispatcher.feed_update(bot, message_update(35, STAFF, "Tez orada javob beramiz."))
    sent = api.of(SendMessage)
    check(
        "17) javob mijozga yuborildi (support_answered + xodimga tasdiq)",
        len(sent) == 2
        and sent[0].chat_id == CLIENT
        and sent[0].text
        == translate("support_answer", "uz", id=1, answer="Tez orada javob beramiz.")
        and sent[1].chat_id == STAFF
        and sent[1].text == translate("admin_reply_sent", "uz"),
        [(m.chat_id, m.text[:40]) for m in sent],
    )

    api.clear()
    await dispatcher.feed_update(bot, message_update(36, CLIENT, translate("btn_admin", "uz")))
    check(
        "17) mijoz boshqaruv paneliga kira olmadi (faqat xodimlar)",
        translate("admin_staff_only", "uz") in [m.text for m in api.of(SendMessage)],
        [m.text for m in api.of(SendMessage)],
    )

    # ---------------- 18. main.run() integratsiyasi ---------------------
    booted: list[Bot] = []
    polling: dict[str, Any] = {}

    class RecordingBot(Bot):
        """Haqiqiy tarmoq sessiyasini `StubSession` bilan almashtiradi."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            kwargs["session"] = StubSession(
                responses={
                    GetMe: TelegramUser(
                        id=777,
                        is_bot=True,
                        first_name="SmokeBot",
                        username="smoke_bot",
                    )
                }
            )
            super().__init__(*args, **kwargs)
            booted.append(self)

    async def fake_start_polling(self: Dispatcher, *bots: Bot, **kwargs: Any) -> None:
        polling["bots"] = bots
        polling["allowed_updates"] = kwargs.get("allowed_updates")

    boot_settings = Settings(
        bot_token="42:" + "A" * 35,
        database_url=DB_URL,
        admin_ids=[STAFF],
        rate_limit_seconds=0.0,
        brand_name=BRAND,
    )
    with (
        patch.object(main_module, "Bot", RecordingBot),
        patch.object(Dispatcher, "start_polling", fake_start_polling),
        patch.object(main_module, "get_settings", lambda: boot_settings),
    ):
        await main_module.run()

    boot_api: StubSession = booted[0].session if booted else api
    check(
        "18) main.run(): bot polling'ga uzatildi",
        len(booted) == 1 and polling.get("bots") == (booted[0],),
        sorted(polling),
    )
    check(
        "18) main.run(): allowed_updates ro'yxati uzatildi",
        polling.get("allowed_updates") == ["callback_query", "message"],
        polling.get("allowed_updates"),
    )
    commands = boot_api.of(SetMyCommands)
    check(
        "18) main.run(): menyu buyruqlari Telegram'ga uzatildi",
        len(commands) == 1 and [c.command for c in commands[0].commands][:2] == ["start", "help"],
        len(commands[0].commands) if commands else 0,
    )
    check("18) main.run(): get_me() chaqirildi", bool(boot_api.of(GetMe)))

    # ---------------- 19. Katalog: «⬅️ Orqaga» kategoriyalarga qaytaradi ----
    async with pool() as session:
        category = await CategoryRepository(session).create(
            "Ichimliklar", "Напитки", emoji="🥤"
        )
        catalog_products = ProductRepository(session)
        await catalog_products.create(
            "SMOKE-1", "Suv 1L", "Вода 1л", category_id=category.id,
            price=Decimal("9000"), stock=Decimal("30"),
        )
        await catalog_products.create(
            "SMOKE-2", "Sharbat 1L", "Сок 1л", category_id=category.id,
            price=Decimal("14000"), discount_price=Decimal("12000"),
            stock=Decimal("30"), is_promo=True,
        )
        await session.commit()

    api.clear()
    await dispatcher.feed_update(
        bot, message_update(19, CLIENT, translate("btn_catalog", "uz"))
    )
    catalog_message = api.of(SendMessage)
    catalog_markup = catalog_message[0].reply_markup if catalog_message else None
    check(
        "19) katalog: kategoriya tugmasi ko'rinadi",
        catalog_markup is not None and catalog_markup.inline_keyboard[0][0].text.startswith("🥤"),
        catalog_markup.inline_keyboard[0][0].text if catalog_markup else "",
    )
    category_cb = catalog_markup.inline_keyboard[0][0].callback_data

    api.clear()
    await dispatcher.feed_update(bot, callback_update(20, CLIENT, category_cb))
    listing = api.of(EditMessageText)
    listing_markup = listing[0].reply_markup if listing else None
    check(
        "19) kategoriya: mahsulotlar ro'yxati ochildi",
        any(label.startswith("Suv 1L") for label in button_labels(listing_markup)),
        button_labels(listing_markup)[:3],
    )
    listing_back = find_button(listing_markup, translate("btn_back", "uz"))
    check(
        "19) ro'yxatdagi «Orqaga» kategoriyalarga ishora qiladi",
        listing_back == CatalogCB(action="categories").pack(),
        listing_back,
    )

    api.clear()
    await dispatcher.feed_update(bot, callback_update(21, CLIENT, listing_back))
    back_to_categories = api.of(EditMessageText)
    check(
        "19) «Orqaga» kategoriyalar ro'yxatini qaytaradi",
        bool(back_to_categories)
        and back_to_categories[0].text == translate("catalog_title", "uz"),
        (back_to_categories[0].text or "")[:40] if back_to_categories else "",
    )

    # ---------------- 20. Aksiya ro'yxati: «⬅️ Orqaga» ------------------
    api.clear()
    await dispatcher.feed_update(
        bot, message_update(22, CLIENT, translate("btn_promo", "uz"))
    )
    promo_message = api.of(SendMessage)
    promo_markup = promo_message[0].reply_markup if promo_message else None
    check(
        "20) aksiya: chegirmali mahsulot ro'yxati",
        any(label.startswith("Sharbat 1L") for label in button_labels(promo_markup)),
        button_labels(promo_markup)[:3],
    )
    promo_back = find_button(promo_markup, translate("btn_back", "uz"))
    check(
        "20) aksiyadagi «Orqaga» kategoriyalarga ishora qiladi",
        promo_back == CatalogCB(action="categories").pack(),
        promo_back,
    )
    api.clear()
    await dispatcher.feed_update(bot, callback_update(23, CLIENT, promo_back))
    back_from_promo = api.of(EditMessageText)
    check(
        "20) aksiyadan «Orqaga» kategoriyalar ro'yxatini qaytaradi",
        bool(back_from_promo)
        and back_from_promo[0].text == translate("catalog_title", "uz"),
        (back_from_promo[0].text or "")[:40] if back_from_promo else "",
    )

    # ---------------- 21. Buyurtmani tasdiqlashda «⬅️ Orqaga» --------------
    async with pool() as session:
        client = await UserRepository(session).get_with_customer(CLIENT)
        drink = await ProductRepository(session).get_by_sku("SMOKE-1")
        await CartService(session, settings).add(client.id, drink, Decimal("10"))
        await session.commit()

    api.clear()
    await dispatcher.feed_update(
        bot, message_update(24, CLIENT, translate("btn_cart", "uz"))
    )
    cart_message = api.of(SendMessage)
    cart_markup = cart_message[0].reply_markup if cart_message else None
    checkout_cb = find_button(cart_markup, translate("btn_checkout", "uz"))
    check("21) savat: «Buyurtma berish» tugmasi", checkout_cb is not None, checkout_cb)

    api.clear()
    await dispatcher.feed_update(bot, callback_update(25, CLIENT, checkout_cb))
    delivery = api.of(EditMessageText)
    check(
        "21) yetkazish turi qadami",
        bool(delivery) and delivery[0].text == translate("co_delivery_title", "uz"),
        (delivery[0].text or "")[:40] if delivery else "",
    )
    await feed_callback(
        dispatcher, bot, api, 26, CLIENT, CheckoutCB(action="delivery").pack()
    )

    api.clear()
    await dispatcher.feed_update(
        bot, message_update(27, CLIENT, "Chilonzor 12-uy, 3-podyezd")
    )
    step_time = api.of(SendMessage)
    check(
        "21) manzil qabul qilindi, vaqt qadami",
        any(m.text == translate("co_ask_time", "uz") for m in step_time),
        [m.text for m in step_time][:2],
    )
    await feed_callback(
        dispatcher, bot, api, 28, CLIENT, CheckoutCB(action="time", value="asap").pack()
    )
    step_comment = api.of(EditMessageText)
    check(
        "21) izoh qadami",
        bool(step_comment) and step_comment[-1].text == translate("co_ask_comment", "uz"),
        (step_comment[-1].text or "")[:40] if step_comment else "",
    )
    await feed_callback(
        dispatcher, bot, api, 29, CLIENT, CheckoutCB(action="skip").pack()
    )
    step_payment = api.of(EditMessageText)
    check(
        "21) to'lov usuli qadami",
        bool(step_payment) and step_payment[-1].text == translate("co_choose_payment", "uz"),
        (step_payment[-1].text or "")[:40] if step_payment else "",
    )
    await feed_callback(
        dispatcher,
        bot,
        api,
        30,
        CLIENT,
        CheckoutCB(action="payment", value=PaymentMethod.CASH.value).pack(),
    )
    step_confirm = api.of(EditMessageText)
    confirm_markup = step_confirm[-1].reply_markup if step_confirm else None
    confirm_back = find_button(confirm_markup, translate("btn_back", "uz"))
    check(
        "21) tasdiqlash ekranidagi «Orqaga» to'lovga ishora qiladi",
        confirm_back == CheckoutCB(action="back").pack(),
        confirm_back,
    )
    await feed_callback(dispatcher, bot, api, 31, CLIENT, confirm_back)
    back_to_payment = api.of(EditMessageText)
    check(
        "21) «Orqaga» to'lov usulini tanlashga qaytaradi",
        bool(back_to_payment)
        and back_to_payment[-1].text == translate("co_choose_payment", "uz"),
        (back_to_payment[-1].text or "")[:40] if back_to_payment else "",
    )

    # ---------------- 22. Minimal summa alerti (HTML tegsiz) -------------
    # Minimal summani 100 000 so'm qilib, yetishmayotgan summani hisoblab,
    # alert (show_alert) matnida HTML teglar qolmasligini tekshiramiz.
    min_settings = Settings(
        database_url=DB_URL,
        admin_ids=[STAFF],
        rate_limit_seconds=0.0,
        brand_name=BRAND,
        min_order_amount=Decimal("100000"),
    )
    min_dispatcher = build_dispatcher(min_settings, pool)
    async with pool() as session:
        client = await UserRepository(session).get_with_customer(CLIENT)
        cart_summary = await CartService(session, settings).summary(client.id)
    shortfall = Decimal("100000") - cart_summary.subtotal

    api.clear()
    await min_dispatcher.feed_update(bot, callback_update(33, CLIENT, checkout_cb))
    min_alert = api.of(AnswerCallbackQuery)
    expected_min_alert = translate(
        "cart_min_amount", "uz", amount=round_money(shortfall)
    )
    check(
        "22) minimal summa: alert HTML tegsiz yuborildi",
        checkout_cb is not None
        and bool(min_alert)
        and min_alert[0].show_alert is True
        and min_alert[0].text == strip_html(expected_min_alert),
        [a.text for a in min_alert],
    )
    check(
        "22) minimal summa: alert matnida «<b>» teg qolmadi",
        bool(min_alert) and "<" not in (min_alert[0].text or ""),
        [a.text for a in min_alert],
    )

    await finish(engine)
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    asyncio.run(main())
