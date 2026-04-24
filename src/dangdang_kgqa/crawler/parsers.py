from __future__ import annotations

import html
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import quote, urljoin, urlparse

from bs4 import BeautifulSoup

from dangdang_kgqa.models import BookRecord, Category, CategoryPage, ProductDetail


NOVEL_CODE_PATTERN = re.compile(r"cp(01\.03\.\d{2}\.\d{2}\.\d{2}\.\d{2})\.html", re.I)
PRODUCT_ID_PATTERN = re.compile(r"product\.dangdang\.com/(\d+)\.html", re.I)


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return html.unescape(re.sub(r"\s+", " ", value.replace("\xa0", " "))).strip()


def absolute_url(url: str) -> str:
    if url.startswith("//"):
        return f"https:{url}"
    return urljoin("https://book.dangdang.com/", url)


def parse_homepage_categories(page_html: str) -> list[Category]:
    soup = BeautifulSoup(page_html, "html.parser")
    categories: list[Category] = []
    seen: set[str] = set()
    anchors = soup.select('.sidemenu a[nname^="book-"][href*="category.dangdang.com/cp01.03"]')
    if not anchors:
        anchors = soup.select('a[href*="category.dangdang.com/cp01.03"]')
    for anchor in anchors:
        url = absolute_url(anchor["href"].split("#", 1)[0])
        match = NOVEL_CODE_PATTERN.search(url)
        name = normalize_text(anchor.get("title")) or normalize_text(anchor.get_text())
        if not match or not name:
            continue
        code = match.group(1)
        if code not in seen:
            categories.append(Category(code=code, name=name, url=url))
            seen.add(code)
    return categories


def parse_category_page(page_html: str, category_name: str, category_code: str | None = None) -> CategoryPage:
    soup = BeautifulSoup(page_html, "html.parser")
    total_count = _parse_int_from_match(r"共\s*<em class=\"b\">(\d+)</em>\s*件商品", page_html)
    total_pages = _parse_int_from_match(
        r"<span class=\"or\">\s*\d+\s*</span>\s*<span>/(\d+)</span>", page_html
    )
    books = [_parse_book_card(li, category_name, category_code) for li in soup.select("ul.bigimg > li")]
    return CategoryPage(total_count=total_count, total_pages=total_pages, books=[book for book in books if book])


def parse_product_detail(page_html: str) -> ProductDetail:
    publisher = _match_clean(
        r'dd_name="出版社"[^>]*>\s*出版社:\s*<a[^>]*>(.*?)</a>', page_html
    )
    published_at = _match_clean(r"出版时间:\s*([^<]+)", page_html)
    comments_count = _parse_int_from_match(r'id="comm_num_down"[^>]*>\s*([\d,]+)\s*</a>', page_html)
    rating_percent = _parse_rating_percent(page_html)
    category_code = _match_clean(r'"categoryPath"\s*:\s*"([^"]+)"', page_html)
    category_name = _decode_json_string(_match_clean(r'"pathName"\s*:\s*"([^"]+)"', page_html))
    dangdang_id = _match_clean(r'"productId"\s*:\s*"?(\d+)"?', page_html)
    return ProductDetail(
        dangdang_id=dangdang_id or None,
        category_code=category_code or None,
        category_name=category_name or None,
        publisher=publisher or None,
        published_at=published_at or None,
        rating_percent=rating_percent,
        comments_count=comments_count,
    )


def merge_detail(book: BookRecord, detail: ProductDetail) -> BookRecord:
    return BookRecord(
        dangdang_id=book.dangdang_id,
        title=book.title,
        price=book.price,
        authors=book.authors,
        publisher=detail.publisher or book.publisher,
        published_at=detail.published_at or book.published_at,
        rating_percent=book.rating_percent if book.rating_percent is not None else detail.rating_percent,
        comments_count=detail.comments_count if detail.comments_count is not None else book.comments_count,
        category_code=detail.category_code or book.category_code,
        category_name=detail.category_name or book.category_name,
        url=book.url,
    )


