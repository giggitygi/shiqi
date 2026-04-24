from __future__ import annotations

import argparse
from pathlib import Path

from dangdang_kgqa.config import settings
from dangdang_kgqa.rdf_exporter import export_xml_directory_to_nt


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Dangdang book XML files to N-Triples.")
    parser.add_argument("--xml-dir", type=Path, default=settings.xml_dir)
    parser.add_argument("--out", type=Path, default=settings.nt_dir / "books.nt")
    args = parser.parse_args()
    count = export_xml_directory_to_nt(args.xml_dir, args.out)
    print(f"exported_books={count} out={args.out}")


if __name__ == "__main__":
    main()

