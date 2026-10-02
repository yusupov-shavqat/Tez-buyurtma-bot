"""Foydalanuvchi konteksti middleware'i.

Vazifalari:
    1. Telegram foydalanuvchisini bazada ro'yxatdan o'tkazish (`get_or_create`).
    2. `ADMIN_IDS` ro'yxatidagilarga admin rolini berish.
    3. Faol bo'lmagan/bloklangan foydalanuvchilarni to'xtatish.
    4. Mijoz kartochkasini tayyorlash (mijozlar uchun).
    5. `BotContext` (sessiya + servislar) ni `data["ctx"]` ga joylash.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import Settings
from bot.database.enums import Language, UserRole
from bot.database.models import Customer, User
from bot.database.repositories.users import CustomerRepository, UserRepository
from bot.locales import DEFAULT_LANGUAGE, normalize_language, translate
from bot.middlewares.common import Handler, answer_event, event_chat_id, event_user
from bot.middlewares.i18n import resolve_language
from bot.services import (
    CartService,
    CatalogService,
    NotificationService,
    OrderService,
    ServiceError,
    SettingsService,
    SupportService,
)

logger = logging.getLogger(__name__)

CONTEXT_KEY = "ctx"


@dataclass(slots=True)
class BotContext:
    """Bitta yangilanish uchun kontekst: foydalanuvchi, sessiya va servislar."""

    settings: Settings
    bot: Bot
    session: AsyncSession
    user: User | None = None
    customer: Customer | None = None
    language: str = DEFAULT_LANGUAGE

    catalog: CatalogService = field(init=False)
    cart: CartService = field(init=False)
    orders: OrderService = field(init=False)
    support: SupportService = field(init=False)
    settings_service: SettingsService = field(init=False)
    notifications: NotificationService = field(init=False)

    def __post_init__(self) -> None:
        session = self.session
        self.language = normalize_language(self.language)
        self.catalog = CatalogService(session)
        self.cart = CartService(session, self.settings)
        self.orders = OrderService(session, self.settings)
        self.support = SupportService(session)
        self.settings_service = SettingsService(session, self.settings)
        self.notifications = NotificationService(self.bot, session, self.settings)

    # ------------------------- Qulayliklar -----------------------------
    @property
    def lang(self) -> str:
        return self.language

    @property
    def user_id(self) -> int | None:
        """Telegram foydalanuvchi ID (bazadagi PK emas)."""
        return self.user.telegram_id if self.user is not None else None

    @property
    def chat_id(self) -> int | None:
        """Foydalanuvchi bilan shaxsiy chat ID (xabar yuborish uchun)."""
        if self.user is None:
            return None
        return self.user.chat_id or self.user.telegram_id

    @property
    def is_staff(self) -> bool:
        return bool(self.user is not None and self.user.is_staff)

    @property
    def is_admin(self) -> bool:
        return bool(self.user is not None and self.user.role is UserRole.ADMIN)

    def t(self, key: str, **kwargs: object) -> str:
        """Kontekst tiliga bog'langan tarjima funksiyasi."""
        return translate(key, self.language, **kwargs)

    def error_text(self, error: ServiceError) -> str:
        """Servis xatosini foydalanuvchi tilida ko'rsatadi."""
        return error.text(self.t)


class BotContextMiddleware(BaseMiddleware):
    """Foydalanuvchini bazaga yozadi va `BotContext` ni tayyorlaydi.

    Nom aiogram'ning ichki `UserContextMiddleware` idan farqlanishi uchun
    `BotContextMiddleware` deb nomlangan.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def __call__(
        self,
        handler: Handler,
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        session: AsyncSession | None = data.get("session")
        bot: Bot | None = data.get("bot")
        telegram_user = event_user(event)
        if session is None or bot is None or telegram_user is None or telegram_user.is_bot:
            return await handler(event, data)

        users = UserRepository(session)
        language = resolve_language(data.get("lang"), self.settings.default_language)
        user, created = await users.get_or_create(
            telegram_user.id,
            username=telegram_user.username,
            full_name=telegram_user.full_name,
            chat_id=event_chat_id(event),
            language=Language(language),
        )

        if self.settings.is_admin(user.telegram_id) and user.role is not UserRole.ADMIN:
            await users.set_role(user, UserRole.ADMIN)
            logger.info("Admin roli berildi: %s", user.telegram_id)

        if not user.is_active or user.is_blocked:
            logger.info("Faol bo'lmagan foydalanuvchi: %s", user.telegram_id)
            await answer_event(event, translate("error_denied", data.get("lang") or language))
            return None

        customer: Customer | None = None
        if not user.is_staff:
            customer = await CustomerRepository(session).get_or_create_for_user(user)

        ctx = BotContext(
            settings=self.settings,
            bot=bot,
            session=session,
            user=user,
            customer=customer,
            language=str(user.language),
        )
        data[CONTEXT_KEY] = ctx
        data["user"] = user
        data["customer"] = customer
        data["lang"] = ctx.language
        data["t"] = ctx.t
        if created:
            logger.info("Yangi foydalanuvchi: %s", user.telegram_id)
        return await handler(event, data)


__all__ = ["CONTEXT_KEY", "BotContext", "BotContextMiddleware"]
