"""GitHub 趋势仓库源（GitHub Search API）。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .base import NewsItem
import util

API = "https://api.github.com/search/repositories"
_KEYWORDS = ("ai", "llm", "gpt", "agent", "model", "rag", "machine learning",
             "deep learning", "vision", "diffusion", "embedding", "neural")


class GitHubTrendingSource:
    def __init__(self, name: str, weight: float = 1.0, days: int = 7) -> None:
        self.name = name
        self.weight = weight
        self.days = days

    def fetch(self) -> list[NewsItem]:
        since = (datetime.now(timezone.utc) - timedelta(days=self.days)).date().isoformat()
        url = (
            f"{API}?q=ai+OR+llm+OR+%22machine+learning%22+created:%3E{since}"
            f"&sort=stars&order=desc&per_page=30"
        )
        headers = dict(util.JSON_HEADERS)
        headers["Accept"] = "application/vnd.github+json"
        data = util.http_get_json(url, headers=headers, timeout=30)
        items: list[NewsItem] = []
        for r in data.get("items", []):
            name = (r.get("full_name") or "").strip()
            desc = (r.get("description") or "").strip()
            combined = f"{name} {desc}".lower()
            if not name or not any(k in combined for k in _KEYWORDS):
                continue
            try:
                created = datetime.fromisoformat((r.get("created_at") or "").replace("Z", "+00:00"))
            except Exception:  # noqa: BLE001
                created = None
            stars = int(r.get("stargazers_count") or 0)
            language = r.get("language") or "未知语言"
            items.append(NewsItem(
                title=name, url=r.get("html_url") or f"https://github.com/{name}",
                source=self.name, weight=self.weight, published=created,
                summary=f"过去 {self.days} 天新建仓库 · ⭐ {stars} · {language}",
                pop=min(stars / 8000.0, 1.0), lang="en", windowed=False))
        return items