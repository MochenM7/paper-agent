"""
arXiv Scraper — official Atom API
"""

import requests
import time
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict
from config import ARXIV_CATS, TOPICS

logger = logging.getLogger(__name__)
NS = {"atom": "http://www.w3.org/2005/Atom"}
API = "https://export.arxiv.org/api/query"


def fetch_arxiv(days_back: int = 7) -> List[Dict]:
    all_papers, seen = [], set()
    cutoff = datetime.utcnow() - timedelta(days=days_back)

    # 1. Fetch by q-fin categories
    for cat in ARXIV_CATS:
        papers = _query(f"cat:{cat}", max_results=40)
        for p in papers:
            if p["id"] not in seen:
                seen.add(p["id"]); all_papers.append(p)
        time.sleep(0.3)

    # 2. ML/finance keyword searches
    for q in [
        "ti:transformer AND ti:portfolio",
        "ti:reinforcement AND ti:trading",
        "ti:LLM AND ti:finance",
        "ti:deep learning AND ti:asset",
        "ti:gender AND ti:finance",
        "ti:machine learning AND ti:factor",
    ]:
        papers = _query(f"({q}) AND (cat:cs.LG OR cat:stat.ML OR cat:econ.GN OR cat:q-fin.GN)",
                        max_results=15)
        for p in papers:
            if p["id"] not in seen:
                seen.add(p["id"]); all_papers.append(p)
        time.sleep(0.3)

    # Filter by recency
    recent = [p for p in all_papers
              if _parse_date(p["date"]) >= cutoff]

    # Filter by relevance
    relevant = _filter(recent or all_papers)
    logger.info(f"arXiv: {len(all_papers)} total → {len(recent)} recent → {len(relevant)} relevant")
    return relevant[:60]


def _query(search_query: str, max_results: int = 40) -> List[Dict]:
    try:
        r = requests.get(API, params={
            "search_query": search_query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": max_results,
        }, timeout=20)
        if r.status_code != 200:
            return []
        return _parse(r.text)
    except Exception as e:
        logger.warning(f"arXiv query error: {e}")
        return []


def _parse(xml_text: str) -> List[Dict]:
    papers = []
    try:
        root = ET.fromstring(xml_text)
    except:
        return []
    for entry in root.findall("atom:entry", NS):
        try:
            aid = entry.findtext("atom:id", "", NS).split("/abs/")[-1].strip()
            title = entry.findtext("atom:title", "", NS).strip().replace("\n", " ")
            abstract = entry.findtext("atom:summary", "", NS).strip().replace("\n", " ")
            date = entry.findtext("atom:published", "", NS)[:10]
            authors = ", ".join(
                a.findtext("atom:name", "", NS)
                for a in entry.findall("atom:author", NS)
            )[:120]
            cats = [t.get("term","") for t in entry.findall("atom:category", NS)]
            papers.append({
                "source": "arXiv", "id": aid, "title": title,
                "authors": authors, "abstract": abstract[:1500],
                "url": f"https://arxiv.org/abs/{aid}",
                "date": date, "categories": cats,
                "primary_category": cats[0] if cats else "",
            })
        except:
            continue
    return papers


def _filter(papers: List[Dict]) -> List[Dict]:
    out = []
    for p in papers:
        text = f"{p.get('title','')} {p.get('abstract','')}".lower()
        matched = [t for t, kws in TOPICS.items() if any(k.lower() in text for k in kws)]
        is_qfin = any(c.startswith("q-fin") for c in p.get("categories", []))
        if matched or is_qfin:
            p["matched_topics"] = matched or ["quant_trading"]
            p["relevance_score"] = len(matched) + (1 if is_qfin else 0)
            out.append(p)
    return sorted(out, key=lambda x: -x["relevance_score"])


def _parse_date(s: str) -> datetime:
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d")
    except:
        return datetime.min
