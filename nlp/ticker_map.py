"""Company name → ticker symbol lookup, sector-scoped using sectors.py."""

from sectors import SECTORS, get_sector_tickers


# Common company name → ticker (used across sectors where applicable)
COMPANY_TO_TICKER: dict[str, str] = {
    "freeport-mcmoran": "FCX",
    "freeport": "FCX",
    "newmont": "NEM",
    "barrick": "GOLD",
    "alcoa": "AA",
    "mp materials": "MP",
    "lithium americas": "LAC",
    "albemarle": "ALB",
    "vale": "VALE",
    "rio tinto": "RIO",
    "bhp": "BHP",
    "southern copper": "SCCO",
    "hecla": "HL",
    "pan american silver": "PAAS",
    "coinbase": "COIN",
    "microstrategy": "MSTR",
    "marathon digital": "MARA",
    "riot platforms": "RIOT",
    "cleanspark": "CLSK",
    "hut 8": "HUT",
    "bit digital": "BTBT",
    "square": "SQ",
    "block": "SQ",
    "paypal": "PYPL",
    "robinhood": "HOOD",
    "ionq": "IONQ",
    "rigetti": "RGTI",
    "quantum computing inc": "QUBT",
    "ibm": "IBM",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "microsoft": "MSFT",
    "quantum corp": "QMCO",
    "arqit": "ARQQ",
    "exxon": "XOM",
    "exxonmobil": "XOM",
    "chevron": "CVX",
    "conocophillips": "COP",
    "schlumberger": "SLB",
    "slb": "SLB",
    "occidental": "OXY",
    "phillips 66": "PSX",
    "valero": "VLO",
    "nextera": "NEE",
    "first solar": "FSLR",
    "enphase": "ENPH",
    "cameco": "CCJ",
    "vistra": "VST",
    "constellation energy": "CEG",
}


def resolve_ticker(company_or_ticker: str, sector: str) -> str | None:
    """
    Resolve company name or $TICKER to ticker symbol.
    Only returns a ticker if it is in the sector's allowed list; otherwise None.
    """
    allowed = set(t.upper() for t in get_sector_tickers(sector))
    raw = (company_or_ticker or "").strip().upper()
    if not raw:
        return None
    if raw.startswith("$"):
        raw = raw[1:]
    if raw in allowed:
        return raw
    key = company_or_ticker.strip().lower()
    ticker = COMPANY_TO_TICKER.get(key)
    if ticker and ticker.upper() in allowed:
        return ticker.upper()
    return None
