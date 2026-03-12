"""
Central sector definitions. All other components import from here.
Never hardcode tickers or keywords elsewhere.
"""

SECTORS = {
    "natural_resources": {
        "tickers": [
            "FCX", "NEM", "GOLD", "AA", "MP", "LAC", "ALB", "VALE", "RIO", "BHP",
            "SCCO", "HL", "PAAS",
        ],
        "keywords": [
            "mining", "lithium", "copper", "gold", "silver", "rare earth",
            "natural resources", "iron ore", "nickel", "cobalt",
        ],
        "subreddits": ["investing", "commodities", "mining"],
        "alpha_vantage": True,
    },
    "crypto": {
        "tickers": [
            "COIN", "MSTR", "MARA", "RIOT", "CLSK", "HUT", "BTBT", "SQ", "PYPL", "HOOD",
        ],
        "keywords": [
            "bitcoin", "ethereum", "crypto", "blockchain", "digital assets",
            "coinbase", "microstrategy", "crypto regulation", "ETF bitcoin",
        ],
        "subreddits": ["CryptoCurrency", "Bitcoin", "wallstreetbets"],
        "alpha_vantage": True,
    },
    "quantum_computing": {
        "tickers": [
            "IONQ", "RGTI", "QUBT", "IBM", "GOOGL", "MSFT", "QMCO", "ARQQ",
        ],
        "keywords": [
            "quantum computing", "quantum supremacy", "qubit", "quantum processor",
            "IonQ", "IBM quantum", "quantum hardware", "quantum software",
        ],
        "subreddits": ["QuantumComputing", "investing", "stocks"],
        "alpha_vantage": True,
    },
    "energy": {
        "tickers": [
            "XOM", "CVX", "COP", "SLB", "OXY", "PSX", "VLO", "NEE", "FSLR", "ENPH",
            "CCJ", "VST", "CEG",
        ],
        "keywords": [
            "oil price", "natural gas", "crude oil", "OPEC", "energy transition",
            "solar", "wind energy", "nuclear", "LNG", "refinery", "energy stocks",
        ],
        "subreddits": ["energy", "RenewableEnergy", "investing", "wallstreetbets"],
        "alpha_vantage": True,
    },
}

VALID_SECTORS = tuple(SECTORS.keys())


def get_sector_tickers(sector: str) -> list[str]:
    """Return ticker list for a sector. Empty if sector unknown."""
    return list(SECTORS.get(sector, {}).get("tickers", []))


def get_sector_keywords(sector: str) -> list[str]:
    """Return keyword list for a sector."""
    return list(SECTORS.get(sector, {}).get("keywords", []))


def get_sector_subreddits(sector: str) -> list[str]:
    """Return subreddit list for a sector (without r/ prefix)."""
    return list(SECTORS.get(sector, {}).get("subreddits", []))


def sector_uses_alpha_vantage(sector: str) -> bool:
    """Return True if sector should use Alpha Vantage as supplementary source."""
    return bool(SECTORS.get(sector, {}).get("alpha_vantage", False))


def ticker_in_sector(ticker: str, sector: str) -> bool:
    """Check if ticker is in the sector's allowed list."""
    return ticker.upper() in [t.upper() for t in get_sector_tickers(sector)]


def all_tickers() -> set[str]:
    """Return set of all tickers across sectors."""
    out = set()
    for s in SECTORS:
        out.update(get_sector_tickers(s))
    return out
