"""Pul va miqdor qiymatlari bilan ishlash (Decimal asosida).

Barcha hisob-kitoblar `Decimal` da bajariladi - float xatolari bo'lmasligi uchun.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENTS = Decimal("0.01")
ZERO = Decimal("0")
THOUSANDTH = Decimal("0.001")


def to_decimal(value: object, default: Decimal = ZERO) -> Decimal:
    """Turli tipdagi qiymatni Decimal ga aylantiradi."""
    if value is None:
        return default
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return Decimal(int(value))
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    text = str(value).strip().replace("\u00a0", "").replace(" ", "")
    if not text:
        return default
    text = text.replace(",", ".")
    try:
        return Decimal(text)
    except InvalidOperation:
        return default


def round_money(value: object) -> Decimal:
    """Pul summasini 2 xonaga yaxlitlaydi."""
    return to_decimal(value).quantize(CENTS, rounding=ROUND_HALF_UP)


def parse_decimal(raw: object) -> Decimal:
    """Foydalanuvchi kiritgan sonni Decimal ga aylantiradi.

    "1 250,5" ham, "1250.5" ham qabul qilinadi.
    Xato bo'lsa `ValueError` ko'tariladi.
    """
    text = str(raw).strip().replace("\u00a0", "").replace("\u2009", "").replace(" ", "")
    if not text:
        raise ValueError("empty")
    text = text.replace(",", ".")
    if text.count(".") > 1:
        raise ValueError("invalid")
    try:
        return Decimal(text)
    except (InvalidOperation, ArithmeticError) as exc:  # pragma: no cover - himoya
        raise ValueError("invalid") from exc


def format_number(value: object, *, max_decimals: int = 3) -> str:
    """Sonni o'zbek/rus formatida yozadi: 1 250 000,5"""
    number = to_decimal(value)
    sign = "-" if number < 0 else ""
    number = abs(number).quantize(
        Decimal(1).scaleb(-max_decimals), rounding=ROUND_HALF_UP
    )
    integer_part, _, fraction_part = f"{number:f}".partition(".")
    integer_part = f"{int(integer_part):,}".replace(",", " ")
    fraction_part = fraction_part.rstrip("0")
    if fraction_part:
        return f"{sign}{integer_part},{fraction_part}"
    return f"{sign}{integer_part}"


def format_money(value: object, currency: str = "so'm", *, decimals: int = 2) -> str:
    """Summani valyuta bilan yozadi: '1 250 000 so'm'."""
    body = format_number(value, max_decimals=decimals)
    return f"{body} {currency}".strip() if currency else body


def format_quantity(quantity: object, unit_label: str) -> str:
    """Miqdorni o'lchov birligi bilan yozadi: '5 dona'."""
    return f"{format_number(quantity)} {unit_label}".strip()


def percent_of(value: object, percent: object) -> Decimal:
    base = to_decimal(value)
    rate = to_decimal(percent)
    return round_money(base * rate / Decimal(100))


def apply_discount(value: object, percent: object) -> Decimal:
    """Chegirmani qo'llaydi: 100000, 10% -> 90000."""
    return round_money(to_decimal(value) - percent_of(value, percent))


__all__ = [
    "CENTS",
    "ZERO",
    "apply_discount",
    "format_money",
    "format_number",
    "format_quantity",
    "parse_decimal",
    "percent_of",
    "round_money",
    "to_decimal",
]
