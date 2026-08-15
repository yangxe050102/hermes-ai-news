"""公共工具：网络请求、日志、HTML 清理、URL 规范化、时间处理。"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser

TZ_CN = timezone(timedelta(hours=8))
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
JSON_HEADERS = {"Accept": "application/json", "User-Agent": USER_AGENT}

log = logging.getLogger("briefing")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_cn() -> datetime:
    return datetime.now(TZ_CN)


def setup_logging(log_dir: str) -> None:
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(os.path.join(log_dir, "briefing.log"), encoding="utf-8"),
        ],
    )


def load_dotenv(path: str) -> None:
    """轻量 .env 加载，仅填充未设置的环境变量。"""
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _request(url: str, headers: dict | None = None, timeout: int = 20,
             retries: int = 3, method: str = "GET", body: dict | None = None) -> bytes:
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            if body is not None:
                payload = json.dumps(body).encode("utf-8")
                req = urllib.request.Request(url, data=payload, headers=headers or {}, method=method)
            else:
                req = urllib.request.Request(url, headers=headers or {}, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            code = getattr(exc, "code", type(exc).__name__)
            log.warning("请求失败 [%s] %s（第 %d/%d 次）", code, url, attempt + 1, retries)
            if attempt < retries - 1:
                time.sleep(2 * (2 ** attempt))
    assert last_exc is not None
    raise last_exc


def http_get(url: str, headers: dict | None = None, timeout: int = 20, retries: int = 3) -> bytes:
    return _request(url, headers=headers, timeout=timeout, retries=retries)


def http_get_json(url: str, headers: dict | None = None, timeout: int = 20, retries: int = 3) -> dict:
    data = http_get(url, headers=headers, timeout=timeout, retries=retries)
    return json.loads(data.decode("utf-8"))


def http_post_json(url: str, body: dict, headers: dict | None = None,
                   timeout: int = 30, retries: int = 3) -> dict:
    data = _request(url, headers=headers, timeout=timeout, retries=retries, method="POST", body=body)
    return json.loads(data.decode("utf-8"))


def quote(text: str) -> str:
    return urllib.parse.quote(text, safe="")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):  # noqa: ANN001
        if tag in ("script", "style"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip and data.strip():
            self.parts.append(data)


def strip_html(text: str | None) -> str:
    """去掉 HTML 标签，保留纯文本。"""
    if not text:
        return ""
    parser = _TextExtractor()
    try:
        parser.feed(text)
        raw = " ".join(parser.parts)
    except Exception:  # noqa: BLE001
        raw = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", raw).strip()


def normalize_url(url: str) -> str:
    """去掉跟踪参数、尾部斜杠、www 前缀，用于跨源去重。"""
    try:
        u = urllib.parse.urlparse(url)
        keep = [(k, v) for k, v in urllib.parse.parse_qsl(u.query)
                if not k.lower().startswith(("utm_", "ref", "source", "from"))]
        host = u.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        path = u.path.rstrip("/") or "/"
        return urllib.parse.urlunparse((u.scheme, host, path, "", urllib.parse.urlencode(keep), ""))
    except Exception:  # noqa: BLE001
        return url


def url_hash(url: str) -> str:
    return hashlib.sha256(normalize_url(url).encode("utf-8")).hexdigest()


def truncate(text: str, limit: int = 120) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "..."


def parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except Exception:  # noqa: BLE001
        return None