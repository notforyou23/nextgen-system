# Validation & Feedback Architecture

## Validation Service
- Reads latest predictions (by ticker/date/model) and actual market data from `market_prices`.
- Computes next-day direction & percentage move, writes to `prediction_accuracy` with `is_correct` flag.
- Returns summary metrics (validated count, accuracy) for orchestration logging.
- Designed to run daily after predictions (configurable window).

## Feedback Engine
- Consumes validation outputs to compute biases, quality scores, and alignment metrics.
- Updates `feedback_metrics` (key metrics per day) and `learning_insights` (qualitative notes).
- Generates `retrain_signals` for underperforming tickers, including reason and confidence.
- Communicates configuration adjustments by writing to dedicated tables/columns (e.g., suggested threshold updates) that services read before execution.

## Workflow
1. Prediction task writes to `predictions` with diagnostics.
2. Validation service cross-checks predictions with actual closes and populates `prediction_accuracy`.
3. Feedback engine analyzes accuracy & diagnostics to update metrics, insights, and emit retrain signals.
4. Training service reads `retrain_signals` in subsequent runs to prioritize retraining and clears/acknowledges processed signals.
5. Configuration adjustments (e.g., updated up_threshold) persisted in DB and read by services on initialization.

## Goals
- Ensure all outcomes are tracked in DB, enabling transparent auditing.
- Maintain a tight feedback loop that keeps the system learning and adapting to market changes.
- Preserve the philosophical intent by logging decision reasoning and corrective actions.
