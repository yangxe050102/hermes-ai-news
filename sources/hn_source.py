"""Hacker News 源（Algolia API）。"""
from __future__ import annotations

from datetime import datetime

from .base import NewsItem
import util

API = "https://hn.algolia.com/api/v1/search"


class HackerNewsSource:
    def __init__(self, name: str, weight: float = 1.0, min_points: int = 60,
                 query: str = "AI") -> None:
        self.name = name
        self.weight = weight
        self.min_points = min_points
        self.query = query

    def fetch(self) -> list[NewsItem]:
        url = (
            f"{API}?query={util.quote(self.query)}&tags=story"
            f"&hitsPerPage=40&numericFilters=points%3E%3D{self.min_points}"
        )
        data = util.http_get_json(url, headers=util.JSON_HEADERS, timeout=25)
        items: list[NewsItem] = []
        for h in data.get("hits", []):
            title = (h.get("title") or "").strip()
            if not title:
                continue
            item_url = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}"
            points = int(h.get("points") or 0)
            try:
                published = datetime.fromisoformat((h.get("created_at") or "").replace("Z", "+00:00"))
            except Exception:  # noqa: BLE001
                published = None
            items.append(NewsItem(
                title=title, url=item_url, source=self.name, weight=self.weight,
                published=published, summary=f"Hacker News 社区热点 · {points} 分",
                pop=min(points / 300.0, 1.0), lang="en"))
        return items