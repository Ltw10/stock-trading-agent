"""Email/Slack alerts on anomalies (e.g. large drawdown, API failures)."""

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Optional: Slack webhook URL from env
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
ALERT_EMAIL = os.getenv("ALERT_EMAIL", "")


def _send_slack(message: str, details: dict[str, Any] | None = None) -> bool:
    """Send message to Slack webhook. Returns True if sent."""
    if not SLACK_WEBHOOK_URL:
        return False
    try:
        import requests
        payload = {"text": message}
        if details:
            payload["attachments"] = [{"text": str(details)}]
        r = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        logger.warning("Slack alert failed: %s", e)
        return False


def alert_large_drawdown(pct: float, portfolio_before: float, portfolio_after: float) -> None:
    """Alert when portfolio drops >3% in one day."""
    _send_slack(
        f"Trading agent: large drawdown {pct:.1%}",
        {"before": portfolio_before, "after": portfolio_after},
    )


def alert_api_failure(service: str, error: str) -> None:
    """Alert on NewsAPI/Reddit/Alpaca failure."""
    _send_slack(f"Trading agent: {service} API failure", {"error": error})


def alert_signal_acted(signal_id: str, ticker: str, direction: str, quantity: float) -> None:
    """Optional: notify when a trade was executed (for auditing)."""
    _send_slack(
        f"Trade executed: {direction} {quantity} {ticker} (signal {signal_id})",
    )
