"""
AI Paper Processor
Uses Claude API to generate structured summaries of academic papers
"""

import requests
import json
import logging
import time
from typing import List, Dict, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import AI_CONFIG, TOPICS

logger = logging.getLogger(__name__)


class PaperProcessor:
    """Processes papers with Claude AI to generate summaries and insights"""

    def __init__(self):
        self.api_url = "https://api.anthropic.com/v1/messages"
        self.model = AI_CONFIG["model"]
        self.max_tokens = AI_CONFIG["max_tokens"]

    def process_papers(self, papers: List[Dict]) -> List[Dict]:
        processed = []
        for i, paper in enumerate(papers):
            logger.info(f"Processing {i+1}/{len(papers)}: {paper['title'][:60]}...")
            try:
                enhanced = self._process_single_paper(paper)
                processed.append(enhanced)
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Failed to process paper: {e}")
                paper["ai_summary"] = None
                paper["ai_error"] = str(e)
                processed.append(paper)
        return processed

    def _process_single_paper(self, paper: Dict) -> Dict:
        title    = paper.get("title", "Unknown Title")
        authors  = paper.get("authors", "Unknown Authors")
        abstract = paper.get("abstract", "")
        source   = paper.get("source", "?")

        if not abstract or len(abstract) < 50:
            paper["ai_summary"] = None
            paper["ai_note"] = "Abstract too short"
            return paper

        prompt = AI_CONFIG["summary_prompt"].format(
            title=title, authors=authors,
            source=source, abstract=abstract[:2000]
        )
        response = self._call_claude_api(prompt)

        if response:
            paper["ai_summary"] = response
            paper["ai_tags"]    = self._extract_tags(response, paper)
            paper["importance_score"] = self._score_importance(paper)
        else:
            paper["ai_summary"] = None
            paper["importance_score"] = self._score_importance(paper)
        return paper

    def _call_claude_api(self, prompt: str) -> Optional[str]:
        try:
            response = requests.post(
                self.api_url,
                headers={"Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "max_tokens": self.max_tokens,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=30
            )
            if response.status_code == 200:
                return response.json()["content"][0]["text"]
            else:
                logger.error(f"Claude API {response.status_code}: {response.text[:200]}")
                return None
        except Exception as e:
            logger.error(f"API call failed: {e}")
            return None

    def _extract_tags(self, summary: str, paper: Dict) -> List[str]:
        tags = []
        methods = {
            "machine_learning":     ["machine learning", "neural network", "deep learning",
                                     "transformer", "BERT", "GPT", "LLM", "gradient boosting",
                                     "random forest", "XGBoost", "reinforcement learning"],
            "empirical":            ["regression", "panel data", "fixed effects", "OLS",
                                     "IV", "instrumental variable", "DID", "propensity score"],
            "theoretical":          ["model", "equilibrium", "theorem", "proof", "proposition"],
            "text_analysis":        ["NLP", "text analysis", "sentiment", "language model",
                                     "topic model", "word embedding"],
            "high_frequency":       ["high frequency", "intraday", "order flow", "microstructure"],
            "portfolio_methods":    ["portfolio optimization", "mean-variance", "factor", "backtest",
                                     "Sharpe", "alpha", "risk parity"],
            "causal_inference":     ["causal", "instrumental variable", "regression discontinuity",
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
        topics   = paper.get("matched_topics", [])
        tags     = paper.get("ai_tags", [])
        full_text = f"{paper.get('title','').lower()} {paper.get('abstract','').lower()}"

        score += paper.get("relevance_score", 0) * 1.5

        # High-value intersections
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

        # Keyword boosts (first match only)
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

        # arXiv q-fin bonus
        if paper.get("source") == "arXiv":
            if any(c.startswith("q-fin") for c in paper.get("categories", [])):
                score += 1.0

        return round(score, 2)

    def generate_batch_insights(self, papers: List[Dict]) -> Dict:
        if not papers:
            return {}

        topic_counts  = {}
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
        top_papers    = sorted_papers[:5]

        paper_list    = "\n".join([
            f"- [{p.get('source','?')}] {p['title']}" for p in sorted_papers[:12]
        ])
        topic_summary = ", ".join([
            f"{t.replace('_',' ').title()} ({c})"
            for t, c in sorted(topic_counts.items(), key=lambda x: -x[1])
        ])

        narrative_prompt = AI_CONFIG["narrative_prompt"].format(
            topics=topic_summary, total=len(papers), paper_list=paper_list,
        )
        narrative = self._call_claude_api(narrative_prompt)

        return {
            "topic_distribution":  topic_counts,
            "method_distribution": method_counts,
            "source_distribution": source_counts,
            "top_papers":          top_papers,
            "narrative":           narrative or "Analysis unavailable",
            "total_papers":        len(papers),
        }
