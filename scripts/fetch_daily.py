#!/usr/bin/env python3
"""Fetch today's AI HOT selected items and write data_{DATE}.json in the format build_single.py expects."""
import json, os, sys, datetime, subprocess, re

BASE = os.environ.get("AI_DAILY_BASE") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE, "data")
os.makedirs(DATA_DIR, exist_ok=True)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 aihot-skill/0.2.0"
API = "https://aihot.virxact.com/api/public/items?mode=selected&take=50"

# Map aihot's 5 categories to our 8 visual buckets.
# Our buckets: biz / infra / model / tool / research / industry / opinion / (fallback industry)
API_TO_OURS = {
    "ai-models":   ("model",    "大模型"),
    "ai-products": ("tool",     "工具"),
    "industry":    ("industry", "行业"),
    "paper":       ("research", "研究"),
    "tip":         ("opinion",  "观点"),
}

# Keyword overrides — promote items into biz / infra when title hints at them.
BIZ_RX   = re.compile(r"融资|投资|收购|上市|IPO|估值|股价|轮|被收|併购|裁员|fundra|acqui|invest|valuation|IPO|funding|billion|million", re.I)
INFRA_RX = re.compile(r"GPU|TPU|HBM|芯片|算力|集群|cluster|H100|H200|B100|B200|MI3|MI4|NVIDIA|AMD|台积电|TSMC|数据中心|datacenter|infra|inference|训练效率|训练算力", re.I)

def classify(item):
    api_cat = item.get("category")
    title = (item.get("title") or "") + " " + (item.get("summary") or "")
    if BIZ_RX.search(title):
        return ("biz", "商业")
    if INFRA_RX.search(title):
        return ("infra", "基础设施")
    if api_cat in API_TO_OURS:
        return API_TO_OURS[api_cat]
    return ("industry", "行业")  # fallback

def to_local(iso):
    """ISO UTC -> HH:MM in Asia/Shanghai."""
    if not iso:
        return "—"
    try:
        # Strip trailing Z and milliseconds, parse manually (no zoneinfo in sandbox).
        s = iso.rstrip("Z").split(".")[0]
        dt = datetime.datetime.fromisoformat(s).replace(tzinfo=datetime.timezone.utc)
        local = dt.astimezone(datetime.timezone(datetime.timedelta(hours=8)))
        return local.strftime("%H:%M")
    except Exception:
        return "—"

def extract_tags(title, summary, cat_label):
    """Pull 1-3 short tags from title/summary (heuristic: capitalised words + numbers)."""
    text = f"{title} {summary or ''}"
    candidates = re.findall(r"[A-Z][A-Za-z0-9.\-]{2,15}|\d+B|\d+亿|\d+万|v\d+(?:\.\d+)?", text)
    seen, out = set(), []
    for c in candidates:
        if c.lower() in seen: continue
        seen.add(c.lower()); out.append(c)
        if len(out) == 3: break
    if not out: out = [cat_label]
    return out

def fetch():
    cmd = ["curl", "-sS", "-H", f"User-Agent: {UA}", API]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        raise RuntimeError(f"curl failed: {out.stderr}")
    data = json.loads(out.stdout)
    return data.get("items", [])

def main():
    items = fetch()
    if not items:
        print("ERROR: API returned no items", file=sys.stderr)
        sys.exit(1)

    # Build records with our schema, sorted by publishedAt desc, heat assigned by recency rank.
    items.sort(key=lambda x: x.get("publishedAt") or "", reverse=True)
    records = []
    for idx, it in enumerate(items[:21]):  # cap at 21 for readability (3 top + 18 grid)
        cat_key, cat_label = classify(it)
        heat = max(72, 96 - idx)  # newest = 96, then degrade
        records.append({
            "cat": cat_label,
            "catKey": cat_key,
            "time": to_local(it.get("publishedAt")),
            "source": it.get("source") or "—",
            "heat": heat,
            "title": it.get("title") or "(无标题)",
            "summary": it.get("summary") or "",
            "reason": f"{cat_label}方向的新动态,值得关注。",
            "tags": extract_tags(it.get("title", ""), it.get("summary", ""), cat_label),
            "url": it.get("url") or "#",
        })

    # Split top3 vs items, assign rank
    top3 = []
    for i, r in enumerate(records[:3]):
        r2 = dict(r); r2["rank"] = i + 1
        top3.append(r2)
    rest = []
    for i, r in enumerate(records[3:], start=4):
        r2 = dict(r); r2["rank"] = i
        rest.append(r2)

    # Categories — count from all records
    cat_count = {}
    for r in records:
        cat_count[(r["catKey"], r["cat"])] = cat_count.get((r["catKey"], r["cat"]), 0) + 1
    cat_label_map = {
        "biz": "商业", "infra": "基础设施", "model": "大模型", "tool": "工具",
        "research": "研究", "industry": "行业", "opinion": "观点",
    }
    categories = [{"key": "all", "label": "全部", "count": len(records)}]
    for k, lbl in cat_label_map.items():
        c = sum(v for (kk, _l), v in cat_count.items() if kk == k)
        if c > 0:
            categories.append({"key": k, "label": lbl, "count": c})

    date = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).date()
    weekdays = ["周一","周二","周三","周四","周五","周六","周日"]
    out_obj = {
        "date": date.isoformat(),
        "weekday": weekdays[date.weekday()],
        "totalCount": len(records),
        "categories": categories,
        "top3": top3,
        "items": rest,
    }

    out_path = os.path.join(DATA_DIR, f"data_{date.isoformat()}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out_obj, f, ensure_ascii=False, indent=2)

    # Also overwrite the "current" file that build_single.py reads.
    with open(os.path.join(DATA_DIR, "data_current.json"), "w", encoding="utf-8") as f:
        json.dump(out_obj, f, ensure_ascii=False, indent=2)

    print(f"OK fetched {len(records)} items -> {out_path}")

if __name__ == "__main__":
    main()
