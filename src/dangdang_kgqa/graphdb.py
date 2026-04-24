from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from dangdang_kgqa.config import Settings, settings


class GraphDBClient:
    def __init__(self, config: Settings = settings):
        self.config = config

    @property
    def query_url(self) -> str:
        return f"{self.config.graphdb_base_url}/repositories/{self.config.graphdb_repo}"

    @property
    def statements_url(self) -> str:
        return f"{self.query_url}/statements"

    def query(self, sparql: str) -> list[dict[str, Any]]:
        response = httpx.post(
            self.query_url,
            data={"query": sparql},
            headers={"Accept": "application/sparql-results+json"},
            timeout=30.0,
        )
        response.raise_for_status()
        payload = response.json()
        return [_flatten_binding(row) for row in payload.get("results", {}).get("bindings", [])]

    def import_file(self, source: Path, content_type: str) -> None:
        with source.open("rb") as file_obj:
            response = httpx.post(
                self.statements_url,
                content=file_obj.read(),
                headers={"Content-Type": content_type},
                timeout=120.0,
            )
        response.raise_for_status()


def graphdb_query(sparql: str) -> list[dict[str, Any]]:
    return GraphDBClient().query(sparql)


def _flatten_binding(row: dict[str, dict[str, str]]) -> dict[str, str]:
    return {key: value.get("value", "") for key, value in row.items()}

