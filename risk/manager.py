"""Position sizing, blackout rules, dedup, sector cap. All guard checks before execution."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import config
from sectors import ticker_in_sector, get_sector_tickers, SECTORS, VALID_SECTORS

logger = logging.getLogger(__name__)


def check_ticker_in_sector(ticker: str, sector: str) -> bool:
    """Ticker must be in sector's allowed list."""
    return ticker_in_sector(ticker, sector)


def check_not_duplicate_signal(
    ticker: str,
    sector: str,
    direction: str,
    window_minutes: int | None = None,
    db_client=None,
) -> bool:
    """True if no same (ticker, sector, direction) signal within window."""
    window_minutes = window_minutes or config.SIGNAL_DEDUP_WINDOW_MINUTES
    if not db_client:
        try:
            from db.supabase_client import get_client
            db_client = get_client()
        except Exception:
            return True
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=window_minutes)).isoformat()
    r = (
        db_client.table("trade_signals")
        .select("id")
        .eq("ticker", ticker)
        .eq("sector", sector)
        .eq("direction", direction)
        .gte("generated_at", cutoff)
        .execute()
    )
    return (len(r.data or []) == 0)


def check_daily_trade_count(db_client=None) -> bool:
    """True if daily trade count < MAX_DAILY_TRADES."""
    if not db_client:
        from db.supabase_client import get_client
        db_client = get_client()
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    r = db_client.table("trades").select("id", count="exact").gte("created_at", today_start).execute()
    count = r.count if hasattr(r, "count") and r.count is not None else len(r.data or [])
    return count < config.MAX_DAILY_TRADES


def check_market_open(alpaca_client=None) -> bool:
    """Use Alpaca calendar/clock to see if market is open."""
    if not alpaca_client:
        try:
            from execution.alpaca_client import get_client
            alpaca_client = get_client()
        except Exception:
            return False
    try:
        clock = alpaca_client.get_clock()
        return clock.is_open if hasattr(clock, "is_open") else False
    except Exception as e:
        logger.warning("Alpaca clock check failed: %s", e)
        return False


def check_confidence(confidence: float) -> bool:
    """Confidence >= MIN_SIGNAL_CONFIDENCE."""
    return confidence >= config.MIN_SIGNAL_CONFIDENCE


def check_not_already_in_position(ticker: str, alpaca_client=None) -> bool:
    """True if we don't already have a position in this ticker."""
    if not alpaca_client:
        try:
            from execution.alpaca_client import get_client
            alpaca_client = get_client()
        except Exception:
            return True
    try:
        pos = alpaca_client.get_position(ticker)
        return pos is None or (getattr(pos, "qty", 0) or 0) == 0
    except Exception:
        return True  # No position


def get_sector_exposure_pct(alpaca_client=None) -> dict[str, float]:
    """Return sector -> fraction of total portfolio value (by position)."""
    if not alpaca_client:
        from execution.alpaca_client import get_client
        alpaca_client = get_client()
    try:
        positions = alpaca_client.list_positions()
        total = 0.0
        by_sector: dict[str, float] = {s: 0.0 for s in VALID_SECTORS}
        for p in positions or []:
            sym = getattr(p, "symbol", None) or (p.get("symbol") if isinstance(p, dict) else None)
            val = float(getattr(p, "market_value", 0) or p.get("market_value", 0) or 0)
            total += val
            for sector in VALID_SECTORS:
                if sym and sym.upper() in [t.upper() for t in get_sector_tickers(sector)]:
                    by_sector[sector] += val
                    break
        if total <= 0:
            return by_sector
        return {s: by_sector[s] / total for s in VALID_SECTORS}
    except Exception as e:
        logger.warning("Sector exposure check failed: %s", e)
        return {s: 0.0 for s in VALID_SECTORS}


def check_sector_cap(sector: str, alpaca_client=None) -> bool:
    """No single sector should exceed 40% of total open position value."""
    exposure = get_sector_exposure_pct(alpaca_client)
    return (exposure.get(sector, 0) or 0) <= config.MAX_SECTOR_EXPOSURE_PCT


def position_size_usd(
    portfolio_value: float,
    current_price: float,
    sector: str | None = None,
) -> float:
    """
    portfolio_value * (effective pct) / current_price -> quantity in shares (fractional).
    Sector cap: quantum_computing uses half of MAX_POSITION_SIZE_PCT due to lower liquidity
    (e.g. RGTI, QUBT, ARQQ).
    """
    pct = config.MAX_POSITION_SIZE_PCT
    if sector == "quantum_computing":
        pct = pct * 0.5
    return (portfolio_value * pct) / current_price if current_price > 0 else 0.0


def stop_loss_price(entry_price: float, direction: str) -> float:
    """-3% from entry. For SELL/short it would be opposite; we assume long-only BUY."""
    return entry_price * (1.0 - config.STOP_LOSS_PCT)


def take_profit_price(entry_price: float) -> float:
    """+6% from entry."""
    return entry_price * (1.0 + config.TAKE_PROFIT_PCT)


def should_allow_signal(
    ticker: str,
    sector: str,
    direction: str,
    confidence: float,
    alpaca_client=None,
    db_client=None,
) -> tuple[bool, str]:
    """
    Run all guard checks. Returns (allowed: bool, reason: str).
    """
    if not check_ticker_in_sector(ticker, sector):
        return False, "ticker not in sector"
    if not check_confidence(confidence):
        return False, "confidence below threshold"
    if direction == "BUY" and not check_not_already_in_position(ticker, alpaca_client):
        return False, "already in position"
    if not check_not_duplicate_signal(ticker, sector, direction, db_client=db_client):
        return False, "duplicate signal in window"
    if not check_daily_trade_count(db_client):
        return False, "max daily trades reached"
    if not check_market_open(alpaca_client):
        return False, "market closed"
    if not check_sector_cap(sector, alpaca_client):
        return False, "sector exposure cap"
    return True, "ok"
