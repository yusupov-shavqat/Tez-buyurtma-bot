"""Qo'llab-quvvatlash so'rovlari repozitoriyasi (TZ 4.4)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from bot.database.enums import SupportStatus
from bot.database.models import SupportRequest, utcnow
from bot.database.repositories.base import BaseRepository


class SupportRepository(BaseRepository[SupportRequest]):
    """`support_requests` jadvali: mijoz xabarlari va operator javoblari."""

    model = SupportRequest

    async def create(
        self,
        *,
        user_id: int,
        message: str,
        order_id: int | None = None,
    ) -> SupportRequest:
        request = SupportRequest(
            user_id=user_id,
            order_id=order_id,
            message=message.strip(),
            status=SupportStatus.OPEN,
        )
        return await self.add(request)

    async def get_with_user(self, request_id: int) -> SupportRequest | None:
        stmt = (
            select(SupportRequest)
            .options(selectinload(SupportRequest.user))
            .where(SupportRequest.id == request_id)
        )
        return await self.session.scalar(stmt)

    async def list_open(self, *, offset: int = 0, limit: int = 5) -> list[SupportRequest]:
        stmt = (
            select(SupportRequest)
            .options(selectinload(SupportRequest.user))
            .where(SupportRequest.status == SupportStatus.OPEN)
            .order_by(SupportRequest.id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return list(result)

    async def count_open(self) -> int:
        return await self.count(SupportRequest.status == SupportStatus.OPEN)

    async def list_for_user(self, user_id: int, *, limit: int = 10) -> list[SupportRequest]:
        stmt = (
            select(SupportRequest)
            .where(SupportRequest.user_id == user_id)
            .order_by(SupportRequest.id.desc())
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return list(result)

    async def answer(
        self,
        request: SupportRequest,
        *,
        answer_text: str,
        answered_by_id: int | None = None,
    ) -> SupportRequest:
        """Javobni saqlaydi va so'rovni yopadi."""
        request.answer = answer_text.strip()
        request.answered_by_id = answered_by_id
        request.answered_at = utcnow()
        request.status = SupportStatus.ANSWERED
        await self.flush()
        return request

    async def close(self, request: SupportRequest) -> SupportRequest:
        request.status = SupportStatus.CLOSED
        await self.flush()
        return request


__all__ = ["SupportRepository"]
