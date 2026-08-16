"""基于 URL 哈希的当日去重：同一天内不重复发送，跨天自动重置。"""
from __future__ import annotations

import json
import os

import util


class SeenStore:
    def __init__(self, path: str) -> None:
        self.path = path
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

    def _today(self) -> str:
        return util.now_cn().date().isoformat()

    def is_seen(self, url: str) -> bool:
        # 只有当天标记过的才算已发送，跨天记录自动视为未发送
        return self._data.get(util.url_hash(url)) == self._today()

    def mark(self, url: str) -> None:
        self._data[util.url_hash(url)] = self._today()

    def prune(self) -> None:
        today = self._today()
        self._data = {k: v for k, v in self._data.items() if v == today}

    def save(self) -> None:
        self.prune()
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)