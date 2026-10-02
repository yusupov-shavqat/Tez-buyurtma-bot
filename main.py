"""Botni ishga tushirish uchun kirish nuqtasi (entrypoint).

Ishlatilishi (Windows, loyiha ildizidan)::

    .venv\\Scripts\\python.exe main.py

Talablar:
    1. `.env` fayli `.env.example` dan nusxa olinib to'ldirilgan bo'lishi
       kerak::

           Copy-Item .env.example .env

    2. `BOT_TOKEN` @BotFather'dan olingan token bilan to'ldirilgan bo'lishi
       kerak (aks holda bot aniq xato bilan to'xtaydi).

Ishga tushish tartibi:

    init_models -> Bot(parse_mode=HTML) -> Dispatcher(MemoryStorage)
    -> register_middlewares -> register_routers -> start_polling
"""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.config import Settings, get_settings
from bot.database import create_engine, create_session_pool, dispose_engine, init_models
from bot.handlers import register_routers
from bot.middlewares import register_middlewares

logger = logging.getLogger("bot")

TOKEN_MISSING = (
    "BOT_TOKEN topilmadi!\n"
    "  1) `.env.example` dan nusxa oling:  Copy-Item .env.example .env\n"
    "  2) `.env` ichida BOT_TOKEN=123456:ABC... qiymatini to'ldiring (BotFather)."
)

#: Bot menyusidagi buyruqlar (Telegram'da «/» bosilganda ko'rinadi).
COMMANDS: tuple[BotCommand, ...] = (
    BotCommand(command="start", description="🏠 Bosh menyu / Главное меню"),
    BotCommand(command="help", description="ℹ️ Yordam / Помощь"),
    BotCommand(command="language", description="🌐 Tilni o'zgartirish / Язык"),
    BotCommand(command="myid", description="🆔 Mening ID'im / Мой ID"),
)


def setup_logging(level: int = logging.INFO) -> None:
    """Konsolga o'qiladigan loglarni yoqadi."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)


def build_dispatcher(
    settings: Settings, session_pool: async_sessionmaker[AsyncSession]
) -> Dispatcher:
    """Middleware va router'lar ulangan dispatcher yasaydi (testlarda ham qulay)."""
    dispatcher = Dispatcher(storage=MemoryStorage())
    register_middlewares(dispatcher, session_pool, settings)
    register_routers(dispatcher)
    return dispatcher


async def run() -> None:
    """Botni polling rejimida ishga tushiradi (to'xtaguncha ishlaydi)."""
    settings = get_settings()
    if not settings.token:
        raise SystemExit(TOKEN_MISSING)

    logger.info("Baza: %s", settings.database_url)
    engine = create_engine(settings.database_url, echo=settings.db_echo)
    bot: Bot | None = None
    try:
        await init_models(engine)
        session_pool = create_session_pool(engine)

        bot = Bot(
            token=settings.token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        dispatcher = build_dispatcher(settings, session_pool)

        await bot.set_my_commands(list(COMMANDS))
        me = await bot.get_me()
        logger.info(
            "Bot ishga tushdi: @%s | adminlar: %s | tillar: %s",
            me.username or settings.bot_username or "?",
            ", ".join(str(item) for item in settings.admin_ids) or "yo'q",
            ", ".join(settings.language_list),
        )
        if settings.enable_daily_jobs:
            logger.info(
                "Eslatma: kunlik vazifalar hali ulanmagan "
                "(enable_daily_jobs=True, low_stock_hour=%s).",
                settings.low_stock_hour,
            )

        await dispatcher.start_polling(
            bot, allowed_updates=dispatcher.resolve_used_update_types()
        )
    finally:
        if bot is not None:
            await bot.session.close()
        await dispose_engine(engine)


def main() -> None:
    """Sinxron kirish nuqtasi: `python main.py`."""
    setup_logging()
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, SystemExit) as stop:
        if isinstance(stop, SystemExit) and stop.code not in (0, None):
            raise
        logger.info("Bot to'xtatildi 👋")


if __name__ == "__main__":
    main()


__all__ = ["COMMANDS", "TOKEN_MISSING", "build_dispatcher", "main", "run", "setup_logging"]
