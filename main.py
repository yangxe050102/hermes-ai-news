"""AI 热点日报主程序：抓取 → 翻译 → HTML → GitHub Pages → 飞书。"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import util  # noqa: E402
from dedupe import SeenStore  # noqa: E402
from deploy_github import deploy  # noqa: E402
from feishu_notify import send  # noqa: E402
from html_report import render_html  # noqa: E402
from sources.base import NewsItem  # noqa: E402
from sources.github_source import GitHubTrendingSource  # noqa: E402
from sources.hn_source import HackerNewsSource  # noqa: E402
from sources.rss_source import RssSource  # noqa: E402
from translate import Translator  # noqa: E402

log = logging.getLogger("briefing")
ROOT = os.path.dirname(os.path.abspath(__file__))


def load_config() -> dict:
    with open(os.path.join(ROOT, "config.json"), encoding="utf-8") as f:
        return json.load(f)


def build_sources(cfg: dict) -> list:
    sources = []
    for s in cfg["sources"]:
        stype = s["type"]
        if stype == "rss":
            sources.append(RssSource(name=s["name"], url=s["url"], weight=s.get("weight", 1.0),
                                     lang=s.get("lang", "en"), use_ua=s.get("use_ua", False),
                                     keywords=s.get("keywords")))
        elif stype == "hn":
            sources.append(HackerNewsSource(name=s["name"], weight=s.get("weight", 1.0),
                                            min_points=s.get("min_points", 60)))
        elif stype == "github":
            sources.append(GitHubTrendingSource(name=s["name"], weight=s.get("weight", 1.0)))
        else:
            log.warning("未知源类型: %s", stype)
    return sources


def score(item: NewsItem, now: datetime) -> float:
    rf = 1.0
    if item.published:
        age_h = (now - item.published).total_seconds() / 3600.0
        rf = max(0.0, 1.0 - age_h / 48.0)
    return item.weight * (0.6 * rf + 0.4 * item.pop)


def select_with_quota(fresh: list, cfg: dict) -> list:
    """按配额选题：config.quota 中每个源保底一定比例的名额，其余名额给其他源。"""
    limit = cfg["max_items"]
    quotas = cfg.get("quota", {})
    if not quotas:
        return fresh[:limit]
    quota_pools = {name: [] for name in quotas}
    rest = []
    for it in fresh:
        pool = quota_pools.get(it.source)
        if pool is not None:
            pool.append(it)
        else:
            rest.append(it)
    picked = []
    for name, frac in quotas.items():
        n = min(len(quota_pools[name]), max(0, round(frac * limit)))
        picked.extend(quota_pools[name][:n])
    # 剩余名额给非配额源
    if len(picked) < limit:
        picked.extend(rest[: limit - len(picked)])
    # 配额源不足时，从其他配额源补足
    if len(picked) < limit:
        for name, frac in quotas.items():
            base = max(0, round(frac * limit))
            extra = quota_pools[name][base:][: limit - len(picked)]
            picked.extend(extra)
            if len(picked) >= limit:
                break
    return picked[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description="AI 热点日报")
    parser.add_argument("--no-deploy", action="store_true", help="不部署 GitHub Pages")
    parser.add_argument("--no-notify", action="store_true", help="不发送飞书")
    args = parser.parse_args()

    cfg = load_config()
    util.setup_logging(os.path.join(ROOT, "state", "logs"))
    util.load_dotenv(os.path.join(ROOT, ".env"))
    log.info("====== AI 热点日报 开始 ======")

    seen = SeenStore(os.path.join(ROOT, "state", "seen.json"), keep_days=cfg["dedupe_days"])
    window_start = util.now_utc() - timedelta(hours=cfg["lookback_hours"])

    all_items: list[NewsItem] = []
    for source in build_sources(cfg):
        try:
            items = source.fetch()
            log.info("源「%s」抓取 %d 条", getattr(source, "name", "?"), len(items))
            all_items.extend(items)
        except Exception as exc:  # noqa: BLE001
            log.warning("源「%s」抓取失败: %s", getattr(source, "name", "?"), exc)

    fresh: list[NewsItem] = []
    skipped = 0
    seen_in_run: set[str] = set()
    for it in all_items:
        key = util.normalize_url(it.url)
        if key in seen_in_run:
            continue
        seen_in_run.add(key)
        if seen.is_seen(it.url):
            skipped += 1
            continue
        if it.windowed and it.published and it.published < window_start:
            skipped += 1
            continue
        fresh.append(it)

    log.info("候选 %d 条，过滤重复/超窗 %d 条", len(fresh), skipped)
    if not fresh:
        log.warning("今天没有可发送的新内容")
        return 0

    fresh.sort(key=lambda it: score(it, util.now_utc()), reverse=True)
    picked = select_with_quota(fresh, cfg)

    translator = Translator(
        cache_path=os.path.join(ROOT, "state", "translations.json"),
        model=cfg["translate"]["model"],
        batch_size=cfg["translate"]["batch_size"],
        max_tokens=cfg["translate"]["max_tokens"],
        provider=cfg["translate"].get("provider", "deepseek"),
    )
    translator.translate(picked)

    date_str = util.now_cn().strftime("%Y-%m-%d")
    html = render_html(picked, date_str)
    os.makedirs(os.path.join(ROOT, "output"), exist_ok=True)
    with open(os.path.join(ROOT, "output", "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

    page_url = ""
    if not args.no_deploy:
        page_url = deploy(html, ROOT, cfg)
    else:
        page_url = f"https://{cfg['github']['owner']}.github.io/{cfg['github']['repo']}/"

    notified = False
    if args.no_notify:
        log.info("跳过飞书发送（--no-notify），不记录已发送状态")
    else:
        try:
            send(picked, page_url, cfg)
            notified = True
        except Exception as exc:  # noqa: BLE001
            log.error("飞书发送失败: %s（下次运行将自动重试）", exc)
            return 1

    if notified:
        for it in picked:
            seen.mark(it.url)
        seen.save()
    log.info("====== 完成：%d 条，页面 %s ======", len(picked), page_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())