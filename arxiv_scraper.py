"""
arXiv Paper Scraper
Uses arXiv's Atom API to fetch recent papers in q-fin, cs.LG, stat.ML
arXiv API docs: https://arxiv.org/help/api/
"""

import requests
import time
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict

from config import ARXIV_CONFIG, TOPICS

logger = logging.getLogger(__name__)

# arXiv Atom namespace
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


class ArXivScraper:
    """
    Scrapes arXiv using the official Atom API.
    Focuses on q-fin.* categories plus ML/stat papers mentioning finance.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "PaperAgent/1.0 (PhD Research)"})
        self.api_url = ARXIV_CONFIG["api_url"]

    # ------------------------------------------------------------------ #
    def fetch_recent_papers(self, days_back: int = 7) -> List[Dict]:
        all_papers: List[Dict] = []
        seen_ids: set = set()

        # ── 1. Fetch by q-fin subcategories ──────────────────────────── #
        for cat in ARXIV_CONFIG["qfin_cats"]:
            papers = self._fetch_by_category(cat, max_results=40)
            for p in papers:
                if p["id"] not in seen_ids:
                    seen_ids.add(p["id"])
                    all_papers.append(p)
            time.sleep(0.4)

        # ── 2. Keyword searches across cs.LG + stat.ML ──────────────── #
        ml_queries = [
            "ti:transformer AND ti:stock",
            "ti:reinforcement learning AND ti:trading",
            "ti:deep learning AND ti:portfolio",
            "ti:LSTM AND ti:financial",
            "ti:LLM AND ti:finance",
            "ti:neural AND ti:asset pricing",
            "ti:machine learning AND ti:factor",
            "ti:gender AND ti:finance",
            "ti:CEO AND ti:corporate",
        ]
        for q in ml_queries:
            papers = self._search(q, categories=["cs.LG", "stat.ML", "econ.GN", "q-fin.GN"],
                                  max_results=15)
            for p in papers:
                if p["id"] not in seen_ids:
                    seen_ids.add(p["id"])
                    all_papers.append(p)
            time.sleep(0.4)

        # ── 3. Filter by recency ─────────────────────────────────────── #
        cutoff = datetime.utcnow() - timedelta(days=days_back)
        recent = [p for p in all_papers if self._parse_date(p.get("date", "")) >= cutoff]

        # ── 4. Filter by relevance ───────────────────────────────────── #
        relevant = self._filter_relevant(recent or all_papers)
        logger.info(f"arXiv: {len(all_papers)} total → {len(recent)} recent → {len(relevant)} relevant")
        return relevant[:ARXIV_CONFIG["max_papers_per_run"]]

    # ------------------------------------------------------------------ #
    def _fetch_by_category(self, category: str, max_results: int = 40) -> List[Dict]:
        """Fetch latest papers in an arXiv category."""
        params = {
            "search_query": f"cat:{category}",
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": max_results,
        }
        return self._query(params)

    def _search(self, query: str, categories: List[str], max_results: int = 20) -> List[Dict]:
        """Full-text / title search optionally restricted to categories."""
        cat_filter = " OR ".join(f"cat:{c}" for c in categories)
        full_query = f"({query}) AND ({cat_filter})"
        params = {
            "search_query": full_query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": max_results,
        }
        return self._query(params)

    def _query(self, params: dict) -> List[Dict]:
        """Execute arXiv API query and parse Atom response."""
        try:
            resp = self.session.get(self.api_url, params=params, timeout=20)
            if resp.status_code != 200:
                logger.warning(f"arXiv API {resp.status_code}: {resp.text[:200]}")
                return []
            return self._parse_atom(resp.text)
        except Exception as e:
            logger.warning(f"arXiv query failed: {e}")
            return []

    # ------------------------------------------------------------------ #
    def _parse_atom(self, xml_text: str) -> List[Dict]:
        """Parse Atom XML into paper dicts."""
        papers = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logger.error(f"XML parse error: {e}")
            return []

        for entry in root.findall("atom:entry", NS):
            try:
                arxiv_id_url = entry.findtext("atom:id", "", NS)
                arxiv_id = arxiv_id_url.split("/abs/")[-1].strip()

                title = entry.findtext("atom:title", "", NS).strip().replace("\n", " ")
                summary = entry.findtext("atom:summary", "", NS).strip().replace("\n", " ")
                published = entry.findtext("atom:published", "", NS)[:10]  # YYYY-MM-DD

                authors = [
                    a.findtext("atom:name", "", NS)
                    for a in entry.findall("atom:author", NS)
                ]

                categories = [
                    tag.get("term", "")
                    for tag in entry.findall("atom:category", NS)
                ]
                primary_cat = categories[0] if categories else ""

                paper = {
                    "source": "arXiv",
                    "id": arxiv_id,
                    "title": title,
                    "authors": ", ".join(authors[:5]),  # cap at 5
                    "abstract": summary,
                    "url": f"https://arxiv.org/abs/{arxiv_id}",
                    "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}",
                    "date": published,
                    "categories": categories,
                    "primary_category": primary_cat,
                }
                papers.append(paper)
            except Exception as e:
                logger.debug(f"Entry parse error: {e}")

        return papers

    # ------------------------------------------------------------------ #
    def _filter_relevant(self, papers: List[Dict]) -> List[Dict]:
        relevant = []
        for paper in papers:
            text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()

            matched_topics = []
            for topic, keywords in TOPICS.items():
                if any(kw.lower() in text for kw in keywords):
                    matched_topics.append(topic)

            # Always keep core q-fin papers
            is_qfin = any(c.startswith("q-fin") for c in paper.get("categories", []))
            if matched_topics or is_qfin:
                paper["matched_topics"] = matched_topics if matched_topics else ["asset_pricing"]
                paper["relevance_score"] = len(matched_topics) + (1 if is_qfin else 0)
                relevant.append(paper)

        return sorted(relevant, key=lambda x: x["relevance_score"], reverse=True)

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        try:
            return datetime.strptime(date_str[:10], "%Y-%m-%d")
        except Exception:
            return datetime.min


# ── Quick test ────────────────────────────────────────────────────────── #
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    s = ArXivScraper()
    papers = s.fetch_recent_papers(days_back=14)
    print(f"\nFound {len(papers)} papers")
    for p in papers[:5]:
        print(f"\n[{p['primary_category']}] {p['title'][:80]}")
        print(f"  Topics: {p.get('matched_topics', [])}")
        print(f"  Date:   {p['date']}")
