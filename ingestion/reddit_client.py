"""Poll sector-specific subreddits via PRAW; tag and store posts in Supabase."""

import logging
from typing import Any

import config
from sectors import SECTORS, VALID_SECTORS, get_sector_tickers
from db.supabase_client import insert_reddit_post, log_event

logger = logging.getLogger(__name__)

MIN_SCORE = 10
POSTS_PER_SUBREDDIT = 25


def _reddit_client():
    """Lazy PRAW client."""
    try:
        import praw
    except ImportError:
        logger.warning("praw not installed; Reddit polling disabled")
        return None
    if not config.REDDIT_CLIENT_ID or not config.REDDIT_CLIENT_SECRET:
        logger.warning("Reddit credentials not set")
        return None
    return praw.Reddit(
        client_id=config.REDDIT_CLIENT_ID,
        client_secret=config.REDDIT_CLIENT_SECRET,
        user_agent=config.REDDIT_USER_AGENT,
    )


def _post_mentions_sector_ticker(post: Any, sector: str) -> bool:
    """True only if post title or body mentions at least one ticker from the sector's allowed list."""
    allowed = set(t.upper() for t in get_sector_tickers(sector))
    text = f"{getattr(post, 'title', '')} {getattr(post, 'selftext', '')}".upper()
    for t in allowed:
        if f"${t}" in text or f" {t} " in text or text.startswith(f"{t} ") or text.endswith(f" {t}"):
            return True
    return False


def poll_reddit() -> int:
    """
    Poll each sector's subreddits (hot + new), filter by score > 10.
    Tag with sector and insert into reddit_posts. Returns count inserted.
    """
    reddit = _reddit_client()
    if not reddit:
        return 0
    total = 0
    for sector in VALID_SECTORS:
        subreddits = SECTORS.get(sector, {}).get("subreddits", [])
        for sub_name in subreddits:
            try:
                sub = reddit.subreddit(sub_name)
                for listing in ("hot", "new"):
                    try:
                        posts = list(sub.hot(limit=POSTS_PER_SUBREDDIT)) if listing == "hot" else list(sub.new(limit=POSTS_PER_SUBREDDIT))
                    except Exception as e:
                        logger.warning("Reddit listing %s for r/%s failed: %s", listing, sub_name, e)
                        continue
                    for post in posts:
                        if getattr(post, "score", 0) < MIN_SCORE:
                            continue
                        if not _post_mentions_sector_ticker(post, sector):
                            continue
                        created = getattr(post, "created_utc", None)
                        created_at = None
                        if created:
                            from datetime import datetime, timezone
                            created_at = datetime.fromtimestamp(created, tz=timezone.utc).isoformat()
                        row = insert_reddit_post(
                            subreddit=sub_name,
                            post_id=post.id,
                            title=getattr(post, "title", "") or "",
                            body=getattr(post, "selftext", "") or "",
                            score=getattr(post, "score", 0) or 0,
                            num_comments=getattr(post, "num_comments", 0) or 0,
                            sector=sector,
                            created_at=created_at,
                        )
                        if row:
                            total += 1
            except Exception as e:
                logger.exception("Reddit poll failed for r/%s (sector %s): %s", sub_name, sector, e)
                log_event("ERROR", "ingestion", f"Reddit failed r/{sub_name}: {e}", {"sector": sector})
    logger.info("Reddit poll complete: %d new posts", total)
    return total
