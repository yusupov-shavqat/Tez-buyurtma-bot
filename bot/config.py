"""Loyiha sozlamalari (pydantic-settings orqali .env dan o'qiladi)."""

from __future__ import annotations

import re
from decimal import Decimal
from functools import lru_cache
from typing import Any

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_LIST_SPLIT_RE = re.compile(r"[,;\s]+")


class Settings(BaseSettings):
    """Barcha sozlamalar bitta joyda. Qiymatlar .env fayldan yoki muhitdan olinadi."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---------------- Bot ----------------
    bot_token: SecretStr = SecretStr("")
    bot_username: str = ""
    admin_ids: list[int] = Field(default_factory=list)
    support_chat_id: int | None = None

    # ---------------- Baza ----------------
    database_url: str = "sqlite+aiosqlite:///./data/distribution.db"
    db_echo: bool = False

    # ---------------- Til / valyuta ----------------
    default_language: str = "uz"
    supported_languages: list[str] = Field(default_factory=lambda: ["uz", "ru"])
    currency: str = "so'm"
    timezone: str = "Asia/Tashkent"

    # ---------------- Savdo siyosati ----------------
    delivery_fee: Decimal = Decimal("15000")
    free_delivery_from: Decimal = Decimal("1000000")
    min_order_amount: Decimal = Decimal("0")
    order_prefix: str = "ORD"

    # ---------------- Brend / kontaktlar ----------------
    brand_name: str = "Distribyutsiya xizmati"
    support_phone: str = ""
    pickup_address: str = ""
    working_hours: str = "09:00–19:00"

    # ---------------- Interfeys ----------------
    cards_per_page: int = 6
    products_per_page: int = 5
    orders_per_page: int = 5
    rate_limit_seconds: float = 0.5

    # ---------------- Onlayn to'lov ----------------
    payme_merchant_id: str = ""
    click_service_id: str = ""
    click_merchant_id: str = ""

    # ---------------- Fon vazifalari ----------------
    enable_daily_jobs: bool = True
    low_stock_hour: int = 9

    # ------------------------------------------------------------
    @field_validator("admin_ids", mode="before")
    @classmethod
    def _parse_admin_ids(cls, value: Any) -> Any:
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [int(item) for item in _LIST_SPLIT_RE.split(value) if item]
        return value

    @field_validator("supported_languages", mode="before")
    @classmethod
    def _parse_languages(cls, value: Any) -> Any:
        if value is None or value == "":
            return ["uz", "ru"]
        if isinstance(value, str):
            return [item.lower() for item in _LIST_SPLIT_RE.split(value) if item]
        return value

    @field_validator("default_language")
    @classmethod
    def _normalize_default_language(cls, value: str) -> str:
        return value.strip().lower()

    # ------------------------------------------------------------
    @property
    def token(self) -> str:
        return self.bot_token.get_secret_value()

    @property
    def is_online_payment_enabled(self) -> bool:
        """Onlayn to'lov (Payme/Click) sozlanganmi?"""
        return bool(self.payme_merchant_id or self.click_service_id)

    @property
    def language_list(self) -> tuple[str, ...]:
        return tuple(self.supported_languages)

    def is_admin(self, telegram_id: int | None) -> bool:
        return telegram_id is not None and telegram_id in self.admin_ids


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Keshlangan sozlamalar (butun ilova bo'ylab bitta nusxa)."""
    return Settings()


def reset_settings_cache() -> None:
    """Testlarda sozlamalarni qayta o'qish uchun."""
    get_settings.cache_clear()
