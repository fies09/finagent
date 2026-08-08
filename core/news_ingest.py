import os
from typing import List, Dict
import requests
import feedparser
from log import logger


class NewsIngest:
    COINDESK_RSS = "https://www.coindesk.com/arc/outboundfeeds/rss/"
    COINTELEGRAPH_RSS = "https://cointelegraph.com/rss"
    COINGAPE_RSS = "https://coingape.com/feed/"
    DECRYPT_RSS = "https://decrypt.co/feed"

    def __init__(self, symbols: List[str] | None = None, timeout: int = 15):
        self.symbols = [s.upper() for s in (symbols or os.getenv("SYMBOLS", "BTC/USDT,ETH/USDT,SOL/USDT").split(","))]
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) FinAgent/0.1",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        })

    def _match(self, text: str) -> List[str]:
        t = text.upper()
        return [s for s in self.symbols if s.split("/")[0] in t]

    def fetch_rss(self, url: str, source: str) -> List[Dict]:
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            out = []
            for e in feed.entries[:30]:
                text = f"{e.get('title', '')} {e.get('summary', '')}"
                syms = self._match(text)
                if syms:
                    out.append({
                        "source": source,
                        "title": e.get("title", ""),
                        "text": text,
                        "symbols": syms,
                        "url": e.get("link", ""),
                        "published_at": e.get("published", "") or e.get("updated", ""),
                    })
            return out
        except Exception as ex:
            logger.error(f"rss {source} fetch failed: {ex}")
            return []

    def fetch_all(self) -> List[Dict]:
        items = self.fetch_rss(self.COINDESK_RSS, "coindesk")
        items += self.fetch_rss(self.COINTELEGRAPH_RSS, "cointelegraph")
        items += self.fetch_rss(self.COINGAPE_RSS, "coingape")
        items += self.fetch_rss(self.DECRYPT_RSS, "decrypt")
        return items