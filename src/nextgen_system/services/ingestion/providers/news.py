"""News & sentiment providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

try:
    from nextgen_system.integrations.real_news import RealNewsAPI  # type: ignore
except ImportError:  # pragma: no cover - optional integration
    class RealNewsAPI:  # type: ignore[no-redef]
        """Fallback stub when an external news integration is not available."""

        def get_news_from_multiple_sources(
            self, ticker: str, company_name: str, days_back: int | None = None
        ) -> list[dict]:
            return []


@dataclass
class NewsArticle:
    ticker: str
    headline: str
    published_at: datetime
    source: str
    url: str
    raw_json: dict


@dataclass
class SentimentAggregate:
    ticker: str
    as_of: datetime
    method: str
    article_count: int
    avg_sentiment: float
    buzz_score: float
    volatility: float
    details: dict


class NewsProvider(ABC):
    @abstractmethod
    def fetch_articles(self, ticker: str) -> List[NewsArticle]:
        raise NotImplementedError

    @abstractmethod
    def aggregate_sentiment(self, articles: Iterable[NewsArticle]) -> SentimentAggregate:
        raise NotImplementedError

    @property
    def method(self) -> str:
        return self.__class__.__name__.lower()


class NullNewsProvider(NewsProvider):
    """Placeholder provider returning no data."""

    def fetch_articles(self, ticker: str) -> List[NewsArticle]:
        return []

    def aggregate_sentiment(self, articles: Iterable[NewsArticle]) -> SentimentAggregate:
        now = datetime.utcnow()
        return SentimentAggregate(
            ticker="",
            as_of=now,
            method="noop",
            article_count=0,
            avg_sentiment=0.0,
            buzz_score=0.0,
            volatility=0.0,
            details={},
        )


class RealNewsProvider(NewsProvider):
    """Provider that fetches real articles via RealNewsAPI and scores with VADER."""

    def __init__(self):
        self.api = RealNewsAPI()
        self.sentiment = SentimentIntensityAnalyzer()

    def _parse_articles(self, raw_articles: List[dict], ticker: str) -> List[NewsArticle]:
        parsed: List[NewsArticle] = []
        for article in raw_articles:
            title = article.get("title") or article.get("headline")
            if not title:
                continue
            published = self._parse_date(article.get("published_date") or article.get("pubDate"))
            if not published:
                continue
            parsed.append(
                NewsArticle(
                    ticker=ticker,
                    headline=title,
                    published_at=published,
                    source=article.get("source", "unknown"),
                    url=article.get("url") or article.get("link", ""),
                    raw_json=article,
                )
            )
        return parsed

    def _parse_date(self, value: str) -> datetime:
        if not value:
            return None  # type: ignore
        formats = [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(value, fmt)
                return dt if dt.tzinfo is None else dt.astimezone().replace(tzinfo=None)
            except ValueError:
                continue
        try:
            from email.utils import parsedate_to_datetime

            dt = parsedate_to_datetime(value)
            return dt if dt.tzinfo is None else dt.astimezone().replace(tzinfo=None)
        except Exception:
            return None  # type: ignore

    def fetch_articles(self, ticker: str) -> List[NewsArticle]:
        raw_articles = self.api.get_news_from_multiple_sources(ticker, ticker)
        return self._parse_articles(raw_articles, ticker)

    def aggregate_sentiment(self, articles: Iterable[NewsArticle]) -> SentimentAggregate:
        articles_list = list(articles)
        if not articles_list:
            return SentimentAggregate(
                ticker="",
                as_of=datetime.utcnow(),
                method=self.method,
                article_count=0,
                avg_sentiment=0.0,
                buzz_score=0.0,
                volatility=0.0,
                details={},
            )

        scores = [self.sentiment.polarity_scores(article.headline)["compound"] for article in articles_list]
        avg_sentiment = sum(scores) / len(scores)
        volatility = pd.Series(scores).std(ddof=0) if len(scores) > 1 else 0.0
        buzz = min(len(articles_list) / 10.0, 1.0)

        return SentimentAggregate(
            ticker=articles_list[0].ticker,
            as_of=datetime.utcnow(),
            method=self.method,
            article_count=len(articles_list),
            avg_sentiment=avg_sentiment,
            buzz_score=buzz,
            volatility=volatility,
            details={"scores": scores},
        )


__all__ = [
    "NewsProvider",
    "NullNewsProvider",
    "NewsArticle",
    "SentimentAggregate",
]
