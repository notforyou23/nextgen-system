import importlib
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def nextgen_env(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXTGEN__PATHS__DB_PATH", str(tmp_path / "nextgen.db"))
    monkeypatch.setenv("NEXTGEN__PATHS__DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("NEXTGEN__PATHS__MODELS_DIR", str(tmp_path / "models"))

    for name in [n for n in sys.modules if n.startswith("nextgen_system")]:
        sys.modules.pop(name)

    settings_module = importlib.import_module("nextgen_system.config.settings")
    importlib.reload(settings_module)
    config_pkg = importlib.import_module("nextgen_system.config")
    importlib.reload(config_pkg)

    from nextgen_system.persistence import migrator

    migrator.upgrade()
    return tmp_path


def test_feature_builder_creates_windows(nextgen_env, monkeypatch):
    from nextgen_system.persistence.database import get_database
    from nextgen_system.services.features.builder import FeatureBuilderService
    from nextgen_system.services.features import builder as builder_module

    db = get_database()
    db.execute(
        "INSERT INTO ticker_universe (ticker, source, market, min_date, metadata, updated_at) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
        ("TEST", "unit", None, None, "{}"),
    )

    def fake_market(_db, ticker, window_days=90):
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        values = np.linspace(10, 20, num=10)
        return pd.DataFrame(
            {
                "date": dates,
                "open": values,
                "high": values + 1,
                "low": values - 1,
                "close": values,
                "adjusted_close": values,
                "volume": np.full(10, 1000000, dtype=float),
            }
        )

    def fake_sentiment(_db, ticker):
        return {"avg_sentiment": 0.1, "buzz_score": 0.5, "article_count": 5}

    monkeypatch.setattr(builder_module, "_load_market_history", fake_market)
    monkeypatch.setattr(builder_module, "_load_sentiment", fake_sentiment)

    class DummyProvider:
        def build_features(self, market_data, sentiment_data, ticker):
            feature_df = pd.DataFrame({"feature": np.arange(7)})
            tensor = np.ones((7, 24), dtype=float)
            return feature_df, tensor

    service = FeatureBuilderService(feature_provider=DummyProvider())
    result = service.build(["TEST"])

    assert result.windows_created == 1
    rows = db.fetch_all("SELECT ticker FROM feature_windows")
    assert rows == [("TEST",)]


def test_training_prediction_feedback_trading_cycle(nextgen_env, monkeypatch):
    from nextgen_system.persistence.database import get_database
    from nextgen_system.services.features.repositories import FeatureRepository
    from nextgen_system.services.models.training import TrainingService
    from nextgen_system.services.models import training as training_module
    from nextgen_system.services.prediction import PredictionService
    from nextgen_system.services.prediction import service as prediction_module
    from nextgen_system.services.feedback import PredictionValidator, FeedbackEngine
    from nextgen_system.services.feedback.config_overrides import ConfigOverrideRepository
    from nextgen_system.services.trading.service import TradingService

    db = get_database()
    db.execute(
        "INSERT INTO ticker_universe (ticker, source, market, min_date, metadata, updated_at) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
        ("TEST", "unit", None, None, "{}"),
    )

    tensor = np.ones((7, 24), dtype=float)
    feature_repo = FeatureRepository(db)
    today = datetime.utcnow().date()
    tomorrow = today + timedelta(days=1)
    feature_repo.store_window(
        ticker="TEST",
        as_of=datetime.combine(today, datetime.min.time()),
        version="v1",
        tensor=tensor,
        context={"note": "unit-test"},
    )

    db.execute(
        "INSERT INTO market_prices (ticker, date, open, high, low, close, adjusted_close, volume, source, ingested_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
        ("TEST", today.isoformat(), 10.0, 11.0, 9.5, 10.0, 10.0, 1000000, "unit"),
    )
    db.execute(
        "INSERT INTO market_prices (ticker, date, open, high, low, close, adjusted_close, volume, source, ingested_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
        ("TEST", tomorrow.isoformat(), 11.0, 12.0, 10.5, 11.0, 11.0, 1100000, "unit"),
    )

    db.execute(
        "INSERT INTO retrain_signals (ticker, reason, confidence, window_start, window_end) VALUES (?, ?, ?, ?, ?)",
        ("TEST", "unit", 0.8, today.isoformat(), today.isoformat()),
    )

    class DummyTrainProvider:
        def __init__(self):
            self.saved = None

        def train(self, X, y, **kwargs):
            return {"loss": 0.1}

        def save(self, path):
            Path(path).write_text("model")

    monkeypatch.setattr(training_module, "LSTMModelProvider", DummyTrainProvider)

    training_service = TrainingService()
    training_result = training_service.train_on_universe(["TEST"])
    assert training_result.samples > 0
    processed = db.fetch_all("SELECT processed_at FROM retrain_signals WHERE ticker = ?", ("TEST",))
    assert processed[0][0] is not None

    class DummyPredictProvider:
        def __init__(self):
            pass

        def load(self, path):
            self.path = path

        def predict(self, X):
            direction = np.array([1])
            confidence = np.array([0.9])
            probability = np.array([0.9])
            return direction, confidence, probability

    monkeypatch.setattr(prediction_module, "LSTMModelProvider", DummyPredictProvider)

    prediction_service = PredictionService()
    prediction_results = prediction_service.predict(["TEST"])
    assert prediction_results[0].ticker == "TEST"

    validator = PredictionValidator()
    validation_summary = validator.validate_recent(days_back=2)
    assert validation_summary.validated == 1
    assert validation_summary.correct == 1

    feedback_engine = FeedbackEngine()
    feedback_summary = feedback_engine.process()
    override_repo = ConfigOverrideRepository(db)
    threshold_override = override_repo.get("prediction.up_threshold")
    assert threshold_override is not None
    assert float(threshold_override) >= 0.5
    assert feedback_summary.retrain_signals == 0

    monkeypatch.setattr(
        "nextgen_system.services.trading.prioritizer.PrioritizerAdapter.prioritized_tickers",
        lambda self, max_tickers=10: ["TEST"],
    )

    trading_summary = TradingService().run_trading_cycle()
    assert trading_summary["executed"] == 1

    pred_rows = db.fetch_all("SELECT COUNT(*) FROM predictions")
    accuracy_rows = db.fetch_all("SELECT COUNT(*) FROM prediction_accuracy")
    metrics_rows = db.fetch_all("SELECT COUNT(*) FROM feedback_metrics")
    trades_rows = db.fetch_all("SELECT COUNT(*) FROM executed_trades")

    assert pred_rows[0][0] == 1
    assert accuracy_rows[0][0] == 1
    assert metrics_rows[0][0] >= 2
    assert trades_rows[0][0] == 1
