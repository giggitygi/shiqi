from pathlib import Path

from dangdang_kgqa.crawler.parsers import (
    merge_detail,
    parse_category_page,
    parse_filter_categories,
    parse_filter_groups,
    parse_homepage_categories,
    parse_product_detail,
)
from dangdang_kgqa.models import BookRecord, Category, ProductDetail


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


def test_parse_homepage_categories_preserves_visible_and_popup_hierarchy():
    html = """
    <div class="sidemenu">
      <div class="level_one">
        <dl class="primary_dl">
          <dt><a href="http://category.dangdang.com/cp01.03.56.00.00.00.html" title="世界名著">世界名著</a></dt>
          <dd>
            <a href="http://category.dangdang.com/cp01.03.56.01.00.00.html" title="欧洲">欧洲</a>
            <a href="http://category.dangdang.com/cp01.03.56.03.00.00.html" title="美洲">美洲</a>
          </dd>
        </dl>
      </div>
      <div class="level_one">
        <dl class="primary_dl">
          <dt><a href="http://category.dangdang.com/cp01.03.35.00.00.00.html" title="外国小说">外国小说</a></dt>
        </dl>
        <div class="hide submenu">
          <dl class="inner_dl">
            <dt><a href="http://category.dangdang.com/cp01.03.35.02.00.00.html" title="美国">美国</a></dt>
            <dd>
              <a href="http://category.dangdang.com/cp01.03.35.03.00.00.html" title="德国">德国</a>
              <a href="http://category.dangdang.com/cp01.03.35.01.00.00.html" title="英国">英国</a>
            </dd>
          </dl>
        </div>
      </div>
    </div>
    """

    by_name = {category.name: category for category in parse_homepage_categories(html)}

    assert by_name["欧洲"].parent_code == "01.03.56.00.00.00"
    assert by_name["欧洲"].parent_name == "世界名著"
    assert by_name["欧洲"].path_names == ("世界名著", "欧洲")
    assert by_name["美洲"].path_names == ("世界名著", "美洲")
    assert by_name["美国"].parent_code == "01.03.35.00.00.00"
    assert by_name["美国"].parent_name == "外国小说"
    assert by_name["美国"].path_names == ("外国小说", "美国")
    assert by_name["德国"].path_names == ("外国小说", "德国")


def test_parse_filter_categories_extracts_top_level_search_categories():
    html = """
    <li dd_name="分类" raw_h="35" class="child_li">
      <div class="list_left" title="分类">分类</div>
      <div class="list_right">
        <div class="list_content fix_list">
          <span><a href="/cp01.03.30.00.00.00.html" title="中国当代小说">中国当代小说</a></span>
          <span><a href="/cp01.03.35.00.00.00.html" title="外国小说">外国小说</a></span>
        </div>
      </div>
    </li>
    """

    categories = parse_filter_categories(html)

    assert [category.name for category in categories] == ["中国当代小说", "外国小说"]
    assert categories[0].code == "01.03.30.00.00.00"
    assert categories[0].path_names == ("中国当代小说",)
    assert categories[0].url == "https://category.dangdang.com/cp01.03.30.00.00.00.html"


def test_parse_filter_categories_extracts_second_level_search_categories():
    parent = Category(
        code="01.03.35.00.00.00",
        name="外国小说",
        url="https://category.dangdang.com/cp01.03.35.00.00.00.html",
        path_names=("外国小说",),
    )
    html = """
    <li dd_name="分类" raw_h="35" class="child_li">
      <div class="list_left" title="分类">分类</div>
      <div class="list_right">
        <span><a href="/cp01.03.35.07.00.00.html" title="日本">日本</a></span>
        <span><a href="/cp01.03.35.02.00.00.html" title="美国">美国</a></span>
      </div>
    </li>
    """

    categories = parse_filter_categories(html, parent=parent)

    assert [category.name for category in categories] == ["日本", "美国"]
    assert categories[0].parent_code == "01.03.35.00.00.00"
    assert categories[0].parent_name == "外国小说"
    assert categories[0].path_names == ("外国小说", "日本")


def test_parse_filter_groups_extracts_book_facets():
    html = """
    <li dd_name="篇幅"><div class="list_left" title="篇幅">篇幅</div>
      <div class="list_right"><span rel="1"><a href="/cp01.03.00.00.00.00-a1000770%3A1.html" title="长篇">长篇</a></span></div>
    </li>
    <li dd_name="品牌"><div class="list_left" title="品牌">品牌</div>
      <div class="list_right"><span rel="509"><a href="/cp01.03.00.00.00.00-a1000002%3A509.html" title="作家榜经典">作家榜经典</a></span></div>
    </li>
    <li dd_name="小说类型"><div class="list_left" title="小说类型">小说类型</div>
      <div class="list_right"><span rel="11"><a href="/cp01.03.00.00.00.00-a1000773%3A11.html" title="推理">推理</a></span></div>
    </li>
    <li dd_name="系列"><div class="list_left" title="系列">系列</div>
      <div class="list_right"><span rel="14"><a href="/cp01.03.00.00.00.00-a1000060%3A14.html" title="盗墓笔记系列">盗墓笔记系列</a></span></div>
    </li>
    <li dd_name="折扣"><div class="list_left" title="折扣">折扣</div>
      <div class="list_right"><span rel="1"><a href="/cp01.03.00.00.00.00-ld3-hd5.html" title="3-5折">3-5折</a></span></div>
    </li>
    """

    groups = parse_filter_groups(html)

    assert groups["篇幅"][0].value == "长篇"
    assert groups["品牌"][0].value == "作家榜经典"
    assert groups["小说类型"][0].value == "推理"
    assert groups["系列"][0].value == "盗墓笔记系列"
    assert groups["折扣"][0].url == "https://category.dangdang.com/cp01.03.00.00.00.00-ld3-hd5.html"


def test_parse_category_page_extracts_book_cards_and_paging():
    html = (FIXTURES / "category_sample.html").read_text(encoding="utf-8")

    page = parse_category_page(
        html,
        category_name="中国当代小说",
        facets={
            "length": "长篇",
            "brand": "博集天卷",
            "novel_type": "现实",
            "series": "春天系列",
            "discount": "5-7折",
        },
    )

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
    assert book.length == "长篇"
    assert book.brand == "博集天卷"
    assert book.novel_type == "现实"
    assert book.series == "春天系列"
    assert book.discount == "5-7折"
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
