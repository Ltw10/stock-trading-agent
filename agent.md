# Agent Instructions — Stock Trading Agent

This file gives AI agents and developers consistent context for working on the repo.

## Project purpose

News-driven stock trading agent: ingest news (Finnhub, CryptoPanic, Alpha Vantage) and Reddit, score sentiment per sector/ticker, aggregate into BUY/SELL signals, run risk checks, and execute via Alpaca. Data lives in Supabase; app runs as a worker on Railway.

## Conventions

- **Single source of truth for universe**: All tickers, keywords, and subreddits live in `sectors.py`. No hardcoding of tickers or keywords in other modules.
- **Sectors**: Exactly four in v1: `natural_resources`, `crypto`, `quantum_computing`, `energy`. Use the constants and helpers from `sectors.py` (e.g. `get_sector_tickers`, `ticker_in_sector`).
- **Database**: Tables and semantics are defined in `db/schema.sql`. Use the Supabase client in `db/supabase_client.py` for inserts/upserts; respect unique constraints (e.g. `news_articles.url`, `reddit_posts.post_id`).
- **Config**: All env-driven settings in `config.py`; no raw `os.getenv` elsewhere for app config.
- **Logging**: Use Python `logging`; critical events can also be written to the `logs` table via `db.supabase_client.log_event`.
- **Risk**: Every signal must pass `risk.manager.should_allow_signal()` before execution. Do not bypass risk checks.

## Key files

| File | Role |
|------|------|
| `sectors.py` | Sector definitions; import for tickers/keywords/subreddits |
| `config.py` | Env vars (API keys, risk params, intervals) |
| `db/schema.sql` | Supabase table definitions; run once per project |
| `db/supabase_client.py` | Supabase client and insert helpers |
| `ingestion/finnhub_client.py` | Finnhub company-news per ticker |
| `ingestion/cryptopanic_client.py` | CryptoPanic (crypto sector only) |
| `ingestion/alpha_vantage_client.py` | Alpha Vantage news & sentiment per sector |
| `ingestion/reddit_client.py` | PRAW poll by sector subreddits (ticker-filtered) |
| `nlp/entity_extractor.py` | Ticker from context or text; sector-scoped |
| `nlp/sentiment.py` | FinBERT or OpenAI sentiment; write to `sentiment_scores` |
| `signals/aggregator.py` | Combine scores → `trade_signals` (BUY/SELL/HOLD) |
| `signals/velocity.py` | Mention spike detection; confidence boost |
| `risk/manager.py` | Guard checks, position size, 40% sector cap, quantum half-size |
| `execution/alpaca_client.py` | Place bracket orders; update `trades` |
| `main.py` | APScheduler jobs; graceful SIGTERM/SIGINT |

## When adding features

- **New sector**: Extend `sectors.py` only; ensure schema and any CHECK constraints include the new sector if applicable.
- **New env var**: Add to `config.py` and `.env.example` with a short comment.
- **New table or column**: Add migration (or append) to `db/schema.sql` and document in comments.
- **New API client**: Prefer lazy init and clear error handling; log and optionally `log_event` on failure so monitoring can alert.

## Testing and safety

- Prefer **paper trading** (Alpaca paper URL) for all development and tuning.
- Do not commit `.env` or any secrets; keep `.env.example` up to date.
- Run the Supabase schema once per environment; avoid duplicate table creation in production.

## Phasing

Implementation is phased: foundation (ingestion + DB) → NLP → signals + risk → paper execution → live (see `plan.md` and `next-steps.md`).
