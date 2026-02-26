"""
AI Paper Processor
Uses Gemini API (google-genai) to generate structured summaries of academic papers
"""

import logging
import time
from typing import List, Dict, Optional

from config import AI_CONFIG, TOPICS  # TOPICS 如果你其他地方用到就留着

logger = logging.getLogger(__name__)

try:
    from google import genai
    from google.genai import types
except Exception:
    genai = None
    types = None


class PaperProcessor:
    """Processes papers with Gemini AI to generate summaries and insights"""

    def __init__(self):
        # ---- Cost control knobs (默认省钱) ----
        self.model = AI_CONFIG.get("model", "gemini-2.0-flash-lite")
        self.max_tokens = int(AI_CONFIG.get("max_tokens", 250))          # 摘要长度，越小越省
        self.temperature = float(AI_CONFIG.get("temperature", 0.2))
        self.max_ai_papers = int(AI_CONFIG.get("max_ai_papers", 10))     # 每天只AI处理Top N篇

        self.client = None
        self.ai_disabled = False

        if genai is None:
            logger.error("google-genai not installed. Run: pip install google-genai")
            self.ai_disabled = True
            return

        import os
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            logger.error("GEMINI_API_KEY not set")
            self.ai_disabled = True
            return

        # 显式传 key（比依赖默认读取更稳）
        self.client = genai.Client(api_key=api_key)

    def process_papers(self, papers: List[Dict]) -> List[Dict]:
        if not papers:
            return []

        # 先按 relevance_score 排序，Top N 才调用 AI（省钱/省额度）
        papers_sorted = sorted(papers, key=lambda x: x.get("relevance_score", 0), reverse=True)
        top_ai = papers_sorted[: self.max_ai_papers]

        processed = []
        for i, paper in enumerate(papers_sorted):
            logger.info(f"Processing {i+1}/{len(papers_sorted)}: {paper.get('title','')[:60]}...")

            # 非Top N：直接跳过AI
            if paper not in top_ai:
                paper["ai_summary"] = None
                paper["ai_note"] = f"Skipped AI to save cost (top {self.max_ai_papers} only)"
                paper["importance_score"] = self._score_importance(paper)
                processed.append(paper)
                continue

            try:
                enhanced = self._process_single_paper(paper)
                processed.append(enhanced)
                time.sleep(0.2)  # 稍微放慢一点，避免触发速率限制
            except Exception as e:
                logger.error(f"Failed to process paper: {e}")
                paper["ai_summary"] = None
                paper["ai_error"] = str(e)
                paper["importance_score"] = self._score_importance(paper)
                processed.append(paper)

        return processed

    def _process_single_paper(self, paper: Dict) -> Dict:
        title = paper.get("title", "Unknown Title")
        authors = paper.get("authors", "Unknown Authors")
        abstract = paper.get("abstract", "")
        source = paper.get("source", "?")

        if not abstract or len(abstract) < 50:
            paper["ai_summary"] = None
            paper["ai_note"] = "Abstract too short"
            paper["importance_score"] = self._score_importance(paper)
            return paper

        prompt = AI_CONFIG["summary_prompt"].format(
            title=title,
            authors=authors,
            source=source,
            abstract=abstract[:2000],
        )

        response = self._call_gemini(prompt)

        if response:
            paper["ai_summary"] = response
            paper["ai_tags"] = self._extract_tags(response, paper)
        else:
            paper["ai_summary"] = None

        paper["importance_score"] = self._score_importance(paper)
        return paper

    def _call_gemini(self, prompt: str) -> Optional[str]:
        if self.ai_disabled or self.client is None:
            return None

        try:
            resp = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=self.max_tokens,
                    temperature=self.temperature,
                    candidate_count=1,
                ),
            )
            text = getattr(resp, "text", None)
            if text:
                return text.strip()
            return None

        except Exception as e:
            # 常见：额度/限流/模型名不对等。这里不让程序炸。
            logger.error(f"Gemini call failed: {e}")
            return None

    def _extract_tags(self, summary: str, paper: Dict) -> List[str]:
        tags = []
        methods = {
            "machine_learning": ["machine learning", "neural network", "deep learning",
                                 "transformer", "BERT", "GPT", "LLM", "gradient boosting",
                                 "random forest", "XGBoost", "reinforcement learning"],
            "empirical": ["regression", "panel data", "fixed effects", "OLS",
                          "IV", "instrumental variable", "DID", "propensity score"],
            "theoretical": ["model", "equilibrium", "theorem", "proof", "proposition"],
            "text_analysis": ["NLP", "text analysis", "sentiment", "language model",
                              "topic model", "word embedding"],
            "high_frequency": ["high frequency", "intraday", "order flow", "microstructure"],
            "portfolio_methods": ["portfolio optimization", "mean-variance", "factor", "backtest",
                                  "Sharpe", "alpha", "risk parity"],
            "causal_inference": ["causal", "instrumental variable", "regression discontinuity",
                                 "difference-in-differences", "natural experiment"],
        }
        full_text = f"{paper.get('abstract', '')} {summary}".lower()
        for tag, keywords in methods.items():
            if any(kw.lower() in full_text for kw in keywords):
                tags.append(tag)
        tags.extend(paper.get("matched_topics", []))
        return list(set(tags))

    def _score_importance(self, paper: Dict) -> float:
        score = 0.0
        topics = paper.get("matched_topics", [])
        tags = paper.get("ai_tags", [])
        full_text = f"{paper.get('title','').lower()} {paper.get('abstract','').lower()}"

        score += paper.get("relevance_score", 0) * 1.5

        if "nlp_finance" in topics and "asset_pricing" in topics:
            score += 3.0
        if "behavioral_finance" in topics and "machine_learning" in tags:
            score += 2.0
        if "tail_risk" in topics and "behavioral_finance" in topics:
            score += 2.5
        if "quant_trading" in topics and ("machine_learning" in tags or "nlp_finance" in topics):
            score += 2.5
        if "gender_finance" in topics and "corporate_finance" in topics:
            score += 2.0

        kw_boosts = {
            "quantile": 2.0, "transformer": 2.0, "reinforcement learning": 2.5,
            "sentiment": 1.5, "attention mechanism": 2.0, "diagnostic": 1.5,
            "gender": 1.5, "female ceo": 2.0, "corporate governance": 1.5,
            "llm": 2.0, "gpt": 1.5, "factor model": 1.5, "anomaly": 1.5,
            "deep learning": 1.5, "neural network": 1.5,
        }
        for kw, boost in kw_boosts.items():
            if kw in full_text:
                score += boost
                break

        if paper.get("source") == "arXiv":
            if any(str(c).startswith("q-fin") for c in paper.get("categories", [])):
                score += 1.0

        return round(score, 2)

    def generate_batch_insights(self, papers: List[Dict]) -> Dict:
        if not papers:
            return {}

        topic_counts = {}
        method_counts = {}
        source_counts = {}

        for paper in papers:
            for topic in paper.get("matched_topics", []):
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
            for tag in paper.get("ai_tags", []):
                method_counts[tag] = method_counts.get(tag, 0) + 1
            src = paper.get("source", "?")
            source_counts[src] = source_counts.get(src, 0) + 1

        sorted_papers = sorted(papers, key=lambda x: x.get("importance_score", 0), reverse=True)
        top_papers = sorted_papers[:5]

        paper_list = "\n".join([f"- [{p.get('source','?')}] {p['title']}" for p in sorted_papers[:12]])
        topic_summary = ", ".join([
            f"{t.replace('_',' ').title()} ({c})"
            for t, c in sorted(topic_counts.items(), key=lambda x: -x[1])
        ])

        narrative_prompt = AI_CONFIG["narrative_prompt"].format(
            topics=topic_summary, total=len(papers), paper_list=paper_list,
        )
        narrative = self._call_gemini(narrative_prompt)

        return {
            "topic_distribution": topic_counts,
            "method_distribution": method_counts,
            "source_distribution": source_counts,
            "top_papers": top_papers,
            "narrative": narrative or "Analysis unavailable",
            "total_papers": len(papers),
        }
