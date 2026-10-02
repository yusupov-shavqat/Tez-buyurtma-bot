"""Servis qatlami (business logic).

Handler'lar faqat shu modullardagi servislar bilan ishlaydi; ular
repozitoriyalar, holat mashinasi va hisob-kitoblarni yashiradi.

    from bot.services import CartService, CatalogService, OrderService

Xatolar `ServiceError` avlodlari orqali uzatiladi va handler'da
`t(error.key, **error.params)` ko'rinishida ko'rsatiladi.
"""

from __future__ import annotations

from bot.services.cart import CartLine, CartService, CartSummary
from bot.services.catalog import CatalogService, CategoryCard
from bot.services.errors import (
    AccessDeniedError,
    AddressRequiredError,
    CartEmptyError,
    MinAmountError,
    NotFoundError,
    NotCancellableError,
    PhoneInvalidError,
    QuantityError,
    ServiceError,
    StaleDataError,
    StatusSameError,
    StatusTransitionError,
    StockLimitError,
    SupportTooShortError,
    ValidationError,
)
from bot.services.notifications import NotificationService
from bot.services.orders import (
    CUSTOMER_CANCELLABLE,
    REGULAR_FROM,
    STOCK_RELEASE_STATUSES,
    TRANSITIONS,
    VIP_FROM,
    CheckoutData,
    OrderService,
    StatusChange,
)
from bot.services.settings import SETTING_KEYS, SettingsService
from bot.services.support import MIN_MESSAGE_LENGTH, SupportService

__all__ = [
    "AccessDeniedError",
    "AddressRequiredError",
    "CUSTOMER_CANCELLABLE",
    "CartEmptyError",
    "CartLine",
    "CartService",
    "CartSummary",
    "CatalogService",
    "CategoryCard",
    "CheckoutData",
    "MIN_MESSAGE_LENGTH",
    "MinAmountError",
    "NotFoundError",
    "NotCancellableError",
    "NotificationService",
    "OrderService",
    "PhoneInvalidError",
    "QuantityError",
    "REGULAR_FROM",
    "SETTING_KEYS",
    "STOCK_RELEASE_STATUSES",
    "ServiceError",
    "SettingsService",
    "StaleDataError",
    "StatusChange",
    "StatusSameError",
    "StatusTransitionError",
    "StockLimitError",
    "SupportService",
    "SupportTooShortError",
    "TRANSITIONS",
    "VIP_FROM",
    "ValidationError",
]
