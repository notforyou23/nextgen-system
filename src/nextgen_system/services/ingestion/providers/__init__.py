"""Provider interfaces for ingestion services."""

from .market import MarketDataProvider, YFinanceMarketProvider
from .news import (
    NewsProvider,
    NullNewsProvider,
    RealNewsProvider,
    NewsArticle,
    SentimentAggregate,
)

__all__ = [
    "MarketDataProvider",
    "YFinanceMarketProvider",
    "NewsProvider",
    "NullNewsProvider",
    "RealNewsProvider",
    "NewsArticle",
    "SentimentAggregate",
]
