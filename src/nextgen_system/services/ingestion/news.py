"""News & sentiment ingestion service skeleton."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Optional, Sequence

from nextgen_system.config import settings
from nextgen_system.persistence.database import get_database, Database
from .providers import NewsProvider, NullNewsProvider, RealNewsProvider
from .repositories import NewsRepository, UniverseRepository


@dataclass
class NewsIngestionResult:
    tickers: Iterable[str]
    articles_written: int
    sentiment_rows_written: int


class NewsIngestionService:
    """Collects news articles & aggregates sentiment into canonical tables."""

    def __init__(
        self,
        db: Optional[Database] = None,
        provider: Optional[NewsProvider] = None,
        repository: Optional[NewsRepository] = None,
        universe_repository: Optional[UniverseRepository] = None,
    ):
        self.db = db or get_database()
        self.provider = provider or RealNewsProvider()
        self.repository = repository or NewsRepository(self.db)
        self.universe_repository = universe_repository or UniverseRepository(self.db)
        self.sentiment_cache_hours = settings.get("ingestion", "news", "sentiment_cache_hours", default=4)

    def ingest(self, tickers: Optional[Sequence[str]] = None) -> NewsIngestionResult:
        tickers = list(tickers) if tickers is not None else list(self.universe_repository.list_tickers())
        if not tickers:
            return NewsIngestionResult(tickers=[], articles_written=0, sentiment_rows_written=0)

        article_count = 0
        sentiment_count = 0
        for ticker in tickers:
            if not self._should_refresh_sentiment(ticker):
                continue
            try:
                articles = self.provider.fetch_articles(ticker)
            except Exception:
                continue
            article_payloads = [
                {
                    "ticker": ticker,
                    "headline": article.headline,
                    "published_at": article.published_at,
                    "source": article.source,
                    "url": article.url,
                    "raw_json": article.raw_json,
                }
                for article in articles
            ]
            article_count += self.repository.insert_articles(article_payloads)

            if articles:
                try:
                    aggregate = self.provider.aggregate_sentiment(articles)
                    sentiment_count += self.repository.upsert_sentiment(
                        [
                            {
                                "ticker": ticker,
                                "as_of": aggregate.as_of,
                                "method": aggregate.method,
                                "article_count": aggregate.article_count,
                                "avg_sentiment": aggregate.avg_sentiment,
                                "buzz_score": aggregate.buzz_score,
                                "volatility": aggregate.volatility,
                                "details": aggregate.details,
                            }
                        ]
                    )
                except Exception:
                    continue

        return NewsIngestionResult(tickers=tickers, articles_written=article_count, sentiment_rows_written=sentiment_count)

    def _should_refresh_sentiment(self, ticker: str) -> bool:
        latest = self.repository.latest_sentiment_timestamp(ticker, self.provider.method)
        if not latest:
            return True
        age = datetime.utcnow() - latest
        return age > timedelta(hours=self.sentiment_cache_hours)


__all__ = ["NewsIngestionService", "NewsIngestionResult"]
