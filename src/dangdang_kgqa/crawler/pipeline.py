from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dangdang_kgqa.config import Settings, settings
from dangdang_kgqa.crawler.client import DangdangHttpClient
from dangdang_kgqa.crawler.parsers import (
    category_code_from_url,
    merge_detail,
    parse_category_page,
    parse_homepage_categories,
    parse_product_detail,
)
from dangdang_kgqa.models import BookRecord, Category
from dangdang_kgqa.xml_store import write_book_xml


NOVEL_HOME = "https://book.dangdang.com/01.03.htm?ref=book-01-A"


@dataclass(frozen=True)
class CrawlStats:
    categories_seen: int
    books_seen: int
    books_written: int


class DangdangCrawler:
    def __init__(self, client: DangdangHttpClient | None = None, config: Settings = settings):
        self.client = client or DangdangHttpClient(config)
        self.config = config

    def discover_categories(self, home_url: str = NOVEL_HOME) -> list[Category]:
        return parse_homepage_categories(self.client.fetch_text(home_url))

    def crawl(
        self,
        *,
        xml_dir: Path | None = None,
        categories: list[Category] | None = None,
        max_pages_per_category: int = 1,
        max_books: int | None = 100,
        include_details: bool = True,
    ) -> CrawlStats:
        output_dir = xml_dir or self.config.xml_dir
        categories = categories or self.discover_categories()
        seen_ids: set[str] = set()
        books_seen = 0
        books_written = 0
        for category in categories:
            for page_number in range(1, max_pages_per_category + 1):
                page_url = category_page_url(category.code, page_number)
                category_page = parse_category_page(
                    self.client.fetch_text(page_url),
                    category_name=category.name,
                    category_code=category.code,
                    category_path=category.path_names,
                )
                for book in category_page.books:
                    books_seen += 1
                    if book.dangdang_id in seen_ids:
                        continue
                    seen_ids.add(book.dangdang_id)
                    final_book = self._with_detail(book) if include_details else book
                    self._write_book(output_dir, final_book)
                    books_written += 1
                    if max_books is not None and books_written >= max_books:
                        return CrawlStats(
                            categories_seen=len(categories),
                            books_seen=books_seen,
                            books_written=books_written,
                        )
        return CrawlStats(
            categories_seen=len(categories),
            books_seen=books_seen,
            books_written=books_written,
        )

    def _with_detail(self, book: BookRecord) -> BookRecord:
        if not book.url:
            return book
        detail = parse_product_detail(self.client.fetch_text(book.url))
        return merge_detail(book, detail)

    @staticmethod
    def _write_book(output_dir: Path, book: BookRecord) -> None:
        category = book.category_code or "unknown"
        write_book_xml(book, output_dir / category / f"{book.dangdang_id}.xml")


def category_page_url(category_code: str, page_number: int) -> str:
    if page_number <= 1:
        return f"https://category.dangdang.com/cp{category_code}.html"
    return f"https://category.dangdang.com/pg{page_number}-cp{category_code}.html"


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
