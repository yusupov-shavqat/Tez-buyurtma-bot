"""Handler (router) qatlami.

Router'lar HAR CHAQIRUVDA yangi nusxada quriladi (`build_router` fabrikalari),
chunki aiogram router'ini bitta dispatcher'ga faqat bir marta ulash mumkin -
shu sababli `register_routers()` ni bir necha marta chaqirish xavfsiz.

Ulanish tartibi muhim:

    1. ``start``    - /start, til tanlash, telefon raqami, /help;
    2. ``catalog``  - katalog, qidiruv, mahsulot kartochkasi;
    3. ``cart``     - savat;
    4. ``checkout`` - buyurtma berish (FSM);
    5. ``orders``   - mijozning buyurtmalari;
    6. ``profile``  - profil (telefon, manzillar);
    7. ``support``  - qo'llab-quvvatlash;
    8. ``admin``    - xodimlar paneli (`StaffOnlyMiddleware` bilan);
    9. ``fallback`` - qolgan hamma narsa (har doim OXIRIDA ulanadi).

Yangi bo'limlar ``ROUTER_BUILDERS`` ro'yxatiga ``build_fallback_router`` dan
OLDIN qo'shilishi kerak, aks holda ularning xabarlari fallback'ga tushib qoladi.

Misol::

    from bot.handlers import register_routers
    register_routers(dispatcher)
"""

from __future__ import annotations

from aiogram import Dispatcher, Router

from bot.handlers.admin import build_router as build_admin_router
from bot.handlers.cart import build_router as build_cart_router
from bot.handlers.catalog import build_router as build_catalog_router
from bot.handlers.checkout import build_router as build_checkout_router
from bot.handlers.fallback import build_router as build_fallback_router
from bot.handlers.orders import build_router as build_orders_router
from bot.handlers.profile import build_router as build_profile_router
from bot.handlers.start import build_router as build_start_router
from bot.handlers.support import build_router as build_support_router

#: Router yasovchi fabrikalar (ulanish tartibi - muhim!).
ROUTER_BUILDERS = (
    build_start_router,
    build_catalog_router,
    build_cart_router,
    build_checkout_router,
    build_orders_router,
    build_profile_router,
    build_support_router,
    build_admin_router,
)


def build_routers(*, include_fallback: bool = True) -> list[Router]:
    """Barcha router'larning yangi nusxalarini yasaydi (tartib saqlangan)."""
    builders = (*ROUTER_BUILDERS, build_fallback_router) if include_fallback else ROUTER_BUILDERS
    return [build() for build in builders]


def register_routers(dispatcher: Dispatcher, *, include_fallback: bool = True) -> Dispatcher:
    """Router'larni dispatcher'ga ketma-ket ulaydi va dispatcher'ni qaytaradi."""
    for router in build_routers(include_fallback=include_fallback):
        dispatcher.include_router(router)
    return dispatcher


__all__ = [
    "ROUTER_BUILDERS",
    "build_admin_router",
    "build_cart_router",
    "build_catalog_router",
    "build_checkout_router",
    "build_fallback_router",
    "build_orders_router",
    "build_profile_router",
    "build_routers",
    "build_start_router",
    "build_support_router",
    "register_routers",
]
