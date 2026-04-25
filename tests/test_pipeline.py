import json
from pathlib import Path

import httpx

from dangdang_kgqa.crawler.pipeline import NOVEL_CATEGORY_ROOT, DangdangCrawler, category_page_url
from dangdang_kgqa.models import BookRecord, Category
from dangdang_kgqa.xml_store import write_book_xml


FIXTURES = Path(__file__).parent / "fixtures"


class MissingDetailClient:
    def fetch_text(self, url: str) -> str:
        request = httpx.Request("GET", url)
        response = httpx.Response(404, request=request)
        raise httpx.HTTPStatusError("detail page not found", request=request, response=response)


def test_with_detail_keeps_listing_book_when_detail_page_is_404():
    crawler = DangdangCrawler(client=MissingDetailClient())
    book = BookRecord(
        dangdang_id="410501986",
        title="已失效商品",
        price=39.9,
        url="https://product.dangdang.com/410501986.html",
    )

    result = crawler._with_detail(book)

    assert result == book


def test_crawl_resume_skips_book_with_existing_xml(tmp_path: Path):
    xml_dir = tmp_path / "xml"
    write_book_xml(
        BookRecord(dangdang_id="29914884", title="此刻是春天"),
        xml_dir / "01.03.30.00.00.00" / "29914884.xml",
    )
    client = StaticCategoryClient()
    crawler = DangdangCrawler(client=client)

    stats = crawler.crawl(
        xml_dir=xml_dir,
        state_path=tmp_path / "crawl_state.json",
        categories=[sample_category()],
        max_pages_per_category=1,
        include_details=True,
    )

    assert stats.books_seen == 1
    assert stats.books_written == 0
    assert client.detail_fetches == 0


def test_crawl_resume_skips_completed_page_from_state(tmp_path: Path):
    state_path = tmp_path / "crawl_state.json"
    page_url = category_page_url("01.03.30.00.00.00", 1)
    state_path.write_text(json.dumps({"version": 1, "completed_pages": [page_url]}), encoding="utf-8")
    crawler = DangdangCrawler(client=FailIfFetchedClient())

    stats = crawler.crawl(
        xml_dir=tmp_path / "xml",
        state_path=state_path,
        categories=[sample_category()],
        max_pages_per_category=1,
    )

    assert stats.books_seen == 0
    assert stats.books_written == 0


def test_crawl_resume_marks_page_completed_after_processing(tmp_path: Path):
    state_path = tmp_path / "crawl_state.json"
    crawler = DangdangCrawler(client=StaticCategoryClient())

    stats = crawler.crawl(
        xml_dir=tmp_path / "xml",
        state_path=state_path,
        categories=[sample_category()],
        max_pages_per_category=1,
        include_details=False,
    )

    payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert stats.books_written == 1
    assert category_page_url("01.03.30.00.00.00", 1) in payload["completed_pages"]


def test_discover_categories_uses_search_filter_and_expands_second_level():
    crawler = DangdangCrawler(client=DiscoveryClient())

    categories = crawler.discover_categories()

    assert [category.name for category in categories] == ["中国当代小说", "日本", "美国"]
    by_name = {category.name: category for category in categories}
    assert by_name["中国当代小说"].path_names == ("中国当代小说",)
    assert by_name["日本"].path_names == ("外国小说", "日本")
    assert by_name["日本"].parent_name == "外国小说"


def test_discover_categories_can_expand_facet_pages():
    crawler = DangdangCrawler(client=FacetDiscoveryClient())

    categories = crawler.discover_categories(facet_groups=("篇幅",))

    assert len(categories) == 2
    assert categories[0].name == "中国当代小说"
    assert categories[0].facets == {"length": "长篇"}
    assert categories[0].url == "https://category.dangdang.com/cp01.03.30.00.00.00-a1000770%3A1.html"
    assert categories[1].facets == {}


def test_crawl_resume_merges_missing_facets_into_existing_xml(tmp_path: Path):
    xml_dir = tmp_path / "xml"
    target = xml_dir / "01.03.30.00.00.00" / "29914884.xml"
    write_book_xml(BookRecord(dangdang_id="29914884", title="此刻是春天"), target)
    client = StaticCategoryClient()
    crawler = DangdangCrawler(client=client)
    category = Category(
        code="01.03.30.00.00.00",
        name="中国当代小说",
        url=category_page_url("01.03.30.00.00.00", 1),
        path_names=("中国当代小说",),
        facets={"brand": "博集天卷"},
    )

    stats = crawler.crawl(
        xml_dir=xml_dir,
        state_path=tmp_path / "crawl_state.json",
        categories=[category],
        max_pages_per_category=1,
        include_details=True,
    )

    assert stats.books_written == 0
    assert client.detail_fetches == 0
    assert "博集天卷" in target.read_text(encoding="utf-8")


class StaticCategoryClient:
    def __init__(self) -> None:
        self.detail_fetches = 0

    def fetch_text(self, url: str) -> str:
        if "category.dangdang.com" in url:
            return (FIXTURES / "category_sample.html").read_text(encoding="utf-8")
        self.detail_fetches += 1
        return (FIXTURES / "product_sample.html").read_text(encoding="utf-8")


class FailIfFetchedClient:
    def fetch_text(self, url: str) -> str:
        raise AssertionError(f"resume should skip fetching completed page: {url}")


class DiscoveryClient:
    def fetch_text(self, url: str) -> str:
        if url == NOVEL_CATEGORY_ROOT:
            return """
            <li dd_name="分类">
              <div class="list_left" title="分类">分类</div>
              <div class="list_right">
                <span><a href="/cp01.03.30.00.00.00.html" title="中国当代小说">中国当代小说</a></span>
                <span><a href="/cp01.03.35.00.00.00.html" title="外国小说">外国小说</a></span>
              </div>
            </li>
            """
        if "cp01.03.35.00.00.00.html" in url:
            return """
            <li dd_name="分类">
              <div class="list_left" title="分类">分类</div>
              <div class="list_right">
                <span><a href="/cp01.03.35.07.00.00.html" title="日本">日本</a></span>
                <span><a href="/cp01.03.35.02.00.00.html" title="美国">美国</a></span>
              </div>
            </li>
            """
        return "<html><body></body></html>"


class FacetDiscoveryClient:
    def fetch_text(self, url: str) -> str:
        if url == NOVEL_CATEGORY_ROOT:
            return """
            <li dd_name="分类">
              <div class="list_left" title="分类">分类</div>
              <div class="list_right">
                <span><a href="/cp01.03.30.00.00.00.html" title="中国当代小说">中国当代小说</a></span>
              </div>
            </li>
            """
        if "cp01.03.30.00.00.00.html" in url:
            return """
            <li dd_name="篇幅">
              <div class="list_left" title="篇幅">篇幅</div>
              <div class="list_right">
                <span rel="1"><a href="/cp01.03.30.00.00.00-a1000770%3A1.html" title="长篇">长篇</a></span>
              </div>
            </li>
            """
        return "<html><body></body></html>"


def sample_category() -> Category:
    return Category(
        code="01.03.30.00.00.00",
        name="中国当代小说",
        url=category_page_url("01.03.30.00.00.00", 1),
        path_names=("小说", "中国当代小说"),
    )
