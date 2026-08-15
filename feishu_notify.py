"""通过 lark-cli（hermes 应用）发送飞书私聊富文本消息。"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess

import util

log = logging.getLogger("briefing")


def build_post(items: list, page_url: str, date_str: str) -> dict:
    """构造飞书 post 富文本：标题 + 10 条带链接的标题 + 页面链接。"""
    sources = list(dict.fromkeys(it.source for it in items))
    suffix = " 等" if len(sources) > 6 else ""
    content = [[{"tag": "text", "text": f"来源：{' · '.join(sources[:6])}{suffix}"}]]
    for i, it in enumerate(items, 1):
        content.append([
            {"tag": "text", "text": f"{i}. "},
            {"tag": "a", "text": it.display_title, "href": it.url},
        ])
        if it.display_summary:
            content.append([{"tag": "text", "text": util.truncate(it.display_summary, 80)}])
        content.append([{"tag": "text", "text": f"— {it.source}"}])
    content.append([
        {"tag": "text", "text": "📎 完整版网页："},
        {"tag": "a", "text": page_url, "href": page_url},
    ])
    return {"zh_cn": {"title": f"📰 AI 热点日报 · {date_str}", "content": content}}


def send(items: list, page_url: str, cfg: dict) -> None:
    feishu = cfg["feishu"]
    open_id = feishu["recipient_open_id"]
    identity = feishu.get("as", "bot")
    date_str = util.now_cn().strftime("%m月%d日")
    payload = build_post(items, page_url, date_str)

    env = dict(os.environ)
    env["LARKSUITE_CLI_NO_UPDATE_NOTIFIER"] = "1"
    env["LARKSUITE_CLI_NO_SKILLS_NOTIFIER"] = "1"
    lark_cli = shutil.which("lark-cli") or "lark-cli"
    args = [lark_cli, "im", "+messages-send", "--as", identity,
            "--user-id", open_id, "--msg-type", "post",
            "--content", json.dumps(payload, ensure_ascii=False)]
    proc = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", env=env)
    out = ((proc.stdout or "") + (proc.stderr or "")).strip()
    log.info("飞书发送结果: %s", out[:600])
    if proc.returncode != 0:
        raise RuntimeError(f"飞书消息发送失败: {out[:500]}")