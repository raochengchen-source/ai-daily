#!/usr/bin/env python3
"""Build today's standalone HTML — Selected only (no archive)."""
import json, os

BASE = os.environ.get("AI_DAILY_BASE") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE, "data")
OUT_DIR  = os.environ.get("AI_DAILY_OUT") or BASE
DATA_FILE = f"{DATA_DIR}/data_current.json"
if not os.path.exists(DATA_FILE):
    import glob
    cands = sorted(glob.glob(f"{DATA_DIR}/data_2*.json"))
    DATA_FILE = cands[-1] if cands else DATA_FILE
with open(DATA_FILE, encoding="utf-8") as f:
    today = json.load(f)

CSS = """
:root{
  --primary:#4982C9;--primary-deep:#2A5A9C;--primary-light:#D9E8FB;
  --bg-base:#F6F9FD;--bg-card:#FFFFFF;
  --text-1:#1A2A40;--text-2:#4B5C73;--text-3:#7B8AA0;
  --border:#E1EAF5;--accent-gold:#F0B400;
  --grad:linear-gradient(135deg,#4982C9 0%,#2A5A9C 100%);
  --shadow:0 4px 14px rgba(73,130,201,.10);
  --shadow-hover:0 8px 24px rgba(73,130,201,.18);
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg-base);color:var(--text-1);line-height:1.6;-webkit-font-smoothing:antialiased}
.container{max-width:1280px;margin:0 auto;padding:0 24px}
a{color:inherit;text-decoration:none}

.nav{position:sticky;top:0;z-index:100;background:rgba(255,255,255,.92);backdrop-filter:blur(12px);border-bottom:1px solid var(--border)}
.nav-inner{display:flex;align-items:center;height:64px;gap:32px}
.logo{display:flex;align-items:center;gap:10px;font-weight:700;font-size:18px;color:var(--primary-deep)}
.logo-icon{width:36px;height:36px;background:var(--grad);color:#fff;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:800}
.nav-spacer{flex:1}
.search-box{display:flex;align-items:center;gap:8px;padding:8px 14px;background:#F0F5FC;border-radius:10px;width:280px}
.search-box input{border:none;outline:none;background:transparent;flex:1;font-size:13px;color:var(--text-1)}

.hero{padding:48px 0 32px;background:linear-gradient(180deg,#EAF2FC 0%,#F6F9FD 100%)}
.hero-badge{display:inline-block;padding:6px 14px;background:rgba(73,130,201,.12);color:var(--primary-deep);border-radius:20px;font-size:13px;font-weight:600;margin-bottom:16px}
h1{font-size:42px;font-weight:800;line-height:1.25;margin-bottom:14px}
.accent{background:var(--grad);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
.hero-sub{color:var(--text-2);font-size:15px;max-width:760px;margin-bottom:24px}
.cal-card{display:flex;align-items:center;gap:14px;padding:16px 20px;background:#fff;border-radius:14px;box-shadow:var(--shadow);max-width:520px;margin-bottom:24px}
.cal-icon{width:42px;height:42px;background:var(--primary-light);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:20px}
.cal-info .label{font-size:12px;color:var(--text-3)}
.cal-info .date{font-size:16px;font-weight:700;color:var(--text-1)}
.filter-row{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}
.chip{padding:7px 14px;background:#fff;border:1px solid var(--border);border-radius:18px;font-size:13px;font-weight:500;color:var(--text-2);cursor:pointer;transition:.2s;display:inline-flex;align-items:center;gap:6px}
.chip:hover{border-color:var(--primary);color:var(--primary-deep)}
.chip.active{background:var(--grad);color:#fff;border-color:transparent}
.chip .count{padding:1px 7px;background:rgba(255,255,255,.25);border-radius:10px;font-size:11px}
.chip:not(.active) .count{background:var(--primary-light);color:var(--primary-deep)}

.section{padding:32px 0}
.section-head{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:20px}
.section-title{font-size:24px;font-weight:700;display:flex;align-items:center;gap:10px}
.section-sub{color:var(--text-3);font-size:13px}

.top3-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:18px}
.top-card{position:relative;display:block;padding:22px;background:#fff;border-radius:16px;border:1px solid var(--border);box-shadow:var(--shadow);transition:.25s;overflow:hidden}
.top-card:hover{transform:translateY(-3px);box-shadow:var(--shadow-hover);border-color:var(--primary-light)}
.top-card.rank1{background:linear-gradient(180deg,#FFFBEB 0%,#FFF 50%);border-color:#F5D77F}
.rank-badge{position:absolute;top:14px;right:14px;width:36px;height:36px;background:var(--grad);color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:15px;box-shadow:0 4px 10px rgba(73,130,201,.3)}
.top-card.rank1 .rank-badge{background:linear-gradient(135deg,#F0B400 0%,#D69500 100%);box-shadow:0 4px 10px rgba(240,180,0,.4)}
.meta-row{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text-3);margin-bottom:12px;flex-wrap:wrap}
.cat-tag{padding:3px 9px;background:var(--primary-light);color:var(--primary-deep);border-radius:6px;font-weight:600}
.heat-tag{padding:3px 9px;background:#FEF3C7;color:#B45309;border-radius:6px;font-weight:600}
.dot{width:3px;height:3px;background:var(--text-3);border-radius:50%}
.top-card h3{font-size:17px;line-height:1.45;margin-bottom:10px;color:var(--text-1);padding-right:42px}
.top-card .summary{font-size:13px;color:var(--text-2);line-height:1.65;margin-bottom:12px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.reason-box{padding:10px 12px;background:rgba(73,130,201,.06);border-left:3px solid var(--primary);border-radius:6px;font-size:12px;color:var(--text-2);margin-bottom:12px}
.reason-box strong{color:var(--primary-deep);margin-right:6px}
.tags-row{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}
.tag{padding:2px 8px;background:#F0F5FC;color:var(--text-2);border-radius:4px;font-size:11px}
.read-btn{display:inline-flex;align-items:center;gap:4px;color:var(--primary);font-size:13px;font-weight:600}

.grid-3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px}
.news-card{display:block;padding:18px;background:#fff;border-radius:14px;border:1px solid var(--border);box-shadow:0 2px 8px rgba(73,130,201,.06);transition:.25s}
.news-card:hover{transform:translateY(-2px);box-shadow:var(--shadow);border-color:var(--primary-light)}
.news-card h4{font-size:15px;line-height:1.5;margin-bottom:8px;color:var(--text-1)}
.news-card .summary{font-size:12.5px;color:var(--text-2);line-height:1.6;margin-bottom:10px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}

.footer{padding:30px 0;text-align:center;color:var(--text-3);font-size:12px;border-top:1px solid var(--border);margin-top:32px}
.footer a{color:var(--primary);font-weight:500}

@media(max-width:900px){
  .top3-grid,.grid-3{grid-template-columns:1fr}
  h1{font-size:28px}
  .search-box{display:none}
}
"""

