"""Tizim sozlamalari repozitoriyasi (`settings` jadvali)."""

from __future__ import annotations

from sqlalchemy import select

from bot.database.models import Setting
from bot.database.repositories.base import BaseRepository


class SettingRepository(BaseRepository[Setting]):
    """Kalit-qiymat ko'rinishidagi sozlamalar: ish vaqti, aloqa raqami va h.k."""

    model = Setting

    async def get_value(self, key: str, default: str | None = None) -> str | None:
        setting = await self.session.get(Setting, key)
        if setting is None or not setting.value:
            return default
        return setting.value

    async def set_value(self, key: str, value: str, description: str | None = None) -> Setting:
        setting = await self.session.get(Setting, key)
        if setting is None:
            setting = Setting(key=key, value=value, description=description)
            await self.add(setting)
        else:
            setting.value = value
            if description is not None:
                setting.description = description
            await self.flush()
        return setting

    async def all_values(self) -> dict[str, str]:
        stmt = select(Setting)
        result = await self.session.scalars(stmt)
        return {item.key: item.value for item in result}


__all__ = ["SettingRepository"]
