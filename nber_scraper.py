"""
NBER Paper Scraper
Fetches recent working papers from National Bureau of Economic Research
"""

import requests
import json
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup


from config import NBER_CONFIG, ALL_KEYWORDS, TOPICS

logger = logging.getLogger(__name__)


class NBERScraper:
    """Scrapes NBER working papers with relevance filtering"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Academic Research Bot - PhD Student)",
            "Accept": "application/json, text/html",
        })
        self.base_url = NBER_CONFIG["base_url"]
    
    def fetch_recent_papers(self, days_back: int = 7) -> List[Dict]:
        """Fetch NBER papers from the last N days"""
        papers = []
        
        # Method 1: Try NBER API for working papers
        try:
            papers = self._fetch_via_api(days_back)
        except Exception as e:
            logger.warning(f"NBER API failed: {e}, trying HTML scraping")
            papers = self._fetch_via_html(days_back)
        
        # Filter by relevance
        relevant = self._filter_relevant(papers)
        logger.info(f"NBER: Found {len(papers)} papers, {len(relevant)} relevant")
        return relevant
    
    def _fetch_via_api(self, days_back: int) -> List[Dict]:
        """Use NBER's JSON API"""
        papers = []
        since_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        
        # NBER program codes for finance
        programs = NBER_CONFIG["programs"]
        
        for program in programs:
            url = f"https://www.nber.org/api/v1/working_page_listing/contentType/working_paper/_/_/search?page=1&perPage=30&program={program}"
            try:
                resp = self.session.get(url, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", [])
                    for item in results:
                        pub_date = item.get("publicationDate", "")
                        if pub_date >= since_date:
                            paper = {
                                "source": "NBER",
                                "id": item.get("handle", ""),
                                "title": item.get("title", ""),
                                "authors": self._parse_authors(item.get("authors", [])),
                                "abstract": item.get("abstract", ""),
                                "url": f"https://www.nber.org/papers/{item.get('handle', '')}",
                                "date": pub_date,
                                "program": program,
                                "doi": item.get("doi", ""),
                            }
                            papers.append(paper)
                time.sleep(0.5)
            except Exception as e:
                logger.warning(f"Failed to fetch NBER program {program}: {e}")
        
        return papers
    
    def _fetch_via_html(self, days_back: int) -> List[Dict]:
        """Fallback: scrape NBER HTML pages"""
        papers = []
        since_date = datetime.now() - timedelta(days=days_back)
        
        # Scrape recent papers page
        url = "https://www.nber.org/papers?page=1&perPage=100&sortBy=public_date"
        try:
            resp = self.session.get(url, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            
            for item in soup.select(".digest-list-item, .paper-listing"):
                try:
                    title_el = item.select_one("h3 a, .title a")
                    date_el = item.select_one(".date, time")
                    
                    if not title_el:
                        continue
                    
                    paper = {
                        "source": "NBER",
                        "title": title_el.get_text(strip=True),
                        "url": "https://www.nber.org" + title_el.get("href", ""),
                        "date": date_el.get_text(strip=True) if date_el else "",
                        "authors": "",
                        "abstract": "",
                        "program": "unknown",
                    }
                    papers.append(paper)
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"NBER HTML scraping failed: {e}")
        
        return papers
    
    def fetch_paper_details(self, paper: Dict) -> Dict:
        """Fetch full abstract for a paper"""
        if paper.get("abstract"):
            return paper
        
        try:
            resp = self.session.get(paper["url"], timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # NBER abstract selectors
            abstract_el = soup.select_one(".abstract p, #abstract, .paper-abstract")
            if abstract_el:
                paper["abstract"] = abstract_el.get_text(strip=True)
            
            # Authors
            author_els = soup.select(".authors a, .author-name")
            if author_els:
                paper["authors"] = ", ".join(a.get_text(strip=True) for a in author_els)
            
            time.sleep(0.3)
        except Exception as e:
            logger.warning(f"Could not fetch details for {paper['url']}: {e}")
        
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
        
        # Sort by relevance
        return sorted(relevant, key=lambda x: x["relevance_score"], reverse=True)
    
    def _parse_authors(self, authors_data) -> str:
        """Parse author data from API response"""
        if isinstance(authors_data, list):
            names = []
            for a in authors_data:
                if isinstance(a, dict):
                    names.append(a.get("name", a.get("displayName", "")))
                elif isinstance(a, str):
                    names.append(a)
            return ", ".join(names)
        return str(authors_data)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scraper = NBERScraper()
    papers = scraper.fetch_recent_papers(days_back=30)
    print(f"Found {len(papers)} relevant papers")
    for p in papers[:3]:
        print(f"\n- {p['title']}")
        print(f"  Topics: {p.get('matched_topics', [])}")
