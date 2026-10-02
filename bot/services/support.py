"""Qo'llab-quvvatlash servisi (TZ 4.4 - mijoz ↔ operator aloqasi)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.enums import SupportStatus
from bot.database.models import SupportRequest, User
from bot.database.repositories.support import SupportRepository
from bot.services.errors import NotFoundError, SupportTooShortError
from bot.utils.pagination import Pagination, paginate

#: Murojaatning minimal uzunligi.
MIN_MESSAGE_LENGTH = 5


class SupportService:
    """Murojaatlarni qabul qilish, ko'rsatish va javob berish."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.support = SupportRepository(session)

    # ------------------------- Mijoz tomoni ----------------------------
    async def create(
        self, user: User, message: str, *, order_id: int | None = None
    ) -> SupportRequest:
        """Yangi murojaat yaratadi (juda qisqa matn rad etiladi)."""
        text = (message or "").strip()
        if len(text) < MIN_MESSAGE_LENGTH:
            raise SupportTooShortError()
        request = await self.support.create(user_id=user.id, message=text, order_id=order_id)
        await self.session.flush()
        return await self.get(request.id)

    async def list_for_user(
        self, user_id: int, *, limit: int = 10
    ) -> list[SupportRequest]:
        return await self.support.list_for_user(user_id, limit=limit)

    # ------------------------- Xodim tomoni ----------------------------
    async def open_page(
        self, *, page: int = 1, per_page: int = 5
    ) -> tuple[list[SupportRequest], Pagination]:
        total = await self.support.count_open()
        pagination = paginate(total, page, per_page)
        items = await self.support.list_open(
            offset=pagination.offset, limit=pagination.limit
        )
        return items, pagination

    async def count_open(self) -> int:
        return await self.support.count_open()

    async def get(self, request_id: int | None) -> SupportRequest:
        if request_id is None:
            raise NotFoundError()
        request = await self.support.get_with_user(request_id)
        if request is None:
            raise NotFoundError()
        return request

    async def answer(
        self, request_id: int | None, answer_text: str, *, actor: User | None = None
    ) -> SupportRequest:
        """Javobni saqlaydi va so'rovni «javob berilgan» holatiga o'tkazadi."""
        text = (answer_text or "").strip()
        if not text:
            raise SupportTooShortError()
        request = await self.get(request_id)
        await self.support.answer(
            request, answer_text=text, answered_by_id=actor.id if actor else None
        )
        await self.session.flush()
        return request

    async def close(self, request: SupportRequest) -> SupportRequest:
        if str(request.status) != str(SupportStatus.CLOSED):
            await self.support.close(request)
        return request


__all__ = ["MIN_MESSAGE_LENGTH", "SupportService"]
