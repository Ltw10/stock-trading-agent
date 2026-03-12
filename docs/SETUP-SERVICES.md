# Service Setup Guide

This guide walks through creating and configuring every external account the trading agent uses. Complete these before running the agent or deploying to Railway.

---

## Table of contents

1. [Supabase (database)](#1-supabase-database)
2. [Finnhub (primary news)](#2-finnhub-primary-news)
3. [CryptoPanic (crypto news)](#3-cryptopanic-crypto-news)
4. [Alpha Vantage (supplementary news)](#4-alpha-vantage-supplementary-news)
5. [Reddit (optional — sentiment / PRAW)](#5-reddit-optional--sentiment--praw)
6. [Alpaca (broker)](#6-alpaca-broker)
7. [Sentiment: FinBERT or OpenAI](#7-sentiment-finbert-default-or-openai)
8. [Railway (hosting)](#8-railway-hosting)
9. [Optional: Slack (alerts)](#9-optional-slack-alerts)
10. [Daily performance email](#10-daily-performance-email)
11. [Assembling your `.env`](#11-assembling-your-env)

---

## 1. Supabase (database)

Supabase hosts the PostgreSQL database and stores news articles, Reddit posts, sentiment scores, trade signals, and trades.

### Steps

1. **Sign up**  
   Go to [https://supabase.com](https://supabase.com) and sign up (GitHub or email).

2. **Create a project**  
   - Click **New project**.  
   - Choose your organization (or create one).  
   - Set **Name** (e.g. `trading-agent`).  
   - Set a **Database password** and store it somewhere safe (you need it for direct DB access; the app uses the API key).  
   - Pick a **Region** close to you or your broker.  
   - Click **Create new project** and wait for the project to be ready.

3. **Get URL and API key**  
   - **URL:** In the left sidebar go to **Integrations** → **Data API**. Copy the **API URL** (e.g. `https://xxxxxxxx.supabase.co`). This is `SUPABASE_URL`.  
   - **Key:** In the left sidebar go to **Settings** → **API keys**. For this backend agent you must use the **service_role** key (the secret key, not the anon/publishable key). The service_role key has full access and is required for server-side inserts. Copy it into `SUPABASE_KEY`.  
   - **Note:** Never expose the service_role key in frontend code or commit it to version control.

4. **Run the schema**  
   - In the left sidebar: **SQL Editor**.  
   - Click **New query**.  
   - Open `db/schema.sql` from this repo, copy its full contents, and paste into the editor.  
   - Click **Run** (or Cmd/Ctrl+Enter).  
   - Confirm there are no errors and that tables appear under **Table Editor**: `news_articles`, `reddit_posts`, `sentiment_scores`, `trade_signals`, `trades`, `logs`.

5. **If you see "Invalid API key" in logs**  
   - Use the **service_role** key: Supabase → Settings → API keys → click **Reveal** next to service_role → copy the whole key (one long line, 200+ characters).  
   - In Railway, set `SUPABASE_KEY` to that value. Paste it as a **single line** with no newlines or extra spaces (multi-line paste can break the key).  
   - Ensure `SUPABASE_URL` and `SUPABASE_KEY` are from the **same** Supabase project.  
   - Restart the worker after changing variables.

6. **If you already had `news_articles` without `data_source`**  
   Run this once in the SQL Editor:
   ```sql
   ALTER TABLE news_articles
   ADD COLUMN IF NOT EXISTS data_source TEXT
   CHECK (data_source IN ('finnhub', 'cryptopanic', 'alpha_vantage'));
   ```

### Env vars

| Variable        | Where to get it                              |
|-----------------|-----------------------------------------------|
| `SUPABASE_URL`  | Integrations → Data API (in left sidebar)     |
| `SUPABASE_KEY`  | Settings → API keys → **service_role** (secret key for backend) |

---

## 2. Finnhub (primary news)

Finnhub provides company-specific news per ticker. The agent calls the company-news endpoint for each ticker in `sectors.py` and respects a 60 calls/minute free-tier limit.

### Steps

1. **Sign up**  
   Go to [https://finnhub.io](https://finnhub.io) and sign up (free account).

2. **Get your API key**  
   - After logging in, open the [Dashboard](https://finnhub.io/dashboard) or **Profile** → **API Key**.  
   - Copy the API key (long string). This is `FINNHUB_API_KEY`.

3. **Rate limits (free tier)**  
   - 60 API calls per minute.  
   - The agent spaces requests (~1 call per ticker per second) so you stay under the limit.  
   - If you add many more tickers, consider a paid plan or increasing the delay in `ingestion/finnhub_client.py`.

### Env vars

| Variable           | Where to get it        |
|--------------------|------------------------|
| `FINNHUB_API_KEY`  | Finnhub dashboard / Profile → API Key |

---

## 3. CryptoPanic (crypto news)

CryptoPanic aggregates crypto news and is used only for the **crypto** sector as a supplementary source alongside Finnhub.

### Steps

1. **Sign up**  
   Go to [https://cryptopanic.com](https://cryptopanic.com) and create an account.

2. **Get API token**  
   - In the left sidebar, click **Integrate**.  
   - Go to **API**.  
   - Find and copy your API token. This is `CRYPTOPANIC_API_KEY`.

3. **Optional**  
   - If the free tier has limited requests, the agent will still run; the crypto sector will rely more on Finnhub and Reddit when CryptoPanic is skipped or rate-limited.

### Env vars

| Variable              | Where to get it                    |
|-----------------------|------------------------------------|
| `CRYPTOPANIC_API_KEY` | Left sidebar → **Integrate** → **API** (copy token) |

---

## 4. Alpha Vantage (supplementary news)

Alpha Vantage provides market news and sentiment by ticker. The agent uses it as a supplementary source for all four sectors (when `alpha_vantage` is true in `sectors.py`).

### Steps

1. **Get an API key**  
   Go to [https://www.alphavantage.co/support/#api-key](https://www.alphavantage.co/support/#api-key), enter your email, and click **Get free API key**.  
   Check your email and copy the key. This is `ALPHA_VANTAGE_API_KEY`.

2. **Rate limits (free tier)**  
   - Typically 5 requests per minute, 25 per day.  
   - The agent makes one request per sector with `alpha_vantage: True`, with a delay between sectors (see `ingestion/alpha_vantage_client.py`).  
   - If you hit limits, increase `RATE_LIMIT_DELAY_SEC` or reduce how often the news job runs.

### Env vars

| Variable                 | Where to get it                    |
|--------------------------|------------------------------------|
| `ALPHA_VANTAGE_API_KEY`  | Alpha Vantage → Request API key → email |

---

## 5. Reddit (optional — sentiment / PRAW)

**You can skip Reddit for now.** The agent runs fine with only news (Finnhub, CryptoPanic, Alpha Vantage). Leave `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` blank in `.env` and Reddit ingestion will be disabled.

If you want Reddit later: it fetches posts from sector-specific subreddits. The agent uses PRAW (Python Reddit API Wrapper) and needs a Reddit “app” (script) to get credentials.

### Steps

1. **Log in to Reddit**  
   Use the account you want to associate with the app (a dedicated account is fine).

2. **Create an application**  
   - Go to [https://www.reddit.com/prefs/apps](https://www.reddit.com/prefs/apps).  
   - Reddit may show a message that "Developers should go through Devvit first." **Use this (legacy) form anyway:** Devvit is for apps that run *inside* Reddit (custom posts, subreddit tools, etc.). This agent is an external script that only reads public subreddit posts via the API, which is not supported by Devvit. Click **create another app** (or **create application**) to continue.

3. **Fill out the form**  
   - **Name:** e.g. `trading-agent` or `stock-news-bot`.  
   - **App type:** Select **script** (required for PRAW with a personal script app).  
   - **Description:** Optional (e.g. “News/sentiment ingestion for a trading agent”).  
   - **About url:** Optional, can leave blank.  
   - **Redirect uri:** Must be set; use `http://localhost:8080` (the agent doesn’t use OAuth redirects; this is a PRAW requirement).  
   - Click **create app**.

4. **Copy credentials**  
   Under your new app you’ll see:  
   - A string under the app name (sometimes labeled “personal use script”) — this is **`REDDIT_CLIENT_ID`**.  
   - A **secret** — this is **`REDDIT_CLIENT_SECRET`**.

5. **User agent**  
   Reddit requires a descriptive User-Agent. Use something like:  
   `trading-bot/1.0` (or `trading-bot/1.0 by your_reddit_username`).  
   Set this as `REDDIT_USER_AGENT` in `.env`.

### Env vars

| Variable               | Where to get it                              |
|------------------------|----------------------------------------------|
| `REDDIT_CLIENT_ID`     | Reddit app → string under app name (personal use script) |
| `REDDIT_CLIENT_SECRET`| Reddit app → “secret”                        |
| `REDDIT_USER_AGENT`    | You choose (e.g. `trading-bot/1.0`)         |

---

## 6. Alpaca (broker)

Alpaca is the broker used to place and manage orders. Start with a **paper** account; switch to live only after testing.

### Steps

1. **Sign up**  
   Go to [https://alpaca.markets](https://alpaca.markets) and sign up.

2. **Paper trading first**  
   - Alpaca gives you a **paper** account by default.  
   - In the dashboard, confirm you’re in **Paper Trading** (not Live).  
   - Use paper until you’re satisfied with signal quality and execution behavior.

3. **Get API keys**  
   - In the dashboard: **API Keys** (or Account → API Keys).  
   - You’ll see **Key ID** (this is `ALPACA_API_KEY`) and **Secret Key** (this is `ALPACA_SECRET_KEY`).  
   - Generate keys for the **Paper** environment first.  
   - Copy both; the secret is shown only once.

4. **Base URL**  
   - **Paper:** `https://paper-api.alpaca.markets` → set as `ALPACA_BASE_URL`.  
   - **Live:** When you switch, use `https://api.alpaca.markets` and generate new keys under the Live environment.

### Env vars

| Variable             | Where to get it                    |
|----------------------|------------------------------------|
| `ALPACA_API_KEY`     | Alpaca dashboard → API Keys → Key ID |
| `ALPACA_SECRET_KEY`  | Alpaca dashboard → API Keys → Secret (copy once) |
| `ALPACA_BASE_URL`    | Paper: `https://paper-api.alpaca.markets`; Live: `https://api.alpaca.markets` |

---

## 7. Sentiment: FinBERT (default) or OpenAI

The agent scores news and Reddit text for sentiment (bullish/bearish). You can use **FinBERT** (local, free, no account) or **OpenAI** (API, paid). By default the agent uses FinBERT.

### FinBERT (default — no setup)

- **No account or API key.** FinBERT runs locally using the [ProsusAI/finbert](https://huggingface.co/ProsusAI/finbert) model from Hugging Face.
- **Dependencies:** Already in `requirements.txt`: `transformers`, `torch`. Run `pip install -r requirements.txt`; that’s all you need.
- **First run:** The first time the agent runs sentiment, it will **download the model** from Hugging Face (~400 MB). This needs internet and can take one to two minutes. After that it’s cached locally (in `~/.cache/huggingface/` by default) and loads quickly.
- **Optional — smaller install:** If you’re only running on CPU (e.g. Railway with no GPU), you can install a CPU-only build of PyTorch to speed up `pip install` and reduce size:
  ```bash
  pip install torch --index-url https://download.pytorch.org/whl/cpu
  ```
  Then install the rest: `pip install -r requirements.txt` (or install everything else and skip `torch` from requirements if you already installed the CPU build).
- **Do not set** `USE_OPENAI_SENTIMENT` (or set it to `0`/`false`). Leave `OPENAI_API_KEY` blank and the agent will use FinBERT.

### OpenAI (optional)

If you prefer OpenAI for sentiment, you need an API key and must explicitly enable it.

### Steps (OpenAI only)

1. **Sign up / log in**  
   Go to [https://platform.openai.com](https://platform.openai.com) and create an account or log in.

2. **Billing**  
   - Add a payment method under **Billing** (required for API access).  
   - Set usage limits if you want to cap spend.

3. **Create an API key**  
   - Go to [API keys](https://platform.openai.com/api-keys).  
   - Click **Create new secret key**, name it (e.g. `trading-agent`), and copy the key.  
   - This is `OPENAI_API_KEY`. Store it securely; it’s shown only once.

4. **Enable in the agent**  
   - Set `OPENAI_API_KEY` in `.env`.  
   - Set `USE_OPENAI_SENTIMENT=1` (or `true`/`yes`) to use OpenAI for sentiment instead of FinBERT.

### Env vars

| Variable               | Where to get it                    |
|------------------------|------------------------------------|
| `OPENAI_API_KEY`       | OpenAI → API keys → Create new secret key |
| `USE_OPENAI_SENTIMENT` | Set to `1` (or `true`) to use OpenAI for sentiment |

---

## 8. Railway (hosting)

Railway runs the agent as a long-running worker (not a web server).

### Steps

1. **Sign up**  
   Go to [https://railway.app](https://railway.app) and sign up (e.g. with GitHub).

2. **Create a project**  
   - **New Project** → **Deploy from GitHub repo**.  
   - Authorize Railway to access your GitHub and select the repo that contains this agent.

3. **Configure as a worker**  
   - Railway may detect Python. Ensure the **root** of the repo is the project root (where `main.py` and `requirements.txt` are).  
   - Set the **start command** to use the Procfile: `worker: python main.py` (Railway often picks this up from `Procfile`).  
   - If there’s a “Web” vs “Worker” type, choose **Worker** so it doesn’t expect an HTTP port.

4. **Add environment variables**  
   - In the project: **Variables** (or **Settings** → **Variables**).  
   - Add every variable from your `.env` (see [Assembling your `.env`](#10-assembling-your-env)):  
     `SUPABASE_URL`, `SUPABASE_KEY`, `FINNHUB_API_KEY`, `CRYPTOPANIC_API_KEY`, `ALPHA_VANTAGE_API_KEY`, `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `ALPACA_BASE_URL`. Optional: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`, `OPENAI_API_KEY`, `USE_OPENAI_SENTIMENT`, plus any risk/alert vars.

5. **Deploy**  
   - Push to the connected branch to trigger a deploy, or use **Deploy** in the dashboard.  
   - Check **Logs** to confirm the scheduler starts and that news ingestion runs. Reddit runs only if those credentials are set.

6. **If the build times out**  
   - The repo includes a **Dockerfile** that installs CPU-only PyTorch first (faster and smaller). Railway will use it automatically if present.

7. **"API key not set" in logs even though you added it**  
   - **Exact name:** Variable names are case-sensitive. Use **`FINNHUB_API_KEY`** (two N's in FINN). A typo like `FINHUB_API_KEY` or `Finnhub_Api_Key` will not work.  
   - **Where to set:** In Railway, open your **service** (the app), then **Variables** (or **Settings** → **Variables**). Add the variable there so it’s available at runtime.  
   - **Redeploy:** After adding or changing variables, trigger a **Redeploy** (or push a commit) so the new environment is loaded.  
   - **No spaces:** Don’t put quotes or extra spaces in the value in the Railway UI; paste the key only.

---

## 9. Optional: Slack (alerts)

For alerts on drawdowns or API failures, you can use a Slack incoming webhook.

### Steps

1. **Create a Slack app (or use existing)**  
   - Go to [https://api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**.  
   - Name it (e.g. `trading-agent-alerts`) and pick a workspace.

2. **Enable Incoming Webhooks**  
   - In the app: **Incoming Webhooks** → turn **On**.  
   - **Add New Webhook to Workspace**, choose the channel (e.g. `#alerts`), then **Allow**.  
   - Copy the **Webhook URL**. This is `SLACK_WEBHOOK_URL`.

3. **Add to `.env`**  
   - Set `SLACK_WEBHOOK_URL` in your `.env` (and in Railway Variables if you deploy).  
   - The agent will send alerts to this URL when configured in `monitoring/alerts.py`.

### Env vars

| Variable            | Where to get it                          |
|---------------------|------------------------------------------|
| `SLACK_WEBHOOK_URL` | Slack app → Incoming Webhooks → Webhook URL |

---

## 10. Daily performance email

The agent sends a **daily performance report** to the email address you set in `REPORT_EMAIL_TO`. The report includes ingestion counts (news, Reddit), sentiment scores, signals (BUY/SELL/HOLD), trades (placed/filled/pending), and—if Alpaca is configured—portfolio value and open positions.

### Steps (Gmail)

1. **Use an App Password**  
   Gmail no longer allows “less secure apps” to sign in with your normal password. Use an [App Password](https://support.google.com/accounts/answer/185833):  
   - Turn on 2-Step Verification for your Google account (if needed).  
   - Go to [Google Account → Security → App passwords](https://myaccount.google.com/apppasswords).  
   - Create an app password for “Mail” (or “Other” and name it “trading-agent”).  
   - Copy the 16-character password. This is `SMTP_PASSWORD`.

2. **Set `.env`**  
   - `REPORT_EMAIL_TO` — recipient.  
   - `REPORT_EMAIL_FROM` — optional; if blank, `SMTP_USER` is used as From.  
   - `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`.  
   - `SMTP_USER` — your Gmail address.  
   - `SMTP_PASSWORD` — the App Password from step 1.  
   - `DAILY_REPORT_HOUR`, `DAILY_REPORT_MINUTE` — time to send (24h, server timezone; default 8:00).

If `SMTP_USER` or `SMTP_PASSWORD` is missing, the daily report is skipped (no error; the job runs but does not send).

### Env vars

| Variable               | Description |
|------------------------|-------------|
| `REPORT_EMAIL_TO`      | Recipient |
| `REPORT_EMAIL_FROM`    | Optional From address |
| `SMTP_HOST`            | e.g. smtp.gmail.com |
| `SMTP_PORT`            | e.g. 587 |
| `SMTP_USER`            | SMTP login (e.g. your Gmail) |
| `SMTP_PASSWORD`        | SMTP password (Gmail: App Password) |
| `DAILY_REPORT_HOUR`    | Hour (0–23) to send report |
| `DAILY_REPORT_MINUTE`  | Minute (0–59) |

---

## 11. Assembling your `.env`

In the project root, copy the example file and fill in values:

```bash
cp .env.example .env
```

Then edit `.env` with your actual values. Minimum for ingestion + DB:

- **Required for database:** `SUPABASE_URL`, `SUPABASE_KEY`
- **Required for news:** `FINNHUB_API_KEY` (CryptoPanic and Alpha Vantage are optional but recommended)
- **Required for paper trading (Phase 4+):** `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `ALPACA_BASE_URL=https://paper-api.alpaca.markets`
- **Optional:** `CRYPTOPANIC_API_KEY`, `ALPHA_VANTAGE_API_KEY`, `OPENAI_API_KEY`, `USE_OPENAI_SENTIMENT`, `SLACK_WEBHOOK_URL`
- **Optional — Reddit:** Leave `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` blank to skip Reddit; the agent runs with news only.
- **Daily report:** Set `REPORT_EMAIL_TO`, plus `SMTP_USER` and `SMTP_PASSWORD` (e.g. Gmail + App Password) to receive the daily performance email.

Never commit `.env` to version control. For deployment, add the same variables to Railway (or your host) in their dashboard.

---

## Quick checklist

| Service        | What you get                    | Env vars |
|----------------|----------------------------------|----------|
| Supabase       | URL: Integrations → Data API; Key: Settings → API keys → **service_role** | `SUPABASE_URL`, `SUPABASE_KEY` |
| Finnhub        | API key                         | `FINNHUB_API_KEY` |
| CryptoPanic    | Integrate → API (token)        | `CRYPTOPANIC_API_KEY` |
| Alpha Vantage  | API key (from email)             | `ALPHA_VANTAGE_API_KEY` |
| Reddit         | Optional — script app → client ID + secret (skip for now) | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` |
| Alpaca         | Paper (or live) API keys        | `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `ALPACA_BASE_URL` |
| OpenAI         | API key (optional)              | `OPENAI_API_KEY`, `USE_OPENAI_SENTIMENT` |
| Railway        | Deploy from GitHub + variables  | All of the above in Railway Variables |
| Slack          | Incoming webhook URL (optional) | `SLACK_WEBHOOK_URL` |
| Daily report   | SMTP (e.g. Gmail App Password)  | `SMTP_USER`, `SMTP_PASSWORD`, `REPORT_EMAIL_TO` |

After all are set, run the schema in Supabase (see [Supabase](#1-supabase-database)) and start the agent with `python main.py`. See **next-steps.md** for the phased implementation plan.
