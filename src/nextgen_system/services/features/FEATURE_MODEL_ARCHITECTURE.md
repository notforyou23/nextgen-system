# Feature & Model Architecture Blueprint

## Philosophy Alignment
The legacy system encoded its trading philosophy directly in feature engineering, model construction, and feedback. In the next-gen system we preserve that intent by:
- Maintaining separation of **signals (data)**, **reasoning (features + philosophy flags)**, and **decisions (predictions/trades)** so every choice is auditable in the database.
- Allowing the feedback loop to adjust feature parameters, re-train models, and update thresholds through configuration stored in the DB (`feedback_metrics`, `learning_insights`, `retrain_signals`).
- Recording every transformation step with metadata (feature window IDs, model versions, prediction diagnostics, trade reasoning) so change suggestions can be actioned and reviewed.

## Components

### 1. Feature Providers
- Wrap legacy `FeatureEngineer` logic to operate on `market_prices` + `news_sentiment` tables.
- Support parameter overrides (window lengths, indicator toggles) fetched from configuration tables, enabling feedback-driven adjustments.
- Emit feature tensors + context metadata (indicator contributions, philosophy flags such as "hold until profitable" metrics).

### 2. Feature Repository & Service
- `FeatureRepository` writes sequences into `feature_windows` with deterministic IDs (hash of ticker+date+version) and stores context JSON.
- `FeatureBuilderService` orchestrates loading raw data, generating features, persisting windows, and returning summary metrics (tickers processed, windows created, warnings).
- Supports dependency on `UniverseRepository` and can accept ad-hoc ticker lists (for retraining) or scheduled batches (daily builds).

### 3. Model Registry & Training Service
- `ModelRepository` manages `model_registry` entries and tracks artifact paths, metrics, promotion status.
- `TrainingService` (rebuilt from `BulkModelTrainer`) pulls feature windows by ticker/date range, trains LSTM or ensemble models, evaluates them, records metrics, and registers new model versions.
- Accepts `retrain_signals` to prioritize tickers flagged by feedback; updates those signals after completion.

### 4. Prediction Service
- `PredictionService` consumes feature windows, loads the promoted model, produces predictions, and persists to `predictions` including diagnostic breakdown (`ensemble_diversity`, `bounds_reasoning`, etc.).
- Stores reasoning aligned with philosophy (e.g., feature contributions, risk guardrails) in `diagnostics` JSON for transparency.

### 5. Validation & Feedback Hooks
- After predictions, validator compares outcomes (market data) and writes to `prediction_accuracy`.
- Feedback engine reads accuracy + diagnostics, updates `feedback_metrics`, logs insights, and creates `retrain_signals` or configuration recommendations (e.g., adjust indicator weightings).
- Feature service reads these recommendations on next run (via config tables) to adapt inputs dynamically.

### 6. Decision Tracking
- Each stage writes comprehensive metadata to DB:
  * `feature_windows`: includes indicator values, philosophy flags.
  * `predictions`: stores ensemble breakdown, bounds, reasoning text.
  * `trade_plans`/`executed_trades`: record AI reasoning, confidence, and references back to predictions and feature IDs.
- This ensures every decision is traceable end-to-end and can be updated or audited later.

## Next Implementation Steps
1. Scaffold feature service modules (`providers`, `repositories`, `service`) mirroring ingestion pattern; port the existing `FeatureEngineer` calculations.
2. Create model repository/service scaffolding with clear separation between training and inference; integrate with `model_registry`.
3. Extend orchestrator tasks to sequence feature builds before predictions and to accept feedback-driven overrides.
4. Implement validator + feedback services to close the loop and ensure configuration changes propagate via DB entries.

This architecture keeps the philosophical intent front and center while ensuring every input, transformation, and decision is stored and observable in the new database schema.
