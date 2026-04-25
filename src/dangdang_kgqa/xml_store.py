from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from dangdang_kgqa.models import BookRecord


def write_book_xml(book: BookRecord, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    root = ET.Element("book", {"dangdang_id": book.dangdang_id})
    _add_text(root, "category_code", book.category_code)
    _add_text(root, "category_name", book.category_name)
    path_node = ET.SubElement(root, "category_path")
    for category_name in book.category_path:
        _add_text(path_node, "category", category_name)
    _add_text(root, "title", book.title)
    _add_text(root, "price", f"{book.price:.2f}" if book.price is not None else None)
    authors_node = ET.SubElement(root, "authors")
    for author in book.authors:
        _add_text(authors_node, "author", author)
    _add_text(root, "publisher", book.publisher)
    _add_text(root, "published_at", book.published_at)
    _add_text(root, "rating_percent", f"{book.rating_percent:g}" if book.rating_percent is not None else None)
    _add_text(root, "comments_count", str(book.comments_count) if book.comments_count is not None else None)
    _add_text(root, "length", book.length)
    _add_text(root, "brand", book.brand)
    _add_text(root, "novel_type", book.novel_type)
    _add_text(root, "series", book.series)
    _add_text(root, "discount", book.discount)
    _add_text(root, "url", book.url)
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(target, encoding="utf-8", xml_declaration=True)


def read_book_xml(source: Path) -> BookRecord:
    root = ET.parse(source).getroot()
    authors = [node.text or "" for node in root.findall("./authors/author") if node.text]
    price_text = _child_text(root, "price")
    rating_text = _child_text(root, "rating_percent")
    comments_text = _child_text(root, "comments_count")
    category_path = tuple(
        node.text.strip()
        for node in root.findall("./category_path/category")
        if node.text and node.text.strip()
    )
    return BookRecord(
        dangdang_id=root.attrib["dangdang_id"],
        title=_child_text(root, "title") or "",
        price=float(price_text) if price_text else None,
        authors=authors,
        publisher=_child_text(root, "publisher") or None,
        published_at=_child_text(root, "published_at") or None,
        rating_percent=float(rating_text) if rating_text else None,
        comments_count=int(comments_text) if comments_text else None,
        category_code=_child_text(root, "category_code") or None,
        category_name=_child_text(root, "category_name") or None,
        category_path=category_path,
        length=_child_text(root, "length") or None,
        brand=_child_text(root, "brand") or None,
        novel_type=_child_text(root, "novel_type") or None,
        series=_child_text(root, "series") or None,
        discount=_child_text(root, "discount") or None,
        url=_child_text(root, "url") or None,
    )


def iter_book_xml(xml_dir: Path):
    for path in sorted(xml_dir.rglob("*.xml")):
        yield read_book_xml(path)


def _add_text(parent: ET.Element, tag: str, value: str | None) -> None:
    node = ET.SubElement(parent, tag)
    node.text = value or ""


def _child_text(parent: ET.Element, tag: str) -> str:
    node = parent.find(tag)
    return node.text.strip() if node is not None and node.text else ""