def _parse_book_card(li, category_name: str, category_code: str | None) -> BookRecord | None:
    title_anchor = li.select_one('p.name a[href*="product.dangdang.com"]') or li.select_one(
        'a[href*="product.dangdang.com"]'
    )
    if not title_anchor:
        return None
    url = absolute_url(title_anchor.get("href", ""))
    product_match = PRODUCT_ID_PATTERN.search(url)
    if not product_match:
        return None
    raw_title = title_anchor.get_text(" ", strip=True) or title_anchor.get("title", "")
    title = normalize_text(raw_title)
    # List pages often put the short display title in the anchor text and the ad copy in title attr.
    if not title or len(title) > 80:
        title = normalize_text(title_anchor.get("title", ""))

    price = _parse_price(li.select_one(".search_now_price").get_text() if li.select_one(".search_now_price") else "")
    comments_count = _parse_int_from_match(r"([\d,]+)\s*条评论", li.get_text(" ", strip=True))
    rating_percent = _parse_rating_percent(str(li))
    authors = _parse_authors(li)
    publisher, published_at = _parse_list_publisher_and_date(li)
    return BookRecord(
        dangdang_id=product_match.group(1),
        title=title,
        price=price,
        authors=authors,
        publisher=publisher,
        published_at=published_at,
        rating_percent=rating_percent,
        comments_count=comments_count,
        category_code=category_code,
        category_name=category_name,
        url=url,
    )


def _parse_authors(li) -> list[str]:
    author_box = li.select_one(".search_book_author")
    if not author_box:
        return []
    first_span = author_box.find("span")
    if not first_span:
        return []
    text = normalize_text(first_span.get_text(" ", strip=True))
    text = re.split(r"[,，、;/；]\s*[^,，、;/；]*出品", text, maxsplit=1)[0]
    text = re.split(r"\s*/\s*\d{4}", text, maxsplit=1)[0]
    text = re.sub(r"\s*(著|编著|主编|译|译者|出品)\b", "", text)
    authors = [normalize_text(part) for part in re.split(r"[,，、;/；]\s*", text) if normalize_text(part)]
    return [author for author in authors if "出品" not in author][:4]


def _parse_list_publisher_and_date(li) -> tuple[str | None, str | None]:
    box = li.select_one(".search_book_author")
    if not box:
        return None, None
    text = normalize_text(box.get_text(" ", strip=True))
    date_match = re.search(r"/\s*(\d{4}-\d{2}-\d{2})", text)
    publisher_anchor = box.select_one('a[name="P_cbs"], a[dd_name="单品出版社"]')
    if not publisher_anchor:
        anchors = box.find_all("a")
        publisher_anchor = anchors[-1] if anchors else None
    publisher = normalize_text(publisher_anchor.get_text()) if publisher_anchor else None
    return publisher or None, date_match.group(1) if date_match else None


def _parse_price(value: str) -> float | None:
    cleaned = normalize_text(value).replace("¥", "").replace("￥", "")
    match = re.search(r"\d+(?:\.\d+)?", cleaned)
    if not match:
        return None
    try:
        return float(Decimal(match.group(0)))
    except InvalidOperation:
        return None


def _parse_rating_percent(value: str) -> float | None:
    match = re.search(r'style=["\'][^"\']*width:\s*(\d+(?:\.\d+)?)\s*%', value, re.I)
    if not match:
        return None
    try:
        return float(Decimal(match.group(1)))
    except InvalidOperation:
        return None


def _parse_int_from_match(pattern: str, text: str) -> int | None:
    match = re.search(pattern, text, re.I | re.S)
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def _match_clean(pattern: str, text: str) -> str:
    match = re.search(pattern, text, re.I | re.S)
    return normalize_text(match.group(1)) if match else ""


def _decode_json_string(value: str) -> str:
    if not value:
        return ""
    if "\\u" not in value and "\\x" not in value:
        return value
    try:
        return value.encode("utf-8").decode("unicode_escape")
    except UnicodeDecodeError:
        return value


def safe_uri_part(value: str) -> str:
    return quote(value.strip(), safe="")


def category_code_from_url(url: str) -> str | None:
    match = NOVEL_CODE_PATTERN.search(urlparse(url).path)
    return match.group(1) if match else None
