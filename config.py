"""Load configuration from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


def _env(key: str, default: str = "") -> str:
    """Get env var and strip whitespace (avoids issues with Railway/paste)."""
    return (os.getenv(key, default) or "").strip()


# Finnhub (primary news per ticker)
FINNHUB_API_KEY = _env("FINNHUB_API_KEY")

# CryptoPanic (crypto sector supplementary)
CRYPTOPANIC_API_KEY = _env("CRYPTOPANIC_API_KEY")

# Alpha Vantage (supplementary market news & sentiment per sector)
ALPHA_VANTAGE_API_KEY = _env("ALPHA_VANTAGE_API_KEY")

# Reddit
REDDIT_CLIENT_ID = _env("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = _env("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = _env("REDDIT_USER_AGENT") or "trading-bot/1.0"

# Supabase
SUPABASE_URL = _env("SUPABASE_URL")
SUPABASE_KEY = _env("SUPABASE_KEY")

# Alpaca
ALPACA_API_KEY = _env("ALPACA_API_KEY")
ALPACA_SECRET_KEY = _env("ALPACA_SECRET_KEY")
ALPACA_BASE_URL = _env("ALPACA_BASE_URL") or "https://paper-api.alpaca.markets"

# NLP
OPENAI_API_KEY = _env("OPENAI_API_KEY")
USE_OPENAI_SENTIMENT = bool(os.getenv("USE_OPENAI_SENTIMENT", "0").lower() in ("1", "true", "yes"))

# Risk
MAX_POSITION_SIZE_PCT = float(os.getenv("MAX_POSITION_SIZE_PCT", "0.05"))
MAX_DAILY_TRADES = int(os.getenv("MAX_DAILY_TRADES", "10"))
MIN_SIGNAL_CONFIDENCE = float(os.getenv("MIN_SIGNAL_CONFIDENCE", "0.65"))
SIGNAL_DEDUP_WINDOW_MINUTES = int(os.getenv("SIGNAL_DEDUP_WINDOW_MINUTES", "30"))
MAX_SECTOR_EXPOSURE_PCT = float(os.getenv("MAX_SECTOR_EXPOSURE_PCT", "0.40"))
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "0.03"))
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "0.06"))

# Scheduler intervals (minutes)
NEWS_POLL_INTERVAL_MIN = 15
REDDIT_POLL_INTERVAL_MIN = 5
SIGNAL_AGGREGATION_INTERVAL_MIN = 10
POSITION_MONITOR_INTERVAL_MIN = 2

# Execution
LIMIT_ORDER_TIMEOUT_SEC = 300
ORDER_STATUS_POLL_INTERVAL_SEC = 30

# Daily performance email
REPORT_EMAIL_TO = _env("REPORT_EMAIL_TO")
REPORT_EMAIL_FROM = _env("REPORT_EMAIL_FROM")
SMTP_HOST = _env("SMTP_HOST") or "smtp.gmail.com"
SMTP_PORT = int(os.getenv("SMTP_PORT", "587") or "587")
SMTP_USER = _env("SMTP_USER")
SMTP_PASSWORD = _env("SMTP_PASSWORD")  # Gmail: use App Password
DAILY_REPORT_HOUR = int(os.getenv("DAILY_REPORT_HOUR", "8"))  # 24h, server timezone
DAILY_REPORT_MINUTE = int(os.getenv("DAILY_REPORT_MINUTE", "0"))
