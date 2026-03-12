"""
News-driven stock trading agent.
Entry point: starts APScheduler for ingestion, NLP, signals, and execution.
"""

import logging
import signal
import sys
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

import config
from ingestion.finnhub_client import poll_finnhub
from ingestion.cryptopanic_client import poll_cryptopanic
from ingestion.alpha_vantage_client import poll_alpha_vantage
from signals.aggregator import run_aggregation
from db.supabase_client import log_event
from monitoring.daily_report import send_daily_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

scheduler = BlockingScheduler()
shutdown_requested = False


def _poll_news_job():
    try:
        poll_finnhub()
        poll_cryptopanic()
        poll_alpha_vantage()
    except Exception as e:
        logger.exception("News poll job failed: %s", e)
        log_event("ERROR", "ingestion", f"News poll failed: {e}", None)


def _poll_reddit_job():
    try:
        from ingestion.reddit_client import poll_reddit
        poll_reddit()
    except Exception as e:
        logger.exception("Reddit poll job failed: %s", e)
        log_event("ERROR", "ingestion", f"Reddit poll failed: {e}", None)


def _aggregation_job():
    try:
        run_aggregation()
    except Exception as e:
        logger.exception("Signal aggregation job failed: %s", e)
        log_event("ERROR", "signal", f"Aggregation failed: {e}", None)


def _position_monitor_job():
    """Every 2 min during market hours: sync order status, consider acting on signals."""
    try:
        # TODO: fetch unacted signals, run risk checks, call execution
        pass
    except Exception as e:
        logger.exception("Position monitor job failed: %s", e)


def _daily_report_job():
    """Send daily performance email to REPORT_EMAIL_TO."""
    try:
        send_daily_report()
    except Exception as e:
        logger.exception("Daily report job failed: %s", e)
        log_event("ERROR", "monitoring", f"Daily report failed: {e}", None)


def _graceful_shutdown(signum=None, frame=None):
    global shutdown_requested
    shutdown_requested = True
    logger.info("Shutdown requested (SIGTERM/SIGINT); stopping scheduler.")
    scheduler.shutdown(wait=False)


def main():
    signal.signal(signal.SIGTERM, _graceful_shutdown)
    signal.signal(signal.SIGINT, _graceful_shutdown)

    # News: every 15 min
    scheduler.add_job(
        _poll_news_job,
        IntervalTrigger(minutes=config.NEWS_POLL_INTERVAL_MIN),
        id="news",
    )
    # Reddit: every 5 min (only when credentials are set; skip if not configured)
    if config.REDDIT_CLIENT_ID and config.REDDIT_CLIENT_SECRET:
        scheduler.add_job(
            _poll_reddit_job,
            IntervalTrigger(minutes=config.REDDIT_POLL_INTERVAL_MIN),
            id="reddit",
        )
    else:
        logger.info("Reddit credentials not set; skipping Reddit ingestion.")
    # Signals: every 10 min
    scheduler.add_job(
        _aggregation_job,
        IntervalTrigger(minutes=config.SIGNAL_AGGREGATION_INTERVAL_MIN),
        id="signals",
    )
    # Position monitor: every 2 min
    scheduler.add_job(
        _position_monitor_job,
        IntervalTrigger(minutes=config.POSITION_MONITOR_INTERVAL_MIN),
        id="position_monitor",
    )
    # Daily performance email (default 8:00 AM server time)
    scheduler.add_job(
        _daily_report_job,
        CronTrigger(hour=config.DAILY_REPORT_HOUR, minute=config.DAILY_REPORT_MINUTE),
        id="daily_report",
    )

    # Run once at startup (optional)
    try:
        _poll_news_job()
        if config.REDDIT_CLIENT_ID and config.REDDIT_CLIENT_SECRET:
            _poll_reddit_job()
    except Exception as e:
        logger.warning("Startup poll error: %s", e)

    reddit_note = f", Reddit={config.REDDIT_POLL_INTERVAL_MIN}m" if (config.REDDIT_CLIENT_ID and config.REDDIT_CLIENT_SECRET) else ""
    logger.info("Scheduler started. News=%dm%s, Signals=%dm, Monitor=%dm, Daily report=%s:%02d.",
                config.NEWS_POLL_INTERVAL_MIN, reddit_note,
                config.SIGNAL_AGGREGATION_INTERVAL_MIN,
                config.POSITION_MONITOR_INTERVAL_MIN,
                config.DAILY_REPORT_HOUR, config.DAILY_REPORT_MINUTE)
    scheduler.start()


if __name__ == "__main__":
    main()
