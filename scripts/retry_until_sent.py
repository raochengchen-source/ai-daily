#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
retry_until_sent.py —— AI 精选日报「重试直到成功一次」守护脚本

用途:
  当天日报若尚未成功推送(常见根因:上游数据源 aihot.virxact.com 短时不可用,
  导致 fetch_daily 超时、线上 workflow_dispatch 失败),就重新派发一次 GitHub
  Actions workflow(workflow_dispatch, ref=main)。一旦当天已成功,则直接跳过、
  不再重复触发 —— 即「成功一次就停」。

设计要点(与 skill 幂等语义一致):
  - 只用仓库 remote URL 里的 PAT 触发 workflow_dispatch(HTTP 204=成功),
    不需要 LARK_APP_SECRET 明文,安全。
  - 「当天是否已成功」的判定采用双信号,任一命中即视为成功、直接退出:
      1) 仓库存在当天幂等锁 data/.sent_<YYYY-MM-DD>(send_card 发送成功后写并推回);
      2) GitHub Actions 当天有一条 conclusion=success 的 daily 工作流 run。
  - 由 Mira 定时任务每 2 小时调用本脚本;配合上面的判定,天然实现
    「没成功就每 2 小时重试一次,直到有一次成功」。

退出码:
  0  当天已成功(无需动作) 或 本次成功派发了一次 workflow_dispatch
  2  本次判定为「未成功」且派发失败(留待下一个 2 小时窗口再试)
"""
import os
import re
import sys
import json
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

BASE = os.environ.get("AI_DAILY_BASE") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW_ID = os.environ.get("AI_DAILY_WORKFLOW_ID", "291762623")
CST = timezone(timedelta(hours=8))


def today_str():
    return datetime.now(CST).strftime("%Y-%m-%d")


def run(cmd, **kw):
    return subprocess.run(cmd, cwd=BASE, capture_output=True, text=True, **kw)


def get_token_and_repo():
    """从 remote.origin.url 里取出 PAT 与 owner/repo。"""
    r = run(["git", "config", "--get", "remote.origin.url"])
    url = (r.stdout or "").strip()
    m = re.match(r"https://[^:]+:([^@]+)@github\.com/([^/]+/[^/.]+)", url)
    if not m:
        print("[retry] 无法从 remote URL 解析 PAT/repo", file=sys.stderr)
        return None, None
    return m.group(1), m.group(2)


def gh_api(token, path):
    req = urllib.request.Request(
        "https://api.github.com/repos/" + path,
        headers={"Authorization": "token " + token,
                 "Accept": "application/vnd.github+json",
                 "User-Agent": "ai-daily-retry"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def already_sent_today(token, repo):
    day = today_str()
    # 信号 1:先 git pull 再看当天锁
    run(["git", "pull", "--rebase", "origin", "main"])
    if os.path.exists(os.path.join(BASE, "data", ".sent_" + day)):
        print("[retry] 命中当天幂等锁 .sent_%s → 已成功,跳过。" % day)
        return True
    # 信号 2:当天是否有 success 的 workflow run
    try:
        data = gh_api(token, "%s/actions/workflows/%s/runs?per_page=20" % (repo, WORKFLOW_ID))
        for r in data.get("workflow_runs", []):
            created = r.get("created_at", "")
            # created_at 为 UTC;转 CST 比对日期
            try:
                dt = datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone(CST)
            except Exception:
                continue
            if dt.strftime("%Y-%m-%d") == day and r.get("conclusion") == "success":
                print("[retry] 当天已有成功的 workflow run(id=%s)→ 跳过。" % r.get("id"))
                return True
    except Exception as e:
        print("[retry] 查询 runs 失败(忽略,继续尝试派发):%s" % e, file=sys.stderr)
    return False


def dispatch(token, repo):
    body = json.dumps({"ref": "main"}).encode()
    req = urllib.request.Request(
        "https://api.github.com/repos/%s/actions/workflows/%s/dispatches" % (repo, WORKFLOW_ID),
        data=body, method="POST",
        headers={"Authorization": "token " + token,
                 "Accept": "application/vnd.github+json",
                 "User-Agent": "ai-daily-retry"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            code = resp.getcode()
    except urllib.error.HTTPError as e:
        code = e.code
    print("[retry] workflow_dispatch HTTP %s" % code)
    return code == 204


def main():
    token, repo = get_token_and_repo()
    if not token:
        sys.exit(2)
    if already_sent_today(token, repo):
        sys.exit(0)  # 成功一次就停
    print("[retry] 当天未成功 → 重新派发 workflow_dispatch ...")
    ok = dispatch(token, repo)
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
