"""Task registration for the next-generation orchestrator."""

from __future__ import annotations

from dataclasses import asdict
from typing import Iterable, List

from nextgen_system.config import settings
from nextgen_system.services.features import FeatureBuilderService
from nextgen_system.services.prediction import PredictionService
from nextgen_system.services.feedback import PredictionValidator, FeedbackEngine
from nextgen_system.services.trading.service import TradingService
from nextgen_system.services.ingestion import MarketIngestionService, NewsIngestionService, UniverseCuratorService
from nextgen_system.services.ingestion.repositories import UniverseRepository

SCHEDULER_TASKS = settings.get("scheduler", "tasks", default=[])

def _universe_tickers() -> List[str]:
    repo = UniverseRepository()
    tickers = list(repo.list_tickers())
    if not tickers:
        UniverseCuratorService().refresh()
        tickers = list(repo.list_tickers())
    return tickers


def register_tasks(registry):
    registry.register(
        "ingest_market_daily",
        lambda: _run_market_ingestion(),
        dependencies=["build_ticker_universe"],
        description="Fetch OHLCV data for universe tickers",
    )
    registry.register(
        "ingest_news_hourly",
        lambda: _run_news_ingestion(),
        dependencies=["build_ticker_universe"],
        description="Collect news and sentiment",
    )
    registry.register(
        "build_ticker_universe",
        lambda: asdict(UniverseCuratorService().refresh()),
        description="Refresh dynamic ticker universe",
    )
    registry.register(
        "build_features_daily",
        lambda: _run_feature_build(),
        dependencies=["ingest_market_daily", "ingest_news_hourly"],
        description="Generate feature windows for prediction",
    )
    registry.register(
        "run_predictions_daily",
        lambda: _run_predictions(),
        dependencies=["build_features_daily"],
        description="Run model inference across universe",
    )
    registry.register(
        "validate_predictions_daily",
        lambda: _run_validation(),
        dependencies=["run_predictions_daily"],
        description="Validate predictions against market outcomes",
    )
    registry.register(
        "feedback_daily",
        lambda: _run_feedback(),
        dependencies=["validate_predictions_daily"],
        description="Update feedback metrics and retrain signals",
    )
    registry.register(
        "trading_cycle_intraday",
        lambda: _run_trading(),
        dependencies=["feedback_daily"],
        description="Execute trading cycle with philosophical reasoning",
    )
    # TODO: add trading tasks once services exist.


def _run_market_ingestion():
    tickers = _universe_tickers()
    if not tickers:
        raise RuntimeError("Universe contains no tickers; cannot run market ingestion")
    result = MarketIngestionService().ingest(tickers)
    if result.rows_written == 0:
        raise RuntimeError("Market ingestion produced no rows; check data providers")
    return asdict(result)


def _run_news_ingestion():
    tickers = _universe_tickers()
    if not tickers:
        raise RuntimeError("Universe contains no tickers; cannot run news ingestion")
    result = NewsIngestionService().ingest(tickers)
    if result.articles_written == 0:
        raise RuntimeError("News ingestion produced no articles; check data providers")
    return asdict(result)


def _run_feature_build():
    tickers = _universe_tickers()
    if not tickers:
        raise RuntimeError("Universe contains no tickers; cannot build features")
    result = FeatureBuilderService().build(tickers)
    if result.windows_created == 0:
        raise RuntimeError("Feature build produced no windows; ensure market/news data available")
    payload = asdict(result)
    payload["warnings"] = list(result.warnings)
    return payload


def _run_predictions():
    tickers = _universe_tickers()
    if not tickers:
        raise RuntimeError("Universe contains no tickers; cannot run predictions")
    results = PredictionService().predict(tickers)
    return {"predictions": [asdict(result) for result in results]}


def _run_validation():
    result = PredictionValidator().validate_recent(days_back=1)
    if result.validated == 0:
        raise RuntimeError("Validation processed zero predictions; ensure predictions exist")
    return asdict(result)


def _run_feedback():
    summary = FeedbackEngine().process()
    return {"metrics": summary.metrics, "retrain_signals": summary.retrain_signals}


def _run_trading():
    summary = TradingService().run_trading_cycle()
    if summary["executed"] == 0:
        raise RuntimeError("Trading cycle executed zero trades; verify predictions and prioritizer")
    return summary


__all__ = ["register_tasks", "SCHEDULER_TASKS"]
