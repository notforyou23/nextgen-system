"""Trading repositories."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, Iterable, Optional

from nextgen_system.persistence.database import get_database, Database


class TradeRepository:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_database()

    def log_plan(self, plan: Dict) -> None:
        self.db.execute(
            """
            INSERT INTO trade_plans
                (plan_id, as_of, ticker, action, quantity, price_ref, prediction_id, confidence, reasoning)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plan["plan_id"],
                plan["as_of"],
                plan["ticker"],
                plan["action"],
                plan["quantity"],
                plan["price_ref"],
                plan["prediction_id"],
                plan["confidence"],
                json.dumps(plan.get("reasoning", {})),
            ),
        )

    def log_execution(self, trade: Dict) -> None:
        self.db.execute(
            """
            INSERT INTO executed_trades
                (trade_id, plan_id, ticker, action, quantity, price, executed_at, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade["trade_id"],
                trade["plan_id"],
                trade["ticker"],
                trade["action"],
                trade["quantity"],
                trade["price"],
                trade["executed_at"],
                trade["status"],
                json.dumps(trade.get("notes", {})),
            ),
        )

    def log_portfolio_snapshot(self, snapshot: Dict) -> None:
        self.db.execute(
            """
            INSERT INTO portfolio_holdings
                (snapshot_id, taken_at, total_value, cash_balance, positions, pnl_daily, pnl_total, win_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot["snapshot_id"],
                snapshot["taken_at"],
                snapshot["total_value"],
                snapshot["cash_balance"],
                json.dumps(snapshot.get("positions", {})),
                snapshot.get("pnl_daily", 0.0),
                snapshot.get("pnl_total", 0.0),
                snapshot.get("win_rate", 0.0),
            ),
        )


__all__ = ["TradeRepository"]
