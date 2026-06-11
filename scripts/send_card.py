#!/usr/bin/env python3
"""Send the daily AI digest card via Feishu self-built app bot.

Reads creds from env (LARK_APP_ID, LARK_APP_SECRET, LARK_CHAT_ID).
Reads latest data from data/data_current.json or newest data_2*.json.
Uses the permanent GitHub Pages URL.
"""
import json, os, sys, glob, urllib.request, urllib.error

APP_ID     = os.environ["LARK_APP_ID"]
APP_SECRET = os.environ["LARK_APP_SECRET"]
CHAT_ID    = os.environ["LARK_CHAT_ID"]
SITE_URL   = os.environ.get("AI_DAILY_SITE_URL", "https://raochengchen-source.github.io/ai-daily/")
BASE       = os.environ.get("AI_DAILY_BASE") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR   = os.path.join(BASE, "data")


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


def send(token, card):
    body = {
        "receive_id": CHAT_ID,
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


def main():
    d = load_data()
    date = d["date"]
    # 幂等锁:当天已发过则跳过(支持一天多个 cron 触发点而不重复发卡片)
    force = os.environ.get("AI_DAILY_FORCE_SEND") == "1"
    lock = os.path.join(DATA_DIR, f".sent_{date}")
    if os.path.exists(lock) and not force:
        print(f"SKIP already sent for {date} (lock exists). Set AI_DAILY_FORCE_SEND=1 to override.")
        return
    token = get_token()
    card = build_card(d)
    mid = send(token, card)
    try:
        with open(lock, "w", encoding="utf-8") as f:
            f.write(mid)
    except Exception:
        pass
    print(f"OK sent {mid} for {date} -> {CHAT_ID}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
