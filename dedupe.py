"""基于 URL 哈希的持久化去重（默认保留 30 天）。"""
from __future__ import annotations

import json
import os
from datetime import timedelta

import util


class SeenStore:
    def __init__(self, path: str, keep_days: int = 30) -> None:
        self.path = path
        self.keep_days = keep_days
        self._data: dict[str, str] = self._load()

    def _load(self) -> dict[str, str]:
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:  # noqa: BLE001
            return {}

    def is_seen(self, url: str) -> bool:
        return util.url_hash(url) in self._data

    def mark(self, url: str) -> None:
        self._data[util.url_hash(url)] = util.now_cn().isoformat()

    def prune(self) -> None:
        cutoff = util.now_cn() - timedelta(days=self.keep_days)
        self._data = {
            k: v for k, v in self._data.items()
            if (util.parse_dt(v) or cutoff) >= cutoff
        }

    def save(self) -> None:
        self.prune()
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)