"""Poll Alpha Vantage NEWS_SENTIMENT filtered by sector tickers; supplementary source."""

import logging
import time
from typing import Any

import requests

import config
from sectors import get_sector_tickers, sector_uses_alpha_vantage, VALID_SECTORS
from db.supabase_client import insert_news_article, log_event

logger = logging.getLogger(__name__)

ALPHA_VANTAGE_BASE = "https://www.alphavantage.co/query"
# Free tier: 5 req/min — space sector calls
RATE_LIMIT_DELAY_SEC = 12.5


def _fetch_news_sentiment(tickers: list[str]) -> list[dict[str, Any]]:
    """Fetch market news & sentiment for given tickers. Limit 50 items."""
    if not config.ALPHA_VANTAGE_API_KEY or not tickers:
        return []
    # API accepts comma-separated tickers
    ticker_str = ",".join(tickers[:20])
    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": ticker_str,
        "limit": 50,
        "apikey": config.ALPHA_VANTAGE_API_KEY,
    }
    try:
        r = requests.get(ALPHA_VANTAGE_BASE, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        feed = data.get("feed") if isinstance(data, dict) else []
        return feed if isinstance(feed, list) else []
    except requests.RequestException as e:
        logger.warning("Alpha Vantage NEWS_SENTIMENT failed: %s", e)
        return []


def poll_alpha_vantage() -> int:
    """
    For each sector with alpha_vantage=True, fetch news filtered by sector tickers.
    Tag each article with that sector. Returns count of new articles inserted.
    """
    if not config.ALPHA_VANTAGE_API_KEY:
        logger.debug("ALPHA_VANTAGE_API_KEY not set; skipping Alpha Vantage fetch")
        return 0
    total_inserted = 0
    for sector in VALID_SECTORS:
        if not sector_uses_alpha_vantage(sector):
            continue
        tickers = get_sector_tickers(sector)
        if not tickers:
            continue
        items = _fetch_news_sentiment(tickers)
        for item in items:
            url = (item.get("url") or "").strip()
            if not url:
                continue
            title = (item.get("title") or "").strip()
            summary = (item.get("summary") or "").strip()
            source = (item.get("source") or "alpha_vantage").strip()
            pub = item.get("time_published")
            if pub:
                try:
                    # Format: 20240101T120000
                    from datetime import datetime, timezone
                    if isinstance(pub, str) and len(pub) >= 15:
                        pub = pub[:4] + "-" + pub[4:6] + "-" + pub[6:8] + "T" + pub[9:11] + ":" + pub[11:13] + ":" + pub[13:15] + "+00:00"
                except Exception:
                    pub = None
            row = insert_news_article(
                source=source,
                title=title,
                description=summary,
                url=url,
                sector=sector,
                published_at=pub,
                data_source="alpha_vantage",
            )
            if row:
                total_inserted += 1
        time.sleep(RATE_LIMIT_DELAY_SEC)
    logger.info("Alpha Vantage poll complete: %d new articles", total_inserted)
    return total_inserted
