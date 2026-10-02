"""Foydalanuvchi va mijoz (CRM) repozitoriylari."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from bot.database.enums import CustomerSegment, Language, STAFF_ROLES, UserRole
from bot.database.models import Address, Customer, User, utcnow
from bot.database.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """`users` jadvali bilan ishlash."""

    model = User

    # ------------------------------------------------------------------
    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        stmt = select(User).where(User.telegram_id == telegram_id)
        return await self.session.scalar(stmt)

    async def get_with_customer(self, telegram_id: int) -> User | None:
        """Foydalanuvchi + mijoz kartochkasi + manzillari (bir so'rovda)."""
        stmt = (
            select(User)
            .options(selectinload(User.customer).selectinload(Customer.addresses))
            .where(User.telegram_id == telegram_id)
        )
        return await self.session.scalar(stmt)

    async def create(
        self,
        telegram_id: int,
        *,
        username: str | None = None,
        full_name: str | None = None,
        chat_id: int | None = None,
        language: Language = Language.UZ,
        role: UserRole = UserRole.CLIENT,
    ) -> User:
        user = User(
            telegram_id=telegram_id,
            chat_id=chat_id,
            username=username,
            full_name=full_name,
            language=language,
            role=role,
            last_seen_at=utcnow(),
        )
        return await self.add(user)

    async def get_or_create(
        self,
        telegram_id: int,
        *,
        username: str | None = None,
        full_name: str | None = None,
        chat_id: int | None = None,
        language: Language = Language.UZ,
        role: UserRole = UserRole.CLIENT,
    ) -> tuple[User, bool]:
        """(foydalanuvchi, yaratilganmi) qaytaradi."""
        user = await self.get_by_telegram_id(telegram_id)
        created = False
        if user is None:
            user = await self.create(
                telegram_id,
                username=username,
                full_name=full_name,
                chat_id=chat_id,
                language=language,
                role=role,
            )
            created = True
        else:
            await self.sync_from_telegram(
                user, username=username, full_name=full_name, chat_id=chat_id
            )
        return user, created

    async def sync_from_telegram(
        self,
        user: User,
        *,
        username: str | None = None,
        full_name: str | None = None,
        chat_id: int | None = None,
    ) -> User:
        """Telegram profili o'zgargan bo'lsa yangilaydi."""
        changed = False
        if username is not None and user.username != username:
            user.username = username
            changed = True
        if full_name and user.full_name != full_name:
            user.full_name = full_name
            changed = True
        if chat_id is not None and user.chat_id != chat_id:
            user.chat_id = chat_id
            changed = True
        if changed:
            user.last_seen_at = utcnow()
            await self.flush()
        return user

    async def set_phone(self, user: User, phone: str) -> User:
        user.phone = phone
        await self.flush()
        return user

    async def set_language(self, user: User, language: Language | str) -> User:
        user.language = Language(str(language))
        await self.flush()
        return user

    async def set_role(self, user: User, role: UserRole | str) -> User:
        user.role = UserRole(str(role))
        await self.flush()
        return user

    async def set_active(self, user: User, is_active: bool) -> User:
        user.is_active = is_active
        await self.flush()
        return user

    async def touch(self, user: User) -> User:
        user.last_seen_at = utcnow()
        await self.flush()
        return user

    async def list_staff(self) -> list[User]:
        stmt = select(User).where(User.role.in_([r.value for r in STAFF_ROLES])).order_by(User.id)
        result = await self.session.scalars(stmt)
        return list(result)

    async def count_by_role(self, role: UserRole) -> int:
        return await self.count(User.role == role)


class CustomerRepository(BaseRepository[Customer]):
    """`customers` va `addresses` jadvallari (CRM qismi)."""

    model = Customer

    # ------------------------------------------------------------------
    async def get_by_user_id(self, user_id: int) -> Customer | None:
        stmt = select(Customer).where(Customer.user_id == user_id)
        return await self.session.scalar(stmt)

    async def get_with_addresses(self, user_id: int) -> Customer | None:
        stmt = (
            select(Customer)
            .options(selectinload(Customer.addresses))
            .where(Customer.user_id == user_id)
        )
        return await self.session.scalar(stmt)

    async def get_or_create_for_user(self, user: User) -> Customer:
        customer = await self.get_by_user_id(user.id)
        if customer is None:
            customer = Customer(
                user_id=user.id,
                segment=CustomerSegment.NEW,
                company_name=user.display_name,
            )
            await self.add(customer)
        return customer

    async def update_profile(
        self,
        customer: Customer,
        *,
        company_name: str | None = None,
        address: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        notes: str | None = None,
    ) -> Customer:
        if company_name is not None:
            customer.company_name = company_name
        if address is not None:
            customer.address = address
        if latitude is not None:
            customer.latitude = latitude
        if longitude is not None:
            customer.longitude = longitude
        if notes is not None:
            customer.notes = notes
        await self.flush()
        return customer

    async def set_segment(self, customer: Customer, segment: CustomerSegment | str) -> Customer:
        customer.segment = CustomerSegment(str(segment))
        await self.flush()
        return customer

    async def add_debt(self, customer: Customer, amount: Decimal) -> Customer:
        """Qarzdorlikni o'zgartiradi (musbat - qarz oshadi, manfiy - kamayadi)."""
        current = Decimal(customer.debt_amount or 0)
        customer.debt_amount = (current + Decimal(amount)).quantize(Decimal("0.01"))
        await self.flush()
        return customer

    async def count_total(self) -> int:
        return await self.count()

    # -------------------------- Manzillar -----------------------------
    async def list_addresses(self, customer_id: int) -> list[Address]:
        stmt = (
            select(Address)
            .where(Address.customer_id == customer_id)
            .order_by(Address.is_default.desc(), Address.id.desc())
        )
        result = await self.session.scalars(stmt)
        return list(result)

    async def get_address(self, address_id: int) -> Address | None:
        return await self.session.get(Address, address_id)

    async def count_addresses(self, customer_id: int) -> int:
        """Mijozning saqlangan manzillari soni."""
        stmt = (
            select(func.count())
            .select_from(Address)
            .where(Address.customer_id == customer_id)
        )
        return int(await self.session.scalar(stmt) or 0)

    async def add_address(
        self,
        customer_id: int,
        address: str,
        *,
        label: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        make_default: bool = False,
    ) -> Address:
        """Manzilni saqlaydi (bir xil matn takrorlanmaydi)."""
        address = address.strip()
        existing = await self.session.scalar(
            select(Address).where(Address.customer_id == customer_id, Address.address == address)
        )
        if existing is not None:
            if latitude is not None:
                existing.latitude = latitude
            if longitude is not None:
                existing.longitude = longitude
            if make_default:
                await self.clear_default(customer_id)
                existing.is_default = True
            await self.flush()
            return existing

        total = await self.count_addresses(customer_id)
        is_default = make_default or total == 0
        if is_default:
            await self.clear_default(customer_id)
        item = Address(
            customer_id=customer_id,
            label=label,
            address=address,
            latitude=latitude,
            longitude=longitude,
            is_default=is_default,
        )
        return await self.add(item)

    async def clear_default(self, customer_id: int) -> None:
        for item in await self.list_addresses(customer_id):
            item.is_default = False
        await self.flush()

    async def delete_address(self, address: Address) -> None:
        customer_id = address.customer_id
        was_default = address.is_default
        await self.delete(address)
        if was_default:
            remaining = await self.list_addresses(customer_id)
            if remaining:
                remaining[0].is_default = True
                await self.flush()

    async def get_default_address(self, customer_id: int) -> Address | None:
        stmt = (
            select(Address)
            .where(Address.customer_id == customer_id)
            .order_by(Address.is_default.desc(), Address.id.desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def count_by_segment(self) -> dict[str, int]:
        stmt = select(Customer.segment, func.count()).group_by(Customer.segment)
        rows = (await self.session.execute(stmt)).all()
        return {str(segment): int(total) for segment, total in rows}


__all__ = ["CustomerRepository", "UserRepository"]

