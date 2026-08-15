"""通过 lark-cli（hermes 应用）发送飞书私聊消息。"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess

import util

log = logging.getLogger("briefing")


def build_markdown(items: list, page_url: str, date_str: str) -> str:
    lines = [f"**📰 AI 热点日报 · {date_str}**", ""]
    sources = list(dict.fromkeys(it.source for it in items))
    suffix = " 等" if len(sources) > 6 else ""
    lines.append(f"来源：{' · '.join(sources[:6])}{suffix}")
    lines.append("")
    for i, it in enumerate(items, 1):
        lines.append(f"{i}. **[{it.display_title}]({it.url})**")
        if it.display_summary:
            lines.append(f"   {util.truncate(it.display_summary, 90)}")
        lines.append(f"   — {it.source}")
        lines.append("")
    lines.append(f"📎 完整版网页：{page_url}")
    return "\n".join(lines)


def send(items: list, page_url: str, cfg: dict) -> None:
    feishu = cfg["feishu"]
    open_id = feishu["recipient_open_id"]
    identity = feishu.get("as", "bot")
    date_str = util.now_cn().strftime("%m月%d日")
    md = build_markdown(items, page_url, date_str)

    env = dict(os.environ)
    env["LARKSUITE_CLI_NO_UPDATE_NOTIFIER"] = "1"
    env["LARKSUITE_CLI_NO_SKILLS_NOTIFIER"] = "1"
    lark_cli = shutil.which("lark-cli") or "lark-cli"
    args = [lark_cli, "im", "+messages-send", "--as", identity,
            "--user-id", open_id, "--markdown", md]
    proc = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", env=env)
    out = ((proc.stdout or "") + (proc.stderr or "")).strip()
    log.info("飞书发送结果: %s", out[:600])
    if proc.returncode != 0:
        raise RuntimeError(f"飞书消息发送失败: {out[:500]}")