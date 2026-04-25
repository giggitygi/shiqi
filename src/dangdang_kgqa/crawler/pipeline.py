from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import httpx

from dangdang_kgqa.config import Settings, settings
from dangdang_kgqa.crawler.client import DangdangHttpClient
from dangdang_kgqa.crawler.parsers import (
    category_code_from_url,
    merge_detail,
    parse_category_page,
    parse_filter_categories,
    parse_filter_groups,
    parse_homepage_categories,
    parse_product_detail,
)
from dangdang_kgqa.models import BookRecord, Category
from dangdang_kgqa.xml_store import read_book_xml, write_book_xml


NOVEL_HOME = "https://book.dangdang.com/01.03.htm?ref=book-01-A"
NOVEL_CATEGORY_ROOT = "https://category.dangdang.com/cp01.03.00.00.00.00.html"
FACET_FIELD_BY_GROUP = {
    "篇幅": "length",
    "品牌": "brand",
    "小说类型": "novel_type",
    "系列": "series",
    "折扣": "discount",
}
DEFAULT_FACET_GROUPS = tuple(FACET_FIELD_BY_GROUP)
FACET_GROUP_ALIASES = {
    "length": "篇幅",
    "brand": "品牌",
    "novel_type": "小说类型",
    "novel-type": "小说类型",
    "type": "小说类型",
    "series": "系列",
    "discount": "折扣",
}


@dataclass(frozen=True)
class CrawlStats:
    categories_seen: int
    books_seen: int
    books_written: int


@dataclass
class CrawlState:
    path: Path | None
    completed_pages: set[str]

    @classmethod
    def load(cls, path: Path) -> CrawlState:
        if not path.exists():
            return cls(path=path, completed_pages=set())
        payload = json.loads(path.read_text(encoding="utf-8"))
        pages = payload.get("completed_pages", [])
        if not isinstance(pages, list):
            raise ValueError(f"Invalid crawl state completed_pages in {path}")
        return cls(path=path, completed_pages={str(page) for page in pages})

    @classmethod
    def disabled(cls) -> CrawlState:
        return cls(path=None, completed_pages=set())

    def is_completed(self, page_url: str) -> bool:
        return page_url in self.completed_pages

    def mark_completed(self, page_url: str) -> None:
        self.completed_pages.add(page_url)
        self.save()

    def save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "version": 1,
            "completed_pages": sorted(self.completed_pages),
        }
        temp_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(self.path)


