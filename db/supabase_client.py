"""Supabase connection and helpers."""

import logging
from typing import Any

from supabase import create_client, Client

import config
from sectors import VALID_SECTORS

logger = logging.getLogger(__name__)

_client: Client | None = None


def get_client() -> Client:
    """Return singleton Supabase client."""
    global _client
    if _client is None:
        if not config.SUPABASE_URL or not config.SUPABASE_KEY:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _client


def insert_news_article(
    source: str,
    title: str,
    description: str | None,
    url: str,
    sector: str,
    published_at: str | None,
    data_source: str = "finnhub",
) -> dict[str, Any] | None:
    """Insert a news article. Returns None if URL already exists (dedup). data_source: finnhub, cryptopanic, or alpha_vantage."""
    if sector not in VALID_SECTORS:
        logger.warning("Invalid sector for news: %s", sector)
        return None
    if data_source not in ("finnhub", "cryptopanic", "alpha_vantage"):
        data_source = "finnhub"
    try:
        result = (
            get_client()
            .table("news_articles")
            .upsert(
                {
                    "source": source,
                    "title": title,
                    "description": description or "",
                    "url": url,
                    "sector": sector,
                    "data_source": data_source,
                    "published_at": published_at,
                },
                on_conflict="url",
                ignore_duplicates=True,
            )
            .execute()
        )
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    except Exception as e:
        logger.exception("Failed to insert news article: %s", e)
        return None


def insert_reddit_post(
    subreddit: str,
    post_id: str,
    title: str,
    body: str,
    score: int,
    num_comments: int,
    sector: str,
    created_at: str | None,
) -> dict[str, Any] | None:
    """Insert a Reddit post. Returns None if post_id already exists."""
    if sector not in VALID_SECTORS:
        logger.warning("Invalid sector for reddit: %s", sector)
        return None
    try:
        result = (
            get_client()
            .table("reddit_posts")
            .upsert(
                {
                    "subreddit": subreddit,
                    "post_id": post_id,
                    "title": title,
                    "body": body or "",
                    "score": score,
                    "num_comments": num_comments,
                    "sector": sector,
                    "created_at": created_at,
                },
                on_conflict="post_id",
                ignore_duplicates=True,
            )
            .execute()
        )
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    except Exception as e:
        logger.exception("Failed to insert reddit post: %s", e)
        return None


def insert_sentiment_score(
    source_type: str,
    source_id: str,
    ticker: str,
    sector: str,
    sentiment: float,
    confidence: float,
    model_used: str,
) -> dict[str, Any] | None:
    """Insert a sentiment score."""
    if sector not in VALID_SECTORS:
        return None
    try:
        result = (
            get_client()
            .table("sentiment_scores")
            .insert(
                {
                    "source_type": source_type,
                    "source_id": source_id,
                    "ticker": ticker,
                    "sector": sector,
                    "sentiment": sentiment,
                    "confidence": confidence,
                    "model_used": model_used,
                }
            )
            .execute()
        )
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    except Exception as e:
        logger.exception("Failed to insert sentiment score: %s", e)
        return None


def insert_trade_signal(
    ticker: str,
    sector: str,
    direction: str,
    confidence: float,
    signal_strength: float,
    source_count: int,
) -> dict[str, Any] | None:
    """Insert a trade signal."""
    try:
        result = (
            get_client()
            .table("trade_signals")
            .insert(
                {
                    "ticker": ticker,
                    "sector": sector,
                    "direction": direction,
                    "confidence": confidence,
                    "signal_strength": signal_strength,
                    "source_count": source_count,
                }
            )
            .execute()
        )
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    except Exception as e:
        logger.exception("Failed to insert trade signal: %s", e)
        return None


def log_event(level: str, component: str, message: str, metadata: dict | None = None) -> None:
    """Write to logs table."""
    try:
        get_client().table("logs").insert(
            {"level": level, "component": component, "message": message, "metadata": metadata or {}}
        ).execute()
    except Exception as e:
        logger.warning("Failed to write to logs table: %s", e)
