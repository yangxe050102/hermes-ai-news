# Hermes AI 热点日报

每天自动抓取 AI 热点新闻 → 翻译成中文 → 生成精美 HTML 简报 → 部署到 GitHub Pages → 通过飞书（hermes 应用）推送到你的私聊。

- 部署地址：https://yangxe050102.github.io/hermes-ai-news/
- 发送方式：飞书 hermes 机器人私聊（每天 08:00 一条消息，含 10 条热点 + 完整版网页链接）
- 语言：全部翻译为简体中文（中文源原文保留，英文源由 DeepSeek 翻译）

## 功能特性

- **多源聚合**：RSS（量子位、雷锋网、极客公园、MIT 科技评论）+ API（Hacker News Algolia、GitHub 趋势仓库）
- **配额选题**：GitHub 趋势保底占每日一半名额（默认 10 条中 5 条），其余源按热度排名补齐
- **全中文**：英文内容由 DeepSeek 批量翻译，带缓存，只翻译新内容、省钱省时
- **去重**：按 URL 规范化后哈希持久化去重，保留 30 天，避免跨天重复
- **HTML 简报**：单文件响应式页面，按热度排序，手机/桌面均适配
- **GitHub Pages 部署**：自动创建/更新公开仓库并启用 Pages
- **失败重试**：抓取 3 次指数退避重试；发送失败时保留状态，下次运行自动补发
- **定时执行**：Windows 计划任务（默认每日 08:00）通过 `ai-news-briefing` 技能运行，也支持 Linux cron / GitHub Actions

## 项目结构

```
hermes-ai-news/
├── config.json            # 源、收件人、仓库、翻译等全部配置
├── main.py                # 主流程入口
├── util.py                # 网络请求、日志、HTML 清理、URL 规范化
├── dedupe.py              # 持久化去重（30 天）
├── translate.py           # DeepSeek 翻译（带缓存）
├── html_report.py         # HTML 简报渲染
├── deploy_github.py       # GitHub Pages 部署
├── feishu_notify.py       # 飞书发送（lark-cli）
├── sources/               # 各数据源适配器（RSS / HN / GitHub）
├── skill/                  # ai-news-briefing 技能副本（仓库内版本化备份）
├── install_schedule.ps1   # 一键安装每日 08:00 计划任务
├── uninstall_schedule.ps1 # 卸载计划任务
├── docs/                  # 部署文档 + 发布到 Pages 的 HTML
├── output/                # 本地最新一期 HTML（不入库）
└── state/                 # 去重/翻译/日志状态（不入库）
```

## 快速开始

```bash
# 1. 安装依赖（仅需要 Python 3.10+，无第三方包）
# 2. 配置密钥：复制 .env.example 为 .env，填入 DEEPSEEK_API_KEY
# 3. 按需修改 config.json（收件人 open_id、GitHub 仓库、新闻源）
# 4. 试运行（不部署、不发送）
python main.py --no-deploy --no-notify
# 5. 完整运行（部署 + 发送飞书）
python main.py
# 6. Windows 一键安装每日定时任务（08:00）
powershell -ExecutionPolicy Bypass -File install_schedule.ps1
```

## 封装为 Codex 技能

- 技能名：`ai-news-briefing`，本仓库 `skill/` 目录保存了技能副本（版本化备份），实际安装在 `~/.codex/skills/ai-news-briefing/`（复制 `skill/` 下内容过去即可重新安装）
- 手动调用：在 Codex 中说「运行 AI 热点日报」或 `$ai-news-briefing`，会读取技能说明并按流程执行
- 定时任务：`HermesAI-News-Briefing`（每天 08:00）入口为 `~/.codex/skills/ai-news-briefing/scripts/run.ps1`，由 Codex CLI 加载技能后执行 `python main.py`
- 查看/触发：`Get-ScheduledTask -TaskName HermesAI-News-Briefing` / `Start-ScheduledTask -TaskName HermesAI-News-Briefing`
## 依赖的外部工具

| 工具 | 用途 | 说明 |
|---|---|---|
| Python 3.10+ | 运行脚本 | 纯标准库，无 pip 依赖 |
| lark-cli | 发送飞书 | `lark-cli auth status` 确认 hermes 应用可用 |
| gh (GitHub CLI) | 创建仓库 / 启用 Pages / 推送 | `gh auth status` 确认已登录 |
| git + SSH key | 推送到 GitHub | 已配置 SSH 到 github.com |
| DeepSeek API Key | 英译中 | 环境变量 `DEEPSEEK_API_KEY` 或项目 `.env` |

## 配置说明（config.json）

- `feishu.recipient_open_id`：你的飞书 open_id（`lark-cli whoami` 可查）
- `feishu.as`：发送身份，默认 `bot`（hermes 应用）
- `github`：仓库 owner/名称、分支、Pages 目录
- `sources`：新闻源列表；`weight` 越高排序越靠前；`keywords` 用于过滤宽泛的源
- `translate`：DeepSeek 模型与批大小

详细部署与排障见 [docs/DEPLOY.md](docs/DEPLOY.md)。



