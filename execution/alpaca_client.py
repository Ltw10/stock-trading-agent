"""Place and manage orders via Alpaca API; bracket orders with stop-loss and take-profit."""

import logging
from typing import Any, Optional
from uuid import UUID

import config
from db.supabase_client import get_client as get_supabase

logger = logging.getLogger(__name__)

_api = None


def get_client():
    """Singleton Alpaca API client."""
    global _api
    if _api is None:
        import alpaca_trade_api as tradeapi
        _api = tradeapi.REST(
            key_id=config.ALPACA_API_KEY,
            secret_key=config.ALPACA_SECRET_KEY,
            base_url=config.ALPACA_BASE_URL,
        )
    return _api


def get_current_quote(ticker: str) -> tuple[float, float]:
    """(bid, ask) or (0, 0) on failure."""
    try:
        q = get_client().get_latest_quote(ticker)
        bid = float(q.bid_price or 0)
        ask = float(q.ask_price or 0)
        return bid, ask
    except Exception as e:
        logger.warning("Quote failed for %s: %s", ticker, e)
        return 0.0, 0.0


def place_bracket_order(
    ticker: str,
    sector: str,
    quantity: float,
    signal_id: str | UUID,
    limit_price: float,
    stop_loss: float,
    take_profit: float,
) -> Optional[dict[str, Any]]:
    """
    Place limit order at limit_price with bracket (stop_loss, take_profit).
    Record in trades table; poll until filled or timeout.
    """
    if not quantity or quantity <= 0:
        return None
    try:
        api = get_client()
        order = api.submit_order(
            symbol=ticker,
            qty=quantity,
            side="buy",
            type="limit",
            time_in_force="day",
            limit_price=round(limit_price, 2),
            order_class="bracket",
            stop_loss=dict(stop_price=round(stop_loss, 2)),
            take_profit=dict(limit_price=round(take_profit, 2)),
        )
        oid = order.id if hasattr(order, "id") else (order.get("id") if isinstance(order, dict) else None)
        if not oid:
            return None
        # Record in trades
        supabase = get_supabase()
        supabase.table("trades").insert(
            {
                "signal_id": str(signal_id),
                "ticker": ticker,
                "sector": sector,
                "direction": "BUY",
                "quantity": quantity,
                "order_type": "limit",
                "limit_price": limit_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "alpaca_order_id": oid,
                "status": "pending",
            }
        ).execute()
        return {"order_id": oid, "ticker": ticker, "quantity": quantity}
    except Exception as e:
        logger.exception("Alpaca order failed: %s", e)
        return None


def poll_order_status(alpaca_order_id: str) -> str:
    """Get order status: pending, filled, cancelled, rejected."""
    try:
        order = get_client().get_order(alpaca_order_id)
        return (order.status or "pending").lower()
    except Exception:
        return "pending"


def cancel_order(alpaca_order_id: str) -> bool:
    """Cancel order. Returns True if cancelled."""
    try:
        get_client().cancel_order(alpaca_order_id)
        return True
    except Exception as e:
        logger.warning("Cancel order failed: %s", e)
        return False


def sync_trade_status(alpaca_order_id: str) -> None:
    """Update trades table with current order status and filled_at if filled."""
    try:
        order = get_client().get_order(alpaca_order_id)
        status = (order.status or "pending").lower()
        filled_at = None
        if hasattr(order, "filled_at") and order.filled_at:
            filled_at = order.filled_at
        supabase = get_supabase()
        supabase.table("trades").update({"status": status, "filled_at": filled_at}).eq(
            "alpaca_order_id", alpaca_order_id
        ).execute()
    except Exception as e:
        logger.warning("Sync trade status failed: %s", e)
