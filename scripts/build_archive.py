#!/usr/bin/env python3
"""Build the persistent archive page from all data_2*.json files.
Each day collapses by default; clicking expands the FULL day content
(TOP3 cards + waterfall cards) just like the daily page.
"""
import json, os, glob, datetime, time

BUILD_TS = str(int(time.time()))  # 构建时间戳,用于页面防缓存自动刷新

BASE = os.environ.get("AI_DAILY_BASE") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE, "data")
OUT_DIR  = os.environ.get("AI_DAILY_OUT") or BASE
files = sorted(glob.glob(f"{DATA_DIR}/data_2*.json"), reverse=True)

days = []
total_items = 0
all_cats = set()
heat_sum = 0
heat_n = 0
for fp in files:
    try:
        with open(fp, encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:
        print(f"skip {fp}: {e}")
        continue
    date_str = d.get("date") or os.path.basename(fp).replace("data_", "").replace(".json", "")
    wd = d.get("weekday", "")
    top3 = d.get("top3", [])
    items = d.get("items", [])
    total_count = d.get("totalCount", len(items) + len(top3))
    total_items += total_count
    for c in d.get("categories", []):
        if c.get("key") != "all":
            all_cats.add(c.get("label"))
    for it in top3 + items:
        if isinstance(it.get("heat"), int):
            heat_sum += it["heat"]; heat_n += 1
    try:
        dt = datetime.date.fromisoformat(date_str)
        ym = dt.strftime("%Y/%m"); day_num = dt.day
    except Exception:
        ym = ""; day_num = 0
    days.append({
        "date": date_str, "wd": wd, "ym": ym, "day": day_num,
        "count": total_count, "top3": top3, "items": items,
        "categories": d.get("categories", []),
    })

avg_heat = round(heat_sum / heat_n) if heat_n else 0

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

.hero{padding:48px 0 32px;background:linear-gradient(180deg,#EAF2FC 0%,#F6F9FD 100%)}
.hero-badge{display:inline-block;padding:6px 14px;background:rgba(73,130,201,.12);color:var(--primary-deep);border-radius:20px;font-size:13px;font-weight:600;margin-bottom:16px}
h1{font-size:42px;font-weight:800;line-height:1.25;margin-bottom:14px}
.accent{background:var(--grad);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
.hero-sub{color:var(--text-2);font-size:15px;max-width:760px;margin-bottom:24px}

.stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:24px}
.stat-card{padding:18px;background:#fff;border-radius:12px;border:1px solid var(--border);box-shadow:var(--shadow)}
.stat-num{font-size:28px;font-weight:800;color:var(--primary-deep);margin-bottom:4px}
.stat-label{font-size:12px;color:var(--text-3)}

.tool-row{display:flex;gap:10px;flex-wrap:wrap;align-items:center;padding:14px;background:#fff;border-radius:12px;box-shadow:var(--shadow);margin-bottom:20px}
.tool-row button{padding:8px 16px;background:#F0F5FC;color:var(--primary-deep);border:1px solid var(--border);border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;transition:.2s}
.tool-row button:hover{background:var(--primary-light)}
.tool-row .grow{flex:1}

.section{padding:32px 0}
.day-list{display:flex;flex-direction:column;gap:18px}
.day-group{background:#fff;border-radius:14px;border:1px solid var(--border);box-shadow:var(--shadow);overflow:hidden;transition:.2s}
.day-group:hover{box-shadow:var(--shadow-hover)}

.day-summary{display:flex;align-items:center;gap:20px;padding:20px 24px;cursor:pointer;user-select:none;transition:.2s}
.day-summary:hover{background:#F8FBFE}
.day-box{flex-shrink:0;width:80px;height:80px;background:var(--grad);color:#fff;border-radius:12px;display:flex;flex-direction:column;align-items:center;justify-content:center}
.day-box .d{font-size:28px;font-weight:800;line-height:1}
.day-box .ym{font-size:11px;margin-top:4px;opacity:.9}

.day-meta{flex:1;min-width:0}
.day-meta-head{display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap}
.day-date{font-weight:700;font-size:16px}
.day-week{font-size:12px;color:var(--primary-deep);padding:2px 8px;background:var(--primary-light);border-radius:5px}
.day-count{font-size:12px;color:var(--text-3)}
.day-top3-preview{display:flex;flex-direction:column;gap:4px}
.preview-item{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--text-2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.preview-rank{flex-shrink:0;width:18px;height:18px;background:var(--grad);color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700}
.preview-item:first-child .preview-rank{background:linear-gradient(135deg,#F0B400 0%,#D69500 100%)}
.preview-title{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text-1)}

.toggle-btn{flex-shrink:0;display:flex;align-items:center;gap:6px;padding:8px 14px;background:var(--primary-light);color:var(--primary-deep);border-radius:8px;font-size:13px;font-weight:600;transition:.2s}
.day-group.open .toggle-btn{background:var(--grad);color:#fff}
.toggle-btn .arrow{display:inline-block;transition:transform .25s}
.day-group.open .toggle-btn .arrow{transform:rotate(180deg)}

.day-detail{display:none;padding:0 24px 24px;border-top:1px dashed var(--border)}
.day-group.open .day-detail{display:block}

.detail-section{margin-top:20px}
.detail-section-title{font-size:16px;font-weight:700;margin-bottom:14px;display:flex;align-items:center;gap:8px;color:var(--text-1)}
.detail-section-sub{font-size:12px;color:var(--text-3);font-weight:400;margin-left:6px}

.top3-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}
.top-card{position:relative;display:block;padding:18px;background:#fff;border-radius:14px;border:1px solid var(--border);box-shadow:var(--shadow);transition:.2s;overflow:hidden}
.top-card:hover{transform:translateY(-2px);box-shadow:var(--shadow-hover);border-color:var(--primary-light)}
.top-card.rank1{background:linear-gradient(180deg,#FFFBEB 0%,#FFF 50%);border-color:#F5D77F}
.rank-badge{position:absolute;top:12px;right:12px;width:32px;height:32px;background:var(--grad);color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:13px;box-shadow:0 4px 10px rgba(73,130,201,.3)}
.top-card.rank1 .rank-badge{background:linear-gradient(135deg,#F0B400 0%,#D69500 100%)}
.meta-row{display:flex;align-items:center;gap:8px;font-size:11px;color:var(--text-3);margin-bottom:10px;flex-wrap:wrap}
.cat-tag{padding:2px 8px;background:var(--primary-light);color:var(--primary-deep);border-radius:5px;font-weight:600}
.heat-tag{padding:2px 8px;background:#FEF3C7;color:#B45309;border-radius:5px;font-weight:600}
.dot{width:3px;height:3px;background:var(--text-3);border-radius:50%}
.top-card h3{font-size:15px;line-height:1.45;margin-bottom:10px;color:var(--text-1);padding-right:38px}
.top-card .summary{font-size:12.5px;color:var(--text-2);line-height:1.6;margin-bottom:10px}
.reason-box{padding:8px 10px;background:rgba(73,130,201,.06);border-left:3px solid var(--primary);border-radius:5px;font-size:11.5px;color:var(--text-2);margin-bottom:10px}
.reason-box strong{color:var(--primary-deep);margin-right:6px}
.tags-row{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:8px}
.tag{padding:2px 7px;background:#F0F5FC;color:var(--text-2);border-radius:4px;font-size:10.5px}
.read-btn{display:inline-flex;align-items:center;gap:4px;color:var(--primary);font-size:12px;font-weight:600}

.grid-3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}
.news-card{display:block;padding:16px;background:#fff;border-radius:12px;border:1px solid var(--border);box-shadow:0 2px 8px rgba(73,130,201,.06);transition:.2s}
.news-card:hover{transform:translateY(-2px);box-shadow:var(--shadow);border-color:var(--primary-light)}
.news-card h4{font-size:14px;line-height:1.5;margin-bottom:8px;color:var(--text-1)}
.news-card .summary{font-size:12px;color:var(--text-2);line-height:1.55;margin-bottom:8px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}

.footer{padding:30px 0;text-align:center;color:var(--text-3);font-size:12px;border-top:1px solid var(--border);margin-top:32px}
.footer a{color:var(--primary);font-weight:500}

@media(max-width:900px){
  .stats-grid{grid-template-columns:1fr 1fr}
  .top3-grid,.grid-3{grid-template-columns:1fr}
  h1{font-size:28px}
  .day-summary{flex-wrap:wrap}
  .day-box{width:64px;height:64px}
}
"""

JS = """
function toggleDay(el){
  const g = el.closest('.day-group');
  g.classList.toggle('open');
  if(g.classList.contains('open')){
    const t = g.querySelector('.toggle-btn span:not(.arrow)');
    if(t) t.textContent = '收起';
  } else {
    const t = g.querySelector('.toggle-btn span:not(.arrow)');
    if(t) t.textContent = '展开全部';
  }
}
function expandAll(){
  document.querySelectorAll('.day-group').forEach(g=>{
    g.classList.add('open');
    const t = g.querySelector('.toggle-btn span:not(.arrow)');
    if(t) t.textContent = '收起';
  });
}
function collapseAll(){
  document.querySelectorAll('.day-group').forEach(g=>{
    g.classList.remove('open');
    const t = g.querySelector('.toggle-btn span:not(.arrow)');
    if(t) t.textContent = '展开全部';
  });
}
"""

def card_html(item, top=False, rank=None):
    tags = "".join(f'<span class="tag">#{t}</span>' for t in item.get("tags", []))
    rank_html = f'<div class="rank-badge">{rank}</div>' if rank else ""
    cls = "top-card rank1" if rank == 1 else ("top-card" if top else "news-card")
    h = "h3" if top else "h4"
    cat_key = item.get("catKey", "")
    summary = item.get("summary", "").replace("\n", "<br>")
    return f"""<a href="{item.get('url','#')}" target="_blank" rel="noopener" class="{cls}" data-cat="{cat_key}">
  {rank_html}
  <div class="meta-row"><span class="cat-tag">{item.get('cat','')}</span><span class="heat-tag">🔥 {item.get('heat','')}</span><span>{item.get('time','')}</span><span class="dot"></span><span>{item.get('source','')}</span></div>
  <{h}>{item.get('title','')}</{h}>
  <div class="summary">{summary}</div>
  <div class="reason-box"><strong>💡 推荐理由</strong>{item.get('reason','')}</div>
  <div class="tags-row">{tags}</div>
  <span class="read-btn">阅读原文 →</span>
</a>"""

def render_day(g, default_open=False):
    # Preview (always visible) — top3 titles
    preview = ""
    for it in g["top3"][:3]:
        preview += (
            f'<div class="preview-item">'
            f'<span class="preview-rank">{it.get("rank","")}</span>'
            f'<span class="preview-title">{it.get("title","")}</span>'
            f'</div>'
        )
    # Full detail
    top3_cards = "".join(card_html(it, top=True, rank=it.get("rank")) for it in g["top3"])
    waterfall = "".join(card_html(it, top=False) for it in g["items"])
    open_cls = " open" if default_open else ""
    btn_text = "收起" if default_open else "展开全部"
    return f"""<div class="day-group{open_cls}">
  <div class="day-summary" onclick="toggleDay(this)">
    <div class="day-box"><div class="d">{g['day']:02d}</div><div class="ym">{g['ym']}</div></div>
    <div class="day-meta">
      <div class="day-meta-head">
        <span class="day-date">{g['date']}</span>
        <span class="day-week">{g['wd']}</span>
        <span class="day-count">共 {g['count']} 条精选</span>
      </div>
      <div class="day-top3-preview">{preview}</div>
    </div>
    <div class="toggle-btn"><span>{btn_text}</span><span class="arrow">▾</span></div>
  </div>
  <div class="day-detail">
    <div class="detail-section">
      <div class="detail-section-title">🏆 TOP 3 精选 <span class="detail-section-sub">综合热度与价值评分</span></div>
      <div class="top3-grid">{top3_cards}</div>
    </div>
    <div class="detail-section">
      <div class="detail-section-title">📰 完整资讯 <span class="detail-section-sub">共 {len(g['items'])} 条 · 按热度排序</span></div>
      <div class="grid-3">{waterfall}</div>
    </div>
  </div>
</div>"""

# 最新一天默认展开,方便用户一进来就能看
days_html = "".join(render_day(g, default_open=(i == 0)) for i, g in enumerate(days)) if days else \
    '<div style="text-align:center;padding:60px;color:var(--text-3)">暂无归档数据</div>'

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<meta name="ai-daily-build" content="{(days[0]['date'] if days else '—')}|{BUILD_TS}">
<title>AI 精选日报 · 历史记录</title>
<style>{CSS}</style>
<script>
// 自动防缓存:发现页面变旧就自动强刷一次。
(function(){{
  var CUR = "{(days[0]['date'] if days else '—')}|{BUILD_TS}";
  function check(){{
    fetch(location.pathname + "?_=" + Date.now(), {{cache:"no-store"}})
      .then(function(r){{return r.text();}})
      .then(function(t){{
        var m = t.match(/name="ai-daily-build" content="([^"]+)"/);
        if(m && m[1] && m[1] !== CUR){{
          location.replace(location.pathname + "?v=" + Date.now());
        }}
      }}).catch(function(){{}});
  }}
  check();
  document.addEventListener("visibilitychange", function(){{
    if(document.visibilityState === "visible") check();
  }});
}})();
</script>
</head>
<body>
<nav class="nav"><div class="container nav-inner">
  <a class="logo"><span class="logo-icon">AI</span>AI 精选日报 · 历史记录</a>
  <div class="nav-spacer"></div>
  <span style="color:var(--text-3);font-size:13px">最近更新:{days[0]['date'] if days else '—'}</span>
</div></nav>

<section class="hero"><div class="container">
  <div class="hero-badge">📚 历史归档 · 累计 {len(days)} 天</div>
  <h1>历史<span class="accent">精选回顾</span></h1>
  <p class="hero-sub">按日浏览过往每日 AI 精选,点击「展开全部」查看当天完整内容(TOP 3 卡片 + 全部资讯),沉淀 AI 行业完整脉络。</p>
  <div class="stats-grid">
    <div class="stat-card"><div class="stat-num">{len(days)}</div><div class="stat-label">归档天数</div></div>
    <div class="stat-card"><div class="stat-num">{total_items}</div><div class="stat-label">累计资讯</div></div>
    <div class="stat-card"><div class="stat-num">{len(all_cats)}</div><div class="stat-label">分类覆盖</div></div>
    <div class="stat-card"><div class="stat-num">{avg_heat}</div><div class="stat-label">平均热度</div></div>
  </div>
  <div class="tool-row">
    <button onclick="expandAll()">📂 全部展开</button>
    <button onclick="collapseAll()">📁 全部收起</button>
    <span class="grow"></span>
    <span style="color:var(--text-3);font-size:12px">提示:点击每日卡片任意位置可展开/收起</span>
  </div>
</div></section>

<section class="section" style="padding-top:0"><div class="container">
  <div class="day-list">{days_html}</div>
</div></section>

<footer class="footer"><div class="container">
  © 2026 AI 精选日报 · Powered by <a href="#">Mira AI</a> · 数据来源:aihot.virxact.com
</div></footer>

<script>{JS}</script>
</body>
</html>"""

out = os.path.join(OUT_DIR, "archive.html")
os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print(f"OK archive: {out} ({os.path.getsize(out)} bytes), {len(days)} days, {total_items} items")
