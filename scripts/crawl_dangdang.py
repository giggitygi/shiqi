from __future__ import annotations

import argparse
from pathlib import Path

from dangdang_kgqa.config import settings
from dangdang_kgqa.crawler.pipeline import DangdangCrawler, categories_from_codes


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl Dangdang novel books into per-book XML files.")
    parser.add_argument("--sample", action="store_true", help="Use safe defaults for a small validation crawl.")
    parser.add_argument("--full", action="store_true", help="Crawl all discovered novel categories up to 100 pages each.")
    parser.add_argument("--category-code", action="append", default=[], help="Category code such as 01.03.30.00.00.00.")
    parser.add_argument("--max-pages-per-category", type=int, default=1)
    parser.add_argument("--max-books", type=int, default=100, help="Maximum books to write. Use 0 for no limit.")
    parser.add_argument("--xml-dir", type=Path, default=settings.xml_dir)
    parser.add_argument("--no-details", action="store_true", help="Skip product detail pages.")
    args = parser.parse_args()

    crawler = DangdangCrawler()
    discovered = crawler.discover_categories()
    categories = categories_from_codes(args.category_code, discovered) if args.category_code else discovered
    if args.full:
        args.max_pages_per_category = max(args.max_pages_per_category, 100)
        if args.max_books == 100:
            args.max_books = 0
    if args.sample:
        categories = categories[:2]
        args.max_pages_per_category = min(args.max_pages_per_category, 1)
        args.max_books = min(args.max_books, 50)
    max_books = None if args.max_books == 0 else args.max_books
    stats = crawler.crawl(
        xml_dir=args.xml_dir,
        categories=categories,
        max_pages_per_category=args.max_pages_per_category,
        max_books=max_books,
        include_details=not args.no_details,
    )
    print(
        f"categories={stats.categories_seen} books_seen={stats.books_seen} "
        f"books_written={stats.books_written} xml_dir={args.xml_dir}"
    )


if __name__ == "__main__":
    main()
