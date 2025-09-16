"""Local feature engineering provider for the next-gen system."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np
import pandas as pd


@dataclass
class FeatureEngineeringProvider:
    """Generates technical features and tensors without legacy dependencies."""

    min_history: int = 30

    def build_features(
        self, market_data: pd.DataFrame, sentiment_data: Dict, ticker: str
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        if market_data.empty:
            raise ValueError(f"No market data available for {ticker}")

        df = market_data.copy()
        df = df.sort_values("date")

        # Basic price-derived indicators
        df["return_1d"] = df["close"].pct_change().fillna(0.0)
        df["sma_5"] = df["close"].rolling(window=5, min_periods=1).mean()
        df["sma_20"] = df["close"].rolling(window=20, min_periods=1).mean()
        df["sma_ratio"] = np.where(df["sma_20"] == 0, 0.0, df["sma_5"] / df["sma_20"])
        df["volatility_10"] = df["return_1d"].rolling(window=10, min_periods=1).std().fillna(0.0)
        df["volume_z"] = (df["volume"] - df["volume"].rolling(window=20, min_periods=1).mean())
        volume_std = df["volume"].rolling(window=20, min_periods=1).std().replace(0, np.nan)
        df["volume_z"] = df["volume_z"] / volume_std
        df["volume_z"] = df["volume_z"].fillna(0.0)

        # Inject sentiment context if available
        sentiment_score = float(sentiment_data.get("avg_sentiment", 0.0)) if sentiment_data else 0.0
        buzz_score = float(sentiment_data.get("buzz_score", 0.0)) if sentiment_data else 0.0
        df["sentiment_score"] = sentiment_score
        df["sentiment_buzz"] = buzz_score

        df = df.fillna(0.0)

        # Build tensor expected by downstream models (sequence of OHLCV rows)
        seq = df[["open", "high", "low", "close", "volume"]].to_numpy(dtype=float)
        if len(seq) < self.min_history:
            pad_rows = self.min_history - len(seq)
            pad = np.repeat(seq[:1], pad_rows, axis=0) if len(seq) else np.zeros((pad_rows, 5))
            seq = np.vstack([pad, seq])
        return df, seq


__all__ = ["FeatureEngineeringProvider"]
