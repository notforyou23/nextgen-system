from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class TaskRun(BaseModel):
    run_id: str
    task_name: str
    status: str
    triggered_at: Optional[str]
    completed_at: Optional[str]
    artifacts: Optional[str]
    error: Optional[str]


class Metric(BaseModel):
    as_of: str
    metric_name: str
    metric_value: float
    status: str
    details: Optional[str]


class PredictionRecord(BaseModel):
    prediction_id: str
    ticker: str
    as_of: str
    prediction: str
    probability: float
    confidence: float
    diagnostics: Optional[str]
    created_at: Optional[str]


class AccuracyRecord(BaseModel):
    prediction_id: str
    ticker: str
    prediction_date: str
    verification_date: str
    actual_direction: str
    price_move: float
    is_correct: int


class RetrainSignal(BaseModel):
    ticker: str
    reason: str
    confidence: float
    window_start: str
    window_end: str
    created_at: Optional[str]
    processed_at: Optional[str]


class TradeRecord(BaseModel):
    trade_id: str
    plan_id: str
    ticker: str
    action: str
    quantity: float
    price: float
    executed_at: Optional[str]
    status: str
    notes: Optional[str]


class PortfolioSnapshot(BaseModel):
    snapshot_id: str
    taken_at: str
    total_value: float
    cash_balance: float
    positions: Optional[str]
    pnl_daily: float
    pnl_total: float
    win_rate: float


class StatusResponse(BaseModel):
    task_runs: List[TaskRun]
    feedback_metrics: List[Metric]
    config_overrides: Dict[str, Any]


class PredictionsResponse(BaseModel):
    predictions: List[PredictionRecord]


class FeedbackResponse(BaseModel):
    metrics: List[Metric]
    accuracy: List[AccuracyRecord]
    retrain_signals: List[RetrainSignal]


class TradesResponse(BaseModel):
    trades: List[TradeRecord]


class PortfolioResponse(BaseModel):
    portfolio: Optional[PortfolioSnapshot]
