"""Sentiment scoring: FinBERT (local) or OpenAI API. Output -1.0 to 1.0 per ticker."""

import logging
from typing import Optional

import config
from db.supabase_client import insert_sentiment_score
from sectors import VALID_SECTORS

logger = logging.getLogger(__name__)

MODEL_FINBERT = "finbert"
MODEL_OPENAI = "openai"


def _score_openai(text: str) -> tuple[float, float]:
    """Call OpenAI for sentiment and confidence. Returns (sentiment, confidence)."""
    if not config.OPENAI_API_KEY:
        return 0.0, 0.0
    try:
        from openai import OpenAI
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial sentiment analyzer. Respond with JSON only: {\"sentiment\": number from -1.0 (very bearish) to 1.0 (very bullish), \"confidence\": number from 0.0 to 1.0}.",
                },
                {"role": "user", "content": text[:4000]},
            ],
            max_tokens=100,
        )
        import json
        content = (r.choices[0].message.content or "").strip()
        # Handle markdown code block
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        data = json.loads(content)
        s = float(data.get("sentiment", 0))
        c = float(data.get("confidence", 0.5))
        s = max(-1.0, min(1.0, s))
        c = max(0.0, min(1.0, c))
        return s, c
    except Exception as e:
        logger.exception("OpenAI sentiment failed: %s", e)
        return 0.0, 0.0


def _score_finbert(text: str) -> tuple[float, float]:
    """Use FinBERT locally. Returns (sentiment, confidence)."""
    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        import torch
        model_name = "ProsusAI/finbert"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        inputs = tokenizer(text[:512], return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            out = model(**inputs)
        probs = torch.softmax(out.logits, dim=1)[0]
        # finbert: 0=positive, 1=negative, 2=neutral
        pos, neg, neu = probs[0].item(), probs[1].item(), probs[2].item()
        sentiment = pos - neg
        confidence = max(pos, neg, neu)
        return sentiment, confidence
    except Exception as e:
        logger.exception("FinBERT sentiment failed: %s", e)
        return 0.0, 0.0


def score_text(text: str) -> tuple[float, float]:
    """Score text; return (sentiment, confidence). Uses OpenAI if configured else FinBERT."""
    if not text or not text.strip():
        return 0.0, 0.0
    if config.USE_OPENAI_SENTIMENT and config.OPENAI_API_KEY:
        return _score_openai(text)
    return _score_finbert(text)


def score_news_article(article_id: str, title: str, description: str, sector: str, tickers: list[str]) -> int:
    """
    Score a news article for each ticker; store in sentiment_scores.
    tickers must be from entity_extractor (sector-scoped). Returns count stored.
    """
    if sector not in VALID_SECTORS:
        return 0
    text = f"{title}\n{description or ''}".strip()
    if not text:
        return 0
    sent, conf = score_text(text)
    model_used = MODEL_OPENAI if (config.USE_OPENAI_SENTIMENT and config.OPENAI_API_KEY) else MODEL_FINBERT
    stored = 0
    for ticker in tickers:
        row = insert_sentiment_score(
            source_type="news",
            source_id=article_id,
            ticker=ticker,
            sector=sector,
            sentiment=sent,
            confidence=conf,
            model_used=model_used,
        )
        if row:
            stored += 1
    return stored


def score_reddit_post(post_id: str, title: str, body: str, sector: str, tickers: list[str]) -> int:
    """Score a Reddit post for each ticker; store in sentiment_scores."""
    if sector not in VALID_SECTORS:
        return 0
    text = f"{title}\n{body or ''}".strip()
    if not text:
        return 0
    sent, conf = score_text(text)
    model_used = MODEL_OPENAI if (config.USE_OPENAI_SENTIMENT and config.OPENAI_API_KEY) else MODEL_FINBERT
    stored = 0
    for ticker in tickers:
        row = insert_sentiment_score(
            source_type="reddit",
            source_id=post_id,
            ticker=ticker,
            sector=sector,
            sentiment=sent,
            confidence=conf,
            model_used=model_used,
        )
        if row:
            stored += 1
    return stored
