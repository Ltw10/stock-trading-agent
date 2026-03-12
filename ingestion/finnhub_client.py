"""Poll Finnhub company_news per ticker; tag sector from ticker and store in Supabase."""

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any

import requests

import config
from sectors import SECTORS, VALID_SECTORS, get_sector_tickers
from db.supabase_client import insert_news_article, log_event

logger = logging.getLogger(__name__)

FINNHUB_BASE = "https://finnhub.io/api/v1/company-news"
# Free tier: 60 API calls per minute — space ticker calls
RATE_LIMIT_DELAY_SEC = 1.05


def _ticker_to_sector(ticker: str) -> str | None:
    """Return sector for a ticker, or None if not in any sector."""
    ticker = ticker.upper()
    for sector in VALID_SECTORS:
        if ticker in [t.upper() for t in get_sector_tickers(sector)]:
            return sector
    return None


def _fetch_company_news(ticker: str, from_date: str, to_date: str) -> list[dict[str, Any]]:
    """Fetch company news for one ticker. from/to in YYYY-MM-DD."""
    if not config.FINNHUB_API_KEY:
        return []
    params = {
        "symbol": ticker,
        "from": from_date,
        "to": to_date,
        "token": config.FINNHUB_API_KEY,
    }
    try:
        r = requests.get(FINNHUB_BASE, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []
    except requests.RequestException as e:
        logger.warning("Finnhub company-news failed for %s: %s", ticker, e)
        return []


def poll_finnhub() -> int:
    """
    Iterate over every ticker in sectors.py; fetch company_news for each.
    Tag article with sector derived from the ticker used to fetch.
    Rate limit: ~1 call per second (60/min). Returns count of new articles inserted.
    """
    if not config.FINNHUB_API_KEY:
        logger.warning(
            "FINNHUB_API_KEY not set or empty; skipping Finnhub fetch. "
            "On Railway: use exact name FINNHUB_API_KEY (two N's), set it in the service Variables, then redeploy."
        )
        return 0
    to_dt = datetime.now(timezone.utc)
    from_dt = to_dt - timedelta(days=2)
    from_date = from_dt.strftime("%Y-%m-%d")
    to_date = to_dt.strftime("%Y-%m-%d")
    total_inserted = 0
    for sector in VALID_SECTORS:
        for ticker in get_sector_tickers(sector):
            articles = _fetch_company_news(ticker, from_date, to_date)
            for a in articles:
                url = (a.get("url") or "").strip()
                if not url:
                    continue
                source = (a.get("source") or "unknown").strip()
                title = (a.get("headline") or a.get("title") or "").strip()
                summary = (a.get("summary") or "").strip()
                pub = a.get("datetime")
                if pub:
                    try:
                        # Finnhub returns Unix timestamp
                        pub_dt = datetime.fromtimestamp(pub, tz=timezone.utc)
                        pub = pub_dt.isoformat()
                    except Exception:
                        pub = None
                # Sector from the ticker we used to fetch
                row = insert_news_article(
                    source=source,
                    title=title,
                    description=summary,
                    url=url,
                    sector=sector,
                    published_at=pub,
                    data_source="finnhub",
                )
                if row:
                    total_inserted += 1
            time.sleep(RATE_LIMIT_DELAY_SEC)
    logger.info("Finnhub poll complete: %d new articles", total_inserted)
    return total_inserted
