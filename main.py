"""
Paper Agent v2 — Main
NBER RSS + SSRN RSS + arXiv → Gemini AI → HTML Report
"""

import json, logging, os, shutil, argparse
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(BASE / "logs" / "agent.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("PaperAgent")

from rss_scraper import fetch_nber, fetch_ssrn
from arxiv_scraper import fetch_arxiv
from gemini_processor import GeminiProcessor
from report_generator import generate_charts, generate_report


def run(days_back: int = 7, dry_run: bool = False):
    logger.info("=" * 60)
    logger.info(f"Paper Agent v2 — {datetime.now():%Y-%m-%d %H:%M}  days_back={days_back}")
    logger.info("=" * 60)

    all_papers = []

   # ── NBER RSS ──────────────────────────────────────────────
    logger.info("[1/4] NBER RSS...")
    try:
        p = fetch_nber(days_back); all_papers.extend(p)
        logger.info(f"      NBER: {len(p)} papers")
    except Exception as e:
        logger.error(f"      NBER failed: {e}")

    # ── SSRN RSS ──────────────────────────────────────────────
    logger.info("[2/4] SSRN RSS...")
    try:
        p = fetch_ssrn(days_back); all_papers.extend(p)
        logger.info(f"      SSRN: {len(p)} papers")
    except Exception as e:
        logger.error(f"      SSRN failed: {e}")

    # ── Top Journals ──────────────────────────────────────────
    logger.info("[3/4] Top Journals (JF/JFE/RFS/AER/QJE/JPE/JFQA/MS)...")
    try:
        from rss_scraper import fetch_journals
        p = fetch_journals(days_back); all_papers.extend(p)
        logger.info(f"      Journals: {len(p)} papers")
    except Exception as e:
        logger.error(f"      Journals failed: {e}")

    # ── arXiv ─────────────────────────────────────────────────
    logger.info("[4/4] arXiv...")
    try:
        p = fetch_arxiv(days_back); all_papers.extend(p)
        logger.info(f"      arXiv: {len(p)} papers")
    except Exception as e:
        logger.error(f"      arXiv failed: {e}")

    if not all_papers:
        logger.warning("No papers — using demo data")
        all_papers = _demo()

    # Deduplicate
    seen, uniq = set(), []
    for p in all_papers:
        k = p.get("title","").lower()[:60]
        if k and k not in seen:
            seen.add(k); uniq.append(p)
    all_papers = uniq
    logger.info(f"Total unique: {len(all_papers)}")

    # ── AI Processing ─────────────────────────────────────────
    proc = GeminiProcessor()
    if not dry_run:
        all_papers = proc.process_papers(all_papers[:30])
    else:
        for p in all_papers:
            p["ai_summary"] = None
            p["importance_score"] = proc._score(p)
        logger.info("[DRY RUN] skipped AI")

    insights = proc.generate_insights(all_papers) if not dry_run else _basic_insights(all_papers)

    # ── Save & Report ─────────────────────────────────────────
    date_str = datetime.now().strftime("%Y-%m-%d")

    data_path = BASE / "data" / f"papers_{date_str}.json"
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump({"date": date_str, "papers": all_papers,
                   "insights": {k:v for k,v in insights.items() if k!="top_papers"}},
                  f, indent=2, ensure_ascii=False)

    charts_dir = BASE / "charts" / date_str
    charts = generate_charts(insights, str(charts_dir))

    report_path = BASE / "reports" / f"digest_{date_str}.html"
    generate_report(all_papers, insights, charts, str(report_path))
    shutil.copy(str(report_path), str(BASE / "reports" / "latest.html"))

    logger.info(f"Done → {report_path}")
    return str(report_path)


def _basic_insights(papers):
    tc, sc = {}, {}
    for p in papers:
        for t in p.get("matched_topics",[]): tc[t] = tc.get(t,0)+1
        src = p.get("source","?"); sc[src] = sc.get(src,0)+1
    sp = sorted(papers, key=lambda x: x.get("importance_score",0), reverse=True)
    return {"topic_distribution":tc,"method_distribution":{},"source_distribution":sc,
            "top_papers":sp[:5],"narrative":"Demo mode — run without --dry-run for AI analysis.",
            "total_papers":len(papers)}


def _demo():
    return [
        {"source":"NBER","title":"Transformer Attention and Cross-Sectional Return Predictability",
         "authors":"J. Smith, L. Chen","abstract":"We apply transformer attention mechanisms to measure time-varying investor attention and demonstrate predictability in cross-sectional returns. Stocks with elevated attention earn significant alphas after controlling for known risk factors.",
         "url":"https://nber.org","date":"2026-02-26","matched_topics":["behavioral_finance","asset_pricing","nlp_finance"],"relevance_score":3},
        {"source":"SSRN","title":"Quantile Sentiment and Tail Risk Premia",
         "authors":"M. Zhang, S. Park","abstract":"We develop a quantile-based framework linking sentiment-induced belief distortions to tail risk premia. Diagnostic expectations shift quantile preference parameters asymmetrically, generating excess skewness in the cross-section.",
         "url":"https://ssrn.com","date":"2026-02-26","matched_topics":["behavioral_finance","asset_pricing","tail_risk"],"relevance_score":3},
        {"source":"arXiv","title":"Reinforcement Learning for Optimal Execution","authors":"A. Wang",
         "abstract":"We train deep RL agents on a realistic limit order book simulator. Our agent outperforms TWAP/VWAP benchmarks by 15 bps on average while controlling market impact.",
         "url":"https://arxiv.org","date":"2026-02-26","categories":["q-fin.TR","cs.LG"],"primary_category":"q-fin.TR",
         "matched_topics":["quant_trading","market_microstructure"],"relevance_score":2},
        {"source":"NBER","title":"Gender Diversity and Corporate Innovation: Causal Evidence",
         "authors":"E. Johnson","abstract":"Using board gender quota legislation as a natural experiment, we identify the causal effect of female board representation on corporate innovation. Firms with more female directors file significantly more patents.",
         "url":"https://nber.org","date":"2026-02-26","matched_topics":["gender_finance","corporate_finance"],"relevance_score":2},
        {"source":"arXiv","title":"Deep Learning for Factor Zoo: Neural Alpha Prediction","authors":"Y. Liu",
         "abstract":"We train a deep neural network on 200+ firm characteristics to predict monthly returns. Out-of-sample Sharpe ratio reaches 2.1 with modest transaction costs.",
         "url":"https://arxiv.org","date":"2026-02-26","categories":["q-fin.PM","cs.LG"],"primary_category":"q-fin.PM",
         "matched_topics":["asset_pricing","quant_trading"],"relevance_score":3},
    ]


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["run","demo"], default="run")
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    for d in ["logs","data","reports","charts"]:
        (BASE / d).mkdir(exist_ok=True)

    if args.mode == "demo":
        run(days_back=args.days, dry_run=True)
    else:
        run(days_back=args.days, dry_run=args.dry_run)
