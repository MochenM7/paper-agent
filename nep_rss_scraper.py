import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict
import feedparser

from config import NEP_RSS_CONFIG, TOPICS

logger = logging.getLogger(__name__)

class NEPRSSScraper:
    """
    Fetch recent working papers via RePEc NEP RSS feeds (stable, no SSRN 403).
    """
    def __init__(self):
        self.feeds = NEP_RSS_CONFIG["feeds"]  # list of dicts: {"name": "...", "url": "..."}
        self.max_papers = NEP_RSS_CONFIG.get("max_papers_per_run", 80)

    def fetch_recent_papers(self, days_back: int = 7) -> List[Dict]:
        since = datetime.now(timezone.utc) - timedelta(days=days_back)
        papers: List[Dict] = []
        seen = set()

        for f in self.feeds:
            name = f["name"]
            url = f["url"]
            try:
                d = feedparser.parse(url)
                if getattr(d, "bozo", 0):
                    logger.warning(f"NEP RSS parse issue for {name}: {getattr(d, 'bozo_exception', '')}")

                for e in d.entries:
                    link = getattr(e, "link", "") or ""
                    title = getattr(e, "title", "") or ""
                    summary = getattr(e, "summary", "") or getattr(e, "description", "") or ""

                    # time.struct_time -> datetime
                    dt = None
                    if getattr(e, "published_parsed", None):
                        dt = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
                    elif getattr(e, "updated_parsed", None):
                        dt = datetime(*e.updated_parsed[:6], tzinfo=timezone.utc)

                    if dt and dt < since:
                        continue

                    pid = getattr(e, "id", "") or link or title
                    if not pid or pid in seen:
                        continue
                    seen.add(pid)

                    paper = {
                        "source": f"NEP:{name}",
                        "id": pid,
                        "title": title.strip(),
                        "authors": "",              # NEP RSS 通常不保证有作者字段
                        "abstract": summary.strip(), # 如果 feed 含摘要会在这里
                        "url": link.strip(),
                        "date": (dt.date().isoformat() if dt else datetime.now(timezone.utc).date().isoformat()),
                    }
                    papers.append(paper)

            except Exception as ex:
                logger.warning(f"NEP RSS fetch failed for {name}: {ex}")

        # 复用你现有的 topic 过滤逻辑
        relevant = self._filter_relevant(papers)
        logger.info(f"NEP RSS: Found {len(papers)} items, {len(relevant)} relevant")
        return relevant[: self.max_papers]

    def _filter_relevant(self, papers: List[Dict]) -> List[Dict]:
        relevant = []
        for paper in papers:
            text = f"{paper.get('title','')} {paper.get('abstract','')}".lower()

            matched_topics = []
            for topic, keywords in TOPICS.items():
                if any(kw.lower() in text for kw in keywords):
                    matched_topics.append(topic)

            if matched_topics:
                paper["matched_topics"] = matched_topics
                paper["relevance_score"] = len(matched_topics)
                relevant.append(paper)

        return sorted(relevant, key=lambda x: x.get("relevance_score", 0), reverse=True)