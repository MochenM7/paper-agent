"""
Configuration for Paper Agent
Fetches papers from NBER, SSRN, and arXiv across behavioral finance,
asset pricing, corporate finance, gender economics, and quant trading.
"""

# ============================================================
# TOPICS OF INTEREST
# ============================================================
TOPICS = {
    "behavioral_finance": [
        "behavioral finance", "investor sentiment", "market sentiment",
        "overconfidence", "loss aversion", "prospect theory",
        "attention allocation", "limited attention", "salience",
        "extrapolation", "belief formation", "diagnostic expectations",
        "anchoring", "herding", "disposition effect", "narrative finance",
        "investor psychology", "retail investor", "household finance"
    ],
    "asset_pricing": [
        "asset pricing", "risk premium", "factor model", "anomaly",
        "cross-sectional returns", "time-series predictability",
        "expected returns", "momentum", "value premium",
        "machine learning asset pricing", "neural network returns",
        "quantile regression finance", "stochastic discount factor",
        "no-arbitrage", "option pricing", "variance risk premium"
    ],
    "market_microstructure": [
        "market microstructure", "price discovery", "liquidity",
        "high frequency trading", "order flow", "informed trading",
        "insider trading", "information asymmetry", "bid-ask spread",
        "dark pool", "market making", "adverse selection"
    ],
    "nlp_finance": [
        "text analysis finance", "NLP finance", "LLM finance",
        "language model asset pricing", "transformer finance",
        "sentiment analysis stock", "news and returns", "ChatGPT finance",
        "large language model investment", "GPT stock prediction",
        "earnings call NLP", "10-K text analysis"
    ],
    "tail_risk": [
        "tail risk", "downside risk", "crash risk", "volatility risk",
        "conditional value at risk", "extreme returns", "skewness premium",
        "jump risk", "rare disaster", "left tail", "systemic risk"
    ],
    "corporate_finance": [
        "corporate finance", "capital structure", "CEO", "board of directors",
        "managerial incentives", "executive compensation", "M&A",
        "mergers and acquisitions", "corporate governance", "firm investment",
        "dividend policy", "payout policy", "IPO", "seasoned equity offering",
        "debt financing", "financial constraints", "cash holdings",
        "corporate debt", "credit risk", "default risk", "bankruptcy",
        "private equity", "venture capital", "financial distress"
    ],
    "gender_finance": [
        "gender finance", "gender gap", "female CEO", "women board",
        "gender diversity", "glass ceiling", "gender discrimination",
        "female executives", "gender pay gap", "gender investment",
        "women entrepreneurship", "gender bias finance", "female investor",
        "gender and risk", "maternity leave firm", "gender board diversity",
        "racial diversity board", "diversity inclusion finance"
    ],
    "quant_trading": [
        "quantitative trading", "algorithmic trading", "systematic trading",
        "backtesting", "trading strategy", "alpha generation",
        "machine learning trading", "reinforcement learning trading",
        "deep learning portfolio", "factor investing", "smart beta",
        "statistical arbitrage", "pairs trading", "mean reversion strategy",
        "trend following", "CTA", "risk parity", "portfolio optimization",
        "dynamic asset allocation", "execution algorithm", "market impact",
        "transaction costs", "Kelly criterion", "Sharpe ratio optimization",
        "neural network trading", "LSTM forecasting returns",
        "gradient boosting finance", "random forest stock selection"
    ],
}

# Flatten all keywords
ALL_KEYWORDS = [kw for kws in TOPICS.values() for kw in kws]

# Topic display metadata (for UI/charts)
TOPIC_META = {
    "behavioral_finance":   {"emoji": "🧠", "color": "#e94560", "short": "Behavioral"},
    "asset_pricing":        {"emoji": "📈", "color": "#00b4d8", "short": "Asset Pricing"},
    "market_microstructure":{"emoji": "⚡", "color": "#f5a623", "short": "Microstructure"},
    "nlp_finance":          {"emoji": "🤖", "color": "#06d6a0", "short": "NLP/LLM"},
    "tail_risk":            {"emoji": "⚠️",  "color": "#ff6b6b", "short": "Tail Risk"},
    "corporate_finance":    {"emoji": "🏢", "color": "#7b2d8b", "short": "Corp Finance"},
    "gender_finance":       {"emoji": "⚖️",  "color": "#ff9f43", "short": "Gender"},
    "quant_trading":        {"emoji": "🔢", "color": "#45b7d1", "short": "Quant Trading"},
}

# ============================================================
# NBER SETTINGS
# ============================================================
NBER_CONFIG = {
    "base_url": "https://www.nber.org",
    # Program codes: AP=Asset Pricing, CF=Corporate Finance,
    # ME=Monetary Economics, IFM=Intl Finance, LS=Labor Studies (for gender)
    "programs": ["AP", "CF", "ME", "IFM", "LS", "IO"],
    "max_papers_per_run": 60,
}

