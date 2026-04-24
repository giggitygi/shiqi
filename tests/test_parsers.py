from pathlib import Path

from dangdang_kgqa.crawler.parsers import (
    merge_detail,
    parse_category_page,
    parse_homepage_categories,
    parse_product_detail,
)
from dangdang_kgqa.models import BookRecord, ProductDetail


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_homepage_categories_extracts_novel_categories():
    html = """
    <div class="sidemenu">
      <div class="con flq_body">
        <a nname="book-104655-12626_1-695541_1"
           href="http://category.dangdang.com/cp01.03.32.00.00.00.html"
           title="中国古典小说">ignored text</a>
        <a nname="book-104655-12626_1-695542_1"
           href="http://category.dangdang.com/cp01.03.33.00.00.00.html"
           title="四大名著">四大名著        </a>
        <a nname="book-104655-12626_1-695631_1"
           href="http://category.dangdang.com/cp01.03.33.01.00.00.html#ddclick?act=clickcat"
           title="红楼梦">红楼梦</a>
      </div>
    </div>
    <a href="http://category.dangdang.com/cp01.04.00.00.00.00.html" title="青春文学">青春文学</a>
    """

    categories = parse_homepage_categories(html)

    assert [category.name for category in categories] == ["中国古典小说", "四大名著", "红楼梦"]
    assert [category.code for category in categories] == [
        "01.03.32.00.00.00",
        "01.03.33.00.00.00",
        "01.03.33.01.00.00",
    ]


def test_parse_category_page_extracts_book_cards_and_paging():
    html = (FIXTURES / "category_sample.html").read_text(encoding="utf-8")

    page = parse_category_page(html, category_name="中国当代小说")

    assert page.total_count == 245011
    assert page.total_pages == 100
    assert len(page.books) == 1
    book = page.books[0]
    assert book.dangdang_id == "29914884"
    assert book.title == "此刻是春天"
    assert book.price == 31.10
    assert book.authors == ["卢思浩"]
    assert book.publisher == "湖南文艺出版社"
    assert book.published_at == "2025-07-01"
    assert book.rating_percent == 90.0
    assert book.comments_count == 151053
    assert book.category_name == "中国当代小说"
    assert book.url == "https://product.dangdang.com/29914884.html"


def test_parse_product_detail_extracts_metadata():
    html = (FIXTURES / "product_sample.html").read_text(encoding="utf-8")

    detail = parse_product_detail(html)

    assert detail.dangdang_id == "29587088"
    assert detail.category_code == "01.03.30.00.00.00"
    assert detail.category_name == "中国当代小说"
    assert detail.publisher == "时代文艺出版社"
    assert detail.published_at == "2023年07月"
    assert detail.rating_percent == 95.4
    assert detail.comments_count == 107094


def test_merge_detail_keeps_listing_rating_when_available():
    book = BookRecord(
        dangdang_id="102771",
        title="红楼梦",
        rating_percent=90.0,
        comments_count=1061953,
    )
    detail = ProductDetail(rating_percent=91.8, comments_count=1061953, publisher="人民文学出版社")

    merged = merge_detail(book, detail)

    assert merged.rating_percent == 90.0
    assert merged.publisher == "人民文学出版社"
