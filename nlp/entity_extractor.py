"""Extract company names and $TICKER mentions from text; map to sector-allowed tickers."""

import re
import logging
from typing import Optional

from sectors import get_sector_tickers
from nlp.ticker_map import resolve_ticker, COMPANY_TO_TICKER

logger = logging.getLogger(__name__)

# Match $TICKER (1–5 uppercase letters)
TICKER_PATTERN = re.compile(r"\$([A-Z]{1,5})\b", re.IGNORECASE)


def _extract_tickers_from_text_only(text: str, sector: str) -> list[str]:
    """Extract tickers from text only (no context). Hard-filter to sector allowed list."""
    if not (text or "").strip():
        return []
    text = text or ""
    allowed = set(t.upper() for t in get_sector_tickers(sector))
    found: set[str] = set()
    for m in TICKER_PATTERN.finditer(text):
        sym = m.group(1).upper()
        if sym in allowed:
            found.add(sym)
    for name, ticker in COMPANY_TO_TICKER.items():
        if name in text.lower() and ticker.upper() in allowed:
            found.add(ticker.upper())
    return list(found)


def extract_tickers_from_text(
    text: str,
    sector: str,
    ticker_context: Optional[str] = None,
) -> list[str]:
    """
    Extract ticker symbols. When ticker_context is provided (e.g. Finnhub fetch by ticker),
    use it as the primary entity if it is in the sector's allowed list. Only fall back to
    text extraction when no ticker context (e.g. Reddit posts). All resolved tickers are
    hard-filtered against the sector's allowed list; anything outside is discarded.
    """
    allowed = set(t.upper() for t in get_sector_tickers(sector))
    found: set[str] = set()
    if ticker_context and (ticker_context or "").strip():
        ctx = ticker_context.strip().upper()
        if ctx in allowed:
            found.add(ctx)
    from_text = _extract_tickers_from_text_only(text or "", sector)
    found.update(from_text)
    return list(found)


def extract_tickers_with_entity(
    text: str,
    sector: str,
    ticker_context: Optional[str] = None,
) -> list[tuple[str, Optional[str]]]:
    """
    Extract (ticker, company_name_or_none). When ticker_context is provided, use it as
    primary; otherwise use NER/text extraction only. Hard-filter all to sector allowed list.
    """
    allowed = set(t.upper() for t in get_sector_tickers(sector))
    result: list[tuple[str, Optional[str]]] = []
    if ticker_context and (ticker_context or "").strip():
        ctx = ticker_context.strip().upper()
        if ctx in allowed:
            result.append((ctx, None))
    for m in TICKER_PATTERN.finditer(text or ""):
        sym = m.group(1).upper()
        if sym in allowed and (sym, None) not in result and not any(r[0] == sym for r in result):
            result.append((sym, None))
    for name, ticker in COMPANY_TO_TICKER.items():
        if name in (text or "").lower() and ticker.upper() in allowed:
            if not any(r[0] == ticker.upper() for r in result):
                result.append((ticker.upper(), name))
    return result
