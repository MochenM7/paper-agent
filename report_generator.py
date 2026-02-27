"""
Report Generator — HTML report with charts and Gemini-powered deep-dive chat
"""

import os, base64, logging
from datetime import datetime
from typing import List, Dict
from config import TOPIC_META, SOURCE_COLORS

logger = logging.getLogger(__name__)


def _b64(path):
    if path and os.path.exists(path):
        with open(path,"rb") as f:
            return f'<img src="data:image/png;base64,{base64.b64encode(f.read()).decode()}" style="width:100%;border-radius:8px;">'
    return '<p style="color:#555;padding:20px;text-align:center;">Chart unavailable</p>'

def _color(t): return TOPIC_META.get(t,{}).get("color","#8b949e")
def _emoji(t): return TOPIC_META.get(t,{}).get("emoji","📌")
def _label(t): return t.replace("_"," ").title()


def generate_charts(insights: Dict, out_dir: str) -> Dict:
    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
    except: return {}

    os.makedirs(out_dir, exist_ok=True)
    charts = {}
    BG, CARD, WHITE, GREY, BORDER = "#0d1117","#161b22","#f0f6fc","#8b949e","#30363d"
    src_colors = SOURCE_COLORS

    # Topic distribution
    td = insights.get("topic_distribution",{})
    if td:
        fig, ax = plt.subplots(figsize=(9,5)); fig.patch.set_facecolor(BG); ax.set_facecolor(CARD)
        items = sorted(td.items(), key=lambda x:-x[1])
        labels = [_label(t) for t,_ in items]; counts = [c for _,c in items]
        colors = [_color(t) for t,_ in items]
        bars = ax.barh(labels, counts, color=colors, edgecolor="none", height=0.6)
        for b,v in zip(bars,counts):
            ax.text(b.get_width()+.05, b.get_y()+b.get_height()/2, str(v), va="center", color=WHITE, fontsize=10, fontweight="bold")
        ax.set_xlabel("Papers", color=GREY, fontsize=10); ax.set_title("Topic Distribution", color=WHITE, fontsize=13, fontweight="bold", pad=12)
        ax.tick_params(colors=WHITE, labelsize=10); [s.set_color(BORDER) for s in ax.spines.values()]
        ax.set_xlim(0, max(counts)*1.25); plt.tight_layout()
        p = os.path.join(out_dir,"topic_dist.png"); plt.savefig(p,dpi=150,bbox_inches="tight",facecolor=BG); plt.close(); charts["topic"] = p

    # Source donut
    sd = insights.get("source_distribution",{})
    if sd:
        fig, ax = plt.subplots(figsize=(5,5)); fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
        labels = list(sd.keys()); sizes = list(sd.values()); colors = [src_colors.get(l,"#8b949e") for l in labels]
        wedges,texts,autotexts = ax.pie(sizes,labels=labels,autopct="%1.0f%%",colors=colors,pctdistance=0.75,
            wedgeprops={"edgecolor":BG,"linewidth":3,"width":0.5})
        for t in texts: t.set_color(WHITE); t.set_fontsize(12)
        for a in autotexts: a.set_color(WHITE); a.set_fontsize(11)
        ax.set_title("By Source", color=WHITE, fontsize=13, fontweight="bold", pad=12)
        ax.text(0,0,str(sum(sizes)),ha="center",va="center",color=WHITE,fontsize=20,fontweight="bold")
        p = os.path.join(out_dir,"sources.png"); plt.tight_layout(); plt.savefig(p,dpi=150,bbox_inches="tight",facecolor=BG); plt.close(); charts["source"] = p

    # Top papers score
    top = insights.get("top_papers",[])
    if top:
        items = top[:8]; fig,ax = plt.subplots(figsize=(10,5)); fig.patch.set_facecolor(BG); ax.set_facecolor(CARD)
        titles = [p["title"][:45]+"…" if len(p["title"])>45 else p["title"] for p in items]
        scores = [p.get("importance_score",0) for p in items]
        bcolors = [src_colors.get(p.get("source",""),"#8b949e") for p in items]
        bars = ax.barh(range(len(titles)), scores, color=bcolors, edgecolor="none", height=0.55)
        ax.set_yticks(range(len(titles))); ax.set_yticklabels(titles, color=WHITE, fontsize=9)
        for b,s in zip(bars,scores): ax.text(b.get_width()+.05,b.get_y()+b.get_height()/2,f"{s:.1f}",va="center",color=WHITE,fontsize=9)
        ax.set_xlabel("Importance Score",color=GREY,fontsize=10); ax.set_title("Top Papers",color=WHITE,fontsize=13,fontweight="bold",pad=12)
        ax.tick_params(colors=WHITE); [s.set_color(BORDER) for s in ax.spines.values()]
        used_srcs = {p.get("source","") for p in items}
        patches = [mpatches.Patch(color=src_colors.get(k,"#8b949e"),label=k) for k in used_srcs if k]
        ax.legend(handles=patches,facecolor=CARD,labelcolor=WHITE,framealpha=0.9,fontsize=9)
        p = os.path.join(out_dir,"scores.png"); plt.tight_layout(); plt.savefig(p,dpi=150,bbox_inches="tight",facecolor=BG); plt.close(); charts["scores"] = p

    return charts


