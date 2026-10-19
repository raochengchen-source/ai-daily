#!/usr/bin/env python3
"""Send the daily AI digest card to the user via bot open_id private chat."""
import json, os, sys, glob, subprocess, urllib.request, urllib.error

APP_ID     = os.environ["LARK_APP_ID"]
APP_SECRET = os.environ["LARK_APP_SECRET"]
# 接收人：默认本人。内部用邮箱换「本应用视角的 open_id」，最终以 open_id 发私聊。
EMAIL      = os.environ.get("LARK_EMAIL", "raochengchen@bytedance.com")
SITE_URL   = os.environ.get("AI_DAILY_SITE_URL", "https://raochengchen-source.github.io/ai-daily/")
BASE       = os.environ.get("AI_DAILY_BASE") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR   = os.path.join(BASE, "data")


def load_targets():
    ids = []
    for x in (EMAIL or "").split(","):
        x = x.strip()
        if x:
            ids.append(x)
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
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8")
        except Exception:
            pass
        raise RuntimeError(f"HTTP {e.code}: {detail}")


def get_token():
    r = http_json(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        body={"app_id": APP_ID, "app_secret": APP_SECRET},
        method="POST",
    )
    if r.get("code") != 0:
        raise RuntimeError(f"token failed: {r}")
    return r["tenant_access_token"]


def resolve_open_id(token, email):
    """用本应用 tenant token + 邮箱换出「本应用视角的 open_id」。"""
    r = http_json(
        "https://open.feishu.cn/open-apis/contact/v3/users/batch_get_id?user_id_type=open_id",
        body={"emails": [email]},
        headers={"Authorization": f"Bearer {token}"},
        method="POST",
    )
    if r.get("code") != 0:
        raise RuntimeError(f"resolve open_id failed: {r}")
    users = r.get("data", {}).get("user_list", [])
    if not users or not users[0].get("open_id"):
        raise RuntimeError(f"cannot resolve open_id for {email}: {r}")
    return users[0]["open_id"]


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


def send(token, card, open_id):
    body = {
        "receive_id": open_id,
        "msg_type": "interactive",
        "content": json.dumps(card, ensure_ascii=False),
    }
    r = http_json(
        "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id",
        body=body,
        headers={"Authorization": f"Bearer {token}"},
        method="POST",
    )
    if r.get("code") != 0:
        raise RuntimeError(f"send failed: {r}")
    return r["data"]["message_id"]


def commit_lock(lock_path, date):
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
        if git("diff", "--cached", "--quiet", check=False).returncode == 0:
            print(f"lock {rel} already committed, nothing to push")
            return
        git("commit", "-m", f"chore: lock sent {date} [skip ci]")
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
    targets_list = load_targets()
    if not targets_list:
        raise RuntimeError("no target email (set LARK_EMAIL)")

    lock = os.path.join(DATA_DIR, f".sent_{date}")
    sent = set()
    if os.path.exists(lock):
        try:
            with open(lock, encoding="utf-8") as f:
                raw = f.read().strip()
            obj = json.loads(raw)
            sent = set(obj.get("sent", []))
        except Exception:
            sent = set()

    token = get_token()
    card = build_card(d)
    results = {}
    pending = []
    for email in targets_list:
        try:
            oid = resolve_open_id(token, email)
            if not force and oid in sent:
                print(f"SKIP {oid} already sent for {date}.")
                continue
            pending.append((email, oid))
        except Exception as e:
            print(f"WARN resolve open_id for {email} failed: {e}")

    if not pending:
        print(f"SKIP all {len(targets_list)} target(s) already sent for {date}. Set AI_DAILY_FORCE_SEND=1 to override.")
        return

    for email, oid in pending:
        try:
            mid = send(token, card, oid)
            sent.add(oid)
            results[oid] = mid
            print(f"OK sent {mid} for {date} -> {oid} ({email})")
        except Exception as e:
            print(f"WARN send to {oid} ({email}) failed: {e}")

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
