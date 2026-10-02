"""Sozlamalar servisi: `settings` jadvalidagi qiymatlar (TZ 4.4 - admin panel).

Qiymat bazada bo'lmasa - `.env` (bot.config.Settings) dagi standart ishlatiladi.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import Settings
from bot.database.repositories.settings import SettingRepository
from bot.utils.money import to_decimal

#: Boshqariladigan sozlamalar va ularning tavsifi (admin panel uchun).
SETTING_KEYS: dict[str, str] = {
    "brand_name": "Do'kon nomi",
    "support_phone": "Qo'llab-quvvatlash raqami",
    "pickup_address": "Olib ketish manzili",
    "working_hours": "Ish vaqti",
    "delivery_fee": "Yetkazish narxi",
    "free_delivery_from": "Bepul yetkazish chegarasi",
    "min_order_amount": "Minimal buyurtma summasi",
    "order_prefix": "Buyurtma raqami prefiksi",
}


class SettingsService:
    """Bazadagi sozlamalarni o'qish va o'zgartirish."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.config = settings
        self.repo = SettingRepository(session)

    # ------------------------- O'qish ----------------------------------
    def default_value(self, key: str) -> str | None:
        """`.env` dagi standart qiymat."""
        mapping: dict[str, object] = {
            "brand_name": self.config.brand_name,
            "support_phone": self.config.support_phone,
            "pickup_address": self.config.pickup_address,
            "working_hours": self.config.working_hours,
            "delivery_fee": self.config.delivery_fee,
            "free_delivery_from": self.config.free_delivery_from,
            "min_order_amount": self.config.min_order_amount,
            "order_prefix": self.config.order_prefix,
        }
        value = mapping.get(key)
        return None if value is None else str(value)

    async def get(self, key: str) -> str | None:
        """Bazadagi qiymat, bo'lmasa standart qiymat."""
        value = await self.repo.get_value(key)
        if value is None:
            return self.default_value(key)
        return value

    async def all(self) -> dict[str, str]:
        """Barcha boshqariladigan sozlamalar (baza + standart)."""
        stored = await self.repo.all_values()
        result: dict[str, str] = {}
        for key in SETTING_KEYS:
            value = stored.get(key) or self.default_value(key)
            if value is not None:
                result[key] = value
        return result

    async def info(self) -> dict[str, str]:
        """Botning «Ma'lumot» bo'limi uchun matnli qiymatlar."""
        data = await self.all()
        return {
            "brand_name": data.get("brand_name", self.config.brand_name),
            "support_phone": data.get("support_phone", self.config.support_phone or "—"),
            "pickup_address": data.get("pickup_address", self.config.pickup_address or "—"),
            "working_hours": data.get("working_hours", self.config.working_hours or "—"),
        }

    async def _decimal(self, key: str, default: Decimal) -> Decimal:
        raw = await self.get(key)
        if raw is None or str(raw).strip() == "":
            return default
        try:
            return to_decimal(raw)
        except (ValueError, ArithmeticError):
            return default

    async def delivery_fee(self) -> Decimal:
        return await self._decimal("delivery_fee", to_decimal(self.config.delivery_fee))

    async def free_delivery_from(self) -> Decimal:
        return await self._decimal(
            "free_delivery_from", to_decimal(self.config.free_delivery_from)
        )

    async def min_order_amount(self) -> Decimal:
        return await self._decimal(
            "min_order_amount", to_decimal(self.config.min_order_amount)
        )

    async def order_prefix(self) -> str:
        return (await self.get("order_prefix")) or self.config.order_prefix

    # ------------------------- Yozish ----------------------------------
    async def set(self, key: str, value: str) -> None:
        """Sozlamani saqlaydi (bo'sh qiymat standartga qaytaradi)."""
        text = (value or "").strip()
        if not text:
            default = self.default_value(key) or ""
            text = default
        await self.repo.set_value(key, text, SETTING_KEYS.get(key))
        await self.session.flush()


__all__ = ["SETTING_KEYS", "SettingsService"]
