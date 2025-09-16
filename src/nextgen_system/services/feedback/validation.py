"""Prediction validation service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, date
from typing import Optional, Sequence

from nextgen_system.persistence.database import get_database, Database


@dataclass
class ValidationResult:
    validated: int
    correct: int
    accuracy: float


class PredictionValidator:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_database()

    def validate_recent(self, days_back: int = 7) -> ValidationResult:
        start_date = (datetime.utcnow().date() - timedelta(days=days_back)).isoformat()
        predictions = self.db.fetch_all(
            """
            SELECT prediction_id, ticker, as_of, prediction
            FROM predictions
            WHERE as_of >= ?
            """,
            (start_date,),
        )
        validated = 0
        correct = 0
        for prediction_id, ticker, as_of, prediction in predictions:
            if isinstance(as_of, datetime):
                prediction_date = as_of.date()
            elif isinstance(as_of, date):
                prediction_date = as_of
            else:
                prediction_date = datetime.fromisoformat(str(as_of)).date()

            actual_direction, pct_move = self._actual_movement(ticker, prediction_date)
            if actual_direction is None:
                continue
            is_correct = 1 if actual_direction == prediction else 0
            self.db.execute(
                """
                INSERT OR REPLACE INTO prediction_accuracy
                    (prediction_id, ticker, prediction_date, verification_date, actual_direction, price_move, is_correct, validation_source, validated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    prediction_id,
                    ticker,
                    prediction_date.isoformat(),
                    (prediction_date + timedelta(days=1)).isoformat(),
                    actual_direction,
                    pct_move,
                    is_correct,
                    "close_vs_close",
                ),
            )
            validated += 1
            correct += is_correct
        accuracy = correct / validated if validated else 0.0
        return ValidationResult(validated=validated, correct=correct, accuracy=accuracy)

    def _actual_movement(self, ticker: str, as_of: date):
        today_row = self.db.fetch_one(
            "SELECT close FROM market_prices WHERE ticker = ? AND date = ?",
            (ticker, as_of.isoformat()),
        )
        next_row = self.db.fetch_one(
            "SELECT close FROM market_prices WHERE ticker = ? AND date = DATE(?, '+1 day')",
            (ticker, as_of.isoformat()),
        )
        if not today_row or not next_row:
            return None, None
        today_price = float(today_row[0])
        next_price = float(next_row[0])
        pct_move = (next_price - today_price) / today_price
        direction = "UP" if next_price >= today_price else "DOWN"
        return direction, pct_move


__all__ = ["PredictionValidator", "ValidationResult"]
