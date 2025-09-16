"""Prediction service for next-gen system."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, Optional, Sequence

import numpy as np

from nextgen_system.persistence.database import get_database, Database
from nextgen_system.services.features.repositories import FeatureRepository
from nextgen_system.services.models.providers.lstm import LSTMModelProvider
from nextgen_system.services.models.repositories import ModelRepository
from .repositories import PredictionRepository


@dataclass
class PredictionResult:
    ticker: str
    prediction_id: str
    prediction: str
    probability: float
    confidence: float


class PredictionService:
    def __init__(
        self,
        db: Optional[Database] = None,
        feature_repo: Optional[FeatureRepository] = None,
        model_repo: Optional[ModelRepository] = None,
        prediction_repo: Optional[PredictionRepository] = None,
        model_provider: Optional[LSTMModelProvider] = None,
    ):
        self.db = db or get_database()
        self.feature_repo = feature_repo or FeatureRepository(self.db)
        self.model_repo = model_repo or ModelRepository(self.db)
        self.prediction_repo = prediction_repo or PredictionRepository(self.db)
        self.model_provider = model_provider or LSTMModelProvider()

    def predict(self, tickers: Optional[Sequence[str]] = None) -> Sequence[PredictionResult]:
        model_info = self.model_repo.latest_model()
        if not model_info:
            raise RuntimeError("No promoted model available for predictions")
        self.model_provider.load(model_info["artifact_path"])
        tickers = list(tickers) if tickers else [row[0] for row in self.db.fetch_all("SELECT ticker FROM ticker_universe")]
        results = []
        for ticker in tickers:
            window = self.feature_repo.latest_window(ticker)
            if not window:
                continue
            tensor = self.feature_repo.load_tensor(window["data_path"])  # shape (seq, features)
            sample = tensor[np.newaxis, ...]
            direction_raw, confidence_raw, proba_raw = self.model_provider.predict(sample)
            prob_up = float(np.clip(proba_raw[0], 0.0, 1.0))
            direction = "UP" if direction_raw[0] == 1 else "DOWN"
            confidence = float(np.clip(confidence_raw[0], 0.0, 1.0))
            prediction_id = self._prediction_id(ticker, window["as_of"], model_info["model_id"])
            diagnostics = {
                "feature_id": window["id"],
                "feature_version": window["feature_version"],
                "probability_up": prob_up,
            }
            self.prediction_repo.save_prediction(
                prediction_id=prediction_id,
                ticker=ticker,
                as_of=window["as_of"],
                model_id=model_info["model_id"],
                prediction=direction,
                probability=prob_up,
                confidence=confidence,
                ensemble_score=prob_up,
                inputs_ref=window["id"],
                diagnostics=diagnostics,
            )
            results.append(PredictionResult(ticker=ticker, prediction_id=prediction_id, prediction=direction, probability=prob_up, confidence=confidence))
        if not results:
            raise RuntimeError("Prediction run produced no results; ensure feature windows exist")
        return results

    def _prediction_id(self, ticker: str, as_of, model_id: str) -> str:
        key = f"{ticker}|{as_of.isoformat()}|{model_id}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()


__all__ = ["PredictionService", "PredictionResult"]
