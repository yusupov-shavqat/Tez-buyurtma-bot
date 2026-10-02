"""Inline tugmalar uchun callback data sxemalari.

Barcha `CallbackData` sinflari qisqa prefiks bilan belgilanadi va
aiogram'ning `X.filter(F.action == "...")` ko'rinishidagi filtri bilan
ishlatiladi. Har bir maydon standart qiymatga ega - shu sababli
`pack()` natijasi har doim bir xil sonda bo'lakdan iborat bo'ladi.

Misol::

    @router.callback_query(CartCB.filter(F.action == "add"))
    async def add(query: CallbackQuery, callback_data: CartCB, ctx: BotContext) -> None:
        ...
"""

from __future__ import annotations

from aiogram.filters.callback_data import CallbackData

#: Har bir callback data eng ko'p shuncha maydonga ega bo'lishi kerak.
MAX_FIELDS = 5

#: FSM holatlarida ishlatiladigan bo'sh qiymat o'rnini bosuvchi belgi.
EMPTY = "-"


class MenuCB(CallbackData, prefix="menu"):
    """Asosiy menyu va navigatsiya tugmalari."""

    action: str  # main | catalog | cart | orders | profile | support | admin | promo | search
    page: int = 1


class LangCB(CallbackData, prefix="lang"):
    """Til tanlash."""

    action: str = "set"  # set | menu
    code: str = EMPTY


class CatalogCB(CallbackData, prefix="cat"):
    """Katalog: kategoriyalar, sahifalash, aksiya va qidiruv."""

    action: str  # categories | category | promo | search | back
    category_id: int = 0
    page: int = 1


class ProductCB(CallbackData, prefix="prod"):
    """Mahsulot kartochkasi va miqdor tanlash."""

    action: str  # open | add | qty | input
    product_id: int = 0
    value: int = 0  # qadam soni (miqdor = value * unit.step)


class CartCB(CallbackData, prefix="cart"):
    """Savat amallari."""

    action: str  # open | inc | dec | remove | clear | checkout
    product_id: int = 0


class CheckoutCB(CallbackData, prefix="co"):
    """Buyurtma berish jarayoni (FSM)."""

    action: str  # start | delivery | pickup | addr | new_address | location | time
    #            # | comment | skip | payment | confirm | back | cancel
    value: str = EMPTY


class OrderCB(CallbackData, prefix="ord"):
    """Mijoz buyurtmalari ro'yxati va kartochkasi."""

    action: str  # list | detail | cancel | confirm_cancel | repeat
    order_id: int = 0
    page: int = 1


class ProfileCB(CallbackData, prefix="prof"):
    """Profil bo'limi."""

    action: str  # open | phone | language | addresses
    value: str = EMPTY


class SupportCB(CallbackData, prefix="sup"):
    """Qo'llab-quvvatlash bo'limi."""

    action: str  # open | write | call
    request_id: int = 0


class AdminCB(CallbackData, prefix="adm"):
    """Xodimlar (boshqaruv) paneli."""

    action: str  # menu | stats | new_orders | active_orders | order | status | status_set
    #            # | note | search | low_stock | support | reply | back
    order_id: int = 0
    request_id: int = 0
    page: int = 1
    value: str = EMPTY


__all__ = [
    "EMPTY",
    "MAX_FIELDS",
    "AdminCB",
    "CartCB",
    "CatalogCB",
    "CheckoutCB",
    "LangCB",
    "MenuCB",
    "OrderCB",
    "ProductCB",
    "ProfileCB",
    "SupportCB",
]