class DangdangCrawler:
    def __init__(self, client: DangdangHttpClient | None = None, config: Settings = settings):
        self.client = client or DangdangHttpClient(config)
        self.config = config

    def discover_categories(
        self,
        home_url: str = NOVEL_CATEGORY_ROOT,
        facet_groups: tuple[str, ...] = (),
    ) -> list[Category]:
        page_html = self.client.fetch_text(home_url)
        top_categories = parse_filter_categories(page_html)
        if not top_categories:
            return parse_homepage_categories(page_html)

        categories: list[Category] = []
        for top_category in top_categories:
            child_categories = parse_filter_categories(
                self.client.fetch_text(top_category.url),
                parent=top_category,
            )
            categories.extend(child_categories or [top_category])
        if facet_groups:
            categories = self._expand_facet_categories(categories, facet_groups)
        return categories

    def crawl(
        self,
        *,
        xml_dir: Path | None = None,
        categories: list[Category] | None = None,
        max_pages_per_category: int = 1,
        max_books: int | None = 100,
        include_details: bool = True,
        resume: bool = True,
        state_path: Path | None = None,
    ) -> CrawlStats:
        output_dir = xml_dir or self.config.xml_dir
        categories = categories or self.discover_categories()
        crawl_state = CrawlState.load(state_path or output_dir / "crawl_state.json") if resume else CrawlState.disabled()
        existing_paths = _existing_book_paths(output_dir) if resume else {}
        seen_ids = set(existing_paths)
        books_seen = 0
        books_written = 0
        for category in categories:
            for page_number in range(1, max_pages_per_category + 1):
                page_url = category_list_page_url(category, page_number)
                if resume and crawl_state.is_completed(page_url):
                    continue
                category_page = parse_category_page(
                    self.client.fetch_text(page_url),
                    category_name=category.name,
                    category_code=category.code,
                    category_path=category.path_names,
                    facets=category.facets,
                )
                for index, book in enumerate(category_page.books):
                    books_seen += 1
                    if book.dangdang_id in seen_ids:
                        existing_path = existing_paths.get(book.dangdang_id)
                        if existing_path:
                            self._merge_existing_book(existing_path, book)
                        continue
                    seen_ids.add(book.dangdang_id)
                    final_book = self._with_detail(book) if include_details else book
                    existing_paths[book.dangdang_id] = self._write_book(output_dir, final_book)
                    books_written += 1
                    if max_books is not None and books_written >= max_books:
                        if index == len(category_page.books) - 1 and resume:
                            crawl_state.mark_completed(page_url)
                        return CrawlStats(
                            categories_seen=len(categories),
                            books_seen=books_seen,
                            books_written=books_written,
                        )
                if resume:
                    crawl_state.mark_completed(page_url)
        return CrawlStats(
            categories_seen=len(categories),
            books_seen=books_seen,
            books_written=books_written,
        )

    def _with_detail(self, book: BookRecord) -> BookRecord:
        if not book.url:
            return book
        try:
            detail_html = self.client.fetch_text(book.url)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {404, 410}:
                return book
            raise
        detail = parse_product_detail(detail_html)
        return merge_detail(book, detail)

    def _expand_facet_categories(
        self,
        categories: list[Category],
        facet_groups: tuple[str, ...],
    ) -> list[Category]:
        normalized_groups = _normalize_facet_groups(facet_groups)
        expanded: list[Category] = []
        for category in categories:
            groups = parse_filter_groups(self.client.fetch_text(category.url))
            for group in normalized_groups:
                field_name = FACET_FIELD_BY_GROUP[group]
                for option in groups.get(group, []):
                    expanded.append(
                        replace(
                            category,
                            url=option.url,
                            facets={**category.facets, field_name: option.value},
                        )
                    )
            expanded.append(category)
        return expanded

    @staticmethod
    def _write_book(output_dir: Path, book: BookRecord) -> Path:
        target = _book_xml_path(output_dir, book)
        write_book_xml(book, target)
        return target

    @staticmethod
    def _merge_existing_book(path: Path, incoming: BookRecord) -> None:
        current = read_book_xml(path)
        merged = replace(
            current,
            category_code=current.category_code or incoming.category_code,
            category_name=current.category_name or incoming.category_name,
            category_path=current.category_path or incoming.category_path,
            length=current.length or incoming.length,
            brand=current.brand or incoming.brand,
            novel_type=current.novel_type or incoming.novel_type,
            series=current.series or incoming.series,
            discount=current.discount or incoming.discount,
        )
        if merged != current:
            write_book_xml(merged, path)


def category_page_url(category_code: str, page_number: int) -> str:
    if page_number <= 1:
        return f"https://category.dangdang.com/cp{category_code}.html"
    return f"https://category.dangdang.com/pg{page_number}-cp{category_code}.html"


def category_list_page_url(category: Category, page_number: int) -> str:
    if page_number <= 1:
        return category.url
    marker = "https://category.dangdang.com/cp"
    if category.url.startswith(marker):
        return category.url.replace(marker, f"https://category.dangdang.com/pg{page_number}-cp", 1)
    return category_page_url(category.code, page_number)


def categories_from_codes(codes: list[str], known_categories: list[Category]) -> list[Category]:
    by_code = {category.code: category for category in known_categories}
    categories: list[Category] = []
    for code in codes:
        clean_code = code.removeprefix("cp").removesuffix(".html")
        if clean_code in by_code:
            categories.append(by_code[clean_code])
        else:
            categories.append(
                Category(
                    code=clean_code,
                    name=clean_code,
                    url=category_page_url(clean_code, 1),
                    path_names=(clean_code,),
                )
            )
    return categories


def category_from_url(name: str, url: str) -> Category:
    code = category_code_from_url(url)
    if not code:
        raise ValueError(f"Cannot parse category code from {url}")
    return Category(code=code, name=name, url=url, path_names=(name,))


def _book_xml_path(output_dir: Path, book: BookRecord) -> Path:
    category = book.category_code or "unknown"
    return output_dir / category / f"{book.dangdang_id}.xml"


def _existing_book_paths(xml_dir: Path) -> dict[str, Path]:
    if not xml_dir.exists():
        return {}
    return {path.stem: path for path in xml_dir.rglob("*.xml") if path.stem.isdigit()}


def _normalize_facet_groups(groups: tuple[str, ...]) -> tuple[str, ...]:
    normalized: list[str] = []
    for group in groups:
        clean = group.strip()
        clean = FACET_GROUP_ALIASES.get(clean, clean)
        if clean not in FACET_FIELD_BY_GROUP:
            raise ValueError(f"Unsupported facet group: {group}")
        if clean not in normalized:
            normalized.append(clean)
    return tuple(normalized)
