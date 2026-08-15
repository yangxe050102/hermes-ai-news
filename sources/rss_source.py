"""RSS / Atom 源抓取（纯标准库实现）。"""
from __future__ import annotations

import email.utils
import xml.etree.ElementTree as ET
from datetime import datetime

from .base import NewsItem
import util

ATOM_NS = "{http://www.w3.org/2005/Atom}"


def _parse_date(text: str) -> datetime | None:
    if not text:
        return None
    text = text.strip()
    try:
        return email.utils.parsedate_to_datetime(text)
    except Exception:  # noqa: BLE001
        pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return None


class RssSource:
    def __init__(self, name: str, url: str, weight: float = 1.0, lang: str = "en",
                 use_ua: bool = False, keywords: list[str] | None = None) -> None:
        self.name = name
        self.url = url
        self.weight = weight
        self.lang = lang
        self.use_ua = use_ua
        self.keywords = [k.lower() for k in (keywords or [])]

    def fetch(self) -> list[NewsItem]:
        headers = {"User-Agent": util.USER_AGENT} if self.use_ua else {}
        data = util.http_get(self.url, headers=headers, timeout=25)
        return self._parse(data)

    def _parse(self, data: bytes) -> list[NewsItem]:
        try:
            root = ET.fromstring(data)
        except ET.ParseError:
            return []
        items: list[NewsItem] = []
        if root.tag == "rss" or root.tag.endswith("}rss"):
            for node in root.findall("./channel/item"):
                item = self._rss_item(node)
                if item:
                    items.append(item)
        else:
            for node in root.findall(f"{ATOM_NS}entry"):
                item = self._atom_item(node)
                if item:
                    items.append(item)
        seen: set[str] = set()
        out: list[NewsItem] = []
        for it in items:
            key = util.normalize_url(it.url)
            if key in seen:
                continue
            seen.add(key)
            if self.keywords and not _match_keywords(it.title, self.keywords):
                continue
            out.append(it)
        return out

    def _rss_item(self, node) -> NewsItem | None:
        title = _el_text(node, "title")
        link = _el_text(node, "link")
        if not title or not link:
            return None
        summary = util.strip_html(_el_text(node, "description"))
        published = _parse_date(_el_text(node, "pubDate"))
        return NewsItem(title=title, url=link, source=self.name, weight=self.weight,
                        published=published, summary=summary, lang=self.lang)

    def _atom_item(self, node) -> NewsItem | None:
        title = _el_text(node, f"{ATOM_NS}title")
        link_el = node.find(f"{ATOM_NS}link")
        link = link_el.attrib.get("href", "") if link_el is not None else ""
        if not title or not link:
            return None
        summary = util.strip_html(_el_text(node, f"{ATOM_NS}summary"))
        published = _parse_date(_el_text(node, f"{ATOM_NS}updated"))
        return NewsItem(title=title, url=link, source=self.name, weight=self.weight,
                        published=published, summary=summary, lang=self.lang)


def _el_text(node, tag: str) -> str:
    el = node.find(tag)
    return el.text.strip() if el is not None and el.text else ""


def _match_keywords(title: str, keywords: list[str]) -> bool:
    t = title.lower()
    return any(k in t for k in keywords)