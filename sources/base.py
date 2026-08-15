"""新闻条目数据模型。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class NewsItem:
    title: str
    url: str
    source: str
    weight: float = 1.0
    published: datetime | None = None
    summary: str = ""
    pop: float = 0.0            # 归一化热度 0..1
    lang: str = "en"            # 原文语言；zh 无需翻译
    windowed: bool = True       # 是否受 48 小时时间窗口过滤
    zh_title: str | None = None
    zh_summary: str | None = None

    @property
    def display_title(self) -> str:
        return self.zh_title or self.title

    @property
    def display_summary(self) -> str:
        return self.zh_summary or self.summary or ""