def generate_report(papers: List[Dict], insights: Dict, charts: Dict, output_path: str):
    date_str  = datetime.now().strftime("%B %d, %Y")
    total     = insights.get("total_papers", len(papers))
    narrative = insights.get("narrative","")
    src_counts = insights.get("source_distribution",{})

    # One badge per source, sorted: NBER first, arXiv last, journals in between
    _order = ["NBER","JF","RFS","JFE","JFQA","MS","AER","QJE","JPE","ReStud","Econometrica","FEDS","IFDP","arXiv"]
    _sorted_sources = [s for s in _order if src_counts.get(s,0)>0] + \
                      [s for s in src_counts if s not in _order and src_counts[s]>0]
    src_badges = " ".join([
        f'<span style="background:{SOURCE_COLORS.get(s,"#8b949e")}22;color:{SOURCE_COLORS.get(s,"#8b949e")};'
        f'padding:3px 10px;border-radius:10px;font-size:12px;font-weight:600;">{s}: {src_counts[s]}</span>'
        for s in _sorted_sources
    ])

    # Topic rows
    topic_rows = ""
    for topic, count in sorted(insights.get("topic_distribution",{}).items(), key=lambda x:-x[1]):
        c = _color(topic); e = _emoji(topic); l = _label(topic)
        topic_rows += f'<div style="display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid #21262d;"><span style="color:#d1d5db;font-size:13px;">{e} {l}</span><span style="background:{c}22;color:{c};padding:1px 9px;border-radius:8px;font-size:12px;font-weight:600;">{count}</span></div>'

    # Paper cards
    sorted_papers = sorted(papers, key=lambda x: x.get("importance_score",0), reverse=True)
    cards = ""
    for paper in sorted_papers[:30]:
        src = paper.get("source","?")
        sc  = SOURCE_COLORS.get(src,"#8b949e")
        pid = str(hash(paper.get("title","") + paper.get("date","")))[-8:]

        topics_html = " ".join([
            f'<span style="background:{_color(t)}22;color:{_color(t)};padding:2px 8px;border-radius:10px;font-size:11px;">{_emoji(t)} {_label(t)}</span>'
            for t in paper.get("matched_topics",[])[:4]
        ])
        cat_html = f'<span style="background:#1f2937;color:#9ca3af;padding:2px 8px;border-radius:10px;font-size:11px;">{paper["primary_category"]}</span>' if paper.get("primary_category") else ""
        score = paper.get("importance_score",0)
        abstract = (paper.get("abstract","") or "")[:280]
        title_safe = paper.get("title","").replace("'","&#39;").replace('"',"&quot;")
        abstract_safe = abstract.replace("'","&#39;").replace('"',"&quot;")

        ai_block = ""
        if paper.get("ai_summary"):
            ai_block = f"""<div style="background:#1a1a2e;border-left:3px solid {sc};padding:14px;margin-top:12px;border-radius:0 8px 8px 0;">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                <div style="color:#8b949e;font-size:11px;letter-spacing:1px;text-transform:uppercase;">AI Analysis (EN / 中文)</div>
                <button onclick="toggleChat('chat-{pid}')" style="background:#e94560;color:white;border:none;padding:5px 14px;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600;">💬 Deep Dive</button>
              </div>
              <div style="color:#c9d1d9;font-size:13px;line-height:1.8;white-space:pre-line;">{paper['ai_summary']}</div>
              <div id="chat-{pid}" style="display:none;margin-top:14px;border-top:1px solid #30363d;padding-top:14px;">
                <div style="color:#f5a623;font-size:12px;margin-bottom:8px;letter-spacing:1px;">ASK GEMINI ABOUT THIS PAPER</div>
                <div id="log-{pid}" style="max-height:300px;overflow-y:auto;margin-bottom:10px;"></div>
                <div style="display:flex;gap:8px;">
                  <input id="inp-{pid}" type="text" placeholder="e.g. 这篇和quantile preference theory有什么联系？"
                    style="flex:1;background:#0d1117;border:1px solid #30363d;color:#f0f6fc;padding:8px 12px;border-radius:6px;font-size:13px;outline:none;"
                    onkeydown="if(event.key==='Enter')sendMsg('{pid}','{title_safe}','{abstract_safe}')">
                  <button onclick="sendMsg('{pid}','{title_safe}','{abstract_safe}')"
                    style="background:#0f3460;color:#58a6ff;border:1px solid #30363d;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px;">Send</button>
                </div>
              </div>
            </div>"""

        cards += f"""<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:20px;margin-bottom:14px;border-left:4px solid {sc};">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <span style="background:{sc}22;color:{sc};padding:3px 10px;border-radius:10px;font-size:12px;font-weight:600;">{src}</span>
            <span style="color:#f5a623;font-size:13px;">⭐ {score:.1f}</span>
          </div>
          <h3 style="margin:6px 0 8px;font-size:15px;line-height:1.4;">
            <a href="{paper.get('url','#')}" target="_blank" style="color:#58a6ff;text-decoration:none;">{paper.get('title','')}</a>
          </h3>
          <div style="color:#8b949e;font-size:12px;margin-bottom:10px;">{paper.get('authors','')[:80]} &nbsp;·&nbsp; {paper.get('date','')}</div>
          <div style="margin-bottom:8px;display:flex;flex-wrap:wrap;gap:4px;">{topics_html} {cat_html}</div>
          <p style="color:#8b949e;font-size:13px;line-height:1.6;margin:0;">{abstract}…</p>
          {ai_block}
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Finance Research Digest — {date_str}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#0d1117;color:#c9d1d9;line-height:1.6}}
  .wrap{{max-width:1120px;margin:0 auto;padding:24px}}
  a{{color:#58a6ff}}
  @media(max-width:700px){{.g2,.g3{{grid-template-columns:1fr!important}}}}
</style>
</head>
<body>
<div class="wrap">

  <div style="text-align:center;padding:44px 0 28px;border-bottom:1px solid #21262d;margin-bottom:28px;">
    <div style="font-size:11px;color:#8b949e;letter-spacing:3px;text-transform:uppercase;margin-bottom:10px;">Daily Research Digest</div>
    <h1 style="font-size:30px;font-weight:700;color:#f0f6fc;margin-bottom:10px;">Finance &amp; Quant Research Intelligence</h1>
    <div style="color:#8b949e;font-size:14px;margin-bottom:14px;">{date_str} &nbsp;·&nbsp; {total} papers &nbsp;·&nbsp; NBER + JF/RFS/JFE/MS/AER/JPE/FEDS + arXiv</div>
    <div style="display:flex;justify-content:center;gap:8px;flex-wrap:wrap;">{src_badges}</div>
  </div>

  <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);border:1px solid #e94560;border-radius:12px;padding:24px;margin-bottom:24px;">
    <div style="color:#e94560;font-size:11px;letter-spacing:2px;text-transform:uppercase;margin-bottom:10px;">AI Research Pulse · Powered by Gemini</div>
    <p style="color:#e2e8f0;font-size:15px;line-height:1.85;">{narrative}</p>
  </div>

  <div class="g2" style="display:grid;grid-template-columns:260px 1fr;gap:18px;margin-bottom:18px;">
    <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:18px;">
      <div style="color:#f0f6fc;font-weight:600;font-size:14px;margin-bottom:14px;">Topics</div>
      {topic_rows}
    </div>
    <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:18px;">{_b64(charts.get("topic",""))}</div>
  </div>

  <div class="g3" style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:18px;margin-bottom:28px;">
    <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:16px;">{_b64(charts.get("source",""))}</div>
    <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:16px;">{_b64(charts.get("scores",""))}</div>
    <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:16px;">
      <div style="color:#f0f6fc;font-weight:600;font-size:14px;margin-bottom:12px;">Today's Sources</div>
      {''.join(f'<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #21262d;"><span style="color:#d1d5db;font-size:13px;">{s}</span><span style="color:#f5a623;font-size:13px;font-weight:600;">{c}</span></div>' for s,c in src_counts.items())}
    </div>
  </div>

  <h2 style="color:#f0f6fc;font-size:19px;margin-bottom:18px;padding-bottom:10px;border-bottom:1px solid #21262d;">Top Papers Today</h2>
  {cards}

  <div style="text-align:center;padding:22px 0;border-top:1px solid #21262d;color:#8b949e;font-size:12px;margin-top:10px;">
    Paper Agent v2 · Gemini AI · NBER + JF/RFS/JFE/JFQA/MS/AER/QJE/JPE/ReStud/Econometrica/FEDS/IFDP + arXiv · {datetime.now().strftime("%Y-%m-%d %H:%M")} Prague
  </div>

</div>

<script>
function toggleChat(id){{
  var el=document.getElementById(id);
  el.style.display=(el.style.display==='none')?'block':'none';
  if(el.style.display==='block'){{
    var pid=id.replace('chat-','');
    document.getElementById('inp-'+pid).focus();
  }}
}}
async function sendMsg(pid,title,abstract){{
  var input=document.getElementById('inp-'+pid);
  var log=document.getElementById('log-'+pid);
  var q=input.value.trim(); if(!q)return;
  input.value='';
  log.innerHTML+='<div style="background:#0f3460;padding:8px 12px;border-radius:6px;margin-bottom:6px;font-size:13px;color:#93c5fd;"><b>You:</b> '+q+'</div>';
  var tid='t'+Date.now();
  log.innerHTML+='<div id="'+tid+'" style="color:#8b949e;font-size:13px;padding:6px 0;">Thinking...</div>';
  log.scrollTop=log.scrollHeight;
  try{{
    var key=document.getElementById('gemini-key').value.trim();
    if(!key){{ document.getElementById(tid).remove(); log.innerHTML+='<div style="color:#e94560;font-size:13px;padding:6px;">请在上方输入 Gemini API Key 才能使用对话功能</div>'; return; }}
    var r=await fetch('https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key='+key,{{
      method:'POST',
      headers:{{'Content-Type':'application/json'}},
      body:JSON.stringify({{contents:[{{parts:[{{text:'You are a research assistant for a quantitative behavioral finance PhD student.\\n\\nPaper: '+title+'\\nAbstract: '+abstract+'\\n\\nQuestion: '+q+'\\n\\nAnswer technically and concisely. Use the same language as the question (Chinese if asked in Chinese).'}}]}}]}})
    }});
    var data=await r.json();
    var ans=(data.candidates&&data.candidates[0])?data.candidates[0].content.parts[0].text:'API error';
    document.getElementById(tid).remove();
    log.innerHTML+='<div style="background:#1a1a2e;padding:10px 12px;border-radius:6px;margin-bottom:8px;font-size:13px;color:#d1d5db;border-left:3px solid #06d6a0;white-space:pre-wrap;"><b style=\\"color:#06d6a0;\\">Gemini:</b> '+ans+'</div>';
  }}catch(e){{
    document.getElementById(tid).remove();
    log.innerHTML+='<div style="color:#e94560;font-size:13px;">Error: '+e.message+'</div>';
  }}
  log.scrollTop=log.scrollHeight;
}}
</script>

<div style="position:fixed;bottom:16px;right:16px;background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px 16px;z-index:999;">
  <div style="color:#8b949e;font-size:11px;margin-bottom:6px;">Gemini API Key (for Deep Dive chat)</div>
  <input id="gemini-key" type="password" placeholder="AIza..." style="background:#0d1117;border:1px solid #30363d;color:#f0f6fc;padding:6px 10px;border-radius:6px;font-size:12px;width:220px;outline:none;">
</div>

</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info(f"Report saved: {output_path}")
    return output_path