# ============================================================
# SSRN SETTINGS
# ============================================================
SSRN_CONFIG = {
    "enabled": False,                  # 彻底不用 SSRN
    "skip_on_github_actions": True,
    "search_url": "https://papers.ssrn.com/sol3/results.cfm",
    "max_papers_per_run": 60,
    "search_queries": [
        "behavioral finance sentiment investor",
        "asset pricing machine learning anomaly",
        "LLM NLP large language model finance",
        "tail risk skewness downside returns",
        "corporate governance CEO compensation",
        "gender diversity board female executive",
        "quantitative trading algorithmic strategy",
        "transformer attention mechanism returns",
        "quantile regression asset pricing",
        "high frequency trading market microstructure",
        "reinforcement learning portfolio optimization",
        "factor investing smart beta systematic",
    ],
}

# ============================================================
# ARXIV SETTINGS
# ============================================================
ARXIV_CONFIG = {
    "base_url": "https://arxiv.org",
    "api_url": "https://export.arxiv.org/api/query",
    "max_papers_per_run": 60,
    # arXiv categories relevant to finance/quant
    "categories": ["q-fin", "cs.LG", "stat.ML", "econ.GN"],
    # Search queries for arXiv
    "search_queries": [
        # Quant trading & ML
        "ti:\"reinforcement learning\" AND ti:\"trading\"",
        "ti:\"deep learning\" AND ti:\"asset pricing\"",
        "ti:\"transformer\" AND ti:\"financial\"",
        "ti:\"LLM\" AND ti:\"stock\" OR ti:\"portfolio\"",
        "ti:\"machine learning\" AND ti:\"factor\"",
        "ti:\"neural network\" AND ti:\"return prediction\"",
        # Behavioral / sentiment
        "ti:\"sentiment\" AND ti:\"stock returns\"",
        "ti:\"investor attention\" AND ti:\"market\"",
        # Corporate / gender
        "ti:\"corporate\" AND ti:\"machine learning\"",
        "ti:\"gender\" AND ti:\"finance\" OR ti:\"investment\"",
    ],
    # q-fin subcategory codes
    "qfin_cats": [
        "q-fin.TR",   # Trading and Market Microstructure
        "q-fin.PM",   # Portfolio Management
        "q-fin.RM",   # Risk Management
        "q-fin.ST",   # Statistical Finance
        "q-fin.GN",   # General Finance
        "q-fin.CP",   # Computational Finance
    ],
}

# ============================================================
# AI SETTINGS (Claude API)
# ============================================================
AI_CONFIG = {
    # Gemini 省钱优先：flash-lite（如果报 model not found，改成 "gemini-2.0-flash"）
    "model": "gemini-2.0-flash-lite",

    # 省钱关键：不要 2000，双语结构 250~400 已经够用
    "max_tokens": 350,

    # 省钱关键：每天只给 Top N 篇调用 AI（其余跳过）
    "max_ai_papers": 10,

    # 更稳定、更少胡写
    "temperature": 0.2,

    "summary_prompt": """You are a research assistant for a PhD student in quantitative behavioral finance.

Given this paper, provide a BILINGUAL structured analysis (English first, then Chinese for each section):

Title: {title}
Authors: {authors}
Source: {source}
Abstract: {abstract}

---
**Abstract / 摘要**
[Plain-language English summary, 2-3 sentences, no jargon]

【中文摘要】
[同上，自然学术中文，2-3句]

---
**Core Contribution / 核心贡献**
[2-3 sentences English]

【核心贡献】
[2-3句中文]

---
**Methodology / 方法论**
[Data, model, identification — 1-2 sentences English]

【方法论】
[1-2句中文]

---
**Key Results / 主要发现**
• [Result 1]
• [Result 2]
• [Result 3]

【主要发现】
• [发现1]
• [发现2]
• [发现3]

---
**Relevance & Open Question / 相关性与开放问题**
[Connection to behavioral finance / asset pricing / quant trading / gender/corporate finance + one open question]

【相关性与开放问题】
[中文版]

Be precise and technical. Keep Chinese academic and natural, not machine-translated.""",

    "narrative_prompt": """You are a research intelligence assistant for a quantitative behavioral finance PhD student.

Today's paper collection covers these topics: {topics}
Total papers: {total}

Top papers today:
{paper_list}

In 4-5 sentences, synthesize: What are the most active research frontiers today? 
Which methodological approaches are gaining traction? 
Are there any emerging intersections between quant trading and behavioral/corporate finance?
Keep it sharp and insightful — the reader is a PhD student who publishes in top finance journals.""",
}

# ============================================================
# IMPORTANCE SCORING BOOSTS
# ============================================================
IMPORTANCE_BOOSTS = {
    # Dissertation-relevant intersections
    "quantile + behavioral":    ("quantile", "behavioral_finance", 3.0),
    "transformer + finance":    ("transformer", "asset_pricing", 2.5),
    "LLM + returns":            ("language model", "nlp_finance", 2.0),
    "RL + trading":             ("reinforcement learning", "quant_trading", 2.5),
    "gender + corporate":       ("gender", "corporate_finance", 2.0),
    "tail + sentiment":         ("tail risk", "behavioral_finance", 2.5),
    "ML + factor":              ("machine learning", "asset_pricing", 2.0),
}

# ============================================================
# REPORT SETTINGS
# ============================================================
REPORT_CONFIG = {
    "output_dir": "reports",
    "charts_dir": "charts",
    "data_dir": "data",
    "max_papers_in_report": 30,
    "report_format": "html",
}

# ============================================================
# SCHEDULE
# ============================================================
SCHEDULE_CONFIG = {
    "run_time": "08:00",
    "timezone": "Europe/Prague",
}
