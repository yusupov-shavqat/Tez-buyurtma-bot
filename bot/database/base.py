"""Ma'lumotlar bazasi qatlami: Base, engine va sessiya fabrikasi."""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from bot.config import Settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Barcha modellar uchun asosiy klass."""

    def __repr__(self) -> str:  # pragma: no cover - debug yordamchi
        pk = getattr(self, "id", None)
        return f"<{type(self).__name__} id={pk}>"


def _ensure_sqlite_directory(database_url: str) -> None:
    """SQLite fayli uchun papka mavjudligini kafolatlaydi."""
    prefix = "sqlite+aiosqlite:///"
    if not database_url.startswith(prefix):
        return
    raw_path = database_url[len(prefix) :]
    if not raw_path or raw_path.startswith(":memory:"):
        return
    path = Path(raw_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.parent.mkdir(parents=True, exist_ok=True)


def create_engine(database_url: str, *, echo: bool = False) -> AsyncEngine:
    """Async engine yaratadi (SQLite va PostgreSQL ikkalasini qo'llaydi)."""
    kwargs: dict = {"echo": echo, "future": True}
    if database_url.startswith("sqlite"):
        _ensure_sqlite_directory(database_url)
        # SQLite uchun pooling cheklovlari yo'q, shuning uchun default sozlamalar yetarli.
    else:
        kwargs.update({"pool_pre_ping": True, "pool_size": 10, "max_overflow": 20})
    return create_async_engine(database_url, **kwargs)


def create_session_pool(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Sessiyalar fabrikasi. expire_on_commit=False - ob'ektlar commitdan keyin ham o'qiladi."""
    return async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


async def init_models(engine: AsyncEngine) -> None:
    """Jadvallarni yaratadi (MVP uchun create_all; keyinchalik Alembic qo'shiladi)."""
    from bot.database import models  # noqa: F401  (modellar ro'yxatdan o'tishi uchun)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Ma'lumotlar bazasi jadvallari tayyor.")


async def dispose_engine(engine: AsyncEngine) -> None:
    await engine.dispose()
    logger.info("Ma'lumotlar bazasi ulanishlari yopildi.")


__all__ = [
    "Base",
    "Settings",
    "create_engine",
    "create_session_pool",
    "dispose_engine",
    "init_models",
]
