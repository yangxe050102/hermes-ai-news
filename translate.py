"""翻译模块：调用 DeepSeek 批量中译，带缓存与失败降级（保留原文）。"""
from __future__ import annotations

import json
import logging
import os

import util

log = logging.getLogger("briefing")


class Translator:
    def __init__(self, cache_path: str, model: str = "deepseek-chat",
                 batch_size: int = 5, max_tokens: int = 800,
                 provider: str = "deepseek") -> None:
        self.cache_path = cache_path
        self.model = model
        self.batch_size = batch_size
        self.max_tokens = max_tokens
        self.provider = provider
        self._cache: dict[str, dict] = self._load_cache()

    def _load_cache(self) -> dict[str, dict]:
        if not os.path.exists(self.cache_path):
            return {}
        try:
            with open(self.cache_path, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:  # noqa: BLE001
            return {}

    def _save_cache(self) -> None:
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        tmp = self.cache_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._cache, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.cache_path)

    def translate(self, items: list) -> None:
        """就地翻译非中文条目；命中缓存则直接使用。"""
        todo: list = []
        for it in items:
            if it.lang == "zh":
                continue
            cached = self._cache.get(util.url_hash(it.url))
            if cached:
                it.zh_title = cached.get("title")
                it.zh_summary = cached.get("summary")
            if not it.zh_title:
                todo.append(it)
        if not todo:
            return
        api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("ARK_API_KEY")
        if not api_key:
            log.warning("未找到 DEEPSEEK_API_KEY/ARK_API_KEY，跳过翻译（保留英文原文）")
            return
        for start in range(0, len(todo), self.batch_size):
            batch = todo[start:start + self.batch_size]
            self._translate_batch(batch, api_key)
        self._save_cache()

    def _translate_batch(self, batch: list, api_key: str) -> None:
        prompt_lines = [
            "请把下面每条英文科技新闻的标题和摘要翻译成简体中文。",
            "要求：语气像中文科技媒体，术语准确，专有名词可保留英文。",
            "严格只输出 JSON，不要任何额外文字，格式：",
            '{"items":[{"index":0,"title":"翻译后的标题","summary":"翻译后的摘要"}]}',
        ]
        for i, it in enumerate(batch):
            prompt_lines.append(f"\n[{i}] Title: {it.title}")
            if it.summary:
                prompt_lines.append(f"Summary: {util.truncate(it.summary, 300)}")
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是专业的科技新闻翻译，只输出合法 JSON。"},
                {"role": "user", "content": "\n".join(prompt_lines)},
            ],
            "temperature": 0.2,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
        }
        url = "https://api.deepseek.com/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        try:
            data = util.http_post_json(url, body, headers=headers, timeout=90, retries=2)
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except Exception as exc:  # noqa: BLE001
            log.warning("翻译批次失败（保留原文）: %s", exc)
            return
        for entry in parsed.get("items", []):
            try:
                idx = int(entry.get("index"))
            except (TypeError, ValueError):
                continue
            if not (0 <= idx < len(batch)):
                continue
            it = batch[idx]
            it.zh_title = (entry.get("title") or "").strip() or it.title
            it.zh_summary = (entry.get("summary") or "").strip()
            self._cache[util.url_hash(it.url)] = {
                "title": it.zh_title,
                "summary": it.zh_summary,
                "ts": util.now_cn().isoformat(),
            }