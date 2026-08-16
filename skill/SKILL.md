---
name: ai-news-briefing
description: 运行/调试「AI 热点日报」定时任务：抓取多源 AI 新闻（RSS+API）→ 去重 → DeepSeek 翻译为简体中文 → 生成 HTML 简报 → 部署到 GitHub Pages → 通过 lark-cli（hermes 应用）推送飞书。当用户提到 AI 热点日报、AI 新闻简报、每日 AI 新闻、hermes 简报、daily AI news briefing，或要求运行/检查/调试这个每日任务时使用。项目位于 D:\hermes_agent\workspace\hermes-ai-news。
---

# AI 热点日报（ai-news-briefing）

每天聚合 AI 热点新闻，翻译为简体中文，生成 HTML 简报发布到 GitHub Pages，并通过飞书（hermes 应用）私聊推送极简消息（标题行 + 页面链接）。

## 项目位置

- 项目根目录：`D:\hermes_agent\workspace\hermes-ai-news`
- 所有命令都在该目录下执行。

## 运行方式

### 完整任务（默认：部署 GitHub Pages + 发送飞书）

```powershell
cd D:\hermes_agent\workspace\hermes-ai-news
python main.py
```

### 调试选项

- `python main.py --no-deploy`：跳过 GitHub Pages 部署（仍会发送飞书）
- `python main.py --no-notify`：跳过飞书发送（仍会部署）
- `python main.py --no-deploy --no-notify`：只抓取+翻译+生成本地 HTML，安全试运行

运行前提：
- Python 3.10+（纯标准库，无 pip 依赖），`python` 在 PATH
- `DEEPSEEK_API_KEY` 已设置（环境变量或项目 `.env`）
- `lark-cli` 可用且 hermes 应用已登录（`lark-cli auth status --json --verify`）
- `gh` 已登录、`git` 可用、SSH 能推送 github.com

## 配置（config.json）

- `sources`：信息源列表。`type` 支持 `rss`（量子位/雷锋网/极客公园/MIT 科技评论）、`hn`（Hacker News）、`github`（GitHub 趋势）。
- `quota`：配额选题，默认 `{"GitHub 趋势": 0.5}`，即 GitHub 趋势保底占一半名额（10 条中 5 条），其余按「时效×权重×热度」补齐。
- `feishu.recipient_open_id`：飞书收件人 open_id；`feishu.as` 默认 `bot`（hermes 应用）。
- `github`：仓库 owner/名称/分支/Pages 目录。
- `translate`：DeepSeek 模型与批大小。

## 流程

1. 抓取 6 个信息源（每源失败自动重试 3 次，指数退避 2s/4s/8s）。
2. URL 规范化 + 哈希去重（仅当日，跨天自动重置），过滤 48 小时窗口。
3. 配额选题：GitHub 趋势保底 50%，其余源按热度补齐到 10 条。
4. DeepSeek 批量翻译英文条目为简体中文（缓存 30 天）。
5. 渲染 HTML 到 `docs/index.html` 与 `output/index.html`。
6. git 提交推送，GitHub Pages 自动构建（页面：https://yangxe050102.github.io/hermes-ai-news/）。
7. lark-cli 发送极简富文本消息（post 格式：标题行 + 完整版网页链接）。
8. 发送成功后才标记已发送；发送失败不标记，下次运行自动补发。

## 定时任务

- Windows 计划任务：`HermesAI-News-Briefing`，每日 08:00，入口为本技能 `scripts/run.ps1`。
- 查看：`Get-ScheduledTask -TaskName HermesAI-News-Briefing`
- 手动触发：`Start-ScheduledTask -TaskName HermesAI-News-Briefing`
- 安装/卸载脚本在项目根目录：`install_schedule.ps1` / `uninstall_schedule.ps1`

## 排障

- 日志：`state/logs/briefing.log`、`state/logs/run.stdout.log`
- 飞书发送失败：确认 `lark-cli auth status`、`feishu.recipient_open_id`、hermes 应用的 im:message 权限
- 页面 404/内容旧：Pages 构建有 1-2 分钟延迟；`gh api repos/yangxe050102/hermes-ai-news/pages/builds/latest` 查看构建状态
- 某源抓取为 0：源 RSS 可能变更/屏蔽，修改 config.json 的 URL 或移除该源
- 翻译为空：确认 DEEPSEEK_API_KEY；缺失时自动保留英文原文
- 发送的消息只有一行：不要用 `--markdown` 传多行内容（会被截断），用 post 富文本 `--content` 或直接运行 `python main.py`