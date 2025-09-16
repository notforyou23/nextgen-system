# Next-Generation Architecture Blueprint

## Guiding Goals
- Preserve the proven capabilities of the current system (real data ingestion, advanced feature engineering, LSTM modelling, learning feedback, philosophical trading) while stripping away hidden coupling and implicit behaviour.
- Promote clarity and observability: each stage exposes a defined interface, persists durable artefacts, and avoids side effects outside its responsibility.
- Enable incremental evolution: components can be swapped or improved without rewriting the entire stack.

## High-Level Flow
```
Market/News Sources --> Ingestion Service --> Canonical Data Store
                                     \
                                      v
                              Feature Builder ----> Feature Store
                                      |                 |
                                      v                 v
                                Model Service <---- Training Jobs
                                      |
                                      v
                               Prediction Service --> Prediction Ledger
                                      |
                                      v
                   Validation & Feedback Service --> Metrics/Signals
                                      |
                                      v
                             Trading Execution Engine --> Trade Ledger
                                      |
                                      v
                           Control Plane Orchestrator (Schedules, Health)
```

## Core Domains & Responsibilities

### 1. Ingestion Services
- **Market Ingestion Worker**: pulls OHLCV + intraday snapshots using `MarketDataIngester` logic, standardises ticker IDs, enriches with metadata (source, timezone), and writes to `market_prices` (SQLite/Parquet).
- **News & Sentiment Worker**: gathers news via RealNews/OpenAI flows, scores sentiment, records raw articles and aggregate stats in `news_articles` & `news_sentiment`. Responsible for cache policy and rate limiting. No downstream module calls.
- **Universe Curator**: periodically rebuilds the tradable universe (dynamic filters) and persists to `ticker_universe` for others to consume.

### 2. Feature Engineering Layer
- **Feature Builder Service**: consumes canonical market/news tables, computes engineered indicators with `FeatureEngineer`, and stores outputs in `feature_windows` (sequence tensors + metadata). Ensures reproducible feature sets by versioning calculations.
- **Curiosity Hooks**: emits feature provenance (which raw rows contributed) to support post-mortem analysis.

### 3. Model Services
- **Inference Microservice**: loads frozen LSTM weights and scalers, generates predictions from feature batches, and exposes a simple interface (`predict_batch(features_id) -> predictions`). No database writes beyond logging inference metadata.
- **Training Orchestrator**: schedules training jobs (bulk or targeted) via `BulkModelTrainer` rebuilt to operate on stored features. Outputs new model versions with evaluation metrics recorded in `model_registry`.

### 4. Prediction Service
- Thin orchestration layer that:
  1. Selects tickers (via universe + prioritiser tables),
  2. Requests features from Feature Builder,
  3. Calls the inference service,
  4. Applies ensemble/bounds adjustments,
  5. Writes results to `predictions` and attaches artefacts (inputs, ensemble breakdown, diagnostics).
- No feedback or trading side effects—only produces predictions.

### 5. Validation & Feedback
- **Validator Job**: compares `predictions` vs realised prices in `market_prices`, writes outcomes to `prediction_accuracy`, and publishes validation events.
- **Feedback Engine**: reuses `CuriosityEngine` & `FeedbackSystem` to compute calibration adjustments and health metrics, persisting to `feedback_metrics` / `learning_insights`. Produces actionable signals (`retrain_candidates`, `bias_flags`).

### 6. Trading Execution
- **Trade Planner**: consumes predictions + strategic priorities, applies philosophical rules, and drafts trades.
- **Execution Simulator**: realises trades in the simulated ledger (`executed_trades`, `portfolio_holdings`), manages positions, and records reflections. Uses data contracts only—no direct pipeline calls.

### 7. Control Plane
- **Orchestrator**: single entry point (CLI/service) that sequences ingestion, feature builds, prediction runs, validation, feedback, and trading according to configurable schedules. Interacts with services via explicit commands or task queue (initial version can be synchronous).
- **Monitoring & Health**: collects status from each service (heartbeats, last successful run, error counts) and writes to `system_health`. Dashboard rebuild will visualise this later.

## Supporting Components
- **Configuration Layer**: one authoritative configuration package (`nextgen_system/config/`) providing defaults + env overrides. Modules import from here rather than duplicating constants.
- **Persistence Layer**: database helper module (enhanced `bulletproof_database`) offering connection management, migrations, and typed query utilities. Shared across services.
- **Task Definitions**: manifest describing each scheduled task, dependencies, expected outputs, and failover strategy—used by orchestrator to maintain determinism.

## Migration Approach
1. Implement infrastructure & data contracts in isolation (no mutation of current system).
2. Re-point legacy modules gradually to read from canonical stores for validation.
3. Once new pipeline is validated, migrate launchd services to the new orchestrator.

This blueprint anchors the rebuild: every subsequent refactor must map to one of the defined services or supporting components, ensuring the final system remains coherent and maintainable.
