"""Ro'yxatlarni sahifalarga bo'lish (TZ 4.4 - katalog/buyurtmalar ro'yxati)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Pagination:
    """Sahifa hisob-kitoblari (bazadan olingan total asosida)."""

    page: int
    per_page: int
    total: int

    def __post_init__(self) -> None:
        if self.per_page < 1:
            raise ValueError("per_page kamida 1 bo'lishi kerak")

    @property
    def pages(self) -> int:
        """Jami sahifalar soni (bo'sh ro'yxatda ham 1)."""
        if self.total <= 0:
            return 1
        return math.ceil(self.total / self.per_page)

    @property
    def current(self) -> int:
        """Sahifa raqamini 1..pages oralig'iga keltiradi."""
        return max(1, min(self.page, self.pages))

    @property
    def has_prev(self) -> bool:
        return self.current > 1

    @property
    def has_next(self) -> bool:
        return self.current < self.pages

    @property
    def prev_page(self) -> int:
        return max(1, self.current - 1)

    @property
    def next_page(self) -> int:
        return min(self.pages, self.current + 1)

    @property
    def offset(self) -> int:
        return (self.current - 1) * self.per_page

    @property
    def limit(self) -> int:
        return self.per_page

    @property
    def info(self) -> tuple[int, int]:
        """(joriy sahifa, jami sahifa)"""
        return self.current, self.pages

    def index_range(self) -> tuple[int, int]:
        """Joriy sahifadagi elementlarning global tartib raqamlari."""
        start = self.offset + 1
        end = min(self.total, self.offset + self.per_page)
        return start, end

    def slice(self, items: Sequence[T]) -> list[T]:
        """Ro'yxatdan joriy sahifaga tegishli qismini qaytaradi."""
        return list(items)[self.offset : self.offset + self.per_page]

    def number_of(self, position: int) -> int:
        """Sahifadagi mahsulotning umumiy ro'yxatdagi tartib raqami."""
        return self.offset + position


def paginate(total: int, page: int = 1, per_page: int = 5) -> Pagination:
    return Pagination(page=page or 1, per_page=per_page, total=max(0, int(total or 0)))


__all__ = ["Pagination", "paginate"]
