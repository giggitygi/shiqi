from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    data_dir: Path = PROJECT_ROOT / "data"
    xml_dir: Path = PROJECT_ROOT / "data" / "xml"
    nt_dir: Path = PROJECT_ROOT / "data" / "nt"
    cache_dir: Path = PROJECT_ROOT / "data" / "cache"
    graphdb_base_url: str = "http://localhost:7200"
    graphdb_repo: str = "dangdang-books"
    request_timeout_seconds: float = 20.0
    request_delay_seconds: float = 0.8
    user_agent: str = (
        "Mozilla/5.0 (compatible; DangdangKGQA/0.1; "
        "+https://example.local/dangdang-kgqa)"
    )


settings = Settings()

