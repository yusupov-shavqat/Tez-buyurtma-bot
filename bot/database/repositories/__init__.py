"""Repozitoriylar to'plami.

Har bir repozitoriy mavjud `AsyncSession` bilan quriladi:

    repo = UserRepository(session)
"""

from bot.database.repositories.base import BaseRepository
from bot.database.repositories.cart import CartRepository
from bot.database.repositories.catalog import CategoryRepository, ProductRepository
from bot.database.repositories.orders import NotificationLogRepository, OrderRepository
from bot.database.repositories.settings import SettingRepository
from bot.database.repositories.support import SupportRepository
from bot.database.repositories.users import CustomerRepository, UserRepository

__all__ = [
    "BaseRepository",
    "CartRepository",
    "CategoryRepository",
    "CustomerRepository",
    "NotificationLogRepository",
    "OrderRepository",
    "ProductRepository",
    "SettingRepository",
    "SupportRepository",
    "UserRepository",
]
