# News-Driven Stock Trading Agent

An automated trading agent that ingests financial news (Finnhub, CryptoPanic, Alpha Vantage) and optionally Reddit, runs an NLP pipeline, generates trade signals, and executes trades via Alpaca. Data is stored in Supabase. Designed to run as a long-running worker on Railway.

## Sectors (v1)

- **Natural Resources** — mining, lithium, copper, gold, rare earth, etc.
- **Crypto** — crypto-adjacent equities (COIN, MSTR, MARA, etc.)
- **Quantum Computing** — IONQ, IBM, GOOGL, MSFT, etc.
- **Energy** — oil, gas, solar, nuclear, refiners, utilities

All tickers, keywords, and subreddits are defined in `sectors.py`; do not hardcode them elsewhere.

## Tech Stack

| Layer        | Tool                    |
|-------------|-------------------------|
| News        | Finnhub, CryptoPanic, Alpha Vantage |
| Sentiment   | Reddit (PRAW)           |
| NLP         | FinBERT or OpenAI       |
| Database    | Supabase (PostgreSQL)   |
| Broker      | Alpaca API              |
| Hosting     | Railway                 |
| Scheduling  | APScheduler             |

## Setup

For detailed steps to create each account (Supabase, Finnhub, Reddit, Alpaca, etc.) and get API keys, see **[docs/SETUP-SERVICES.md](docs/SETUP-SERVICES.md)**.

1. **Python 3.11+**

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. **Environment**

   Copy `.env.example` to `.env` and set:

   - `FINNHUB_API_KEY` — [Finnhub](https://finnhub.io/) (company news per ticker)
   - `CRYPTOPANIC_API_KEY` — [CryptoPanic](https://cryptopanic.com/developers/api/) (crypto sector only)
   - `ALPHA_VANTAGE_API_KEY` — [Alpha Vantage](https://www.alphavantage.co/) (news & sentiment per sector)
   - `SUPABASE_URL`, `SUPABASE_KEY` — Supabase project
   - Optional: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` for Reddit sentiment (leave blank to skip)
   - `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `ALPACA_BASE_URL` — use paper URL first
   - Optionally `OPENAI_API_KEY` and `USE_OPENAI_SENTIMENT=1` for OpenAI-based sentiment

3. **Database**

   In the Supabase SQL Editor, run `db/schema.sql` to create tables.

4. **Run locally**

   ```bash
   python main.py
   ```

## Deployment (Railway)

1. Push to GitHub and connect the repo to Railway.
2. Set all variables from `.env.example` in Railway → Settings → Variables.
3. Use the `Procfile`: `worker: python main.py` (worker process, not web).
4. Deploy; the process restarts on crash or new deploy.

## Project Layout

```
├── main.py              # Entry point, scheduler
├── config.py            # Env config
├── sectors.py           # Sector definitions (single source of truth)
├── ingestion/           # Finnhub, CryptoPanic, Alpha Vantage, Reddit clients
├── nlp/                 # Sentiment, entity/ticker extraction
├── signals/             # Aggregator + velocity
├── risk/                # Guard checks, position sizing
├── execution/           # Alpaca client
├── db/                  # Supabase client + schema
└── monitoring/         # Alerts (Slack, etc.)
```

## Risk and Compliance

- Use **paper trading** (Alpaca paper URL) until you are satisfied with signal quality.
- Position size is capped per trade; sector exposure is capped at 40%.
- Stop-loss and take-profit are applied per the config.
- This is experimental software; use at your own risk. Not financial advice.

## Next Steps

See **next-steps.md** for a phased implementation and rollout checklist.
