"""
Paper Agent v2 — Config
Sources: NBER RSS + SSRN RSS + arXiv API
AI: Google Gemini
"""

# ── Topics & Keywords ─────────────────────────────────────────────────────
TOPICS = {
    "behavioral_finance": [
        "behavioral finance", "investor sentiment", "overconfidence",
        "loss aversion", "prospect theory", "limited attention", "salience",
        "diagnostic expectations", "herding", "disposition effect",
        "anchoring", "belief formation", "extrapolation", "narrative finance",
    ],
    "asset_pricing": [
        "asset pricing", "risk premium", "factor model", "anomaly",
        "cross-sectional returns", "return predictability", "expected returns",
        "momentum", "value premium", "machine learning asset pricing",
        "stochastic discount factor", "option pricing", "variance risk premium",
    ],
    "market_microstructure": [
        "market microstructure", "price discovery", "liquidity",
        "high frequency trading", "order flow", "informed trading",
        "insider trading", "information asymmetry", "bid-ask spread",
    ],
    "nlp_finance": [
        "text analysis finance", "NLP finance", "LLM finance",
        "language model", "transformer finance", "sentiment analysis stock",
        "earnings call", "ChatGPT finance", "GPT stock",
        "large language model investment",
    ],
    "tail_risk": [
        "tail risk", "downside risk", "crash risk", "volatility risk",
        "conditional value at risk", "extreme returns", "skewness premium",
        "jump risk", "rare disaster", "systemic risk",
    ],
    "corporate_finance": [
        "corporate finance", "capital structure", "CEO", "board of directors",
        "executive compensation", "M&A", "mergers acquisitions",
        "corporate governance", "firm investment", "dividend policy",
        "IPO", "private equity", "venture capital", "financial distress",
    ],
    "gender_finance": [
        "gender finance", "female CEO", "women board", "gender diversity",
        "glass ceiling", "gender discrimination", "female executives",
        "gender pay gap", "women entrepreneurship", "gender bias",
        "diversity inclusion finance", "board diversity",
    ],
    "quant_trading": [
        "quantitative trading", "algorithmic trading", "systematic trading",
        "backtesting", "alpha generation", "machine learning trading",
        "reinforcement learning trading", "deep learning portfolio",
        "factor investing", "smart beta", "statistical arbitrage",
        "pairs trading", "mean reversion", "trend following",
        "portfolio optimization", "neural network trading",
        "LSTM forecasting", "gradient boosting finance",
    ],
}

ALL_KEYWORDS = [kw for kws in TOPICS.values() for kw in kws]

TOPIC_META = {
    "behavioral_finance":    {"emoji": "🧠", "color": "#e94560"},
    "asset_pricing":         {"emoji": "📈", "color": "#00b4d8"},
    "market_microstructure": {"emoji": "⚡", "color": "#f5a623"},
    "nlp_finance":           {"emoji": "🤖", "color": "#06d6a0"},
    "tail_risk":             {"emoji": "⚠️",  "color": "#ff6b6b"},
    "corporate_finance":     {"emoji": "🏢", "color": "#a855f7"},
    "gender_finance":        {"emoji": "⚖️",  "color": "#ff9f43"},
    "quant_trading":         {"emoji": "🔢", "color": "#45b7d1"},
}

# ── Sources ───────────────────────────────────────────────────────────────
NBER_RSS_FEEDS = [
    "https://www.nber.org/rss/new.xml",       # All new Working Papers
    "https://www.nber.org/rss/newap.xml",     # Asset Pricing
    "https://www.nber.org/rss/newcf.xml",     # Corporate Finance
    "https://www.nber.org/rss/newme.xml",     # Monetary Economics
    "https://www.nber.org/rss/newls.xml",     # Labor Studies (gender)
    "https://www.nber.org/rss/newefg.xml",    # Economic Fluctuations & Growth
]

SSRN_RSS_FEEDS = [
    "https://papers.ssrn.com/rss/harg.xml?TOPIC_ID=50208",
    "https://papers.ssrn.com/rss/harg.xml?TOPIC_ID=50209",
]

ARXIV_CATS = [
    "q-fin.TR",  # Trading & Microstructure
    "q-fin.PM",  # Portfolio Management
    "q-fin.RM",  # Risk Management
    "q-fin.ST",  # Statistical Finance
    "q-fin.GN",  # General Finance
    "q-fin.CP",  # Computational Finance
]

# Top Journal RSS Feeds
JOURNAL_RSS_FEEDS = [
    # Finance Top 3
    ("JF",   "https://onlinelibrary.wiley.com/feed/15406261/most-recent"),
    ("JFE",  "https://rss.sciencedirect.com/publication/science/0304405X"),
    ("RFS",  "https://academic.oup.com/rss/site_6122/advanceAccess_6122.xml"),
    # Econ Top 5
    ("AER",  "https://www.aeaweb.org/journals/aer/feed"),
    ("QJE",  "https://academic.oup.com/rss/site_5333/advanceAccess_5333.xml"),
    ("JPE",  "https://www.journals.uchicago.edu/action/showFeed?type=etoc&feed=rss&jc=jpe"),
    ("REStud", "https://academic.oup.com/rss/site_5388/advanceAccess_5388.xml"),
    ("ECMA", "https://onlinelibrary.wiley.com/feed/14680262/most-recent"),
    # Quant/Behavioral
    ("JFQA", "https://www.cambridge.org/core/rss/product/id/6E5C92C81DB3C28B8E59BFF22E9C78FB"),
    ("MS",   "https://pubsonline.informs.org/action/showFeed?type=etoc&feed=rss&jc=mnsc"),
]

# ── Gemini AI ─────────────────────────────────────────────────────────────
GEMINI_CONFIG = {
    "model": "gemini-2.0-flash",
    "api_url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
    "max_tokens": 2000,
    "summary_prompt": """You are a research assistant for a PhD student in quantitative behavioral finance at Charles University Prague.

Analyze this paper with bilingual output (English + Chinese for each section):

Title: {title}
Authors: {authors}
Source: {source}
Abstract: {abstract}

---
**Abstract / 摘要**
[2-3 sentence plain English summary]

【中文摘要】
[2-3句学术中文]

---
**Core Contribution / 核心贡献**
[2-3 sentences English]

【核心贡献】
[2-3句中文]

---
**Methodology / 方法论**
[Data, model, identification — 1-2 sentences]

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

Be precise and technical. Natural academic Chinese, not machine-translated.""",

    "narrative_prompt": """You are a research intelligence assistant for a quantitative behavioral finance PhD student who publishes in top finance journals (JF, RFS, JFE, Management Science).

Today's paper collection:
Topics covered: {topics}
Total papers: {total}

Top papers:
{paper_list}

In 4-5 sentences, synthesize: What are the most active research frontiers today? Which methodological approaches are gaining traction? Any emerging intersections between quant trading, LLMs, and behavioral/corporate finance worth noting?

Be sharp, insightful, and technical — like a senior colleague summarizing the day's arXiv digest.""",
}

# ── Report ────────────────────────────────────────────────────────────────
REPORT_CONFIG = {
    "max_papers": 30,
    "output_dir": "reports",
    "charts_dir": "charts",
    "data_dir":   "data",
}