JS = """
function filterCat(key,el){
  document.querySelectorAll('.chip').forEach(c=>c.classList.remove('active'));
  el.classList.add('active');
  document.querySelectorAll('[data-cat]').forEach(card=>{
    card.style.display = (key==='all'||card.dataset.cat===key)?'':'none';
  });
}
"""

def card(item, top=False, rank=None):
    tags = "".join(f'<span class="tag">#{t}</span>' for t in item.get("tags", []))
    rank_html = f'<div class="rank-badge">{rank}</div>' if rank else ""
    cls = "top-card rank1" if rank == 1 else ("top-card" if top else "news-card")
    h = "h3" if top else "h4"
    return f"""<a href="{item['url']}" target="_blank" rel="noopener" class="{cls}" data-cat="{item['catKey']}">
  {rank_html}
  <div class="meta-row"><span class="cat-tag">{item['cat']}</span><span class="heat-tag">🔥 {item['heat']}</span><span>{item['time']}</span><span class="dot"></span><span>{item['source']}</span></div>
  <{h}>{item['title']}</{h}>
  <div class="summary">{item['summary']}</div>
  <div class="reason-box"><strong>💡 推荐理由</strong>{item['reason']}</div>
  <div class="tags-row">{tags}</div>
  <span class="read-btn">阅读原文 →</span>
</a>"""

chips = "".join(
    f'<span class="chip {"active" if c["key"]=="all" else ""}" onclick="filterCat(\'{c["key"]}\',this)">{c["label"]}<span class="count">{c["count"]}</span></span>'
    for c in today["categories"])
top3 = "".join(card(it, top=True, rank=it["rank"]) for it in today["top3"])
waterfall = "".join(card(it, top=False) for it in today["items"])

# 历史记录页面永久 URL（GitHub Pages）
ARCHIVE_URL = "https://raochengchen-source.github.io/ai-daily/archive.html"

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI 精选日报 · {today['date']}</title>
<style>{CSS}</style>
</head>
<body>
<nav class="nav"><div class="container nav-inner">
  <a class="logo"><span class="logo-icon">AI</span>AI 精选日报</a>
  <div class="nav-spacer"></div>
  <a href="{ARCHIVE_URL}" target="_blank" style="color:var(--primary);font-size:14px;font-weight:600">📚 历史记录 →</a>
  <div class="search-box"><span>🔍</span><input placeholder="搜索资讯、来源、标签..."></div>
</div></nav>

<div id="selected">
  <section class="hero"><div class="container">
    <div class="hero-badge">✨ 每日 AI 精选 · {today['date']} {today['weekday']} · 共 {today['totalCount']} 条</div>
    <h1>今天的 AI 圈,<span class="accent">这 {today['totalCount']} 条就够了</span></h1>
    <p class="hero-sub">每日凌晨自动抓取全网最新动态,经多维度评分模型筛选,精选大模型、商业、工具、研究、基础设施等核心赛道高价值资讯。</p>
    <div class="cal-card">
      <div class="cal-icon">📅</div>
      <div class="cal-info"><div class="label">今日日期</div><div class="date">{today['date']} {today['weekday']}</div></div>
    </div>
    <div class="filter-row">{chips}</div>
  </div></section>

  <section class="section"><div class="container">
    <div class="section-head"><div class="section-title">🏆 今日 TOP 3</div><div class="section-sub">综合热度与价值评分</div></div>
    <div class="top3-grid">{top3}</div>
  </div></section>

  <section class="section"><div class="container">
    <div class="section-head"><div class="section-title">📰 精选资讯</div><div class="section-sub">共 {len(today['items'])} 条 · 按热度排序</div></div>
    <div class="grid-3">{waterfall}</div>
  </div></section>
</div>

<footer class="footer"><div class="container">
  © 2026 AI 精选日报 · Powered by <a href="#">Mira AI</a> · 每日 10:00 自动更新 · 数据来源:aihot.virxact.com · <a href="{ARCHIVE_URL}" target="_blank">查看历史记录</a>
</div></footer>

<script>{JS}</script>
</body>
</html>"""

out = os.path.join(OUT_DIR, "index.html")
os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print(f"OK: {out} ({os.path.getsize(out)} bytes)")
