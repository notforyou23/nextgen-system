-- Core domain tables per DATA_CONTRACTS.md

CREATE TABLE IF NOT EXISTS ticker_universe (
    ticker TEXT PRIMARY KEY,
    source TEXT,
    market TEXT,
    min_date DATE,
    metadata JSON,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS market_prices (
    ticker TEXT NOT NULL,
    date DATE NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    adjusted_close REAL,
    volume REAL,
    source TEXT,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticker, date)
);
CREATE INDEX IF NOT EXISTS idx_market_prices_source ON market_prices(source);

CREATE TABLE IF NOT EXISTS news_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT,
    headline TEXT,
    published_at TIMESTAMP,
    source TEXT,
    url TEXT,
    raw_json JSON,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS news_sentiment (
    ticker TEXT NOT NULL,
    as_of DATE NOT NULL,
    method TEXT NOT NULL,
    article_count INTEGER,
    avg_sentiment REAL,
    buzz_score REAL,
    volatility REAL,
    details JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticker, as_of, method)
);

CREATE TABLE IF NOT EXISTS feature_windows (
    id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    as_of DATE NOT NULL,
    sequence_length INTEGER,
    feature_count INTEGER,
    feature_version TEXT,
    data_path TEXT,
    context JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_feature_windows_ticker ON feature_windows(ticker, as_of);

CREATE TABLE IF NOT EXISTS model_registry (
    model_id TEXT PRIMARY KEY,
    model_type TEXT,
    training_data_range TEXT,
    feature_version TEXT,
    metrics JSON,
    artifact_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    promoted_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS predictions (
    prediction_id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    as_of DATE NOT NULL,
    model_id TEXT,
    prediction TEXT,
    probability REAL,
    confidence REAL,
    ensemble_score REAL,
    inputs_ref TEXT,
    diagnostics JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_predictions_ticker ON predictions(ticker, as_of);

CREATE TABLE IF NOT EXISTS prediction_accuracy (
    prediction_id TEXT PRIMARY KEY,
    ticker TEXT,
    prediction_date DATE,
    verification_date DATE,
    actual_direction TEXT,
    price_move REAL,
    is_correct INTEGER,
    validation_source TEXT,
    validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feedback_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    as_of DATE,
    metric_name TEXT,
    metric_value REAL,
    status TEXT,
    details JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS learning_insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    as_of DATE,
    scope TEXT,
    ticker TEXT,
    insight TEXT,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS retrain_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT,
    reason TEXT,
    confidence REAL,
    window_start DATE,
    window_end DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS strategic_priorities (
    ticker TEXT NOT NULL,
    as_of DATE NOT NULL,
    tier TEXT,
    score REAL,
    rationale TEXT,
    factors JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticker, as_of)
);

CREATE TABLE IF NOT EXISTS trade_plans (
    plan_id TEXT PRIMARY KEY,
    as_of TIMESTAMP,
    ticker TEXT,
    action TEXT,
    quantity REAL,
    price_ref REAL,
    prediction_id TEXT,
    confidence REAL,
    reasoning JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS executed_trades (
    trade_id TEXT PRIMARY KEY,
    plan_id TEXT,
    ticker TEXT,
    action TEXT,
    quantity REAL,
    price REAL,
    executed_at TIMESTAMP,
    status TEXT,
    notes JSON
);
CREATE INDEX IF NOT EXISTS idx_executed_trades_plan ON executed_trades(plan_id);

CREATE TABLE IF NOT EXISTS portfolio_holdings (
    snapshot_id TEXT PRIMARY KEY,
    taken_at TIMESTAMP,
    total_value REAL,
    cash_balance REAL,
    positions JSON,
    pnl_daily REAL,
    pnl_total REAL,
    win_rate REAL
);

CREATE TABLE IF NOT EXISTS system_health (
    component TEXT PRIMARY KEY,
    last_success TIMESTAMP,
    last_failure TIMESTAMP,
    status TEXT,
    message TEXT,
    metadata JSON
);
