"""Kiritilgan ma'lumotlarni tekshirish va normallashtirish."""

from __future__ import annotations

import re

_PHONE_RE = re.compile(r"\D+")
_UZ_MOBILE_PREFIXES = (
    "20", "33", "50", "55", "70", "71", "77", "78", "88", "90", "91", "93", "94",
    "95", "97", "98", "99",
)


def normalize_phone(raw: str | None, default_code: str = "998") -> str:
    """Telefon raqamini xalqaro formatga keltiradi: +998901234567.

    Qabul qilinadi: 90 123 45 67, 8901234567, +998 90 123 45 67.
    Xato bo'lsa bo'sh satr qaytaradi.
    """
    if not raw:
        return ""
    digits = _PHONE_RE.sub("", str(raw))
    if not digits:
        return ""
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 9:
        digits = default_code + digits
    elif len(digits) == 10 and digits.startswith("8"):
        digits = default_code + digits[1:]
    if len(digits) == 12 and digits.startswith(default_code):
        return f"+{digits}"
    if 11 <= len(digits) <= 15:
        return f"+{digits}"
    return ""


def is_valid_phone(raw: str | None, default_code: str = "998") -> bool:
    normalized = normalize_phone(raw, default_code)
    if not normalized:
        return False
    digits = normalized.lstrip("+")
    if digits.startswith(default_code):
        local = digits[len(default_code) :]
        return len(local) == 9 and local[:2] in _UZ_MOBILE_PREFIXES
    return True


def normalize_text(raw: str | None, *, max_length: int = 500, collapse: bool = True) -> str:
    """Ortiqcha bo'shliqlarni olib tashlaydi va uzunlikni cheklaydi."""
    text = "" if raw is None else str(raw).strip()
    text = text.replace("\u00a0", " ")
    if collapse:
        text = re.sub(r"\s+", " ", text)
    if max_length and len(text) > max_length:
        text = text[:max_length].strip()
    return text


def normalize_order_number(raw: str | None, prefix: str = "ORD") -> str:
    """'#ord-240101-0001' -> 'ORD-240101-0001'."""
    text = normalize_text(raw, max_length=32).lstrip("#").upper()
    if not text:
        return ""
    if prefix and not text.startswith(prefix.upper()):
        # Faqat raqamlar kiritilgan bo'lsa - prefiks qo'shamiz
        if re.fullmatch(r"\d+", text):
            return f"{prefix.upper()}-{text}"
    return text


def is_order_number(raw: str | None, prefix: str = "ORD") -> bool:
    text = normalize_text(raw, max_length=32)
    return bool(re.fullmatch(rf"{re.escape(prefix.upper())}-\d{{6}}-\d{{1,6}}", text.lstrip("#").upper()))


__all__ = [
    "is_order_number",
    "is_valid_phone",
    "normalize_order_number",
    "normalize_phone",
    "normalize_text",
]
