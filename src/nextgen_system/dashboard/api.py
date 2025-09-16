from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, Query
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from nextgen_system.dashboard import repository
from nextgen_system.dashboard.schemas import (
    FeedbackResponse,
    PortfolioResponse,
    PredictionsResponse,
    StatusResponse,
    TradesResponse,
)

app = FastAPI(title="Next-Gen Trading Dashboard")
app.mount("/static", StaticFiles(directory=str((Path(__file__).parent / "static"))), name="static")


@app.get("/")
def index() -> RedirectResponse:
    return RedirectResponse(url="/static/index.html")


def get_status_response() -> StatusResponse:
    return StatusResponse(
        task_runs=repository.fetch_latest_task_runs(),
        feedback_metrics=repository.fetch_feedback_metrics(),
        config_overrides=repository.fetch_config_overrides(),
    )


@app.get("/status", response_model=StatusResponse)
def read_status(response: StatusResponse = Depends(get_status_response)):
    return response


@app.get("/predictions", response_model=PredictionsResponse)
def read_predictions(
    limit: int = Query(50, ge=1, le=500), ticker: str | None = Query(None, description="Filter by ticker")
):
    predictions = repository.fetch_recent_predictions(limit=limit, ticker=ticker)
    return PredictionsResponse(predictions=predictions)


@app.get("/feedback", response_model=FeedbackResponse)
def read_feedback(days: int = Query(7, ge=1, le=30)):
    metrics = repository.fetch_feedback_metrics(days=days)
    accuracy = repository.fetch_recent_accuracy(days=days)
    retrain = repository.fetch_retrain_signals()
    return FeedbackResponse(metrics=metrics, accuracy=accuracy, retrain_signals=retrain)


@app.get("/trades", response_model=TradesResponse)
def read_trades(limit: int = Query(50, ge=1, le=200)):
    trades = repository.fetch_recent_trades(limit=limit)
    return TradesResponse(trades=trades)


@app.get("/portfolio", response_model=PortfolioResponse)
def read_portfolio():
    snapshot = repository.fetch_latest_portfolio()
    return PortfolioResponse(portfolio=snapshot)


if __name__ == "__main__":
    uvicorn.run("nextgen_system.dashboard.api:app", host="0.0.0.0", port=8081, reload=False)
