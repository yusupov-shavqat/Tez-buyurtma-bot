"""Servis qatlami istisnolari.

Servis xato matnini tarjima qilmaydi - u faqat i18n kalitini va
parametrlarni saqlaydi. Handler esa `t(error.key, **error.params)` orqali
foydalanuvchi tilida ko'rsatadi.
"""

from __future__ import annotations

from typing import Callable


class ServiceError(Exception):
    """Barcha servis xatolari uchun asos."""

    key = "error_generic"

    def __init__(self, message: str | None = None, *, key: str | None = None, **params: object) -> None:
        self.key = key or self.key
        self.params = params
        super().__init__(message or self.key)

    def text(self, t: Callable[..., str]) -> str:
        """Tilga bog'langan tarjima funksiyasi orqali matnni qaytaradi."""
        return t(self.key, **self.params)


class ValidationError(ServiceError):
    """Kiritilgan ma'lumot yaroqsiz."""

    key = "error_generic"


class AccessDeniedError(ServiceError):
    key = "error_denied"


class NotFoundError(ServiceError):
    key = "error_not_found"


class StaleDataError(ServiceError):
    """Tugma/ma'lumot eskirgan (masalan, savat o'zgargan)."""

    key = "error_stale"


class QuantityError(ValidationError):
    key = "qty_invalid"


class StockLimitError(ValidationError):
    key = "qty_stock_limit"


class AddressRequiredError(ValidationError):
    key = "co_address_required"


class PhoneInvalidError(ValidationError):
    key = "phone_invalid"


class SupportTooShortError(ValidationError):
    key = "support_too_short"


class CartEmptyError(ServiceError):
    key = "cart_empty"


class MinAmountError(ServiceError):
    key = "cart_min_amount"


class StatusTransitionError(ServiceError):
    key = "admin_status_invalid"


class StatusSameError(ServiceError):
    key = "admin_status_same"


class NotCancellableError(ServiceError):
    key = "order_cannot_cancel"


__all__ = [
    "AccessDeniedError",
    "AddressRequiredError",
    "CartEmptyError",
    "MinAmountError",
    "NotFoundError",
    "NotCancellableError",
    "PhoneInvalidError",
    "QuantityError",
    "ServiceError",
    "StaleDataError",
    "StatusSameError",
    "StatusTransitionError",
    "StockLimitError",
    "SupportTooShortError",
    "ValidationError",
]
