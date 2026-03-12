# News-Driven Stock Trading Agent — Build Plan

## Overview

Build an automated trading agent that ingests financial news from **NewsAPI** and sentiment signals from **Reddit**, processes them through an NLP pipeline, generates trade signals, and executes trades via **Alpaca**. All data is persisted in **Supabase**. The system runs as a long-running Python process hosted on **Railway**.

The agent is scoped to four sectors in v1: **Natural Resources**, **Crypto**, **Quantum Computing**, and **Energy**. This keeps the ticker universe small and well-defined, improves signal quality, and makes it easier to tune sector-specific keywords and subreddits before expanding coverage.

---

## Sector Universe

### Natural Resources

**Keywords**: `mining`, `lithium`, `copper`, `gold`, `silver`, `rare earth`, `natural resources`, `iron ore`, `nickel`, `cobalt`
**Tickers**: `FCX`, `NEM`, `GOLD`, `AA`, `MP`, `LAC`, `ALB`, `VALE`, `RIO`, `BHP`, `SCCO`, `HL`, `PAAS`
**Subreddits**: `r/investing`, `r/commodities`, `r/mining`

### Crypto (Crypto-adjacent equities only — Alpaca trades stocks, not coins)

**Keywords**: `bitcoin`, `ethereum`, `crypto`, `blockchain`, `digital assets`, `coinbase`, `microstrategy`, `crypto regulation`, `ETF bitcoin`
**Tickers**: `COIN`, `MSTR`, `MARA`, `RIOT`, `CLSK`, `HUT`, `BTBT`, `SQ`, `PYPL`, `HOOD`
**Subreddits**: `r/CryptoCurrency`, `r/Bitcoin`, `r/wallstreetbets`

### Quantum Computing

**Keywords**: `quantum computing`, `quantum supremacy`, `qubit`, `quantum processor`, `IonQ`, `IBM quantum`, `quantum hardware`, `quantum software`
**Tickers**: `IONQ`, `RGTI`, `QUBT`, `IBM`, `GOOGL`, `MSFT`, `QMCO`, `ARQQ`
**Subreddits**: `r/QuantumComputing`, `r/investing`, `r/stocks`

### Energy

**Keywords**: `oil price`, `natural gas`, `crude oil`, `OPEC`, `energy transition`, `solar`, `wind energy`, `nuclear`, `LNG`, `refinery`, `energy stocks`
**Tickers**: `XOM`, `CVX`, `COP`, `SLB`, `OXY`, `PSX`, `VLO`, `NEE`, `FSLR`, `ENPH`, `CCJ`, `VST`, `CEG`
**Subreddits**: `r/energy`, `r/RenewableEnergy`, `r/investing`, `r/wallstreetbets`

---

## Tech Stack

| Layer           | Tool                                   |
| --------------- | -------------------------------------- |
| News Data       | NewsAPI (Developer tier)               |
| Sentiment Data  | Reddit via PRAW                        |
| NLP/Scoring     | FinBERT (HuggingFace) or OpenAI API    |
| Database        | Supabase (PostgreSQL)                  |
| Broker          | Alpaca API                             |
| Hosting         | Railway                                |
| Language        | Python 3.11+                           |
| Task Scheduling | APScheduler (in-process)               |
| Logging         | Python `logging` + Supabase logs table |

---

## Repository Structure

```
trading-agent/
├── main.py                  # Entry point, starts scheduler
├── config.py                # Loads env vars
├── sectors.py               # Sector definitions: tickers, keywords, subreddits
├── requirements.txt
├── .env.example
│
├── ingestion/
│   ├── newsapi_client.py    # Polls NewsAPI filtered by sector keywords
│   └── reddit_client.py     # Polls sector-specific subreddits via PRAW
│
├── nlp/
│   ├── sentiment.py         # FinBERT or OpenAI scoring
│   ├── entity_extractor.py  # Extract company names → tickers
│   └── ticker_map.py        # Company name → ticker symbol lookup (sector-scoped)
│
├── signals/
│   ├── aggregator.py        # Combines scores into a signal
│   └── velocity.py          # Detects mention spikes
│
├── risk/
│   └── manager.py           # Position sizing, blackout rules, dedup
│
├── execution/
│   └── alpaca_client.py     # Places/manages orders via Alpaca API
│
├── db/
│   ├── supabase_client.py   # Supabase connection + helpers
│   └── schema.sql           # All table definitions
│
└── monitoring/
    └── alerts.py            # Email/Slack alerts on anomalies
```

---

## Supabase Schema

Create the following tables in Supabase. Run `schema.sql` against your project.

