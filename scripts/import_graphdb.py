from __future__ import annotations

import argparse
from pathlib import Path

from dangdang_kgqa.config import Settings, settings
from dangdang_kgqa.graphdb import GraphDBClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Import RDF file into GraphDB through RDF4J REST API.")
    parser.add_argument("--repo", default=settings.graphdb_repo)
    parser.add_argument("--base-url", default=settings.graphdb_base_url)
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--content-type", default="application/n-triples")
    args = parser.parse_args()
    config = Settings(
        data_dir=settings.data_dir,
        xml_dir=settings.xml_dir,
        nt_dir=settings.nt_dir,
        cache_dir=settings.cache_dir,
        graphdb_base_url=args.base_url.rstrip("/"),
        graphdb_repo=args.repo,
        request_timeout_seconds=settings.request_timeout_seconds,
        request_delay_seconds=settings.request_delay_seconds,
        user_agent=settings.user_agent,
    )
    GraphDBClient(config).import_file(args.file, args.content_type)
    print(f"imported file={args.file} repo={args.repo}")


if __name__ == "__main__":
    main()
