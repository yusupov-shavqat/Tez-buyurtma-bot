"""Vaqtinchalik smoke-test: middleware qatlami (TZ 4.4).

Ishlatilishi:  python scripts/_smoke_middlewares.py

Test tarmoqqa chiqmaydi: `Bot` uchun `StubSession` ishlatiladi va barcha
Bot API chaqiruvlari ro'yxatga olinadi. Baza - `data/_smoke_mw.db`.
"""

from __future__ import annotations

import asyncio
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:  # Windows konsolida emoji chiqarish uchun
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

if sys.flags.dev_mode or __import__("os").environ.get("SMOKE_STRICT_WARNINGS"):
    import warnings

    from sqlalchemy.exc import SAWarning

    warnings.filterwarnings("error", category=SAWarning)

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.session.base import BaseSession
from aiogram.dispatcher.event.bases import UNHANDLED
from aiogram.filters import Command
from aiogram.methods import AnswerCallbackQuery, SendMessage, TelegramMethod
from aiogram.types import CallbackQuery, Chat, Message, Update, User as TelegramUser

from bot.config import Settings
from bot.database.base import (
    create_engine,
    create_session_pool,
    dispose_engine,
    init_models,
)
from bot.database.enums import Language, UserRole
from bot.database.repositories.users import UserRepository
from bot.locales import DEFAULT_LANGUAGE, translate
from bot.middlewares import (
    BotContext,
    ThrottlingMiddleware,
    attach_staff_filter,
    register_middlewares,
    resolve_language,
)
from bot.services import ValidationError

DB_PATH = Path("data/_smoke_mw.db")
DB_URL = "sqlite+aiosqlite:///./data/_smoke_mw.db"

FAILURES: list[str] = []
CALLS: list[dict[str, Any]] = []


class StubSession(BaseSession):
    """Bot API so'rovlarini ushlab qoladi (tarmoqqa chiqmaydi)."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[TelegramMethod[Any]] = []

    async def close(self) -> None:  # pragma: no cover - yopadigan narsa yo'q
        return None

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[Any],
        timeout: int | None = None,
    ) -> Any:
        self.calls.append(method)
        return True

    async def stream_content(
        self,
        url: str,
        headers: dict[str, Any] | None = None,
        timeout: int = 30,
        chunk_size: int = 65536,
        raise_for_status: bool = True,
    ) -> Any:  # pragma: no cover - fayl yuklab olish ishlatilmaydi
        yield b""

    def of(self, method_type: type) -> list[Any]:
        """Faqat kerakli turdagi chaqiruvlarni qaytaradi."""
        return [call for call in self.calls if isinstance(call, method_type)]

    def clear(self) -> None:
        self.calls.clear()


def check(label: str, condition: bool, extra: object = "") -> None:
    print(f"[{'OK  ' if condition else 'FAIL'}] {label} {extra}")
    if not condition:
        FAILURES.append(label)


def clean_db(db_path: Path) -> None:
    """Eski test bazasini o'chiradi."""
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(db_path) + suffix)
        if candidate.exists():
            candidate.unlink()


def last(kind: str) -> dict[str, Any]:
    """Oxirgi chaqirilgan handler yozuvini qaytaradi."""
    for record in reversed(CALLS):
        if record["kind"] == kind:
            return record
    return {}


def telegram_user(user_id: int, language_code: str | None) -> TelegramUser:
    return TelegramUser(
        id=user_id,
        is_bot=False,
        first_name=f"User {user_id}",
        language_code=language_code,
    )


def message_update(
    update_id: int,
    user_id: int,
    text: str,
    *,
    language_code: str | None = "uz",
) -> Update:
    return Update(
        update_id=update_id,
        message=Message(
            message_id=update_id,
            date=datetime.now(tz=timezone.utc),
            chat=Chat(id=user_id, type="private"),
            from_user=telegram_user(user_id, language_code),
            text=text,
        ),
    )


