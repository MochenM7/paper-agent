"""
RSS Scraper — NBER + SSRN
Uses official RSS feeds, no scraping, no 403 errors.
"""

import requests
import logging
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict
from config import NBER_RSS_FEEDS, SSRN_RSS_FEEDS, TOPICS

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PaperAgent/2.0; research bot)"}


def _parse_rss(xml_text: str, source: str) -> List[Dict]:
    papers = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        logger.warning(f"RSS parse error ({source}): {e}")
        return []

    # Handle both RSS 2.0 and Atom
    items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")

    for item in items:
        def get(tag, atom_tag=None):
            v = item.findtext(tag, "")
            if not v and atom_tag:
                v = item.findtext(atom_tag, "")
            return (v or "").strip()

        title    = get("title",   "{http://www.w3.org/2005/Atom}title")
        link     = get("link",    "{http://www.w3.org/2005/Atom}id")
        abstract = get("description", "{http://www.w3.org/2005/Atom}summary")
        authors  = get("dc:creator", "{http://purl.org/dc/elements/1.1/}creator")
        pub_date = get("pubDate", "{http://www.w3.org/2005/Atom}updated")

        # Clean HTML from abstract
        import re
        abstract = re.sub(r"<[^>]+>", " ", abstract).strip()

        if not title or len(title) < 5:
            continue

        # Parse date
        date_str = ""
        for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"]:
            try:
                date_str = datetime.strptime(pub_date[:25], fmt[:len(pub_date[:25])]).strftime("%Y-%m-%d")
                break
            except:
                continue
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")

        papers.append({
            "source":   source,
            "id":       link or title[:50],
            "title":    title,
            "authors":  authors,
            "abstract": abstract[:1500],
            "url":      link,
            "date":     date_str,
        })
    return papers


def _filter_relevant(papers: List[Dict]) -> List[Dict]:
    relevant = []
    for p in papers:
        text = f"{p.get('title','')} {p.get('abstract','')}".lower()
        matched = [t for t, kws in TOPICS.items() if any(k.lower() in text for k in kws)]
        if matched:
            p["matched_topics"] = matched
            p["relevance_score"] = len(matched)
            relevant.append(p)
    return relevant


def fetch_nber(days_back: int = 7) -> List[Dict]:
    all_papers, seen = [], set()
    cutoff = datetime.now() - timedelta(days=days_back)

    for url in NBER_RSS_FEEDS:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                logger.warning(f"NBER RSS {r.status_code}: {url}")
                continue
            papers = _parse_rss(r.text, "NBER")
            for p in papers:
                try:
                    d = datetime.strptime(p["date"], "%Y-%m-%d")
                    if d < cutoff:
                        continue
                except:
                    pass
                if p["id"] not in seen:
                    seen.add(p["id"])
                    all_papers.append(p)
            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"NBER RSS error {url}: {e}")

    relevant = _filter_relevant(all_papers)
    logger.info(f"NBER: {len(all_papers)} total → {len(relevant)} relevant")
    return relevant


def fetch_ssrn(days_back: int = 7) -> List[Dict]:
    all_papers, seen = [], set()
    cutoff = datetime.now() - timedelta(days=days_back)

    for url in SSRN_RSS_FEEDS:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                logger.warning(f"SSRN RSS {r.status_code}: {url}")
                continue
            papers = _parse_rss(r.text, "SSRN")
            for p in papers:
                try:
                    d = datetime.strptime(p["date"], "%Y-%m-%d")
                    if d < cutoff:
                        continue
                except:
                    pass
                if p["id"] not in seen:
                    seen.add(p["id"])
                    all_papers.append(p)
            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"SSRN RSS error {url}: {e}")

    relevant = _filter_relevant(all_papers)
    logger.info(f"SSRN: {len(all_papers)} total → {len(relevant)} relevant")
    return relevant
