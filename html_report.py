"""HTML 简报渲染：单文件、响应式、中文界面。"""
from __future__ import annotations

import html as html_mod

import util

_CSS = """
:root {
  --bg: #f4f6fb;
  --card: #ffffff;
  --ink: #1f2430;
  --muted: #6b7280;
  --brand: #4f46e5;
  --accent: #06b6d4;
  --line: #e5e7eb;
  --radius: 16px;
  --shadow: 0 6px 24px rgba(30, 41, 59, 0.08);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
    "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  background: var(--bg);
  color: var(--ink);
  line-height: 1.6;
}
.wrap { max-width: 880px; margin: 0 auto; padding: 24px 16px 48px; }
.hero {
  background: linear-gradient(135deg, #4f46e5 0%, #06b6d4 100%);
  border-radius: 20px;
  padding: 36px 32px;
  color: #fff;
  box-shadow: var(--shadow);
  position: relative;
  overflow: hidden;
}
.hero::after {
  content: "";
  position: absolute; right: -60px; top: -60px;
  width: 220px; height: 220px; border-radius: 50%;
  background: rgba(255, 255, 255, 0.12);
}
.hero .tag {
  display: inline-block; font-size: 13px; letter-spacing: 2px;
  background: rgba(255, 255, 255, 0.18); padding: 4px 12px;
  border-radius: 999px; margin-bottom: 12px;
}
.hero h1 { font-size: 30px; font-weight: 700; }
.hero .sub { margin-top: 8px; font-size: 14px; opacity: 0.92; }
.stats {
  display: flex; gap: 28px; margin-top: 20px; flex-wrap: wrap;
}
.stats .num { font-size: 24px; font-weight: 700; }
.stats .lbl { font-size: 12px; opacity: 0.85; }
.section-title {
  display: flex; align-items: center; gap: 8px;
  margin: 32px 0 16px; font-size: 16px; font-weight: 700; color: var(--brand);
}
.section-title::before {
  content: ""; width: 4px; height: 18px; border-radius: 2px;
  background: linear-gradient(180deg, var(--brand), var(--accent));
}
.card {
  background: var(--card); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 20px 22px;
  box-shadow: var(--shadow); margin-bottom: 14px;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.card:hover { transform: translateY(-2px); box-shadow: 0 10px 28px rgba(30, 41, 59, 0.12); }
.card-top { display: flex; align-items: flex-start; gap: 14px; }
.rank {
  flex: 0 0 auto; width: 34px; height: 34px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-weight: 700; font-size: 15px;
  background: linear-gradient(135deg, var(--brand), var(--accent));
}
.title { font-size: 17px; font-weight: 600; color: var(--ink); text-decoration: none; }
.title:hover { color: var(--brand); }
.meta { margin-top: 6px; font-size: 12.5px; color: var(--muted); }
.badge {
  display: inline-block; background: #eef2ff; color: var(--brand);
  border-radius: 6px; padding: 1px 8px; font-size: 12px; margin-right: 8px;
}
.summary { margin-top: 10px; font-size: 14px; color: #3f4757; }
.read {
  display: inline-block; margin-top: 12px; font-size: 13px; color: var(--accent);
  text-decoration: none; font-weight: 600;
}
.read:hover { text-decoration: underline; }
.footer {
  margin-top: 40px; text-align: center; font-size: 12.5px; color: var(--muted);
}
.footer a { color: var(--brand); text-decoration: none; }
@media (max-width: 600px) {
  .hero { padding: 26px 20px; }
  .hero h1 { font-size: 24px; }
  .title { font-size: 16px; }
}
"""


def render_html(items: list, date_str: str) -> str:
    """items 为已翻译、已排序的 NewsItem 列表。"""
    cards: list[str] = []
    for i, it in enumerate(items, 1):
        title = html_mod.escape(it.display_title)
        url = html_mod.escape(it.url, quote=True)
        summary = html_mod.escape(util.truncate(it.display_summary or "（无摘要）", 180))
        badge = html_mod.escape(it.source)
        meta = ""
        if it.published:
            try:
                meta = " · " + html_mod.escape(it.published.astimezone(util.TZ_CN).strftime("%m-%d %H:%M"))
            except Exception:
                meta = ""
        cards.append(f"""\
      <article class="card">
        <div class="card-top">
          <div class="rank">{i}</div>
          <div>
            <a class="title" href="{url}" target="_blank" rel="noopener">{title}</a>
            <div class="meta"><span class="badge">{badge}</span>{meta}</div>
            <div class="summary">{summary}</div>
            <a class="read" href="{url}" target="_blank" rel="noopener">阅读原文 →</a>
          </div>
        </div>
      </article>""")
    sources = " · ".join(dict.fromkeys(it.source for it in items))
    body = "\n".join(cards)
    page_title = f"AI 热点日报 · {date_str}"
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>{page_title}</title>
<style>{_CSS}</style>
</head>
<body>
  <div class="wrap">
    <header class="hero">
      <span class="tag">HERMES DAILY</span>
      <h1>{page_title}</h1>
      <div class="sub">AI 领域热点聚合 · 全部内容已翻译为简体中文</div>
      <div class="stats">
        <div><div class="num">{len(items)}</div><div class="lbl">今日精选</div></div>
        <div><div class="num">{len(set(it.source for it in items))}</div><div class="lbl">信息源</div></div>
        <div><div class="num">{date_str}</div><div class="lbl">日期</div></div>
      </div>
    </header>

    <div class="section-title">今日热点 Top {len(items)}</div>
{body}

    <footer class="footer">
      由 hermes 自动生成 · 来源：{html_mod.escape(sources)}<br>
      <a href="https://github.com/yangxe050102/hermes-ai-news" target="_blank" rel="noopener">GitHub 仓库</a>
    </footer>
  </div>
</body>
</html>
"""