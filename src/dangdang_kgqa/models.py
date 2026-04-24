from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Category:
    code: str
    name: str
    url: str
    parent_code: str | None = None
    parent_name: str | None = None
    path_names: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ProductDetail:
    dangdang_id: str | None = None
    category_code: str | None = None
    category_name: str | None = None
    publisher: str | None = None
    published_at: str | None = None
    rating_percent: float | None = None
    comments_count: int | None = None


@dataclass(frozen=True)
class BookRecord:
    dangdang_id: str
    title: str
    price: float | None = None
    authors: list[str] = field(default_factory=list)
    publisher: str | None = None
    published_at: str | None = None
    rating_percent: float | None = None
    comments_count: int | None = None
    category_code: str | None = None
    category_name: str | None = None
    category_path: tuple[str, ...] = field(default_factory=tuple)
    url: str | None = None


@dataclass(frozen=True)
class CategoryPage:
    total_count: int | None
    total_pages: int | None
    books: list[BookRecord]


@dataclass(frozen=True)
class ClassifiedQuestion:
    intent: str
    slots: dict[str, str]
    original: str
