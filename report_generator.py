"""
Report Generator
Creates HTML reports with matplotlib charts from processed papers.
Covers: behavioral finance, asset pricing, corporate finance, gender, quant trading, arXiv.
"""

import json, os, logging, base64
from datetime import datetime
from typing import List, Dict

from config import REPORT_CONFIG, TOPIC_META

logger = logging.getLogger(__name__)


# ── helpers ──────────────────────────────────────────────────────────────
def _b64_img(path: str) -> str:
    if path and os.path.exists(path):
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/png;base64,{data}" style="width:100%;border-radius:8px;">'
    return '<p style="color:#555;text-align:center;padding:20px;">Chart unavailable</p>'


def _topic_color(topic: str) -> str:
    return TOPIC_META.get(topic, {}).get("color", "#8b949e")

def _topic_emoji(topic: str) -> str:
    return TOPIC_META.get(topic, {}).get("emoji", "📌")

def _topic_label(topic: str) -> str:
    return TOPIC_META.get(topic, {}).get("short", topic.replace("_", " ").title())


# ── chart generation ─────────────────────────────────────────────────────
def generate_charts(insights: Dict, output_dir: str) -> Dict[str, str]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        import numpy as np
    except ImportError:
        logger.warning("matplotlib not available")
        return {}

    os.makedirs(output_dir, exist_ok=True)
    charts = {}

    DARK_BG   = "#0d1117"
    CARD_BG   = "#161b22"
    BORDER    = "#30363d"
    WHITE     = "#f0f6fc"
    GREY      = "#8b949e"

    topic_colors = {t: m["color"] for t, m in TOPIC_META.items()}

    # ── 1. Topic distribution (horizontal bar) ──────────────────────────
    topic_data = insights.get("topic_distribution", {})
    if topic_data:
        fig, ax = plt.subplots(figsize=(9, 5))
        fig.patch.set_facecolor(DARK_BG)
        ax.set_facecolor(CARD_BG)

        topics = sorted(topic_data.items(), key=lambda x: -x[1])
        labels = [_topic_label(t) for t, _ in topics]
        counts = [c for _, c in topics]
        colors = [topic_colors.get(t, "#60a5fa") for t, _ in topics]

        bars = ax.barh(labels, counts, color=colors, edgecolor="none", height=0.6)
        for bar, val in zip(bars, counts):
            ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height()/2,
                    str(val), va="center", color=WHITE, fontsize=10, fontweight="bold")

        ax.set_xlabel("Papers", color=GREY, fontsize=10)
        ax.set_title("Research Topic Distribution", color=WHITE, fontsize=13, fontweight="bold", pad=12)
        ax.tick_params(colors=WHITE, labelsize=10)
        for spine in ax.spines.values(): spine.set_color(BORDER)
        ax.set_xlim(0, max(counts) * 1.25)
        ax.set_facecolor(CARD_BG)

        plt.tight_layout()
        p = os.path.join(output_dir, "topic_distribution.png")
        plt.savefig(p, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
        plt.close(); charts["topic_distribution"] = p

    # ── 2. Source breakdown (donut) ──────────────────────────────────────
    source_data = insights.get("source_distribution", {})
    if source_data:
        fig, ax = plt.subplots(figsize=(6, 6))
        fig.patch.set_facecolor(DARK_BG)
        ax.set_facecolor(DARK_BG)

        src_colors = {"NBER": "#e94560", "SSRN": "#00b4d8", "arXiv": "#f5a623"}
        labels = list(source_data.keys())
        sizes  = list(source_data.values())
        colors = [src_colors.get(l, "#8b949e") for l in labels]

        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, autopct="%1.0f%%",
            colors=colors, pctdistance=0.75,
            wedgeprops={"edgecolor": DARK_BG, "linewidth": 3, "width": 0.5}
        )
        for t in texts:    t.set_color(WHITE); t.set_fontsize(12)
        for a in autotexts: a.set_color(WHITE); a.set_fontsize(11)

        ax.set_title("Papers by Source", color=WHITE, fontsize=13, fontweight="bold", pad=12)
        total = sum(sizes)
        ax.text(0, 0, str(total), ha="center", va="center",
                color=WHITE, fontsize=20, fontweight="bold")

        p = os.path.join(output_dir, "source_breakdown.png")
        plt.tight_layout()
        plt.savefig(p, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
        plt.close(); charts["source_breakdown"] = p

    # ── 3. Top papers importance scores ─────────────────────────────────
    top_papers = insights.get("top_papers", [])
    if top_papers:
        items = top_papers[:8]
        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_facecolor(DARK_BG)
        ax.set_facecolor(CARD_BG)

        titles  = [p["title"][:42] + "…" if len(p["title"]) > 42 else p["title"] for p in items]
        scores  = [p.get("importance_score", 0) for p in items]
        sources = [p.get("source", "?") for p in items]
        src_colors = {"NBER": "#e94560", "SSRN": "#00b4d8", "arXiv": "#f5a623"}
        bar_colors = [src_colors.get(s, "#8b949e") for s in sources]

        bars = ax.barh(range(len(titles)), scores, color=bar_colors, edgecolor="none", height=0.55)
        ax.set_yticks(range(len(titles)))
        ax.set_yticklabels(titles, color=WHITE, fontsize=9)
        for bar, score in zip(bars, scores):
            ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height()/2,
                    f"{score:.1f}", va="center", color=WHITE, fontsize=9)

        ax.set_xlabel("Importance Score", color=GREY, fontsize=10)
        ax.set_title("Top Papers by Relevance", color=WHITE, fontsize=13, fontweight="bold", pad=12)
        ax.tick_params(colors=WHITE)
        for spine in ax.spines.values(): spine.set_color(BORDER)

        patches = [mpatches.Patch(color=v, label=k) for k, v in src_colors.items()]
        ax.legend(handles=patches, facecolor=CARD_BG, labelcolor=WHITE,
                  framealpha=0.9, fontsize=9)

        plt.tight_layout()
        p = os.path.join(output_dir, "paper_scores.png")
        plt.savefig(p, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
        plt.close(); charts["paper_scores"] = p

    # ── 4. Method tags (horizontal bar) ──────────────────────────────────
    method_data = insights.get("method_distribution", {})
    if method_data:
        method_colors = {
            "machine_learning":  "#06d6a0", "empirical":         "#00b4d8",
            "theoretical":       "#7b2d8b", "text_analysis":     "#f5a623",
            "high_frequency":    "#e94560", "portfolio_methods": "#45b7d1",
            "causal_inference":  "#ff9f43",
        }
        fig, ax = plt.subplots(figsize=(8, 4))
        fig.patch.set_facecolor(DARK_BG)
        ax.set_facecolor(CARD_BG)

        items   = sorted(method_data.items(), key=lambda x: -x[1])[:8]
        labels  = [k.replace("_", " ").title() for k, _ in items]
        counts  = [v for _, v in items]
        colors  = [method_colors.get(k, "#8b949e") for k, _ in items]

        bars = ax.barh(labels, counts, color=colors, edgecolor="none", height=0.55)
        for bar, val in zip(bars, counts):
            ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height()/2,
                    str(val), va="center", color=WHITE, fontsize=10)

        ax.set_xlabel("Papers", color=GREY, fontsize=10)
        ax.set_title("Methodology Tags", color=WHITE, fontsize=13, fontweight="bold", pad=12)
        ax.tick_params(colors=WHITE, labelsize=10)
        for spine in ax.spines.values(): spine.set_color(BORDER)

        plt.tight_layout()
        p = os.path.join(output_dir, "method_tags.png")
        plt.savefig(p, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
        plt.close(); charts["method_tags"] = p

    logger.info(f"Generated {len(charts)} charts in {output_dir}")
    return charts


# ── HTML report ───────────────────────────────────────────────────────────
def generate_html_report(papers: List[Dict], insights: Dict, charts: Dict, output_path: str):
    date_str   = datetime.now().strftime("%B %d, %Y")
    total      = insights.get("total_papers", len(papers))
    narrative  = insights.get("narrative", "")
    src_counts = insights.get("source_distribution", {})

    # Source badges
    src_badge = " ".join([
        f'<span style="background:{c}22;color:{c};padding:3px 10px;border-radius:10px;font-size:12px;font-weight:600;">'
        f'{s}: {src_counts.get(s,0)}</span>'
        for s, c in [("NBER","#e94560"), ("SSRN","#00b4d8"), ("arXiv","#f5a623")]
        if src_counts.get(s, 0) > 0
    ])

    # Paper cards
    sorted_papers = sorted(papers, key=lambda x: x.get("importance_score", 0), reverse=True)
    cards_html = ""
    for paper in sorted_papers[:30]:
        source = paper.get("source", "?")
        src_color = {"NBER": "#e94560", "SSRN": "#00b4d8", "arXiv": "#f5a623"}.get(source, "#8b949e")

        topics_html = " ".join([
            f'<span style="background:{_topic_color(t)}22;color:{_topic_color(t)};'
            f'padding:2px 8px;border-radius:10px;font-size:11px;">'
            f'{_topic_emoji(t)} {_topic_label(t)}</span>'
            for t in paper.get("matched_topics", [])[:4]
        ])

        cats_html = ""
        if paper.get("primary_category"):
            cats_html = f'<span style="background:#1f2937;color:#9ca3af;padding:2px 8px;border-radius:10px;font-size:11px;">{paper["primary_category"]}</span>'

        ai_block = ""
        if paper.get("ai_summary"):
            paper_id = paper.get("id", "").replace("/","-") or str(hash(paper["title"]))[:8]
            ai_block = f"""
            <div style="background:#1a1a2e;border-left:3px solid {src_color};padding:14px;
                        margin-top:12px;border-radius:0 8px 8px 0;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                  <div style="color:#8b949e;font-size:11px;letter-spacing:1px;text-transform:uppercase;">
                    AI Analysis (EN / 中文)
                  </div>
                  <button onclick="toggleChat('chat-{paper_id}')"
                    style="background:#e94560;color:white;border:none;padding:5px 14px;
                           border-radius:6px;cursor:pointer;font-size:12px;font-weight:600;">
                    &#128172; Deep Dive
                  </button>
                </div>
                <div style="color:#c9d1d9;font-size:13px;line-height:1.8;white-space:pre-line;">{paper['ai_summary']}</div>
                <div id="chat-{paper_id}" style="display:none;margin-top:14px;border-top:1px solid #30363d;padding-top:14px;">
                  <div style="color:#f5a623;font-size:12px;margin-bottom:8px;letter-spacing:1px;">ASK AI ABOUT THIS PAPER</div>
                  <div id="chatlog-{paper_id}" style="max-height:300px;overflow-y:auto;margin-bottom:10px;"></div>
                  <div style="display:flex;gap:8px;">
                    <input id="input-{paper_id}" type="text" placeholder="e.g. How does this relate to quantile preference theory?"
                      style="flex:1;background:#0d1117;border:1px solid #30363d;color:#f0f6fc;
                             padding:8px 12px;border-radius:6px;font-size:13px;outline:none;"
                      onkeydown="if(event.key==='Enter')sendMsg('{paper_id}',
                        {repr(paper.get('title',[]))},
                        {repr((paper.get('abstract',[]) or '')[:800])})">
                    <button onclick="sendMsg('{paper_id}',
                        {repr(paper.get('title',[]))},
                        {repr((paper.get('abstract',[]) or '')[:800])})"
                      style="background:#0f3460;color:#58a6ff;border:1px solid #30363d;
                             padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px;">Send</button>
                  </div>
                </div>
            </div>"""

        abstract = paper.get("abstract", "No abstract")[:280]
        score    = paper.get("importance_score", 0)

        cards_html += f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:20px;
                    margin-bottom:14px;border-left:4px solid {src_color};">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <span style="background:{src_color}22;color:{src_color};padding:3px 10px;
                         border-radius:10px;font-size:12px;font-weight:600;">{source}</span>
            <span style="color:#f5a623;font-size:13px;">&#11088; {score:.1f}</span>
          </div>
          <h3 style="margin:6px 0 8px;font-size:15px;line-height:1.4;">
            <a href="{paper.get('url','#')}" target="_blank"
               style="color:#58a6ff;text-decoration:none;">{paper['title']}</a>
          </h3>
          <div style="color:#8b949e;font-size:12px;margin-bottom:10px;">
            {paper.get('authors','')[:80]} &nbsp;·&nbsp; {paper.get('date','')}</div>
          <div style="margin-bottom:8px;display:flex;flex-wrap:wrap;gap:4px;">{topics_html} {cats_html}</div>
          <p style="color:#8b949e;font-size:13px;line-height:1.6;margin:0;">{abstract}…</p>
          {ai_block}
        </div>"""

    # Topic stat rows
    topic_rows = ""
    for topic, count in sorted(insights.get("topic_distribution", {}).items(), key=lambda x: -x[1]):
        color = _topic_color(topic)
        emoji = _topic_emoji(topic)
        label = _topic_label(topic)
        topic_rows += f"""
        <div style="display:flex;justify-content:space-between;align-items:center;
                    padding:7px 0;border-bottom:1px solid #21262d;">
          <span style="color:#d1d5db;font-size:13px;">{emoji} {label}</span>
          <span style="background:{color}22;color:{color};padding:1px 9px;
                       border-radius:8px;font-size:12px;font-weight:600;">{count}</span>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Finance Research Digest — {date_str}</title>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
          background:#0d1117; color:#c9d1d9; line-height:1.6; }}
  .wrap {{ max-width:1120px; margin:0 auto; padding:24px; }}
  a {{ color:#58a6ff; }}
  @media(max-width:700px) {{ .grid2,.grid3 {{ grid-template-columns:1fr !important; }} }}
</style>
</head>
<body>
<div class="wrap">

  <!-- Header -->
  <div style="text-align:center;padding:44px 0 28px;border-bottom:1px solid #21262d;margin-bottom:28px;">
    <div style="font-size:11px;color:#8b949e;letter-spacing:3px;text-transform:uppercase;margin-bottom:10px;">
      Daily Research Digest
    </div>
    <h1 style="font-size:30px;font-weight:700;color:#f0f6fc;margin-bottom:10px;">
      Finance &amp; Quant Research Intelligence
    </h1>
    <div style="color:#8b949e;font-size:14px;margin-bottom:14px;">
      {date_str} &nbsp;·&nbsp; {total} papers &nbsp;·&nbsp; NBER + SSRN + arXiv
    </div>
    <div style="display:flex;justify-content:center;gap:8px;flex-wrap:wrap;">{src_badge}</div>
  </div>

  <!-- AI Narrative -->
  <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);
              border:1px solid #e94560;border-radius:12px;padding:24px;margin-bottom:24px;">
    <div style="color:#e94560;font-size:11px;letter-spacing:2px;text-transform:uppercase;margin-bottom:10px;">
      AI Research Pulse
    </div>
    <p style="color:#e2e8f0;font-size:15px;line-height:1.85;">{narrative}</p>
  </div>

  <!-- Stats + Topic Chart -->
  <div class="grid2" style="display:grid;grid-template-columns:260px 1fr;gap:18px;margin-bottom:18px;">
    <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:18px;">
      <div style="color:#f0f6fc;font-weight:600;font-size:14px;margin-bottom:14px;">Topics</div>
      {topic_rows}
    </div>
    <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:18px;">
      {_b64_img(charts.get("topic_distribution",""))}
    </div>
  </div>

  <!-- 3-col charts -->
  <div class="grid3" style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:18px;margin-bottom:28px;">
    <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:16px;">
      {_b64_img(charts.get("source_breakdown",""))}
    </div>
    <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:16px;">
      {_b64_img(charts.get("paper_scores",""))}
    </div>
    <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:16px;">
      {_b64_img(charts.get("method_tags",""))}
    </div>
  </div>

  <!-- Papers -->
  <h2 style="color:#f0f6fc;font-size:19px;margin-bottom:18px;padding-bottom:10px;
             border-bottom:1px solid #21262d;">
    Top Papers Today
  </h2>
  {cards_html}

  <!-- Footer -->
  <div style="text-align:center;padding:22px 0;border-top:1px solid #21262d;
              color:#8b949e;font-size:12px;margin-top:10px;">
    Paper Agent · Claude AI · Sources: NBER + SSRN + arXiv · {datetime.now().strftime("%Y-%m-%d %H:%M")} Prague
  </div>

</div>

  <!-- Deep-dive chat JS -->
  <script>
  function toggleChat(id) {{
    var el = document.getElementById(id);
    el.style.display = (el.style.display === 'none') ? 'block' : 'none';
    if (el.style.display === 'block') {{
      document.getElementById('input-' + id.replace('chat-','')).focus();
    }}
  }}

  async function sendMsg(paperId, title, abstract) {{
    var input = document.getElementById('input-' + paperId);
    var log   = document.getElementById('chatlog-' + paperId);
    var question = input.value.trim();
    if (!question) return;
    input.value = '';
    log.innerHTML += '<div style="background:#0f3460;padding:8px 12px;border-radius:6px;margin-bottom:6px;font-size:13px;color:#93c5fd;"><b>You:</b> ' + question + '</div>';
    log.scrollTop = log.scrollHeight;
    var thinkId = 'think-' + Date.now();
    log.innerHTML += '<div id="' + thinkId + '" style="color:#8b949e;font-size:13px;padding:6px 0;">Thinking...</div>';
    log.scrollTop = log.scrollHeight;
    try {{
      var res = await fetch('https://api.anthropic.com/v1/messages', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{
          model: 'claude-sonnet-4-20250514',
          max_tokens: 1000,
          messages: [{{
            role: 'user',
            content: 'You are a research assistant for a quantitative behavioral finance PhD student.\n\nPaper: ' + title + '\nAbstract: ' + abstract + '\n\nStudent question: ' + question + '\n\nAnswer concisely and technically. If the question is about methodology or relevance to the student own research, be especially detailed. Answer in the same language the question is asked (Chinese if asked in Chinese, English if in English).'
          }}]
        }})
      }});
      var data = await res.json();
      var answer = (data.content && data.content[0]) ? data.content[0].text : 'API error.';
      document.getElementById(thinkId).remove();
      log.innerHTML += '<div style="background:#1a1a2e;padding:10px 12px;border-radius:6px;margin-bottom:8px;font-size:13px;color:#d1d5db;border-left:3px solid #06d6a0;white-space:pre-wrap;"><b style=\"color:#06d6a0;\">AI:</b> ' + answer + '</div>';
    }} catch(e) {{
      document.getElementById(thinkId).remove();
      log.innerHTML += '<div style="color:#e94560;font-size:13px;padding:6px 0;">Error: ' + e.message + '</div>';
    }}
    log.scrollTop = log.scrollHeight;
  }}
  </script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info(f"Report saved: {output_path}")
    return output_path
