"""Market data providers."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

import pandas as pd

try:
    import yfinance as yf
except ImportError:  # pragma: no cover - dependency should exist but guard anyway
    yf = None

from nextgen_system.config import settings


class MarketDataProvider(ABC):
    """Abstract provider returning OHLCV history for a ticker."""

    @abstractmethod
    def fetch_history(self, ticker: str, start: date, end: date) -> pd.DataFrame:
        raise NotImplementedError


class YFinanceMarketProvider(MarketDataProvider):
    """Fetch market data using yfinance with simple retry/backoff."""

    def __init__(self, *, max_retries: Optional[int] = None, backoff_base: Optional[float] = None):
        if yf is None:
            raise RuntimeError("yfinance not installed")
        cfg = settings.get("ingestion", "market", default={})
        self.max_retries = max_retries if max_retries is not None else cfg.get("max_retries", 3)
        self.backoff_base = backoff_base if backoff_base is not None else cfg.get("retry_backoff_base", 2.0)
        self.logger = logging.getLogger(__name__)

    def _normalise(self, ticker: str) -> str:
        ticker = ticker.strip().upper()
        if ticker.startswith("$"):
            ticker = ticker[1:]
        if "." in ticker and len(ticker.split(".")[-1]) == 1:
            ticker = ticker.replace(".", "-")
        return ticker

    def fetch_history(self, ticker: str, start: date, end: date) -> pd.DataFrame:
        norm = self._normalise(ticker)
        attempt = 0
        while True:
            try:
                df = yf.download(norm, start=start, end=end, progress=False, auto_adjust=False, threads=False)
                if df.empty:
                    raise ValueError(f"No market data returned for {ticker}")
                df = df.rename(
                    columns={
                        "Open": "open",
                        "High": "high",
                        "Low": "low",
                        "Close": "close",
                        "Adj Close": "adjusted_close",
                        "Volume": "volume",
                    }
                )
                df.index = pd.to_datetime(df.index)
                df = df.reset_index().rename(columns={"Date": "date"})
                df["ticker"] = ticker.upper()
                # Validate recency: ensure latest date is within requested range
                latest = df["date"].max()
                if pd.to_datetime(latest).date() < start:
                    raise ValueError(f"Stale data for {ticker}: latest {latest} before start {start}")
                return df[["ticker", "date", "open", "high", "low", "close", "adjusted_close", "volume"]]
            except Exception as exc:
                attempt += 1
                if attempt > self.max_retries:
                    self.logger.error("Market data fetch failed for %s: %s", ticker, exc)
                    raise
                delay = self.backoff_base ** attempt
                time.sleep(delay)


__all__ = ["MarketDataProvider", "YFinanceMarketProvider"]
