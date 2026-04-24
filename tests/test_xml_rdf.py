from pathlib import Path

from rdflib import Graph, Namespace, URIRef

from dangdang_kgqa.models import BookRecord
from dangdang_kgqa.rdf_exporter import book_to_graph, export_xml_directory_to_nt
from dangdang_kgqa.xml_store import read_book_xml, write_book_xml


KG = Namespace("https://example.org/dangdang/kg/")


def sample_book() -> BookRecord:
    return BookRecord(
        dangdang_id="29587088",
        title="河边的错误",
        price=47.30,
        authors=["余华"],
        publisher="时代文艺出版社",
        published_at="2023年07月",
        rating_percent=90.0,
        comments_count=107094,
        category_code="01.03.30.00.00.00",
        category_name="中国当代小说",
        category_path=("小说", "中国当代小说"),
        url="https://product.dangdang.com/29587088.html",
    )


def test_write_and_read_book_xml_round_trip(tmp_path: Path):
    target = tmp_path / "29587088.xml"

    write_book_xml(sample_book(), target)
    loaded = read_book_xml(target)

    assert loaded == sample_book()


def test_book_to_graph_contains_core_relations():
    graph = book_to_graph(sample_book())
    book_uri = URIRef("https://example.org/dangdang/book/29587088")

    assert (book_uri, KG.title, None) in graph
    assert (book_uri, KG.ratingPercent, None) in graph
    assert (book_uri, KG.authoredBy, URIRef("https://example.org/dangdang/author/%E4%BD%99%E5%8D%8E")) in graph
    assert (book_uri, KG.inCategory, URIRef("https://example.org/dangdang/category/01.03.30.00.00.00")) in graph
    assert (
        URIRef("https://example.org/dangdang/category/01.03.30.00.00.00"),
        KG.subCategoryOf,
        URIRef("https://example.org/dangdang/category/01.03.00.00.00.00"),
    ) in graph


def test_export_xml_directory_to_nt(tmp_path: Path):
    xml_dir = tmp_path / "xml"
    xml_dir.mkdir()
    write_book_xml(sample_book(), xml_dir / "29587088.xml")
    target = tmp_path / "books.nt"

    count = export_xml_directory_to_nt(xml_dir, target)

    assert count == 1
    loaded = Graph()
    loaded.parse(target, format="nt")
    assert len(loaded) > 8
