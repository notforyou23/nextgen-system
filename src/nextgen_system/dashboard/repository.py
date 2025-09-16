from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from nextgen_system.persistence.database import get_database


def fetch_latest_task_runs(limit: int = 10) -> List[Dict[str, Any]]:
    db = get_database()
    rows = db.fetch_all(
        """
        SELECT run_id, task_name, status, triggered_at, completed_at, artifacts, error
        FROM task_runs
        ORDER BY triggered_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    results = []
    for row in rows:
        results.append(
            {
                "run_id": row[0],
                "task_name": row[1],
                "status": row[2],
                "triggered_at": row[3],
                "completed_at": row[4],
                "artifacts": row[5],
                "error": row[6],
            }
        )
    return results


def fetch_feedback_metrics(days: int = 7) -> List[Dict[str, Any]]:
    db = get_database()
    rows = db.fetch_all(
        """
        SELECT as_of, metric_name, metric_value, status, details
        FROM feedback_metrics
        WHERE as_of >= DATE('now', ?)
        ORDER BY as_of DESC
        """,
        (f"-{days} days",),
    )
    return [
        {
            "as_of": row[0],
            "metric_name": row[1],
            "metric_value": row[2],
            "status": row[3],
            "details": row[4],
        }
        for row in rows
    ]


def fetch_config_overrides() -> Dict[str, Any]:
    db = get_database()
    rows = db.fetch_all("SELECT key, value, updated_at FROM config_overrides")
    return {row[0]: {"value": row[1], "updated_at": row[2]} for row in rows}


def fetch_recent_predictions(limit: int = 50, ticker: Optional[str] = None) -> List[Dict[str, Any]]:
    db = get_database()
    params: List[Any] = []
    query = (
        "SELECT prediction_id, ticker, as_of, prediction, probability, confidence, diagnostics, created_at "
        "FROM predictions"
    )
    if ticker:
        query += " WHERE ticker = ?"
        params.append(ticker)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = db.fetch_all(query, tuple(params))
    return [
        {
            "prediction_id": row[0],
            "ticker": row[1],
            "as_of": row[2],
            "prediction": row[3],
            "probability": row[4],
            "confidence": row[5],
            "diagnostics": row[6],
            "created_at": row[7],
        }
        for row in rows
    ]


def fetch_recent_accuracy(days: int = 7) -> List[Dict[str, Any]]:
    db = get_database()
    rows = db.fetch_all(
        """
        SELECT prediction_id, ticker, prediction_date, verification_date, actual_direction, price_move, is_correct
        FROM prediction_accuracy
        WHERE prediction_date >= DATE('now', ?)
        ORDER BY prediction_date DESC
        """,
        (f"-{days} days",),
    )
    return [
        {
            "prediction_id": row[0],
            "ticker": row[1],
            "prediction_date": row[2],
            "verification_date": row[3],
            "actual_direction": row[4],
            "price_move": row[5],
            "is_correct": row[6],
        }
        for row in rows
    ]


def fetch_retrain_signals(limit: int = 20) -> List[Dict[str, Any]]:
    db = get_database()
    rows = db.fetch_all(
        """
        SELECT ticker, reason, confidence, window_start, window_end, created_at, processed_at
        FROM retrain_signals
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    return [
        {
            "ticker": row[0],
            "reason": row[1],
            "confidence": row[2],
            "window_start": row[3],
            "window_end": row[4],
            "created_at": row[5],
            "processed_at": row[6],
        }
        for row in rows
    ]


def fetch_recent_trades(limit: int = 50) -> List[Dict[str, Any]]:
    db = get_database()
    rows = db.fetch_all(
        """
        SELECT trade_id, plan_id, ticker, action, quantity, price, executed_at, status, notes
        FROM executed_trades
        ORDER BY executed_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    return [
        {
            "trade_id": row[0],
            "plan_id": row[1],
            "ticker": row[2],
            "action": row[3],
            "quantity": row[4],
            "price": row[5],
            "executed_at": row[6],
            "status": row[7],
            "notes": row[8],
        }
        for row in rows
    ]


def fetch_latest_portfolio() -> Optional[Dict[str, Any]]:
    db = get_database()
    row = db.fetch_one(
        """
        SELECT snapshot_id, taken_at, total_value, cash_balance, positions, pnl_daily, pnl_total, win_rate
        FROM portfolio_holdings
        ORDER BY taken_at DESC
        LIMIT 1
        """
    )
    if not row:
        return None
    return {
        "snapshot_id": row[0],
        "taken_at": row[1],
        "total_value": row[2],
        "cash_balance": row[3],
        "positions": row[4],
        "pnl_daily": row[5],
        "pnl_total": row[6],
        "win_rate": row[7],
    }
