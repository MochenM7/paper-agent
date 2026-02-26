"""
SSRN Paper Scraper
Fetches papers from Social Science Research Network
"""

import requests
import json
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict
from bs4 import BeautifulSoup
import re


from config import SSRN_CONFIG, ALL_KEYWORDS, TOPICS

logger = logging.getLogger(__name__)


class SSRNScraper:
    """Scrapes SSRN papers with keyword filtering"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        })
    
    def fetch_recent_papers(self, days_back: int = 7) -> List[Dict]:
        """Fetch recent SSRN papers by searching key topics"""
        all_papers = []
        seen_ids = set()
        
        # Search for each major topic cluster
        search_queries = [
            "behavioral finance sentiment",
            "asset pricing machine learning",
            "investor attention returns",
            "LLM NLP finance",
            "tail risk sentiment",
            "quantile regression asset pricing",
            "transformer attention finance",
        ]
        
        for query in search_queries:
            try:
                papers = self._search_ssrn(query, days_back)
                for p in papers:
                    pid = p.get("id", p.get("title", ""))
                    if pid not in seen_ids:
                        seen_ids.add(pid)
                        all_papers.append(p)
                time.sleep(1.0)  # Be respectful
            except Exception as e:
                logger.warning(f"SSRN search failed for '{query}': {e}")
        
        # Filter relevant
        relevant = self._filter_relevant(all_papers)
        logger.info(f"SSRN: Found {len(all_papers)} papers, {len(relevant)} relevant")
        return relevant[:SSRN_CONFIG["max_papers_per_run"]]
    
    def _search_ssrn(self, query: str, days_back: int) -> List[Dict]:
        """Search SSRN for a given query string"""
        papers = []
        
        params = {
            "form_name": "journalBrowse",
            "txtFilter_type": "5",  # Full text
            "txtFilter": query,
            "SortOrder": "ab_approval_date desc",
            "strDays": str(days_back),
            "start": "0",
            "resultCount": "50",
        }
        
        try:
            resp = self.session.get(
                "https://papers.ssrn.com/sol3/results.cfm",
                params=params,
                timeout=20
            )
            
            if resp.status_code != 200:
                logger.warning(f"SSRN returned {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.text, "html.parser")
            papers = self._parse_ssrn_results(soup)
            
        except Exception as e:
            logger.error(f"SSRN request failed: {e}")
        
        return papers
    
    def _parse_ssrn_results(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse SSRN search results page"""
        papers = []
        
        # SSRN result items
        items = soup.select(".col-lg-9 .downloads, .abstract-list .trow")
        if not items:
            # Alternative selector
            items = soup.select(".paper-meta, .result-item")
        
        # Try generic approach
        for item in soup.select("div[data-abstract-id], .ssrn-item"):
            try:
                abstract_id = item.get("data-abstract-id", "")
                
                title_el = item.select_one(".title a, h3 a, .abstract-title a")
                author_el = item.select_one(".authors, .by-author")
                abstract_el = item.select_one(".abstract-text, .short-abstract")
                date_el = item.select_one(".date, .submission-date")
                
                if not title_el:
                    continue
                
                paper = {
                    "source": "SSRN",
                    "id": abstract_id,
                    "title": title_el.get_text(strip=True),
                    "authors": author_el.get_text(strip=True) if author_el else "",
                    "abstract": abstract_el.get_text(strip=True) if abstract_el else "",
                    "url": f"https://papers.ssrn.com/sol3/papers.cfm?abstract_id={abstract_id}" if abstract_id else "",
                    "date": date_el.get_text(strip=True) if date_el else datetime.now().strftime("%Y-%m-%d"),
                }
                papers.append(paper)
            except Exception:
                continue
        
        # Fallback: parse table rows
        if not papers:
            papers = self._parse_table_format(soup)
        
        return papers
    
    def _parse_table_format(self, soup: BeautifulSoup) -> List[Dict]:
        """Alternative SSRN parsing for table format"""
        papers = []
        
        rows = soup.select("tr.search-row, .paper-row")
        for row in rows:
            try:
                title_el = row.select_one("a[href*='abstract']")
                if not title_el:
                    continue
                
                href = title_el.get("href", "")
                abstract_id = re.search(r"abstract_id=(\d+)", href)
                
                paper = {
                    "source": "SSRN",
                    "id": abstract_id.group(1) if abstract_id else "",
                    "title": title_el.get_text(strip=True),
                    "authors": "",
                    "abstract": "",
                    "url": f"https://papers.ssrn.com{href}" if href.startswith("/") else href,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                }
                papers.append(paper)
            except Exception:
                continue
        
        return papers
    
    def fetch_paper_details(self, paper: Dict) -> Dict:
        """Fetch full paper details from SSRN abstract page"""
        if paper.get("abstract") and len(paper["abstract"]) > 100:
            return paper
        
        if not paper.get("url"):
            return paper
        
        try:
            resp = self.session.get(paper["url"], timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Extract abstract
            abstract_el = soup.select_one(".abstract-text p, #abstract, .abstractText")
            if abstract_el:
                paper["abstract"] = abstract_el.get_text(strip=True)
            
            # Extract authors
            author_els = soup.select(".author-name a, .authors-list .name")
            if author_els:
                paper["authors"] = ", ".join(a.get_text(strip=True) for a in author_els)
            
            # Extract date
            date_el = soup.select_one(".submission-date, .date-posted")
            if date_el:
                paper["date"] = date_el.get_text(strip=True)
            
            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"Could not fetch SSRN details for {paper.get('url')}: {e}")
        
        return paper
    
    def _filter_relevant(self, papers: List[Dict]) -> List[Dict]:
        """Filter papers by keyword relevance"""
        relevant = []
        for paper in papers:
            text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
            
            matched_topics = []
            for topic, keywords in TOPICS.items():
                if any(kw.lower() in text for kw in keywords):
                    matched_topics.append(topic)
            
            if matched_topics:
                paper["matched_topics"] = matched_topics
                paper["relevance_score"] = len(matched_topics)
                relevant.append(paper)
        
        return sorted(relevant, key=lambda x: x["relevance_score"], reverse=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scraper = SSRNScraper()
    papers = scraper.fetch_recent_papers(days_back=14)
    print(f"Found {len(papers)} relevant papers")
    for p in papers[:3]:
        print(f"\n- {p['title'][:80]}")
        print(f"  Topics: {p.get('matched_topics', [])}")
