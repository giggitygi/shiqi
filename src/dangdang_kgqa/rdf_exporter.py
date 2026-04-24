from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.namespace import OWL, XSD

from dangdang_kgqa.models import BookRecord
from dangdang_kgqa.xml_store import iter_book_xml


KG = Namespace("https://example.org/dangdang/kg/")
BOOK = Namespace("https://example.org/dangdang/book/")
AUTHOR = Namespace("https://example.org/dangdang/author/")
PUBLISHER = Namespace("https://example.org/dangdang/publisher/")
CATEGORY = Namespace("https://example.org/dangdang/category/")


def book_to_graph(book: BookRecord) -> Graph:
    graph = Graph()
    bind_prefixes(graph)
    book_uri = BOOK[book.dangdang_id]
    graph.add((book_uri, RDF.type, KG.Book))
    graph.add((book_uri, KG.dangdangId, Literal(book.dangdang_id)))
    graph.add((book_uri, KG.title, Literal(book.title, lang="zh")))
    if book.url:
        graph.add((book_uri, KG.detailUrl, Literal(book.url, datatype=XSD.anyURI)))
    if book.price is not None:
        graph.add((book_uri, KG.price, Literal(book.price, datatype=XSD.decimal)))
    if book.rating_percent is not None:
        graph.add((book_uri, KG.ratingPercent, Literal(book.rating_percent, datatype=XSD.decimal)))
    if book.comments_count is not None:
        graph.add((book_uri, KG.commentsCount, Literal(book.comments_count, datatype=XSD.integer)))
    if book.published_at:
        graph.add((book_uri, KG.publishedAtText, Literal(book.published_at)))
    if book.category_code:
        path_codes = _category_path_codes(book.category_code, book.category_path)
        path_names = book.category_path or (book.category_name or book.category_code,)
        for index, code in enumerate(path_codes):
            category_uri = CATEGORY[code]
            graph.add((category_uri, RDF.type, KG.NovelCategory))
            label = path_names[index] if index < len(path_names) else code
            graph.add((category_uri, RDFS.label, Literal(label, lang="zh")))
            if index > 0:
                parent_uri = CATEGORY[path_codes[index - 1]]
                graph.add((category_uri, KG.subCategoryOf, parent_uri))
                graph.add((parent_uri, KG.superCategoryOf, category_uri))
        graph.add((book_uri, KG.inCategory, CATEGORY[path_codes[-1]]))
    for author in book.authors:
        author_uri = AUTHOR[_quote(author)]
        graph.add((author_uri, RDF.type, KG.Author))
        graph.add((author_uri, RDFS.label, Literal(author, lang="zh")))
        graph.add((book_uri, KG.authoredBy, author_uri))
    if book.publisher:
        publisher_uri = PUBLISHER[_quote(book.publisher)]
        graph.add((publisher_uri, RDF.type, KG.Publisher))
        graph.add((publisher_uri, RDFS.label, Literal(book.publisher, lang="zh")))
        graph.add((book_uri, KG.publishedBy, publisher_uri))
    return graph


def export_xml_directory_to_nt(xml_dir: Path, target: Path) -> int:
    target.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with target.open("w", encoding="utf-8", newline="\n") as file_obj:
        for book in iter_book_xml(xml_dir):
            file_obj.write(book_to_graph(book).serialize(format="nt"))
            count += 1
    return count


def ontology_graph() -> Graph:
    graph = Graph()
    bind_prefixes(graph)
    for cls in (KG.Book, KG.Author, KG.Publisher, KG.NovelCategory):
        graph.add((cls, RDF.type, OWL.Class))
    graph.add((KG.NovelCategory, RDFS.subClassOf, KG.Category))
    for prop in (
        KG.authoredBy,
        KG.wrote,
        KG.publishedBy,
        KG.publishedBook,
        KG.inCategory,
        KG.hasBook,
        KG.subCategoryOf,
        KG.superCategoryOf,
        KG.broaderCategory,
        KG.relatedToCategory,
    ):
        graph.add((prop, RDF.type, OWL.ObjectProperty))
    graph.add((KG.authoredBy, OWL.inverseOf, KG.wrote))
    graph.add((KG.publishedBy, OWL.inverseOf, KG.publishedBook))
    graph.add((KG.inCategory, OWL.inverseOf, KG.hasBook))
    graph.add((KG.subCategoryOf, OWL.inverseOf, KG.superCategoryOf))
    graph.add((KG.subCategoryOf, RDF.type, OWL.TransitiveProperty))
    graph.add((KG.broaderCategory, RDF.type, OWL.TransitiveProperty))
    graph.add((KG.subCategoryOf, RDFS.subPropertyOf, KG.broaderCategory))
    graph.add((KG.inCategory, RDFS.subPropertyOf, KG.relatedToCategory))
    graph.add((KG.authoredBy, RDFS.domain, KG.Book))
    graph.add((KG.authoredBy, RDFS.range, KG.Author))
    graph.add((KG.publishedBy, RDFS.domain, KG.Book))
    graph.add((KG.publishedBy, RDFS.range, KG.Publisher))
    graph.add((KG.inCategory, RDFS.domain, KG.Book))
    graph.add((KG.inCategory, RDFS.range, KG.NovelCategory))
    graph.add((KG.subCategoryOf, RDFS.domain, KG.NovelCategory))
    graph.add((KG.subCategoryOf, RDFS.range, KG.NovelCategory))
    for prop in (
        KG.title,
        KG.dangdangId,
        KG.detailUrl,
        KG.price,
        KG.ratingPercent,
        KG.commentsCount,
        KG.publishedAtText,
    ):
        graph.add((prop, RDF.type, OWL.DatatypeProperty))
    return graph


def bind_prefixes(graph: Graph) -> None:
    graph.bind("kg", KG)
    graph.bind("book", BOOK)
    graph.bind("author", AUTHOR)
    graph.bind("publisher", PUBLISHER)
    graph.bind("category", CATEGORY)


def _quote(value: str) -> str:
    return quote(value.strip(), safe="")


def _category_path_codes(category_code: str, category_path: tuple[str, ...]) -> tuple[str, ...]:
    if not category_path:
        return (category_code,)
    ancestors = _category_ancestor_codes(category_code)
    if len(ancestors) >= len(category_path):
        return tuple(ancestors[-len(category_path) :])
    return tuple([category_code] * len(category_path))


def _category_ancestor_codes(category_code: str) -> list[str]:
    parts = category_code.split(".")
    if len(parts) != 6:
        return [category_code]
    non_zero_indexes = [index for index in range(2, len(parts)) if parts[index] != "00"]
    codes = [".".join(parts[:2] + ["00"] * (len(parts) - 2))]
    for index in non_zero_indexes:
        code_parts = parts.copy()
        for later in range(index + 1, len(code_parts)):
            code_parts[later] = "00"
        codes.append(".".join(code_parts))
    return codes