def callback_update(
    update_id: int,
    user_id: int,
    data: str = "ping",
    *,
    language_code: str | None = "uz",
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


# ----------------------------------------------------------------------
# Router'lar va handler'lar (BotContext to'g'ridan-to'g'ri qabul qilinadi)
# ----------------------------------------------------------------------
client_router = Router(name="client")
staff_router = attach_staff_filter(Router(name="staff"))
fail_router = Router(name="fail")


@client_router.message(Command("start"))
async def on_start(message: Message, ctx: BotContext) -> None:
    CALLS.append(
        {
            "kind": "start",
            "user": ctx.user_id,
            "lang": ctx.lang,
            "customer": ctx.customer is not None,
            "is_staff": ctx.is_staff,
            "services": all(
                service is not None
                for service in (
                    ctx.catalog,
                    ctx.cart,
                    ctx.orders,
                    ctx.support,
                    ctx.settings_service,
                    ctx.notifications,
                )
            ),
            "error_text": ctx.error_text(ValidationError("smoke", key="error_denied")),
        }
    )
    message_text = ctx.t("start_welcome", brand=ctx.settings.brand_name)
    await message.answer(message_text)


@client_router.message(Command("cart"))
async def on_cart(message: Message, ctx: BotContext) -> None:
    CALLS.append({"kind": "cart", "user": ctx.user_id, "lang": ctx.lang})


@client_router.callback_query(F.data == "ping")
async def on_ping(query: CallbackQuery, ctx: BotContext) -> None:
    CALLS.append({"kind": "ping", "user": ctx.user_id, "lang": ctx.lang})
    await query.answer("pong")


@staff_router.message(Command("staff"))
async def on_staff(message: Message, ctx: BotContext) -> None:
    CALLS.append({"kind": "staff", "user": ctx.user_id, "is_staff": ctx.is_staff})


@fail_router.message(Command("boom"))
async def on_boom(message: Message, ctx: BotContext) -> None:
    """Ataylab xato: tranzaksiya rollback bo'lishini tekshirish uchun."""
    await UserRepository(ctx.session).create(555_000, full_name="Rollback Mijoz")
    raise RuntimeError("smoke rollback")


async def main() -> None:
    clean_db(DB_PATH)

    settings = Settings(
        database_url=DB_URL,
        admin_ids=[9001],
        rate_limit_seconds=0.0,
    )
    engine = create_engine(DB_URL)
    await init_models(engine)
    pool = create_session_pool(engine)
    api = StubSession()
    bot = Bot(token="42:" + "A" * 35, session=api)

    dispatcher = Dispatcher()
    register_middlewares(dispatcher, pool, settings)
    dispatcher.include_router(fail_router)
    dispatcher.include_router(staff_router)
    dispatcher.include_router(client_router)

    order = [type(middleware).__name__ for middleware in dispatcher.update.outer_middleware]
    check(
        "register_middlewares: 4 ta middleware oxirida, to'g'ri tartibda",
        order[-4:]
        == [
            "ThrottlingMiddleware",
            "DbSessionMiddleware",
            "I18nMiddleware",
            "BotContextMiddleware",
        ],
        order,
    )

    # ---------------- 1. Yangi mijoz (Telegram tili - ruscha) ----------
    result = await dispatcher.feed_update(
        bot, message_update(1, 1001, "/start", language_code="ru")
    )
    start = last("start")
    sent = api.of(SendMessage)
    check("start: handler ishga tushdi", start.get("kind") == "start")
    check("start: handled (UNHANDLED emas)", result is not UNHANDLED, result)
    check("start: ctx.user_id to'ldi", start.get("user") == 1001, start.get("user"))
    check("start: Telegram tili aniqlandi", start.get("lang") == "ru", start.get("lang"))
    check("start: mijoz kartochkasi ochildi", start.get("customer") is True)
    check("start: mijoz xodim emas", start.get("is_staff") is False)
    check("start: barcha servislar tayyor", start.get("services") is True)
    check(
        "start: error_text() tarjimasi",
        start.get("error_text") == translate("error_denied", "ru"),
        start.get("error_text"),
    )
    check("start: javob yuborildi", len(sent) == 1, len(sent))
    check(
        "start: matn foydalanuvchi tilida va shablon to'ldirildi",
        bool(sent) and sent[0].text == translate("start_welcome", "ru", brand=settings.brand_name)
        and "{" not in sent[0].text,
        sent[0].text.splitlines()[0] if sent else None,
    )

    async with pool() as session:
        users = UserRepository(session)
        saved = await users.get_with_customer(1001)
    check("baza: sessiya commit qilindi", saved is not None)
    check(
        "baza: foydalanuvchi tili saqlandi",
        saved is not None and saved.language == Language.RU,
        getattr(saved, "language", None),
    )
    check(
        "baza: mijoz kartochkasi bog'landi",
        saved is not None and saved.customer is not None,
    )
    check(
        "baza: chat_id saqlandi",
        saved is not None and saved.chat_id == 1001,
        getattr(saved, "chat_id", None),
    )

    # ---------------- 2. Bazadagi til Telegram tilidan ustuvor ---------
    async with pool() as session:
        users = UserRepository(session)
        target = await users.get_by_telegram_id(1001)
        assert target is not None
        await users.set_language(target, Language.UZ)
        await session.commit()
    await dispatcher.feed_update(bot, message_update(2, 1001, "/cart", language_code="ru"))
    cart = last("cart")
    check("i18n: bazadagi til ustuvor", cart.get("lang") == "uz", cart.get("lang"))
    check("i18n: xabar handler'i ishladi", cart.get("kind") == "cart")


    # ---------------- 3. Xodim bo'lmagan foydalanuvchi -----------------
    api.clear()
    before = len(CALLS)
    result = await dispatcher.feed_update(
        bot, message_update(3, 1002, "/staff", language_code="uz")
    )
    denied = api.of(SendMessage)
    check("staff: mijoz so'rovi to'xtatildi", result is not UNHANDLED, result)
    check("staff: mijoz handler'i ishlamadi", len(CALLS) == before)
    check(
        "staff: ogohlantirish yuborildi",
        len(denied) == 1 and denied[0].text == translate("admin_staff_only", "uz"),
        denied[0].text if denied else None,
    )

    # ---------------- 4. ADMIN_IDS -> avtomatik admin roli -------------
    api.clear()
    before = len(CALLS)
    result = await dispatcher.feed_update(
        bot, message_update(4, 9001, "/staff", language_code="uz")
    )
    staff = last("staff")
    check("staff: admin o'tkazildi", result is not UNHANDLED)
    check("staff: handler ishga tushdi", len(CALLS) == before + 1 and bool(staff))
    check("staff: ctx.is_staff = True", staff.get("is_staff") is True, staff)
    async with pool() as session:
        users = UserRepository(session)
        admin = await users.get_with_customer(9001)
    check(
        "staff: ADMIN_IDS orqali rol berildi",
        admin is not None and admin.role == UserRole.ADMIN,
        getattr(admin, "role", None),
    )
    check(
        "staff: xodimga mijoz kartochkasi ochilmadi",
        admin is not None and admin.customer is None,
    )

    # ---------------- 5. Bloklangan foydalanuvchi ----------------------
    async with pool() as session:
        users = UserRepository(session)
        blocked, _ = await users.get_or_create(1003, full_name="Bloklangan", chat_id=1003)
        await users.set_active(blocked, False)
        await session.commit()
    api.clear()
    before = len(CALLS)
    result = await dispatcher.feed_update(
        bot, message_update(5, 1003, "/start", language_code="uz")
    )
    blocked_msgs = api.of(SendMessage)
    check("bloklangan: handler ishlamadi", len(CALLS) == before and result is not UNHANDLED)
    check(
        "bloklangan: rad javobi yuborildi",
        len(blocked_msgs) == 1
        and blocked_msgs[0].text == translate("error_denied", "uz"),
        blocked_msgs[0].text if blocked_msgs else None,
    )

    # ---------------- 6. Callback query --------------------------------
    api.clear()
    before = len(CALLS)
    await dispatcher.feed_update(bot, callback_update(6, 1001))
    ping = last("ping")
    answers = api.of(AnswerCallbackQuery)
    check("callback: handler ishga tushdi", len(CALLS) == before + 1, ping)
    check("callback: ctx.user_id to'ldi", ping.get("user") == 1001)
    check(
        "callback: handler answer(text) yubordi",
        len(answers) == 1 and answers[0].text == "pong",
        answers[0].text if answers else None,
    )

    # ---------------- 7. Xato -> rollback ------------------------------
    api.clear()
    raised = False
    try:
        await dispatcher.feed_update(bot, message_update(7, 1004, "/boom", language_code="uz"))
    except RuntimeError:
        raised = True
    check("xato: istisno yuqoriga uzatildi", raised)
    async with pool() as session:
        rolled_back = await UserRepository(session).get_by_telegram_id(555_000)
    check("xato: tranzaksiya rollback qilindi", rolled_back is None)


    # ---------------- 8. Rate limit (ThrottlingMiddleware) --------------
    limits: list[int] = []

    async def record_handler(event: object, data: dict[str, Any]) -> None:
        limits.append(1)

    throttling = ThrottlingMiddleware(60)
    event = message_update(8, 1005, "/start").event
    assert event is not None
    await throttling(record_handler, event, {})
    await throttling(record_handler, event, {})
    check("throttle: takroriy xabar to'xtatildi", len(limits) == 1, len(limits))

    api.clear()
    limits.clear()
    callback_event = callback_update(9, 1006).callback_query
    assert callback_event is not None
    callback = CallbackQuery.model_validate(
        callback_event.model_dump(), context={"bot": bot}
    )
    await throttling(record_handler, callback, {})
    await throttling(record_handler, callback, {})
    acks = api.of(AnswerCallbackQuery)
    check("throttle: callback ham cheklanadi", len(limits) == 1, len(limits))
    check(
        "throttle: callback tasdiqlandi (matn yo'q)",
        len(acks) == 1 and acks[0].text is None,
        len(acks),
    )
    check("throttle: rate=0 -> o'chirilgan", ThrottlingMiddleware(0).enabled is False)

    # ---------------- 9. i18n yordamchilari ---------------------------
    check("i18n: 'ru-RU' -> 'ru'", resolve_language("ru-RU") == "ru")
    check("i18n: 'UZ' -> 'uz'", resolve_language("UZ") == "uz")
    check(
        "i18n: noma'lum til -> standart til",
        resolve_language("de") == DEFAULT_LANGUAGE,
        resolve_language("de"),
    )
    check("i18n: fallback ishlatiladi", resolve_language("de", "ru") == "ru")
    check("i18n: bo'sh qiymat -> standart til", resolve_language(None) == DEFAULT_LANGUAGE)
    check(
        "i18n: 'admin_staff_only' ikkala tilda tarjima qilingan",
        translate("admin_staff_only", "uz") != "admin_staff_only"
        and translate("admin_staff_only", "ru") != "admin_staff_only",
        translate("admin_staff_only", "ru"),
    )

    await bot.session.close()
    await dispose_engine(engine)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:  # pragma: no cover - kutilmagan xatolar
        traceback.print_exc()
        FAILURES.append("kutilmagan istisno")
    print()
    if FAILURES:
        print(f"[FAIL] {len(FAILURES)} ta tekshiruv yiqildi:")
        for name in FAILURES:
            print(f"   - {name}")
        sys.exit(1)
    print("Barcha middleware tekshiruvlari muvaffaqiyatli o'tdi.")
    sys.exit(0)
