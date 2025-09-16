"""Market data ingestion service built on the new infrastructure."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from itertools import islice
from typing import Iterable, Optional, Sequence

from nextgen_system.config import settings
from nextgen_system.persistence.database import get_database, Database
from .providers import MarketDataProvider, YFinanceMarketProvider
from .repositories import MarketRepository, UniverseRepository


@dataclass
class MarketIngestionResult:
    tickers: Iterable[str]
    rows_written: int


class MarketIngestionService:
    """Pulls OHLCV data from external providers and writes to ``market_prices``.

    This is a skeleton placeholder: actual fetching logic (yfinance, retries,
    rate limiting) will be ported in future steps. The goal here is to define
    the interface and persistence touchpoints.
    """

    def __init__(
        self,
        db: Optional[Database] = None,
        provider: Optional[MarketDataProvider] = None,
        repository: Optional[MarketRepository] = None,
        universe_repository: Optional[UniverseRepository] = None,
    ):
        self.db = db or get_database()
        self.provider = provider or YFinanceMarketProvider()
        self.repository = repository or MarketRepository(self.db)
        self.universe_repository = universe_repository or UniverseRepository(self.db)
        cfg = settings.get("ingestion", "market", default={})
        self.batch_size = cfg.get("batch_size", 16)
        self.history_days = cfg.get("history_days", 60)

    def ingest(
        self,
        tickers: Optional[Sequence[str]] = None,
        *,
        start: Optional[date] = None,
        end: Optional[date] = None,
    ) -> MarketIngestionResult:
        tickers = list(tickers) if tickers is not None else list(self.universe_repository.list_tickers())
        if not tickers:
            return MarketIngestionResult(tickers=[], rows_written=0)

        today = date.today()
        start = start or (today - timedelta(days=self.history_days))
        end = end or today

        rows_written = 0
        for batch in _chunked(tickers, self.batch_size):
            for symbol in batch:
                try:
                    frame = self.provider.fetch_history(symbol, start, end + timedelta(days=1))
                except Exception:
                    continue
                rows_written += self.repository.upsert_prices(frame)
        return MarketIngestionResult(tickers=tickers, rows_written=rows_written)


def _chunked(seq: Sequence[str], size: int):
    it = iter(seq)
    while True:
        chunk = list(islice(it, size))
        if not chunk:
            break
        yield chunk


__all__ = ["MarketIngestionService", "MarketIngestionResult"]
