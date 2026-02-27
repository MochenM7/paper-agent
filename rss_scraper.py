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
from config import NBER_RSS_FEEDS, SSRN_RSS_FEEDS, CROSSREF_JOURNALS, TOPICS

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PaperAgent/2.0; research bot)"}


def _parse_rss(xml_data, source: str) -> List[Dict]:
    """Accept str or bytes; bytes avoids BOM issues with some feeds."""
    papers = []
    try:
        if isinstance(xml_data, str):
            xml_data = xml_data.encode("utf-8", errors="replace")
        root = ET.fromstring(xml_data)
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

        # Parse date; fall back to today if field is missing or unparseable
        date_str = ""
        if pub_date:
            for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"]:
                try:
                    date_str = datetime.strptime(pub_date[:len(fmt)], fmt).strftime("%Y-%m-%d")
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


def fetch_crossref(days_back: int = 7) -> List[Dict]:
    """Fetch recent papers from QJE, ReStud, JFQA via CrossRef REST API."""
    all_papers, seen = [], set()
    cutoff = datetime.now() - timedelta(days=days_back)
    cutoff_str = cutoff.strftime("%Y-%m-%d")
    base = "https://api.crossref.org/journals/{issn}/works"
    headers = {**HEADERS, "User-Agent": "PaperAgent/2.0 (mailto:mamochen724@gmail.com)"}

    for journal, issn in CROSSREF_JOURNALS.items():
        try:
            params = {
                "rows": 40,
                "sort": "published",
                "order": "desc",
                "filter": f"from-pub-date:{cutoff_str}",
                "select": "DOI,title,author,abstract,published,container-title",
            }
            r = requests.get(base.format(issn=issn), params=params,
                             headers=headers, timeout=20)
            if r.status_code != 200:
                logger.warning(f"CrossRef {journal} {r.status_code}")
                continue
            items = r.json().get("message", {}).get("items", [])
            for item in items:
                doi   = item.get("DOI", "")
                titles = item.get("title", [])
                title = titles[0] if titles else ""
                if not title or len(title) < 5:
                    continue
                # Authors
                authors_raw = item.get("author", [])
                authors = ", ".join(
                    f"{a.get('given','')} {a.get('family','')}".strip()
                    for a in authors_raw[:4]
                )
                # Abstract (may be absent)
                abstract = item.get("abstract", "")
                import re
                abstract = re.sub(r"<[^>]+>", " ", abstract).strip()
                # Date
                dp = item.get("published", {}).get("date-parts", [[]])[0]
                if len(dp) >= 3:
                    date_str = f"{dp[0]:04d}-{dp[1]:02d}-{dp[2]:02d}"
                elif len(dp) == 2:
                    date_str = f"{dp[0]:04d}-{dp[1]:02d}-01"
                else:
                    date_str = datetime.now().strftime("%Y-%m-%d")
                try:
                    if datetime.strptime(date_str, "%Y-%m-%d") < cutoff:
                        continue
                except:
                    pass
                if doi not in seen:
                    seen.add(doi)
                    all_papers.append({
                        "source":   journal,
                        "id":       doi,
                        "title":    title,
                        "authors":  authors,
                        "abstract": abstract[:1500],
                        "url":      f"https://doi.org/{doi}",
                        "date":     date_str,
                    })
            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"CrossRef {journal} error: {e}")

    relevant = _filter_relevant(all_papers)
    logger.info(f"CrossRef: {len(all_papers)} total → {len(relevant)} relevant")
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
            papers = _parse_rss(r.content, "NBER")
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

    for name, url in SSRN_RSS_FEEDS.items():
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                logger.warning(f"{name} RSS {r.status_code}: {url}")
                continue
            papers = _parse_rss(r.content, name)
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
            logger.warning(f"{name} RSS error {url}: {e}")

    relevant = _filter_relevant(all_papers)
    logger.info(f"Journals: {len(all_papers)} total → {len(relevant)} relevant")
    return relevant
