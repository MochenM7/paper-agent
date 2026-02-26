import os
import random
import requests
import time
import logging
from datetime import datetime
from typing import List, Dict
from bs4 import BeautifulSoup
import re

from config import SSRN_CONFIG, TOPICS

logger = logging.getLogger(__name__)


class SSRNScraper:
    """Scrapes SSRN papers with keyword filtering (robust to 403 on GitHub Actions)"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            # 更完整一点的 headers（有时能减少被当成机器人）
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })

        # 一旦遇到 403，就把本次 run 的 SSRN 彻底关掉（防止刷屏）
        self.blocked_this_run = False

        # 在 GitHub Actions 上默认跳过 SSRN（最稳）
        self.skip_on_github = bool(SSRN_CONFIG.get("skip_on_github_actions", True))
        self.on_github = (os.getenv("GITHUB_ACTIONS") == "true")

        # 先访问一下首页拿 cookie（有时有帮助；失败也无所谓）
        try:
            self.session.get("https://papers.ssrn.com", timeout=10)
        except Exception:
            pass

    def fetch_recent_papers(self, days_back: int = 7) -> List[Dict]:
        """Fetch recent SSRN papers by searching key topics"""

        if self.on_github and self.skip_on_github:
            logger.warning("SSRN often blocks GitHub Actions IPs (403). Skipping SSRN on GitHub Actions.")
            return []

        all_papers = []
        seen_ids = set()

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
            if self.blocked_this_run:
                break

            try:
                papers = self._search_ssrn(query, days_back)
                for p in papers:
                    pid = p.get("id", p.get("title", ""))
                    if pid and pid not in seen_ids:
                        seen_ids.add(pid)
                        all_papers.append(p)

                # 随机 sleep，别固定 1 秒（固定节奏更像机器人）
                time.sleep(0.8 + random.random() * 0.7)

            except Exception as e:
                logger.warning(f"SSRN search failed for '{query}': {e}")

        relevant = self._filter_relevant(all_papers)
        logger.info(f"SSRN: Found {len(all_papers)} papers, {len(relevant)} relevant")
        return relevant[:SSRN_CONFIG["max_papers_per_run"]]

    def _search_ssrn(self, query: str, days_back: int) -> List[Dict]:
        """Search SSRN for a given query string"""
        if self.blocked_this_run:
            return []

        params = {
            "form_name": "journalBrowse",
            "txtFilter_type": "5",
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
                timeout=20,
                allow_redirects=True,
            )

            # 关键：403 直接判定被封，本次 run 不再碰 SSRN
            if resp.status_code == 403:
                logger.warning("SSRN returned 403 (blocked). Disable SSRN for this run.")
                self.blocked_this_run = True
                return []

            # 有时会 429/503（限流/风控），也别硬重试
            if resp.status_code in (429, 503):
                logger.warning(f"SSRN returned {resp.status_code} (rate-limited). Disable SSRN for this run.")
                self.blocked_this_run = True
                return []

            if resp.status_code != 200:
                logger.warning(f"SSRN returned {resp.status_code}")
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            return self._parse_ssrn_results(soup)

        except Exception as e:
            logger.error(f"SSRN request failed: {e}")
            return []

    def _parse_ssrn_results(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse SSRN search results page"""
        papers = []

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

        if not papers:
            papers = self._parse_table_format(soup)

        return papers

    def _parse_table_format(self, soup: BeautifulSoup) -> List[Dict]:
        papers = []
        rows = soup.select("tr.search-row, .paper-row")
        for row in rows:
            try:
                title_el = row.select_one("a[href*='abstract']")
                if not title_el:
                    continue

                href = title_el.get("href", "")
                m = re.search(r"abstract_id=(\d+)", href)

                paper = {
                    "source": "SSRN",
                    "id": m.group(1) if m else "",
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

    def _filter_relevant(self, papers: List[Dict]) -> List[Dict]:
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
