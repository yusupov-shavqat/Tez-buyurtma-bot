"""FSM (ko'p qadamli suhbat) holatlari.

Har bir oqim o'z `StatesGroup` sinfiga ega bo'ladi:

    class CheckoutStates(StatesGroup):
        address = State()
        comment = State()

Handler'larda holat shunday filtrlanadi::

    @router.message(StateFilter(CheckoutStates.address), F.text)
    async def on_address(message: Message, ctx: BotContext, state: FSMContext) -> None:
        ...
"""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class StartStates(StatesGroup):
    """Ro'yxatdan o'tish: telefon raqamini kutish.

    Telefon raqami buyurtma berish uchun majburiy, shu sababli `/start`
    dan keyin foydalanuvchi raqamini yubormaguncha shu holat turadi.
    """

    waiting_phone = State()


class CatalogStates(StatesGroup):
    """Katalog: matnli qidiruv natijasini kutish."""

    search = State()


class CartStates(StatesGroup):
    """Savat: miqdorni qo'lda kiritish."""

    quantity = State()


class CheckoutStates(StatesGroup):
    """Buyurtma berish: matn kutadigan qadamlar.

    Yetkazish turi, vaqt va to'lov inline tugmalar orqali tanlanadi,
    shu sababli bu yerda faqat manzil va izoh qadamlari saqlanadi.
    """

    address = State()
    comment = State()


class ProfileStates(StatesGroup):
    """Profil: telefon raqamini yangilash."""

    phone = State()


class SupportStates(StatesGroup):
    """Qo'llab-quvvatlash: operatorga yoziladigan xabarni kutish."""

    message = State()


class AdminStates(StatesGroup):
    """Boshqaruv paneli (xodimlar): qidiruv va javob yozish."""

    search_order = State()
    order_reply = State()
    support_reply = State()


#: Buyurtma berish jarayonining matn kutadigan holatlari (bekor qilish uchun).
CHECKOUT_STATES = (CheckoutStates.address, CheckoutStates.comment)


__all__ = [
    "AdminStates",
    "CHECKOUT_STATES",
    "CartStates",
    "CatalogStates",
    "CheckoutStates",
    "ProfileStates",
    "StartStates",
    "SupportStates",
]
