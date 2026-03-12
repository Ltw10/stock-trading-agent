"""Detect mention spikes: if mentions > 3x the 1-hour average, flag as high-velocity."""

import logging
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from db.supabase_client import get_client

logger = logging.getLogger(__name__)

WINDOW_MINUTES = 15
LOOKBACK_HOURS = 1
SPIKE_MULTIPLIER = 3.0


def get_mention_counts_since(cutoff: datetime) -> dict[str, list[tuple[datetime, int]]]:
    """
    Get per-ticker mention counts per 15-min window since cutoff.
    Returns dict ticker -> [(window_start, count), ...].
    """
    client = get_client()
    # sentiment_scores: ticker, scored_at
    r = (
        client.table("sentiment_scores")
        .select("ticker, scored_at")
        .gte("scored_at", cutoff.isoformat())
        .execute()
    )
    by_ticker: dict[str, list[datetime]] = defaultdict(list)
    for row in r.data or []:
        t = row.get("ticker")
        ts = row.get("scored_at")
        if t and ts:
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                by_ticker[t].append(dt)
            except Exception:
                pass
    # Bucket into 15-min windows
    out: dict[str, list[tuple[datetime, int]]] = {}
    for ticker, times in by_ticker.items():
        buckets: dict[datetime, int] = defaultdict(int)
        for dt in times:
            # Floor to 15 min
            minute = (dt.minute // WINDOW_MINUTES) * WINDOW_MINUTES
            window = dt.replace(minute=minute, second=0, microsecond=0)
            buckets[window] += 1
        out[ticker] = sorted(buckets.items())
    return out


def is_high_velocity(ticker: str, now: datetime | None = None) -> bool:
    """
    True if current 15-min mention count is > 3x the 1-hour average.
    """
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=LOOKBACK_HOURS)
    counts = get_mention_counts_since(cutoff)
    ticker_counts = counts.get(ticker, [])
    if not ticker_counts:
        return False
    current_window_minute = (now.minute // WINDOW_MINUTES) * WINDOW_MINUTES
    current_window = now.replace(minute=current_window_minute, second=0, microsecond=0)
    current_count = sum(c for w, c in ticker_counts if w == current_window)
    total = sum(c for _, c in ticker_counts)
    windows = len(ticker_counts) or 1
    avg = total / windows
    if avg <= 0:
        return False
    return current_count >= SPIKE_MULTIPLIER * avg


def velocity_confidence_boost() -> float:
    """Boost to add to confidence when high-velocity. Plan: 0.1."""
    return 0.1
