"""Poll CryptoPanic for crypto news; crypto sector only, supplementary to Finnhub."""

import logging
from typing import Any

import requests

import config
from db.supabase_client import insert_news_article, log_event

logger = logging.getLogger(__name__)

CRYPTOPANIC_BASE = "https://api.cryptopanic.com/v1/posts/"


def poll_cryptopanic() -> int:
    """
    Fetch crypto news from CryptoPanic. All articles tagged sector=crypto.
    Only runs for crypto sector (supplementary source). Returns count inserted.
    """
    if not config.CRYPTOPANIC_API_KEY:
        logger.debug("CRYPTOPANIC_API_KEY not set; skipping CryptoPanic fetch")
        return 0
    params = {
        "auth_token": config.CRYPTOPANIC_API_KEY,
        "public": "true",
        "filter": "hot",
    }
    try:
        r = requests.get(CRYPTOPANIC_BASE, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        results = data.get("results") if isinstance(data, dict) else []
    except requests.RequestException as e:
        logger.warning("CryptoPanic request failed: %s", e)
        log_event("ERROR", "ingestion", f"CryptoPanic failed: {e}", {"sector": "crypto"})
        return 0
    total_inserted = 0
    sector = "crypto"
    for item in results or []:
        url = (item.get("url") or "").strip()
        if not url:
            continue
        title = (item.get("title") or "").strip()
        source = (item.get("source", {}) or {})
        source_name = source.get("title", "") or source.get("name", "") or "cryptopanic"
        published = item.get("published_at")
        if published:
            try:
                from datetime import datetime, timezone
                if isinstance(published, (int, float)):
                    published = datetime.fromtimestamp(published, tz=timezone.utc).isoformat()
                elif isinstance(published, str) and not published.endswith("Z") and not "+" in published:
                    published = published + "Z" if published else None
            except Exception:
                published = None
        row = insert_news_article(
            source=source_name,
            title=title,
            description="",
            url=url,
            sector=sector,
            published_at=published,
            data_source="cryptopanic",
        )
        if row:
            total_inserted += 1
    logger.info("CryptoPanic poll complete: %d new articles", total_inserted)
    return total_inserted
