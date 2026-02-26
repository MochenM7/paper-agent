"""
AI Processor — Google Gemini
"""

import requests
import os
import logging
import time
from typing import List, Dict, Optional
from config import GEMINI_CONFIG, TOPICS

logger = logging.getLogger(__name__)


class GeminiProcessor:

    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY", "")
        self.api_url = GEMINI_CONFIG["api_url"]
        self.model   = GEMINI_CONFIG["model"]

    def process_papers(self, papers: List[Dict]) -> List[Dict]:
    if not self.api_key:
        logger.error("GEMINI_API_KEY not set — skipping AI processing")
        for p in papers:
            p["ai_summary"] = None
            p["importance_score"] = self._score(p)
        return papers

    # Select top 2 papers per topic to minimize API calls
    selected_ids = set()
    topic_counts = {}
    sorted_papers = sorted(papers, key=lambda x: x.get("relevance_score", 0), reverse=True)
    
    for p in sorted_papers:
        for topic in p.get("matched_topics", []):
            if topic_counts.get(topic, 0) < 2:
                selected_ids.add(id(p))
                topic_counts[topic] = topic_counts.get(topic, 0) + 1

    logger.info(f"Selected {len(selected_ids)}/{len(papers)} papers for AI analysis")

    out = []
    for p in papers:
        if id(p) in selected_ids:
            logger.info(f"AI: {p['title'][:55]}...")
            try:
                p = self._process_one(p)
            except Exception as e:
                logger.error(f"Failed: {e}")
                p["ai_summary"] = None
                p["importance_score"] = self._score(p)
            time.sleep(5)
        else:
            p["ai_summary"] = None
            p["importance_score"] = self._score(p)
        out.append(p)
    return out

    def _process_one(self, paper: Dict) -> Dict:
        abstract = paper.get("abstract", "")
        if not abstract or len(abstract) < 50:
            paper["ai_summary"] = None
            paper["importance_score"] = self._score(paper)
            return paper

        prompt = GEMINI_CONFIG["summary_prompt"].format(
            title=paper.get("title", ""),
            authors=paper.get("authors", ""),
            source=paper.get("source", ""),
            abstract=abstract[:2000],
        )
        response = self._call(prompt)
        if response:
            paper["ai_summary"] = response
            paper["ai_tags"] = self._extract_tags(response, paper)
        else:
            paper["ai_summary"] = None
            paper["ai_tags"] = []
        paper["importance_score"] = self._score(paper)
        return paper

    def _call(self, prompt: str) -> Optional[str]:
        try:
            url = f"{self.api_url}?key={self.api_key}"
            r = requests.post(url,
                json={"contents": [{"parts": [{"text": prompt}]}],
                      "generationConfig": {"maxOutputTokens": GEMINI_CONFIG["max_tokens"]}},
                timeout=30)
            if r.status_code == 200:
                data = r.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            else:
                logger.error(f"Gemini {r.status_code}: {r.text[:200]}")
                return None
        except Exception as e:
            logger.error(f"Gemini call failed: {e}")
            return None

    def _extract_tags(self, summary: str, paper: Dict) -> List[str]:
        tags = []
        text = f"{paper.get('abstract','')} {summary}".lower()
        method_map = {
            "machine_learning":  ["machine learning","neural network","deep learning","transformer","llm","gpt","reinforcement learning","gradient boosting"],
            "empirical":         ["regression","panel data","fixed effects","instrumental variable","difference-in-differences"],
            "theoretical":       ["equilibrium","theorem","proof","proposition"],
            "text_analysis":     ["nlp","text analysis","sentiment","language model","topic model"],
            "high_frequency":    ["high frequency","intraday","order flow","microstructure"],
            "portfolio_methods": ["portfolio optimization","sharpe","alpha","backt","factor","risk parity"],
            "causal_inference":  ["causal","regression discontinuity","natural experiment"],
        }
        for tag, kws in method_map.items():
            if any(k in text for k in kws):
                tags.append(tag)
        tags.extend(paper.get("matched_topics", []))
        return list(set(tags))

    def _score(self, paper: Dict) -> float:
        score = paper.get("relevance_score", 0) * 1.5
        topics = paper.get("matched_topics", [])
        tags   = paper.get("ai_tags", [])
        text   = f"{paper.get('title','')} {paper.get('abstract','')}".lower()

        if "nlp_finance" in topics and "asset_pricing" in topics: score += 3.0
        if "behavioral_finance" in topics and "machine_learning" in tags: score += 2.0
        if "tail_risk" in topics and "behavioral_finance" in topics: score += 2.5
        if "quant_trading" in topics and ("machine_learning" in tags or "nlp_finance" in topics): score += 2.5
        if "gender_finance" in topics and "corporate_finance" in topics: score += 2.0

        for kw, boost in {"quantile":2.0,"transformer":2.0,"reinforcement learning":2.5,
                          "sentiment":1.5,"llm":2.0,"gender":1.5,"factor model":1.5,
                          "deep learning":1.5,"diagnostic":1.5}.items():
            if kw in text:
                score += boost; break

        if paper.get("source") == "arXiv":
            if any(c.startswith("q-fin") for c in paper.get("categories",[])):
                score += 1.0
        return round(score, 2)

    def generate_insights(self, papers: List[Dict]) -> Dict:
        topic_counts  = {}
        method_counts = {}
        source_counts = {}
        for p in papers:
            for t in p.get("matched_topics", []):
                topic_counts[t]  = topic_counts.get(t, 0)  + 1
            for t in p.get("ai_tags", []):
                method_counts[t] = method_counts.get(t, 0) + 1
            src = p.get("source","?")
            source_counts[src] = source_counts.get(src, 0) + 1

        sorted_p  = sorted(papers, key=lambda x: x.get("importance_score",0), reverse=True)
        top       = sorted_p[:5]
        paper_list = "\n".join(f"- [{p.get('source','?')}] {p['title']}" for p in sorted_p[:12])
        topic_str  = ", ".join(f"{t.replace('_',' ').title()} ({c})"
                               for t,c in sorted(topic_counts.items(), key=lambda x:-x[1]))

        narrative = self._call(GEMINI_CONFIG["narrative_prompt"].format(
            topics=topic_str, total=len(papers), paper_list=paper_list))

        return {
            "topic_distribution":  topic_counts,
            "method_distribution": method_counts,
            "source_distribution": source_counts,
            "top_papers":          top,
            "narrative":           narrative or "Analysis unavailable.",
            "total_papers":        len(papers),
        }
