"""Database repositories for ingestion services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional

import pandas as pd

from nextgen_system.persistence.database import get_database, Database


class MarketRepository:
    """Persist OHLCV rows into ``market_prices`` table."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_database()

    def upsert_prices(self, frame: pd.DataFrame) -> int:
        if frame.empty:
            return 0
        records = []
        for _, row in frame.iterrows():
            records.append(
                (
                    row["ticker"],
                    row["date"],
                    row.get("open"),
                    row.get("high"),
                    row.get("low"),
                    row.get("close"),
                    row.get("adjusted_close"),
                    row.get("volume"),
                    "yfinance",
                    datetime.utcnow(),
                )
            )
        self.db.executemany(
            """
            INSERT INTO market_prices
                (ticker, date, open, high, low, close, adjusted_close, volume, source, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker, date) DO UPDATE SET
                open=excluded.open,
                high=excluded.high,
                low=excluded.low,
                close=excluded.close,
                adjusted_close=excluded.adjusted_close,
                volume=excluded.volume,
                source=excluded.source,
                ingested_at=excluded.ingested_at;
            """,
            records,
        )
        return len(records)


@dataclass
class UniverseRow:
    ticker: str
    source: str
    market: Optional[str] = None
    min_date: Optional[str] = None
    metadata: Optional[str] = None


class UniverseRepository:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_database()

    def upsert_rows(self, rows: Iterable[UniverseRow]) -> int:
        records = [
            (row.ticker, row.source, row.market, row.min_date, row.metadata) for row in rows
        ]
        if not records:
            return 0
        self.db.executemany(
            """
            INSERT INTO ticker_universe (ticker, source, market, min_date, metadata, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(ticker) DO UPDATE SET
                source=excluded.source,
                market=excluded.market,
                min_date=excluded.min_date,
                metadata=excluded.metadata,
                updated_at=CURRENT_TIMESTAMP;
            """,
            records,
        )
        return len(records)

    def list_tickers(self) -> Iterable[str]:
        rows = self.db.fetch_all("SELECT ticker FROM ticker_universe")
        return [row[0] for row in rows]


class NewsRepository:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_database()

    def insert_articles(self, articles: Iterable[dict]) -> int:
        records = []
        for article in articles:
            records.append(
                (
                    article.get("ticker"),
                    article.get("headline"),
                    article.get("published_at"),
                    article.get("source"),
                    article.get("url"),
                    article.get("raw_json"),
                    datetime.utcnow(),
                )
            )
        if not records:
            return 0
        self.db.executemany(
            """
            INSERT INTO news_articles (ticker, headline, published_at, source, url, raw_json, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            records,
        )
        return len(records)

    def upsert_sentiment(self, aggregates: Iterable[dict]) -> int:
        records = []
        for agg in aggregates:
            records.append(
                (
                    agg.get("ticker"),
                    agg.get("as_of"),
                    agg.get("method"),
                    agg.get("article_count"),
                    agg.get("avg_sentiment"),
                    agg.get("buzz_score"),
                    agg.get("volatility"),
                    agg.get("details"),
                )
            )
        if not records:
            return 0
        self.db.executemany(
            """
            INSERT INTO news_sentiment
                (ticker, as_of, method, article_count, avg_sentiment, buzz_score, volatility, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker, as_of, method) DO UPDATE SET
                article_count=excluded.article_count,
                avg_sentiment=excluded.avg_sentiment,
                buzz_score=excluded.buzz_score,
                volatility=excluded.volatility,
                details=excluded.details,
                created_at=CURRENT_TIMESTAMP;
            """,
            records,
        )
        return len(records)

    def latest_sentiment_timestamp(self, ticker: str, method: str) -> Optional[datetime]:
        row = self.db.fetch_one(
            "SELECT created_at FROM news_sentiment WHERE ticker = ? AND method = ? ORDER BY created_at DESC LIMIT 1",
            (ticker, method),
        )
        if not row or not row[0]:
            return None
        try:
            return datetime.fromisoformat(str(row[0]))
        except ValueError:
            return None


__all__ = ["MarketRepository", "UniverseRepository", "UniverseRow", "NewsRepository"]
