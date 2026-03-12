# Next Steps — Implementing the Trading Agent

This document outlines the recommended order of work to take the current scaffold to a fully working paper-trading agent, then to live trading.

**Before you start:** Set up external services using the detailed **[Service Setup Guide](docs/SETUP-SERVICES.md)**. You can skip Reddit for now; the agent runs with news only (Finnhub, CryptoPanic, Alpha Vantage).

---

## Phase 1 — Foundation (Week 1)

- [ ] **Supabase**: Create a Supabase project and run `db/schema.sql` in the SQL Editor. Confirm all tables and indexes exist. (See [Setup: Supabase](docs/SETUP-SERVICES.md#1-supabase-database).)
- [ ] **Secrets**: Copy `.env.example` to `.env` and fill in credentials. Minimum: `SUPABASE_URL`, `SUPABASE_KEY`, `FINNHUB_API_KEY`. Optional but recommended: `CRYPTOPANIC_API_KEY`, `ALPHA_VANTAGE_API_KEY`. Reddit can be left blank to skip. (See [Setup: Assembling your .env](docs/SETUP-SERVICES.md#10-assembling-your-env).)
- [ ] **Ingestion**: Run `main.py` locally. Confirm news jobs (Finnhub, CryptoPanic, Alpha Vantage) run without errors and rows appear in `news_articles` with correct `sector` and `data_source`. Reddit is optional; if not configured, the agent logs "skipping Reddit ingestion" and continues.
- [ ] **Railway**: Create a Railway project, connect the repo, set all env vars from `.env.example`, add the `Procfile` (`worker: python main.py`). Deploy and confirm the worker stays running and ingestion continues in Supabase. (See [Setup: Railway](docs/SETUP-SERVICES.md#8-railway-hosting).)

**Deliverable**: News data flowing into Supabase on a schedule, with sectors tagged correctly. Reddit can be added later if desired.

---

## Phase 2 — NLP Pipeline (Week 2)

- [ ] **Entity extraction**: Ensure `nlp/entity_extractor.py` is used after each news/Reddit insert (or in a separate job) to get sector-scoped tickers per article/post. Optionally add spaCy NER and extend `nlp/ticker_map.py` for more company names.
- [ ] **Sentiment**: Wire `nlp/sentiment.py` into the pipeline. Choose FinBERT (no key) or OpenAI (set `OPENAI_API_KEY` and `USE_OPENAI_SENTIMENT=1`). Score each piece of content for each extracted ticker and write to `sentiment_scores`.
- [ ] **Verification**: Inspect `sentiment_scores` in Supabase: correct `sector`, `source_type`, and plausible `sentiment`/`confidence`. Add a few unit tests with known bullish/bearish headlines per sector.

**Deliverable**: Every new news article and Reddit post gets tickers extracted and sentiment stored in `sentiment_scores`.

---

## Phase 3 — Signals and Risk (Week 3)

- [ ] **Aggregator**: Run `signals/aggregator.py` on a schedule (already in `main.py` every 10 min). Confirm rows in `trade_signals` with `direction` BUY/SELL when thresholds are met (e.g. sentiment ≥ 0.6 / ≤ -0.6, source_count ≥ 3). Tune weights (news 0.6, Reddit 0.4) and thresholds if needed.
- [ ] **Velocity**: Integrate `signals/velocity.py` so high-velocity tickers get the confidence boost in the aggregator. Verify mention spikes are computed from `sentiment_scores` over 15-min windows.
- [ ] **Risk manager**: Before any execution, call `risk.manager.should_allow_signal()` for every candidate signal. Implement any missing checks (e.g. Alpaca clock for market hours, daily trade count from `trades`, sector exposure from positions). Enforce 40% sector cap and position sizing from `risk.manager`.
- [ ] **Review**: Log all generated signals to `trade_signals` and review signal quality for at least one week without executing. Tune `MIN_SIGNAL_CONFIDENCE`, thresholds, and dedup window as needed.

**Deliverable**: Signals generated and logged; risk checks implemented and passing before execution.

---

## Phase 4 — Paper Trading (Week 4)

- [ ] **Execution wiring**: In `main.py`’s position monitor job (or a dedicated “act on signals” job), load unacted signals from `trade_signals`, run `should_allow_signal()` for each, then call `execution.alpaca_client.place_bracket_order()` with size from `risk.manager.position_size_usd()` and stop/take-profit from risk manager. Mark signals as acted and record in `trades`.
- [ ] **Alpaca**: Use Alpaca **paper** account only. Confirm bracket orders (limit + stop-loss + take-profit) are placed correctly; fix `execution/alpaca_client.py` for the correct Alpaca API shape if needed. Implement polling/cancel of unfilled limit orders after 5 minutes and sync `trades` with order status.
- [ ] **Run**: Run the full pipeline in paper mode for at least 2 weeks. Track in a spreadsheet or Supabase: signal accuracy (did BUY signals move up / SELL down within 24h?), win rate, average P&L per trade.
- [ ] **Tune**: Adjust confidence thresholds, weights, and risk parameters until paper results show positive expectancy. Target: >55% signal accuracy before considering live.

**Deliverable**: End-to-end paper trading with bracket orders; metrics collected and thresholds tuned.

---

## Phase 5 — Live Trading (Only after successful paper trading)

- [ ] **Go/no-go**: Only proceed if paper trading shows clear positive expectancy and you accept the risk.
- [ ] **Switch URL**: Change `ALPACA_BASE_URL` to the live Alpaca endpoint; keep all other logic unchanged.
- [ ] **Capital**: Start with a small allocation (e.g. $5,000–$10,000).
- [ ] **Monitoring**: Enable Slack (or email) alerts in `monitoring/alerts.py` for large drawdowns (e.g. >3% in one day) and API failures. Optionally alert on each executed trade for auditing.
- [ ] **Review**: Review performance weekly; be prepared to pause or revert to paper if metrics degrade.

**Deliverable**: Live trading with strict risk limits and monitoring.

---

## Optional / Ongoing

- **NLP**: Add spaCy NER in `entity_extractor.py` and expand `ticker_map.py` for better company→ticker coverage.
- **Hard drawdown limit**: In `risk/manager.py`, add a daily drawdown check (e.g. halt new trades if portfolio is down >3% in one day).
- **Per-sector accuracy**: Track signal accuracy per sector in Supabase or logs; drop or retune sectors that stay below 50%.
- **New sectors**: When the four seed sectors are stable, add new sectors by extending `sectors.py` and updating schema CHECK constraints if you add new sector names.

---

## Quick reference

| Phase | Focus | Outcome |
|-------|--------|---------|
| 1 | Supabase, ingestion, Railway | Data in DB on a schedule |
| 2 | Entity extraction, sentiment | `sentiment_scores` populated |
| 3 | Aggregation, velocity, risk | `trade_signals` + all guards in place |
| 4 | Alpaca paper, execution loop | Paper trades end-to-end; metrics |
| 5 | Live URL, small size, alerts | Live trading with monitoring |

Use this file as the checklist for implementing and rolling out the trading agent; update checkboxes as you complete each item.
