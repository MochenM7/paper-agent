"""
Paper Agent — Main Runner
Daily: NBER + SSRN + arXiv  →  AI summaries  →  HTML report + charts
"""

import json, logging, os, sys, time, shutil, argparse
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from config import REPORT_CONFIG, SCHEDULE_CONFIG, SSRN_CONFIG
from nber_scraper  import NBERScraper
from ssrn_scraper  import SSRNScraper
from arxiv_scraper import ArXivScraper
from ai_processor import PaperProcessor
from report_generator import generate_charts, generate_html_report

# Ensure log dir exists BEFORE FileHandler is created
(BASE_DIR / "logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "logs" / "agent.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("PaperAgent")


# ── main run ──────────────────────────────────────────────────────────────
def run_agent(days_back: int = 7, dry_run: bool = False) -> str:
    logger.info("=" * 60)
    logger.info(f"Paper Agent — {datetime.now():%Y-%m-%d %H:%M}  (days_back={days_back})")
    logger.info("=" * 60)

    all_papers = []

    # ── NBER ──────────────────────────────────────────────────────────── #
    logger.info("\n[1/3] NBER...")
    try:
        nber = NBERScraper()
        nber_papers = nber.fetch_recent_papers(days_back=days_back)
        for p in nber_papers[:30]:
            if not p.get("abstract"):
                p = nber.fetch_paper_details(p)
        all_papers.extend(nber_papers)
        logger.info(f"      NBER: {len(nber_papers)} papers")
    except Exception as e:
        logger.error(f"      NBER failed: {e}")

    # ── SSRN ──────────────────────────────────────────────────────────── #
    logger.info("\n[2/3] SSRN...")
    if not SSRN_CONFIG.get("enabled", True):
        logger.info("      SSRN disabled in config — skipping.")
    else:
        try:
            ssrn = SSRNScraper()
            ssrn_papers = ssrn.fetch_recent_papers(days_back=days_back)
            for p in ssrn_papers[:30]:
                if not p.get("abstract"):
                    p = ssrn.fetch_paper_details(p)
            all_papers.extend(ssrn_papers)
            logger.info(f"      SSRN: {len(ssrn_papers)} papers")
        except Exception as e:
            logger.error(f"      SSRN failed: {e}")

    # ── arXiv ─────────────────────────────────────────────────────────── #
    logger.info("\n[3/3] arXiv...")
    try:
        arxiv = ArXivScraper()
        arxiv_papers = arxiv.fetch_recent_papers(days_back=days_back)
        all_papers.extend(arxiv_papers)
        logger.info(f"      arXiv: {len(arxiv_papers)} papers")
    except Exception as e:
        logger.error(f"      arXiv failed: {e}")

    if not all_papers:
        logger.warning("No papers collected — using demo data")
        all_papers = _demo_papers()

    all_papers = _deduplicate(all_papers)
    logger.info(f"\nTotal unique papers: {len(all_papers)}")

    # ── AI processing ─────────────────────────────────────────────────── #
    limit = REPORT_CONFIG["max_papers_in_report"]
    if not dry_run:
        logger.info("\nAI processing...")
        proc = PaperProcessor()
        all_papers = proc.process_papers(all_papers[:limit])
        insights   = proc.generate_batch_insights(all_papers)
    else:
        logger.info("[DRY RUN] skipping AI")
        insights = _build_insights(all_papers)

    # ── save data ─────────────────────────────────────────────────────── #
    date_str  = datetime.now().strftime("%Y-%m-%d")
    data_path = BASE_DIR / "data" / f"papers_{date_str}.json"
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(
            {"date": date_str,
             "papers": all_papers,
             "insights": {k: v for k, v in insights.items() if k != "top_papers"}},
            f,
            indent=2,
            ensure_ascii=False
        )
    logger.info(f"Data saved: {data_path}")

    # ── charts ────────────────────────────────────────────────────────── #
    charts_dir = BASE_DIR / "charts" / date_str
    charts = generate_charts(insights, str(charts_dir))
    logger.info(f"Generated {len(charts)} charts")

    # ── HTML report ───────────────────────────────────────────────────── #
    report_path = BASE_DIR / "reports" / f"digest_{date_str}.html"
    generate_html_report(all_papers, insights, charts, str(report_path))
    shutil.copy(str(report_path), str(BASE_DIR / "reports" / "latest.html"))

    logger.info(f"\nReport: {report_path}")
    logger.info("=" * 60)
    return str(report_path)


# ── helpers ───────────────────────────────────────────────────────────────
def _deduplicate(papers):
    seen, out = set(), []
    for p in papers:
        key = p.get("title", "").lower()[:60]
        if key and key not in seen:
            seen.add(key)
            out.append(p)
    return out


def _build_insights(papers):
    topic_counts  = {}
    method_counts = {}
    source_counts = {}
    for p in papers:
        for t in p.get("matched_topics", []):
            topic_counts[t]  = topic_counts.get(t, 0) + 1
        for t in p.get("ai_tags", []):
            method_counts[t] = method_counts.get(t, 0) + 1
        src = p.get("source", "?")
        source_counts[src] = source_counts.get(src, 0) + 1
    sorted_p = sorted(papers, key=lambda x: x.get("importance_score", 0), reverse=True)
    return {
        "topic_distribution":  topic_counts,
        "method_distribution": method_counts,
        "source_distribution": source_counts,
        "top_papers":          sorted_p[:5],
        "narrative":           "Demo mode — AI narrative disabled. Run without --dry-run for full analysis.",
        "total_papers":        len(papers),
    }


def _demo_papers():
    return [
        {"source":"NBER","title":"Attention Mechanisms and Cross-Sectional Return Predictability",
         "authors":"J. Smith, L. Chen","abstract":"We apply transformer attention to measure time-varying investor attention and show it predicts cross-sectional returns. Stocks with high attention earn significant alphas after controlling for known factors. The effect is strongest for retail-dominated stocks, consistent with behavioral theories of limited attention and salience.",
         "url":"https://www.nber.org/papers/w11111","date":"2025-07-20",
         "matched_topics":["behavioral_finance","asset_pricing","nlp_finance"],"relevance_score":3},
        {"source":"SSRN","title":"Quantile Sentiment and Tail Risk in Equity Markets",
         "authors":"M. Zhang, S. Park","abstract":"We develop a quantile-based framework linking sentiment-induced belief distortions to tail risk premia. Using diagnostic expectations, we show that sentiment shifts the quantile preference parameters asymmetrically, generating excess skewness in the cross-section. Empirically, quantile-sentiment factors earn significant risk-adjusted returns.",
         "url":"https://papers.ssrn.com/abstract=22222","date":"2025-07-19",
         "matched_topics":["behavioral_finance","asset_pricing","tail_risk"],"relevance_score":3},
        {"source":"arXiv","title":"Reinforcement Learning for Optimal Execution in Limit Order Books",
         "authors":"A. Wang, B. Kumar","abstract":"We formulate optimal trade execution as a Markov Decision Process and train deep RL agents on a realistic LOB simulator. Our agent outperforms TWAP/VWAP benchmarks by 15 bps on average while controlling market impact. We analyze the learned policy through attention visualization.",
         "url":"https://arxiv.org/abs/2507.12345","date":"2025-07-18",
         "categories":["q-fin.TR","cs.LG"],"primary_category":"q-fin.TR",
         "matched_topics":["quant_trading","market_microstructure"],"relevance_score":2},
        {"source":"NBER","title":"Gender Diversity and Corporate Innovation: Causal Evidence",
         "authors":"E. Johnson, R. Davis","abstract":"Using board gender quota legislation as a natural experiment, we identify the causal effect of female board representation on corporate innovation. Firms with more female directors file significantly more patents and adopt longer investment horizons. Effects are stronger in male-dominated industries.",
         "url":"https://www.nber.org/papers/w33333","date":"2025-07-17",
         "matched_topics":["gender_finance","corporate_finance"],"relevance_score":2},
        {"source":"SSRN","title":"CEO Overconfidence, Capital Structure, and Financial Distress",
         "authors":"T. Lee, H. Park","abstract":"We construct a CEO overconfidence measure from option exercise behavior and show overconfident CEOs use more debt. This over-leverage increases financial distress probability by 23% in our sample. The effect is attenuated by strong board oversight and institutional monitoring.",
         "url":"https://papers.ssrn.com/abstract=44444","date":"2025-07-16",
         "matched_topics":["behavioral_finance","corporate_finance"],"relevance_score":2},
        {"source":"arXiv","title":"Deep Learning for Factor Zoo: Neural Alpha Prediction",
         "authors":"Y. Liu, X. Zhang","abstract":"We train a deep neural network on 200+ firm characteristics to predict monthly returns. Using feature importance from SHAP values, we identify the top predictive signals and construct neural alpha factors. Out-of-sample Sharpe ratio reaches 2.1 with modest transaction costs.",
         "url":"https://arxiv.org/abs/2507.56789","date":"2025-07-15",
         "categories":["q-fin.PM","cs.LG"],"primary_category":"q-fin.PM",
         "matched_topics":["asset_pricing","quant_trading","nlp_finance"],"relevance_score":3},
        {"source":"NBER","title":"LLM Earnings Call Analysis and Subsequent Stock Returns",
         "authors":"P. Brown, M. Chen","abstract":"We apply GPT-4 to analyze 50,000 earnings call transcripts and extract sentiment, uncertainty, and topic exposure. LLM-extracted signals predict next-quarter returns with a t-stat of 4.2. The predictability is concentrated in periods of high retail investor attention.",
         "url":"https://www.nber.org/papers/w55555","date":"2025-07-14",
         "matched_topics":["nlp_finance","asset_pricing","behavioral_finance"],"relevance_score":3},
        {"source":"SSRN","title":"Statistical Arbitrage with Machine Learning: A Systematic Review",
         "authors":"K. White, J. Lee","abstract":"We survey 200 machine learning approaches to statistical arbitrage, documenting performance decay over time. Long-only ML strategies retain alpha longer than long-short strategies. We provide a meta-analysis of feature importance across studies.",
         "url":"https://papers.ssrn.com/abstract=66666","date":"2025-07-13",
         "matched_topics":["quant_trading","asset_pricing"],"relevance_score":2},
    ]


# ── scheduler ─────────────────────────────────────────────────────────────
def schedule_daily():
    try:
        import schedule
    except ImportError:
        logger.error("pip install schedule")
        return

    def job():
        try:
            run_agent(days_back=1)
        except Exception as e:
            logger.error(f"Scheduled run failed: {e}")

    run_time = SCHEDULE_CONFIG["run_time"]
    schedule.every().day.at(run_time).do(job)
    logger.info(f"Scheduler: daily at {run_time} Prague time")
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Finance Paper Agent")
    p.add_argument("--mode",  choices=["run","schedule","demo"], default="run")
    p.add_argument("--days",  type=int, default=7)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    for d in ["logs","data","reports","charts"]:
        (BASE_DIR / d).mkdir(exist_ok=True)

    if args.mode == "schedule":
        schedule_daily()
    elif args.mode == "demo":
        run_agent(days_back=args.days, dry_run=True)
    else:
        run_agent(days_back=args.days, dry_run=args.dry_run)
