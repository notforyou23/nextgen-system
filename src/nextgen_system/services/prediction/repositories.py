"""Prediction repository."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, Optional

from nextgen_system.persistence.database import get_database, Database


class PredictionRepository:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_database()

    def save_prediction(
        self,
        *,
        prediction_id: str,
        ticker: str,
        as_of: datetime,
        model_id: str,
        prediction: str,
        probability: float,
        confidence: float,
        ensemble_score: float,
        inputs_ref: str,
        diagnostics: Dict,
    ) -> None:
        self.db.execute(
            """
            INSERT OR REPLACE INTO predictions
                (prediction_id, ticker, as_of, model_id, prediction, probability, confidence, ensemble_score, inputs_ref, diagnostics, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                prediction_id,
                ticker,
                as_of.date(),
                model_id,
                prediction,
                probability,
                confidence,
                ensemble_score,
                inputs_ref,
                json.dumps(diagnostics),
            ),
        )


__all__ = ["PredictionRepository"]
