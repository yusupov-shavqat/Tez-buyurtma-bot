"""Repozitoriylar uchun umumiy asos.

Har bir repozitoriy mavjud `AsyncSession` bilan ishlaydi - tranzaksiya
chegarasini middleware yoki servis qatlami boshqaradi.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import Select, delete as sa_delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """CRUD uchun qulay yordamchi metodlar."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    async def get(self, pk: int) -> ModelT | None:
        return await self.session.get(self.model, pk)

    async def list_all(self, limit: int | None = None) -> list[ModelT]:
        stmt: Select = select(self.model).order_by(self.model.id)
        if limit:
            stmt = stmt.limit(limit)
        result = await self.session.scalars(stmt)
        return list(result)

    async def add(self, instance: ModelT) -> ModelT:
        """Ob'ektni sessiyaga qo'shadi va flush qiladi (id olish uchun)."""
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def add_all(self, instances: list[ModelT]) -> list[ModelT]:
        self.session.add_all(instances)
        await self.session.flush()
        return instances

    async def delete(self, instance: ModelT) -> None:
        await self.session.delete(instance)
        await self.session.flush()

    async def delete_where(self, *criteria: Any) -> int:
        """Shartlar bo'yicha o'chirish; o'chirilgan qatorlar soni qaytadi."""
        stmt = sa_delete(self.model).where(*criteria)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return int(result.rowcount or 0)

    async def count(self, *criteria: Any) -> int:
        stmt = select(func.count()).select_from(self.model)
        if criteria:
            stmt = stmt.where(*criteria)
        return int(await self.session.scalar(stmt) or 0)

    async def exists(self, *criteria: Any) -> bool:
        stmt = select(self.model.id).where(*criteria).limit(1)
        return await self.session.scalar(stmt) is not None

    async def flush(self) -> None:
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()


__all__ = ["BaseRepository", "ModelT"]
