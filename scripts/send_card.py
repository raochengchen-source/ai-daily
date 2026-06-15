#!/usr/bin/env python3
"""Send the daily AI digest card via Feishu self-built app bot.

Reads creds from env (LARK_APP_ID, LARK_APP_SECRET, LARK_CHAT_ID).
Reads latest data from data/data_current.json or newest data_2*.json.
Uses the permanent GitHub Pages URL.
"""
import json, os, sys, glob, subprocess, urllib.request, urllib.error

APP_ID     = os.environ["LARK_APP_ID"]
APP_SECRET = os.environ["LARK_APP_SECRET"]
CHAT_ID    = os.environ["LARK_CHAT_ID"]
SITE_URL   = os.environ.get("AI_DAILY_SITE_URL", "https://raochengchen-source.github.io/ai-daily/")
BASE       = os.environ.get("AI_DAILY_BASE") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR   = os.path.join(BASE, "data")


def load_chat_ids():
    """目标群 = 环境变量 LARK_CHAT_ID(可逗号分隔) ∪ data/chat_ids.txt(每行一个,# 注释)。
    新增/删除推送群只需改 data/chat_ids.txt 并提交,无需改 GitHub Secrets。"""
    ids = []
    for x in (CHAT_ID or "").split(","):
        x = x.strip()
        if x:
            ids.append(x)
    f = os.path.join(DATA_DIR, "chat_ids.txt")
    if os.path.exists(f):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                line = line.split("#", 1)[0].strip()
                if line:
                    ids.append(line)
    # 去重并保序
    seen, out = set(), []
    for x in ids:
        if x not in seen:
            seen.add(x); out.append(x)
    return out


def http_json(url, body=None, headers=None, method="GET"):
    data = None if body is None else json.dumps(body).encode("utf-8")
    h = {"Content-Type": "application/json"}
    if headers: h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def get_token():
    r = http_json(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        body={"app_id": APP_ID, "app_secret": APP_SECRET},
        method="POST",
    )
    if r.get("code") != 0:
        raise RuntimeError(f"token failed: {r}")
    return r["tenant_access_token"]


def load_data():
    p = os.path.join(DATA_DIR, "data_current.json")
    if not os.path.exists(p):
        cands = sorted(glob.glob(os.path.join(DATA_DIR, "data_2*.json")))
        if not cands:
            raise FileNotFoundError("no data file")
        p = cands[-1]
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def build_card(d):
    lines = [f"**📅 {d['date']}** · {d.get('weekday','')}", ""]
    for it in d.get("top3", []):
        lines.append(f"**{it['rank']}.** {it['title']}")
    text = "\n".join(lines)
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": f"AI 精选日报 · {d['date']}"},
        },
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": text}},
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [{
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "🔗 打开完整日报"},
                    "type": "primary",
                    "url": SITE_URL,
                }],
            },
        ],
    }


def send(token, card, chat_id):
    body = {
        "receive_id": chat_id,
        "msg_type": "interactive",
        "content": json.dumps(card, ensure_ascii=False),
    }
    r = http_json(
        "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
        body=body,
        headers={"Authorization": f"Bearer {token}"},
        method="POST",
    )
    if r.get("code") != 0:
        raise RuntimeError(f"send failed: {r}")
    return r["data"]["message_id"]


def commit_lock(lock_path, date):
    """把幂等锁立即提交并推送到仓库,让后续被串行化的并发 run 在 checkout 时
    就能看到锁从而跳过,彻底避免一天重复发卡片。仅在 GitHub Actions 中执行。"""
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    rel = os.path.relpath(lock_path, BASE)

    def git(*args, check=True):
        return subprocess.run(["git", "-C", BASE, *args],
                              capture_output=True, text=True, check=check)

    try:
        git("config", "user.name", "github-actions[bot]", check=False)
        git("config", "user.email",
            "github-actions[bot]@users.noreply.github.com", check=False)
        git("add", rel)
        # 没有变更则无需提交(锁已在之前的 run 提交过)
        if git("diff", "--cached", "--quiet", check=False).returncode == 0:
            print(f"lock {rel} already committed, nothing to push")
            return
        git("commit", "-m", f"chore: lock sent {date} [skip ci]")
        # 推送,若被拒绝则 rebase 后重试一次
        if git("push", check=False).returncode != 0:
            git("pull", "--rebase", check=False)
            git("push", check=False)
        print(f"committed+pushed lock {rel}")
    except Exception as e:
        print(f"WARN commit_lock failed: {e}")


def main():
    d = load_data()
    date = d["date"]
    force = os.environ.get("AI_DAILY_FORCE_SEND") == "1"
    chat_ids = load_chat_ids()
    if not chat_ids:
        raise RuntimeError("no target chat_id (set LARK_CHAT_ID or data/chat_ids.txt)")

    lock = os.path.join(DATA_DIR, f".sent_{date}")
    # 锁文件按群记录已发状态:{"sent": ["oc_xxx", ...]}。兼容旧版纯文本锁(视为整体已发)。
    sent = set()
    if os.path.exists(lock):
        try:
            with open(lock, encoding="utf-8") as f:
                raw = f.read().strip()
            obj = json.loads(raw)
            sent = set(obj.get("sent", []))
        except Exception:
            # 旧版纯文本锁:无法区分群,保守地认为列表里第一个群已发
            sent = {chat_ids[0]} if chat_ids else set()

    targets = chat_ids if force else [c for c in chat_ids if c not in sent]
    if not targets:
        print(f"SKIP all {len(chat_ids)} chat(s) already sent for {date}. Set AI_DAILY_FORCE_SEND=1 to override.")
        return

    token = get_token()
    card = build_card(d)
    results = {}
    for cid in targets:
        try:
            mid = send(token, card, cid)
            sent.add(cid)
            results[cid] = mid
            print(f"OK sent {mid} for {date} -> {cid}")
        except Exception as e:
            print(f"WARN send to {cid} failed: {e}")

    # 写锁:记录所有已成功发送的群,再立即提交推送,确保后续串行 run 看到锁
    try:
        with open(lock, "w", encoding="utf-8") as f:
            json.dump({"date": date, "sent": sorted(sent), "ids": results}, f, ensure_ascii=False)
    except Exception:
        pass
    commit_lock(lock, date)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
