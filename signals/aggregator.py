"""Combine sentiment scores into trade signals (BUY/SELL/HOLD)."""

import logging
from datetime import datetime, timezone, timedelta

from db.supabase_client import get_client, insert_trade_signal
from sectors import VALID_SECTORS
from signals.velocity import is_high_velocity, velocity_confidence_boost

logger = logging.getLogger(__name__)

AGGREGATION_WINDOW_MINUTES = 60
NEWS_WEIGHT = 0.6
REDDIT_WEIGHT = 0.4
REDDIT_HIGH_SCORE_THRESHOLD = 1000  # Boost weight for posts with score > 1000
BUY_THRESHOLD = 0.6
SELL_THRESHOLD = -0.6
MIN_SOURCE_COUNT = 3


def _fetch_sentiment_scores_since(cutoff: datetime) -> list[dict]:
    """Fetch all sentiment_scores since cutoff with source metadata for weighting."""
    client = get_client()
    r = (
        client.table("sentiment_scores")
        .select("id, ticker, sector, sentiment, confidence, source_type, source_id, scored_at")
        .gte("scored_at", cutoff.isoformat())
        .execute()
    )
    return list(r.data or [])


def _weighted_avg_by_ticker(scores: list[dict], reddit_scores: dict[str, int]) -> dict[str, dict]:
    """
    Aggregate by (ticker, sector). Weight news 0.6, reddit 0.4; boost reddit weight if score > 1000.
    Returns dict (ticker, sector) -> {sentiment, confidence, source_count, news_count, reddit_count}.
    """
    from collections import defaultdict
    by_key: dict[tuple[str, str], list[tuple[float, float, float]]] = defaultdict(list)
    for row in scores:
        ticker = row.get("ticker")
        sector = row.get("sector")
        if not ticker or not sector:
            continue
        sent = float(row.get("sentiment", 0))
        conf = float(row.get("confidence", 0.5))
        stype = row.get("source_type") or "news"
        src_id = row.get("source_id")
        w = NEWS_WEIGHT if stype == "news" else REDDIT_WEIGHT
        if stype == "reddit" and src_id and reddit_scores.get(src_id, 0) > REDDIT_HIGH_SCORE_THRESHOLD:
            w *= 1.5  # Boost high-score Reddit
        by_key[(ticker, sector)].append((sent, conf, w))
    out = {}
    for (ticker, sector), items in by_key.items():
        if len(items) < MIN_SOURCE_COUNT:
            continue
        total_w = sum(i[2] for i in items)
        if total_w <= 0:
            continue
        weighted_sent = sum(s * c * w for s, c, w in items) / total_w
        avg_conf = sum(c for _, c, _ in items) / len(items)
        out[(ticker, sector)] = {
            "sentiment": weighted_sent,
            "confidence": avg_conf,
            "source_count": len(items),
        }
    return out


def _get_reddit_scores_for_posts(post_ids: list[str]) -> dict[str, int]:
    """Fetch score for reddit_posts by id."""
    if not post_ids:
        return {}
    client = get_client()
    r = client.table("reddit_posts").select("id, score").in_("id", post_ids).execute()
    return {row["id"]: row.get("score", 0) for row in (r.data or []) if row.get("id")}


def run_aggregation() -> int:
    """
    Aggregate sentiment in last 60 minutes; generate trade_signals for BUY/SELL.
    Require source_count >= 3 and sentiment thresholds. Apply velocity boost if applicable.
    Returns number of signals generated.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=AGGREGATION_WINDOW_MINUTES)
    scores = _fetch_sentiment_scores_since(cutoff)
    reddit_source_ids = [s["source_id"] for s in scores if s.get("source_type") == "reddit" and s.get("source_id")]
    reddit_scores = _get_reddit_scores_for_posts(reddit_source_ids)
    aggregates = _weighted_avg_by_ticker(scores, reddit_scores)
    generated = 0
    for (ticker, sector), agg in aggregates.items():
        sent = agg["sentiment"]
        conf = agg["confidence"]
        src_count = agg["source_count"]
        if is_high_velocity(ticker, now):
            conf = min(1.0, conf + velocity_confidence_boost())
        direction = "HOLD"
        if sent >= BUY_THRESHOLD:
            direction = "BUY"
        elif sent <= SELL_THRESHOLD:
            direction = "SELL"
        if direction == "HOLD":
            continue
        signal_strength = abs(sent)
        row = insert_trade_signal(
            ticker=ticker,
            sector=sector,
            direction=direction,
            confidence=conf,
            signal_strength=signal_strength,
            source_count=src_count,
        )
        if row:
            generated += 1
            logger.info("Signal: %s %s %s (confidence=%.2f)", direction, ticker, sector, conf)
    return generated
