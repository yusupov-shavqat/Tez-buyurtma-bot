"""Matn bilan ishlash yordamchilari (HTML parse mode uchun)."""

from __future__ import annotations

import html
import re
from datetime import datetime, timedelta, timezone

TASHKENT_FALLBACK = timezone(timedelta(hours=5), name="UTC+05:00")

#: `<b>`, `</b>`, `<a href="...">` kabi teglar.
TAG_RE = re.compile(r"<[^>]+>")


def escape(value: object) -> str:
    """HTML uchun xavfsiz matn (foydalanuvchi kiritgan ma'lumotlar uchun)."""
    if value is None:
        return ""
    return html.escape(str(value), quote=False)


def code(value: object) -> str:
    return f"<code>{escape(value)}</code>"


def bold(value: object) -> str:
    return f"<b>{escape(value)}</b>"


def strip_html(value: object) -> str:
    """HTML teglari va entity'larini olib tashlab, oddiy matn qaytaradi.

    `answer_callback_query` (toast/alert) HTML parse rejimini qo'llab
    quvvatlamaydi - shu sababli bunday matnlarda `<b>` kabi teglar va
    `&amp;` kabi entity'lar foydalanuvchiga ko'rinib qolmasligi kerak.
    Faqat toast/alert matnlari uchun ishlatiladi (xabar matnlarida HTML
    saqlanadi).
    """
    if value is None:
        return ""
    return html.unescape(TAG_RE.sub("", str(value)))


def truncate(value: object, limit: int = 200, suffix: str = "…") -> str:
    text = "" if value is None else str(value).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - len(suffix))].rstrip() + suffix


def mask_phone(phone: str | None) -> str:
    """+998901234567 -> +998 90 *** 45 67"""
    if not phone:
        return "—"
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) == 12:
        return f"+{digits[:3]} {digits[3:5]} *** {digits[-4:-2]} {digits[-2:]}"
    return phone


def get_timezone(name: str = "Asia/Tashkent"):
    """Hudud vaqt mintaqasi (Windows'da tzdata bo'lmasa UTC+5 ga qaytadi)."""
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(name)
    except Exception:  # pragma: no cover - tzdata o'rnatilmagan holat
        return TASHKENT_FALLBACK


def to_local(value: datetime | None, tz_name: str = "Asia/Tashkent") -> datetime | None:
    """Naive UTC vaqtni mahalliy vaqtga o'tkazadi."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(get_timezone(tz_name))


def format_datetime(
    value: datetime | None,
    tz_name: str = "Asia/Tashkent",
    fmt: str = "%d.%m.%Y %H:%M",
) -> str:
    local = to_local(value, tz_name)
    return local.strftime(fmt) if local else "—"


def format_date(value: datetime | None, tz_name: str = "Asia/Tashkent") -> str:
    return format_datetime(value, tz_name, "%d.%m.%Y")


def format_time(value: datetime | None, tz_name: str = "Asia/Tashkent") -> str:
    return format_datetime(value, tz_name, "%H:%M")


def local_day_start(value: datetime | None = None, tz_name: str = "Asia/Tashkent") -> datetime:
    """Mahalliy kun boshlanishini UTC ko'rinishida qaytaradi (hisobotlar uchun)."""
    local = to_local(value or datetime.now(timezone.utc), tz_name)
    assert local is not None
    start_local = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return start_local.astimezone(timezone.utc).replace(tzinfo=None)


def format_period(start: datetime | None, end: datetime | None, tz_name: str = "Asia/Tashkent") -> str:
    return f"{format_date(start, tz_name)} — {format_date(end, tz_name)}"


__all__ = [
    "bold",
    "code",
    "escape",
    "format_date",
    "format_datetime",
    "format_period",
    "format_time",
    "get_timezone",
    "local_day_start",
    "mask_phone",
    "strip_html",
    "to_local",
    "truncate",
]
