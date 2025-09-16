"""Feedback engine."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

from nextgen_system.config import settings
from nextgen_system.persistence.database import get_database, Database
from .config_overrides import ConfigOverrideRepository


@dataclass
class FeedbackSummary:
    metrics: Dict[str, float]
    retrain_signals: int


class FeedbackEngine:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_database()
        self.overrides = ConfigOverrideRepository(self.db)

    def process(self, for_date: Optional[str] = None) -> FeedbackSummary:
        date_str = for_date or datetime.utcnow().date().isoformat()
        rows = self.db.fetch_all(
            "SELECT ticker, is_correct FROM prediction_accuracy WHERE prediction_date = ?",
            (date_str,),
        )
        if not rows:
            return FeedbackSummary(metrics={}, retrain_signals=0)
        total = len(rows)
        correct = sum(row[1] for row in rows)
        accuracy = correct / total if total else 0.0
        bias = self._calculate_bias(date_str)
        self._store_metric(date_str, "accuracy", accuracy)
        self._store_metric(date_str, "bias", bias)
        self._adjust_thresholds(accuracy)
        retrain_count = self._generate_retrain_signals(date_str, threshold=0.4)
        return FeedbackSummary(metrics={"accuracy": accuracy, "bias": bias}, retrain_signals=retrain_count)

    def _calculate_bias(self, date_str: str) -> float:
        rows = self.db.fetch_all(
            "SELECT prediction FROM predictions WHERE as_of = ?",
            (date_str,),
        )
        if not rows:
            return 0.0
        ups = sum(1 for row in rows if row[0] == "UP")
        downs = sum(1 for row in rows if row[0] == "DOWN")
        if ups + downs == 0:
            return 0.0
        return abs(ups - downs) / (ups + downs)

    def _store_metric(self, date_str: str, name: str, value: float) -> None:
        self.db.execute(
            """
            INSERT INTO feedback_metrics (as_of, metric_name, metric_value, status, details)
            VALUES (?, ?, ?, ?, ?)
            """,
            (date_str, name, value, self._metric_status(name, value), json.dumps({})),
        )

    def _metric_status(self, name: str, value: float) -> str:
        if name == "accuracy":
            if value >= 0.8:
                return "EXCELLENT"
            if value >= 0.6:
                return "GOOD"
            if value >= 0.4:
                return "FAIR"
            return "CRITICAL"
        if name == "bias":
            if value <= 0.2:
                return "EXCELLENT"
            if value <= 0.4:
                return "GOOD"
            if value <= 0.6:
                return "FAIR"
            return "CRITICAL"
        return "UNKNOWN"

    def _generate_retrain_signals(self, date_str: str, threshold: float) -> int:
        rows = self.db.fetch_all(
            """
            SELECT predictions.ticker, predictions.prediction, predictions.probability
            FROM predictions
            JOIN prediction_accuracy ON predictions.prediction_id = prediction_accuracy.prediction_id
            WHERE prediction_accuracy.prediction_date = ? AND prediction_accuracy.is_correct = 0
            """,
            (date_str,),
        )
        count = 0
        for ticker, prediction, probability in rows:
            confidence = abs(probability - 0.5) * 2
            if confidence < threshold:
                continue
            self.db.execute(
                """
                INSERT INTO retrain_signals (ticker, reason, confidence, window_start, window_end)
                VALUES (?, ?, ?, DATE(?, '-7 day'), ?)
                """,
                (
                    ticker,
                    f"High-confidence {prediction} prediction failed",
                    confidence,
                    date_str,
                    date_str,
                ),
            )
            count += 1
        return count

    def _adjust_thresholds(self, accuracy: float) -> None:
        base_threshold = float(self.overrides.get("prediction.up_threshold", "" ) or settings.get("prediction", "up_threshold", default=0.5))
        if accuracy < 0.4:
            new_threshold = max(0.3, base_threshold - 0.05)
            self.overrides.set("prediction.up_threshold", f"{new_threshold:.3f}")
        elif accuracy > 0.7:
            new_threshold = min(0.7, base_threshold + 0.01)
            self.overrides.set("prediction.up_threshold", f"{new_threshold:.3f}")


__all__ = ["FeedbackEngine", "FeedbackSummary"]