```sql
-- Raw incoming articles from NewsAPI
CREATE TABLE news_articles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source TEXT,
  title TEXT,
  description TEXT,
  url TEXT UNIQUE,
  sector TEXT CHECK (sector IN ('natural_resources', 'crypto', 'quantum_computing', 'energy')),
  published_at TIMESTAMPTZ,
  fetched_at TIMESTAMPTZ DEFAULT now()
);

-- Raw Reddit posts/comments
CREATE TABLE reddit_posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subreddit TEXT,
  post_id TEXT UNIQUE,
  title TEXT,
  body TEXT,
  score INT,
  num_comments INT,
  sector TEXT CHECK (sector IN ('natural_resources', 'crypto', 'quantum_computing', 'energy')),
  created_at TIMESTAMPTZ,
  fetched_at TIMESTAMPTZ DEFAULT now()
);

-- NLP sentiment scores applied to each piece of content
CREATE TABLE sentiment_scores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_type TEXT CHECK (source_type IN ('news', 'reddit')),
  source_id UUID,  -- FK to news_articles.id or reddit_posts.id
  ticker TEXT,
  sector TEXT CHECK (sector IN ('natural_resources', 'crypto', 'quantum_computing', 'energy')),
  sentiment FLOAT,         -- -1.0 (bearish) to 1.0 (bullish)
  confidence FLOAT,        -- 0.0 to 1.0
  model_used TEXT,
  scored_at TIMESTAMPTZ DEFAULT now()
);

-- Aggregated trade signals generated by the signal engine
CREATE TABLE trade_signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT,
  sector TEXT CHECK (sector IN ('natural_resources', 'crypto', 'quantum_computing', 'energy')),
  direction TEXT CHECK (direction IN ('BUY', 'SELL', 'HOLD')),
  confidence FLOAT,
  signal_strength FLOAT,
  source_count INT,        -- How many articles/posts contributed
  generated_at TIMESTAMPTZ DEFAULT now(),
  acted_on BOOLEAN DEFAULT false
);

-- All orders sent to Alpaca
CREATE TABLE trades (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  signal_id UUID REFERENCES trade_signals(id),
  ticker TEXT,
  sector TEXT,
  direction TEXT,
  quantity FLOAT,
  order_type TEXT,
  limit_price FLOAT,
  stop_loss FLOAT,
  take_profit FLOAT,
  alpaca_order_id TEXT UNIQUE,
  status TEXT,             -- pending, filled, cancelled, rejected
  filled_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- System event log
CREATE TABLE logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  level TEXT,              -- INFO, WARNING, ERROR
  component TEXT,          -- ingestion, nlp, signal, execution
  message TEXT,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## Environment Variables

Create a `.env` file (never commit this). See `.env.example`:

```env
# NewsAPI
NEWSAPI_KEY=your_newsapi_key

# Reddit (create app at reddit.com/prefs/apps)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=trading-bot/1.0

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key

# Alpaca (use paper keys first)
ALPACA_API_KEY=your_alpaca_key
ALPACA_SECRET_KEY=your_alpaca_secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets  # Switch to live when ready

# NLP (choose one)
OPENAI_API_KEY=your_openai_key   # If using OpenAI for sentiment
# or use FinBERT locally (no key needed)

