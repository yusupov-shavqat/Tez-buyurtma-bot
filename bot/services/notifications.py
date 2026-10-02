"""Bildirishnoma servisi (TZ 4.5).

Xabarlar yuborilishi `notification_logs` jadvalida qayd etiladi, xatolar esa
bot ishini to'xtatmaydi: muvaffaqiyatsizlik shunchaki jurnalga yoziladi.
"""

from __future__ import annotations

from typing import Sequence

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import Settings
from bot.database.enums import NotificationKind, OrderStatus
from bot.database.models import Order, Product, SupportRequest, User
from bot.database.repositories.orders import NotificationLogRepository
from bot.database.repositories.users import UserRepository
from bot.locales import translator
from bot.services import presenters as pr
from bot.utils.money import format_money
from bot.utils.text import escape

HTML = "HTML"


class NotificationService:
    """Mijoz va xodimlarga xabar yuborish."""

    def __init__(self, bot: Bot, session: AsyncSession, settings: Settings) -> None:
        self.bot = bot
        self.session = session
        self.settings = settings
        self.users = UserRepository(session)
        self.logs = NotificationLogRepository(session)

    # ------------------------- Past daraja -----------------------------
    @staticmethod
    def user_chat_id(user: User | None) -> int | None:
        if user is None:
            return None
        return user.chat_id or user.telegram_id

    async def send_text(
        self,
        chat_id: int | None,
        text: str,
        *,
        kind: NotificationKind,
        user_id: int | None = None,
        order_id: int | None = None,
        markup=None,
    ) -> bool:
        """Bitta xabar yuboradi; natija jurnalga yoziladi."""
        if not chat_id:
            return False
        try:
            await self.bot.send_message(chat_id, text, reply_markup=markup, parse_mode=HTML)
        except TelegramAPIError as error:
            await self.logs.log(
                kind=kind,
                text=text,
                user_id=user_id,
                order_id=order_id,
                is_success=False,
                error=str(error)[:255],
            )
            return False
        await self.logs.log(kind=kind, text=text, user_id=user_id, order_id=order_id)
        return True

    async def send_to_user(
        self,
        user: User | None,
        text: str,
        *,
        kind: NotificationKind,
        order_id: int | None = None,
        markup=None,
    ) -> bool:
        if user is None or not user.is_active or user.is_blocked:
            return False
        return await self.send_text(
            self.user_chat_id(user),
            text,
            kind=kind,
            user_id=user.id,
            order_id=order_id,
            markup=markup,
        )

    # ------------------------- Qabul qiluvchilar -----------------------
    async def staff_chat_ids(self) -> list[int]:
        """Xodimlar, adminlar va qo'llab-quvvatlash chati ID lari (takrorlanmaydi)."""
        ids: list[int] = []
        if self.settings.support_chat_id:
            ids.append(int(self.settings.support_chat_id))
        for user in await self.users.list_staff():
            if not user.is_active or user.is_blocked:
                continue
            chat_id = user.chat_id or user.telegram_id
            if chat_id:
                ids.append(int(chat_id))
        for admin_id in self.settings.admin_ids:
            user = await self.users.get_by_telegram_id(admin_id)
            chat_id = (user.chat_id or user.telegram_id) if user else admin_id
            if chat_id:
                ids.append(int(chat_id))
        seen: set[int] = set()
        unique: list[int] = []
        for chat_id in ids:
            if chat_id in seen:
                continue
            seen.add(chat_id)
            unique.append(chat_id)
        return unique

    async def notify_staff(
        self,
        text: str,
        *,
        kind: NotificationKind,
        order_id: int | None = None,
        markup=None,
    ) -> int:
        """Xabar barcha xodimlarga yuboriladi; muvaffaqiyatli yuborilganlar soni."""
        sent = 0
        for chat_id in await self.staff_chat_ids():
            if await self.send_text(
                chat_id, text, kind=kind, order_id=order_id, markup=markup
            ):
                sent += 1
        return sent

    @staticmethod
    def lang_of(user: User | None, fallback: str = "uz") -> str:
        return str(user.language) if user is not None and user.language else fallback

    # ------------------------- Buyurtmalar -----------------------------
    async def order_created(self, order: Order, *, markup=None) -> int:
        """Yangi buyurtma haqida xodimlarga xabar (mijozga handler javob beradi)."""
        for_staff = translator("uz")
        text = for_staff(
            "notif_order_created",
            number=escape(order.number),
            customer=escape(order.customer_name or "—"),
            phone=escape(order.customer_phone or "—"),
            total=format_money(order.total, self.settings.currency),
            delivery_type=for_staff(f"dt_{order.delivery_type}"),
            address=escape(order.address or for_staff("dt_pickup")),
            source=for_staff(f"src_{order.source}"),
        )
        return await self.notify_staff(
            text,
            kind=NotificationKind.ORDER_CREATED,
            order_id=order.id,
            markup=markup,
        )

    async def status_changed(
        self,
        order: Order,
        status: OrderStatus | None = None,
        *,
        reason: str | None = None,
    ) -> bool:
        """Mijozga buyurtma holati haqida xabar."""
        user = await self.order_user(order)
        t = translator(self.lang_of(user, self.settings.default_language))
        target = OrderStatus(str(status or order.status))
        if target in {OrderStatus.CANCELLED, OrderStatus.RETURNED}:
            text = t(
                "notif_order_cancelled",
                number=escape(order.number),
                reason=escape(reason or order.cancel_reason or t("profile_unknown")),
            )
        else:
            text = t(
                "notif_order_status",
                number=escape(order.number),
                status=pr.status_label(t, target),
            )
        return await self.send_to_user(
            user, text, kind=NotificationKind.ORDER_STATUS, order_id=order.id
        )

    async def order_cancelled(self, order: Order, *, reason: str | None = None) -> bool:
        """Bekor qilingan buyurtma haqida mijozga xabar."""
        return await self.status_changed(order, OrderStatus.CANCELLED, reason=reason)

    async def order_user(self, order: Order) -> User | None:
        """Buyurtma egasi (kerak bo'lsa bazadan olinadi)."""
        if order.user is not None:
            return order.user
        return await self.users.get(order.user_id)

    # ------------------------- Qo'llab-quvvatlash ----------------------
    async def support_created(self, request: SupportRequest, *, markup=None) -> int:
        """Yangi murojaat haqida xodimlarga xabar."""
        t = translator("uz")
        user = request.user
        phone = (user.phone if user is not None else None) or t("profile_unknown")
        text = t(
            "notif_new_support",
            id=request.id,
            user=escape(user.display_name if user is not None else t("profile_unknown")),
            phone=escape(phone),
            message=escape(request.message),
        )
        return await self.notify_staff(
            text, kind=NotificationKind.SUPPORT, markup=markup
        )

    async def support_answered(self, request: SupportRequest) -> bool:
        """Murojaatga javob yuboriladi."""
        user = request.user
        if user is None:
            user = await self.users.get(request.user_id)
        t = translator(self.lang_of(user, self.settings.default_language))
        text = t(
            "support_answer",
            id=request.id,
            answer=escape(request.answer or ""),
        )
        return await self.send_to_user(
            user, text, kind=NotificationKind.SUPPORT_REPLY
        )

    # ------------------------- Ombor -----------------------------------
    async def low_stock(self, products: Sequence[Product]) -> int:
        """Kam qolgan mahsulotlar haqida xodimlarga xabar."""
        if not products:
            return 0
        t = translator("uz")
        lines = "\n".join(pr.low_stock_line(t, product, "uz") for product in products[:20])
        text = t("notif_low_stock", count=len(products), lines=lines)
        return await self.notify_staff(text, kind=NotificationKind.LOW_STOCK)


__all__ = ["HTML", "NotificationService"]

