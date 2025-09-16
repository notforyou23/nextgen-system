"""Feature builder service for next-gen system."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, Optional, Sequence

import pandas as pd
import numpy as np

from nextgen_system.persistence.database import get_database, Database
from nextgen_system.services.ingestion.repositories import UniverseRepository
from .providers.feature_engineer import FeatureEngineeringProvider
from .repositories import FeatureRepository


def _load_market_history(db: Database, ticker: str, window_days: int = 90) -> pd.DataFrame:
    query = """
    SELECT date, open, high, low, close, adjusted_close, volume
    FROM market_prices
    WHERE ticker = ?
    ORDER BY date DESC
    LIMIT ?
    """
    rows = db.fetch_all(query, (ticker, window_days))
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "adjusted_close", "volume"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    return df


def _load_sentiment(db: Database, ticker: str) -> Dict:
    row = db.fetch_one(
        """
        SELECT article_count, avg_sentiment, buzz_score, volatility, created_at
        FROM news_sentiment
        WHERE ticker = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (ticker,),
    )
    if not row:
        return {}
    return {
        "article_count": row[0],
        "avg_sentiment": row[1],
        "buzz_score": row[2],
        "volatility": row[3],
        "created_at": row[4],
    }


@dataclass
class FeatureBuildResult:
    tickers: Sequence[str]
    windows_created: int
    warnings: Sequence[str]


class FeatureBuilderService:
    def __init__(
        self,
        db: Optional[Database] = None,
        feature_provider: Optional[FeatureEngineeringProvider] = None,
        feature_repository: Optional[FeatureRepository] = None,
    ):
        self.db = db or get_database()
        self.provider = feature_provider or FeatureEngineeringProvider()
        self.repository = feature_repository or FeatureRepository(self.db)
        self.universe_repo = UniverseRepository(self.db)

    def build(self, tickers: Optional[Sequence[str]] = None) -> FeatureBuildResult:
        tickers = list(tickers) if tickers else list(self.universe_repo.list_tickers())
        warnings = []
        windows_created = 0
        for ticker in tickers:
            market_df = _load_market_history(self.db, ticker)
            if market_df.empty:
                warnings.append(f"No market data for {ticker}; consider re-ingesting")
                continue
            sentiment = _load_sentiment(self.db, ticker)
            try:
                features_df, tensor = self.provider.build_features(market_df, sentiment, ticker)
                tensor = np.asarray(tensor)
            except Exception as exc:
                warnings.append(f"Feature build failed for {ticker}: {exc}")
                continue
            as_of = pd.to_datetime(market_df["date"].iloc[-1]).to_pydatetime()
            context = {
                "sentiment": sentiment,
                "metrics": {
                    "rows": len(market_df),
                    "feature_columns": list(features_df.columns),
                },
            }
            self.repository.store_window(
                ticker=ticker,
                as_of=as_of,
                version="v1",
                tensor=tensor,
                context=context,
            )
            windows_created += 1
        return FeatureBuildResult(tickers=tickers, windows_created=windows_created, warnings=warnings)