# Risk Parameters
MAX_POSITION_SIZE_PCT=0.05       # Max 5% of portfolio per trade
MAX_DAILY_TRADES=10
MIN_SIGNAL_CONFIDENCE=0.65
SIGNAL_DEDUP_WINDOW_MINUTES=30
```

---

## Component Specifications

### 0. `sectors.py`

Central configuration file that defines the full universe for each sector. All other components import from here — never hardcode tickers or keywords elsewhere.

```python
SECTORS = {
    "natural_resources": {
        "tickers": ["FCX","NEM","GOLD","AA","MP","LAC","ALB","VALE","RIO","BHP","SCCO","HL","PAAS"],
        "keywords": ["mining","lithium","copper","gold","silver","rare earth","iron ore","nickel","cobalt"],
        "subreddits": ["investing","commodities","mining"],
    },
    "crypto": {
        "tickers": ["COIN","MSTR","MARA","RIOT","CLSK","HUT","BTBT","SQ","PYPL","HOOD"],
        "keywords": ["bitcoin","ethereum","crypto","blockchain","digital assets","coinbase","microstrategy","bitcoin ETF"],
        "subreddits": ["CryptoCurrency","Bitcoin","wallstreetbets"],
    },
    "quantum_computing": {
        "tickers": ["IONQ","RGTI","QUBT","IBM","GOOGL","MSFT","QMCO","ARQQ"],
        "keywords": ["quantum computing","quantum supremacy","qubit","quantum processor","IonQ","IBM quantum"],
        "subreddits": ["QuantumComputing","investing","stocks"],
    },
    "energy": {
        "tickers": ["XOM","CVX","COP","SLB","OXY","PSX","VLO","NEE","FSLR","ENPH","CCJ","VST","CEG"],
        "keywords": ["oil price","natural gas","crude oil","OPEC","energy transition","solar","nuclear","LNG","refinery"],
        "subreddits": ["energy","RenewableEnergy","investing","wallstreetbets"],
    },
}
```

### 1. `ingestion/newsapi_client.py`

- Poll NewsAPI every **15 minutes**, running one query per sector using the keyword lists defined in `sectors.py`
- Sector queries:
  - **Natural Resources**: `mining OR lithium OR copper OR gold OR "rare earth" OR cobalt OR nickel`
  - **Crypto**: `bitcoin OR ethereum OR crypto OR blockchain OR "digital assets" OR "bitcoin ETF"`
  - **Quantum Computing**: `"quantum computing" OR qubit OR IonQ OR "quantum processor" OR "quantum supremacy"`
  - **Energy**: `"oil price" OR OPEC OR "natural gas" OR "crude oil" OR solar OR nuclear OR LNG OR "energy transition"`
- Tag each article with its `sector` before inserting to Supabase
- Deduplicate by article URL before inserting to `news_articles`

### 2. `ingestion/reddit_client.py`

- Use PRAW to poll sector-specific subreddits every **5 minutes**:
  - **Natural Resources**: `r/investing`, `r/commodities`, `r/mining`
  - **Crypto**: `r/CryptoCurrency`, `r/Bitcoin`, `r/wallstreetbets`
  - **Quantum Computing**: `r/QuantumComputing`, `r/investing`, `r/stocks`
  - **Energy**: `r/energy`, `r/RenewableEnergy`, `r/investing`, `r/wallstreetbets`
- Fetch top 25 posts by `hot` and `new` each cycle per subreddit
- Filter posts with score > 10 to reduce noise
- Tag each post with its `sector` before inserting to `reddit_posts`
- Skip posts whose tickers don't appear in the sector's allowed ticker list

### 3. `nlp/entity_extractor.py`

- Extract company names and `$TICKER` mentions from text
- Use a static lookup dictionary + spaCy NER for company name resolution
- Map company names to tickers using `sectors.py` — **only resolve tickers that exist in the article's sector universe**; discard any extracted ticker not in the allowed list
- This hard scoping prevents the agent from accidentally trading outside the four target sectors

### 4. `nlp/sentiment.py`

- **Option A (cheaper)**: Use `ProsusAI/finbert` via HuggingFace locally — free, finance-specific
- **Option B (easier)**: Call OpenAI API with a structured prompt asking for JSON `{sentiment: float, confidence: float}`
- Output a score from -1.0 (very bearish) to +1.0 (very bullish) per ticker per article
- Store results in `sentiment_scores` table

### 5. `signals/aggregator.py`

- Aggregate all `sentiment_scores` for a given ticker in the last **60 minutes**
- Weighted average: news articles weighted 0.6, Reddit posts weighted 0.4
- Boost weight for Reddit posts with score > 1000
- Generate a `trade_signal` if:
  - Aggregated sentiment > 0.6 → BUY signal
  - Aggregated sentiment < -0.6 → SELL signal
  - Source count >= 3 (require at least 3 independent sources)

### 6. `signals/velocity.py`

- Track mention count per ticker per 15-minute window
- If mentions spike > 3x the 1-hour average → flag as high-velocity
- High-velocity signals increase confidence score by 0.1

### 7. `risk/manager.py`

- Before passing any signal to execution, check:
  - [ ] Ticker exists in the sector's allowed list in `sectors.py`
  - [ ] Not already in a position for this ticker
  - [ ] Signal not duplicate within `SIGNAL_DEDUP_WINDOW_MINUTES`
  - [ ] Daily trade count < `MAX_DAILY_TRADES`
  - [ ] Market is open (use Alpaca calendar endpoint)
  - [ ] Confidence >= `MIN_SIGNAL_CONFIDENCE`
- Calculate position size: `portfolio_value * MAX_POSITION_SIZE_PCT / current_price`
- Set stop-loss at **-3%**, take-profit at **+6%** from entry price
- **Sector exposure cap**: No single sector should exceed 40% of total open position value — enforce across all four sectors

### 8. `execution/alpaca_client.py`

- Place limit orders (not market orders) at current ask price
- Immediately set bracket order with stop-loss and take-profit
- Poll order status every 30 seconds; cancel unfilled limit orders after 5 minutes
- Update `trades` table with fill status and price

### 9. `main.py`

- Use `APScheduler` to run:
  - NewsAPI poll: every 15 minutes
  - Reddit poll: every 5 minutes
  - Signal aggregation: every 10 minutes
  - Open position monitoring: every 2 minutes during market hours
- Handle graceful shutdown on SIGTERM (important for Railway deployments)

---

## Railway Deployment

1. Push code to a GitHub repo
2. Connect repo to Railway — it will auto-detect Python
3. Set all environment variables in Railway's dashboard (Settings → Variables)
4. Add a `Procfile`:
   ```
   worker: python main.py
   ```
5. Railway will restart the process automatically on crash or new deploy

> **Important**: Use Railway's `worker` process type, not `web`. This is a background process, not a web server.

---

## Development Phases

### Phase 1 — Foundation (Week 1)

- [ ] Set up Supabase project and run `schema.sql`
- [ ] Build `sectors.py` with all four sector definitions (tickers, keywords, subreddits)
- [ ] Build `newsapi_client.py` — verify sector-tagged data flowing into `news_articles`
- [ ] Build `reddit_client.py` — verify sector-tagged data flowing into `reddit_posts`
- [ ] Set up Railway deployment with environment variables

### Phase 2 — NLP Pipeline (Week 2)

- [ ] Implement `entity_extractor.py` with sector-scoped ticker mapping from `sectors.py`
- [ ] Implement `sentiment.py` — start with OpenAI for speed, optimize later
- [ ] Verify `sentiment_scores` are being generated with correct `sector` tags
- [ ] Unit test with known bullish/bearish headlines for each of the four sectors

### Phase 3 — Signal + Risk (Week 3)

- [ ] Build `aggregator.py` and `velocity.py`
- [ ] Build `risk/manager.py` with all guard checks
- [ ] Log signals to `trade_signals` table
- [ ] Manually review signal quality for 1 week before trading

### Phase 4 — Paper Trading (Week 4)

- [ ] Connect `alpaca_client.py` to Alpaca **paper** account
- [ ] Run full pipeline end-to-end in paper mode for 2 weeks
- [ ] Track signal accuracy: did BUY signals go up? SELL signals go down?
- [ ] Tune confidence thresholds based on results

### Phase 5 — Live Trading

- [ ] Only proceed if paper trading shows positive expectancy
- [ ] Switch `ALPACA_BASE_URL` to live endpoint
- [ ] Start with small capital ($5,000–$10,000)
- [ ] Set up monitoring alerts for large drawdowns
- [ ] Review performance weekly

---

## Key Risks & Mitigations

| Risk                                | Mitigation                                                                                                                            |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| False signals from satire/clickbait | Require 3+ source minimum; weight by outlet credibility                                                                               |
| Pump-and-dump schemes on Reddit     | Cap Reddit weight at 0.4; require news corroboration for large positions                                                              |
| Slippage on limit orders            | Cancel unfilled orders after 5 min; avoid illiquid small-caps early on                                                                |
| Runaway losses                      | Hard daily drawdown limit: halt trading if portfolio drops >3% in one day                                                             |
| NewsAPI outage                      | Catch exceptions; continue running on Reddit-only with reduced confidence                                                             |
| Duplicate signals                   | Dedup window in risk manager; unique constraint on `trade_signals`                                                                    |
| Over-concentration in one sector    | 40% max sector exposure cap enforced in `risk/manager.py`                                                                             |
| Quantum Computing low liquidity     | Several quantum tickers (RGTI, QUBT, ARQQ) are small-cap — use smaller position sizes and wider limit order tolerance for this sector |

---

## Estimated Monthly Costs (Production)

| Service              | Cost                 |
| -------------------- | -------------------- |
| NewsAPI Developer    | $449/month           |
| Reddit API           | $0                   |
| Supabase Pro         | $25/month            |
| Railway (Hobby)      | $5–$10/month         |
| OpenAI API (if used) | ~$20–$50/month       |
| Alpaca               | $0                   |
| **Total**            | **~$499–$534/month** |

---

## Success Metrics

Track these weekly once live:

- **Signal accuracy**: % of BUY signals where price rose within 24h
- **Win rate**: % of closed trades that were profitable
- **Average P&L per trade**: After costs
- **Sharpe ratio**: Return vs. volatility
- **Break-even**: Need >$534/month profit to cover infrastructure
- **Per-sector signal accuracy**: Track each sector independently — drop or tune any sector consistently below 50% accuracy

> **Target**: Achieve >55% signal accuracy in paper trading before going live. Below that, the strategy has no edge.

---

## Future Expansion

Once the four seed sectors are performing well, the architecture supports adding new sectors by simply extending `sectors.py` with new keyword lists, tickers, and subreddits — no structural changes needed.
