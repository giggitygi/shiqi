from __future__ import annotations

import hashlib
import time
import urllib.robotparser
from pathlib import Path
from urllib.parse import urlparse

import httpx

from dangdang_kgqa.config import Settings, settings


class DangdangHttpClient:
    def __init__(self, config: Settings = settings, use_cache: bool = True, respect_robots: bool = True):
        self.config = config
        self.use_cache = use_cache
        self.respect_robots = respect_robots
        self._last_request_at = 0.0
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}

    def fetch_text(self, url: str) -> str:
        cache_path = self._cache_path(url)
        if self.use_cache and cache_path.exists():
            return cache_path.read_text(encoding="utf-8")
        if self.respect_robots and not self._can_fetch(url):
            raise PermissionError(f"robots.txt disallows fetching {url}")
        self._wait_for_rate_limit()
        with httpx.Client(
            headers={"User-Agent": self.config.user_agent},
            follow_redirects=True,
            timeout=self.config.request_timeout_seconds,
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            text = decode_dangdang_html(response.content)
        if self.use_cache:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(text, encoding="utf-8")
        return text

    def _wait_for_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        delay = self.config.request_delay_seconds
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self._last_request_at = time.monotonic()

    def _cache_path(self, url: str) -> Path:
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()
        return self.config.cache_dir / f"{digest}.html"

    def _can_fetch(self, url: str) -> bool:
        parsed = urlparse(url)
        root = f"{parsed.scheme}://{parsed.netloc}"
        parser = self._robots.get(root)
        if parser is None:
            parser = urllib.robotparser.RobotFileParser(f"{root}/robots.txt")
            try:
                parser.read()
            except Exception:
                return True
            self._robots[root] = parser
        return parser.can_fetch(self.config.user_agent, url)


def decode_dangdang_html(content: bytes) -> str:
    for encoding in ("gb18030", "gbk", "utf-8"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")

