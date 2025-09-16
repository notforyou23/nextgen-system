"""Trading service for next-gen system."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from nextgen_system.persistence.database import get_database, Database
from nextgen_system.services.prediction.repositories import PredictionRepository
from nextgen_system.services.trading.repositories import TradeRepository
from nextgen_system.services.trading.prioritizer import PrioritizerAdapter


@dataclass
class TradeDecision:
    ticker: str
    action: str
    quantity: float
    price_ref: float
    confidence: float
    reasoning: Dict[str, str]
    prediction_id: str


class TradingService:
    def __init__(
        self,
        db: Optional[Database] = None,
        prediction_repo: Optional[PredictionRepository] = None,
        trade_repo: Optional[TradeRepository] = None,
        prioritizer: Optional[PrioritizerAdapter] = None,
    ):
        self.db = db or get_database()
        self.prediction_repo = prediction_repo or PredictionRepository(self.db)
        self.trade_repo = trade_repo or TradeRepository(self.db)
        self.prioritizer = prioritizer or PrioritizerAdapter()
        self.cash = 10000.0

    def run_trading_cycle(self) -> Dict[str, int]:
        prioritized = self.prioritizer.prioritized_tickers(max_tickers=10)
        decisions = [self._create_decision(ticker) for ticker in prioritized]
        executed = 0
        for decision in decisions:
            if not decision:
                continue
            plan_id = self._plan_id(decision)
            self.trade_repo.log_plan(
                {
                    "plan_id": plan_id,
                    "as_of": datetime.utcnow().isoformat(),
                    "ticker": decision.ticker,
                    "action": decision.action,
                    "quantity": decision.quantity,
                    "price_ref": decision.price_ref,
                    "prediction_id": decision.prediction_id,
                    "confidence": decision.confidence,
                    "reasoning": decision.reasoning,
                }
            )
            self.trade_repo.log_execution(
                {
                    "trade_id": f"trade_{plan_id}",
                    "plan_id": plan_id,
                    "ticker": decision.ticker,
                    "action": decision.action,
                    "quantity": decision.quantity,
                    "price": decision.price_ref,
                    "executed_at": datetime.utcnow().isoformat(),
                    "status": "EXECUTED",
                    "notes": decision.reasoning,
                }
            )
            executed += 1
        self.trade_repo.log_portfolio_snapshot(
            {
                "snapshot_id": hashlib.sha256(datetime.utcnow().isoformat().encode()).hexdigest(),
                "taken_at": datetime.utcnow().isoformat(),
                "total_value": self.cash,
                "cash_balance": self.cash,
                "positions": {},
                "pnl_daily": 0.0,
                "pnl_total": 0.0,
                "win_rate": 0.0,
            }
        )
        return {"decisions": len(decisions), "executed": executed}

    def _create_decision(self, ticker: str) -> Optional[TradeDecision]:
        prediction = self.db.fetch_one(
            """
            SELECT prediction_id, prediction, probability, confidence
            FROM predictions
            WHERE ticker = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (ticker,),
        )
        if not prediction:
            return None
        prediction_id, direction, probability, confidence = prediction
        action = "BUY" if direction == "UP" else "SELL"
        price_row = self.db.fetch_one(
            "SELECT close FROM market_prices WHERE ticker = ? ORDER BY date DESC LIMIT 1",
            (ticker,),
        )
        price = float(price_row[0]) if price_row else 0.0
        quantity = max(self.cash * 0.01 / price, 0) if price > 0 else 0
        reasoning = {
            "philosophy": "Grow the portfolio's bottom line bank through confident, future-oriented investments",
            "prediction": direction,
            "probability": f"{probability:.2f}",
        }
        return TradeDecision(
            ticker=ticker,
            action=action,
            quantity=quantity,
            price_ref=price,
            confidence=confidence,
            reasoning=reasoning,
            prediction_id=prediction_id,
        )

    def _plan_id(self, decision: TradeDecision) -> str:
        key = f"{decision.ticker}|{decision.action}|{datetime.utcnow().isoformat()}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()
