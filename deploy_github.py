"""GitHub Pages 部署：提交 docs/index.html、创建仓库、启用 Pages。"""
from __future__ import annotations

import logging
import os
import subprocess

import util

log = logging.getLogger("briefing")


def _run(args: list[str], cwd: str | None = None) -> str:
    proc = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    out = ((proc.stdout or "") + (proc.stderr or "")).strip()
    if proc.returncode != 0:
        raise RuntimeError(f"命令执行失败: {' '.join(args)}\n{out[:800]}")
    return out


def _run_quiet(args: list[str], cwd: str | None = None) -> tuple[int, str]:
    proc = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    return proc.returncode, ((proc.stdout or "") + (proc.stderr or "")).strip()


def _gh_email(gh: str) -> str:
    code, out = _run_quiet([gh, "api", "user", "--jq", ".id"])
    if code == 0 and out.strip().isdigit():
        _, login = _run_quiet([gh, "api", "user", "--jq", ".login"])
        if login:
            return f"{out.strip()}+{login}@users.noreply.github.com"
    return "hermes-bot@users.noreply.github.com"


def _enable_pages(gh: str, full: str, branch: str, pages_path: str) -> None:
    code, out = _run_quiet([gh, "api", "-X", "POST", f"repos/{full}/pages",
                            "-f", f"source[branch]={branch}",
                            "-f", f"source[path]={pages_path}"])
    if code == 0:
        log.info("GitHub Pages 已启用")
        return
    code, out = _run_quiet([gh, "api", "-X", "PUT", f"repos/{full}/pages",
                            "-f", f"source[branch]={branch}",
                            "-f", f"source[path]={pages_path}"])
    if code != 0:
        log.warning("启用 GitHub Pages 未成功: %s", out[:300])


def deploy(html: str, project_dir: str, cfg: dict) -> str:
    gh = cfg.get("gh_bin") or "gh"
    owner = cfg["github"]["owner"]
    repo = cfg["github"]["repo"]
    branch = cfg["github"]["branch"]
    pages_path = cfg["github"]["pages_path"]
    full = f"{owner}/{repo}"

    docs_dir = os.path.join(project_dir, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    with open(os.path.join(docs_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

    if not os.path.exists(os.path.join(project_dir, ".git")):
        _run(["git", "init", "-b", branch], cwd=project_dir)
        _run(["git", "config", "user.name", "hermes-bot"], cwd=project_dir)
        _run(["git", "config", "user.email", _gh_email(gh)], cwd=project_dir)

    code, _ = _run_quiet(["git", "rev-parse", "--verify", "HEAD"], cwd=project_dir)
    if code != 0:
        _run(["git", "add", "-A"], cwd=project_dir)
        _run(["git", "commit", "-m", "init: AI 热点日报"], cwd=project_dir)

    code, _ = _run_quiet([gh, "repo", "view", full])
    if code != 0:
        log.info("创建 GitHub 仓库 %s …", full)
        _run([gh, "repo", "create", full, "--public", "--source", project_dir,
              "--remote", "origin", "--push"])
        _run_quiet([gh, "repo", "edit", full, "--default-branch", branch])
    else:
        _run_quiet(["git", "remote", "remove", "origin"], cwd=project_dir)
        _run(["git", "remote", "add", "origin", f"git@github.com:{full}.git"], cwd=project_dir)

    _run(["git", "add", "docs/index.html"], cwd=project_dir)
    code, _ = _run_quiet(["git", "diff", "--cached", "--quiet"], cwd=project_dir)
    if code != 0:
        _run(["git", "commit", "-m", f"Daily AI news briefing {util.now_cn():%Y-%m-%d}"], cwd=project_dir)
    else:
        log.info("内容无变化，跳过提交")
    _run(["git", "push", "-u", "origin", branch], cwd=project_dir)

    _enable_pages(gh, full, branch, pages_path)

    code, out = _run_quiet([gh, "api", f"repos/{full}/pages", "--jq", ".html_url"])
    if code == 0 and out:
        return out
    return f"https://{owner}.github.io/{repo}/"