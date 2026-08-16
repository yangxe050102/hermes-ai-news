# 部署文档

## 1. 前置条件（一次性）

1. **Python 3.10+**：项目为纯标准库，无需 pip install。
2. **飞书 hermes 应用**：已完成 `lark-cli config init`。验证：
   ```bash
   lark-cli auth status --json --verify
   # 应看到 bot 与 user 均为 ready/verified
   ```
3. **GitHub CLI 已登录**（已安装于本机）：
   ```bash
   gh auth status          # 登录账号 yangxe050102，含 repo scope
   ```
4. **SSH 免密推送**：`ssh -T git@github.com` 能返回 "Hi <user>!" 即可。
5. **翻译密钥**：将 `.env.example` 复制为 `.env`，填入 `DEEPSEEK_API_KEY`（也可直接设置环境变量）。没有密钥时脚本会跳过翻译、保留英文原文。
6. **收件人**：`config.json -> feishu.recipient_open_id` 为你的飞书 open_id（`lark-cli whoami` 查看）。

## 2. 首次运行

```bash
cd D:\hermes_agent\workspace\hermes-ai-news
python main.py --no-deploy --no-notify   # 只抓取+翻译+生成本地 HTML，安全
python main.py                           # 完整运行：部署 Pages + 发送飞书
```

首次完整运行会自动：
- 在 `docs/index.html` 生成简报
- 用 `gh repo create` 创建公开仓库（默认 `yangxe050102/hermes-ai-news`）
- 推送 `main` 分支并启用 GitHub Pages（`/docs`）
- 用 hermes 机器人私聊发送 10 条热点 + 网页链接

## 3. Windows 每日定时任务

```powershell
powershell -ExecutionPolicy Bypass -File .\install_schedule.ps1
```

- 任务入口：`~/.codex/skills/ai-news-briefing/scripts/run.ps1`（通过 Codex CLI 调用 `ai-news-briefing` 技能执行完整任务）
- 任务名：`HermesAI-News-Briefing`
- 时间：每天 08:00（本机时区）
- 查看：`Get-ScheduledTask -TaskName HermesAI-News-Briefing`
- 手动触发：`Start-ScheduledTask -TaskName HermesAI-News-Briefing`
- 卸载：`powershell -ExecutionPolicy Bypass -File .\uninstall_schedule.ps1`

日志位置：`state/logs/briefing.log`（结构化日志）、`state/logs/run.stdout.log`（原始输出）。

## 4. Linux / macOS（cron）

```bash
# crontab -e，每天 08:00（服务器时区），注意用绝对路径
0 8 * * * cd /path/to/hermes-ai-news && /usr/bin/python3 main.py >> state/logs/run.stdout.log 2>&1
```

- 在 Linux 上需确保 `lark-cli`、`gh`、`git`、`ssh` 都在 PATH 中（cron 环境变量少，建议在脚本里 export PATH）。
- `config.json` 中 `gh_bin` 在 Linux 上可改为 `gh`。
- 时区不符时用 `TZ=Asia/Shanghai` 前缀或修改 crontab 时区。

## 5. Docker（可选）

```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y git openssh-client
# 挂载 .ssh、config.json、.env、state 卷，entrypoint 执行 python main.py
```

配合宿主 cron 或 `docker run` + 系统定时器即可。

## 6. GitHub Actions（免本机常驻）

仓库内 `.github/workflows/daily.yml`：

```yaml
name: daily-briefing
on:
  schedule:
    - cron: "0 0 * * *"   # UTC 0 点 = 北京时间 8 点
  workflow_dispatch:
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: python main.py
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
          LARK_APP_ID: ${{ secrets.LARK_APP_ID }}
          LARK_APP_SECRET: ${{ secrets.LARK_APP_SECRET }}
```

> 注意：Actions 环境没有 lark-cli，需要改为直接调用飞书 OpenAPI（用 `LARK_APP_ID/SECRET` 换取 tenant_access_token 后 POST 消息），或安装 lark-cli。当前仓库的 `feishu_notify.py` 依赖本机 lark-cli，Actions 方案需做相应适配。

## 7. 排障

| 现象 | 排查 |
|---|---|
| 飞书发送失败 | `state/logs/briefing.log` 查看错误；确认 `lark-cli auth status`、`feishu.recipient_open_id` 正确、hermes 应用有 `im:message` 权限且你可被应用触达 |
| 页面 404 | GitHub Pages 首次构建约 1 分钟；`gh api repos/yangxe050102/hermes-ai-news/pages/builds/latest` 查看构建状态 |
| 某些源抓取为 0 | 可能是该源 RSS 变更/屏蔽，改 `config.json` 里的 URL 或删除该源 |
| 翻译为空 | 确认 `.env` 有 `DEEPSEEK_API_KEY`；没有则自动保留英文 |
| 定时任务未触发 | `Start-ScheduledTask` 手动触发；检查任务运行是否失败，日志看 `state/logs/` |

## 8. 失败重试策略

- 抓取：每个源最多重试 3 次，指数退避（2s/4s/8s）。
- 翻译：每批最多重试 3 次；仍失败则保留英文原文，不影响当天发送。
- 发送：若飞书发送失败，当天的 10 条不会标记为已发送，下次运行会自动重试并补发。
- 去重：已成功发送的内容进入 `state/seen.json`，仅当日生效，第二天自动重置。