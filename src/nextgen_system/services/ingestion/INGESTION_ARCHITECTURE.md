# Ingestion Service Architecture

## Goals
- Separate **data acquisition** (external APIs) from **persistence** (writing to canonical tables).
- Provide deterministic, testable units: providers can be mocked; repositories operate on the database; services orchestrate retries & batching.
- Maintain strict adherence to `DATA_CONTRACTS.md`.

## Components

### Providers
- `MarketDataProvider`: interface with method `fetch(ticker: str, start: date, end: date) -> DataFrame`.
- `NewsProvider`: returns articles + metadata; supports enhanced search flags.
- Providers encapsulate rate limiting/retry logic and live under `services/ingestion/providers/`.

### Repositories
- `MarketRepository`: insert/update rows in `market_prices`, with idempotent upserts.
- `NewsRepository`: batch insert into `news_articles` & `news_sentiment`.
- `UniverseRepository`: read/write `ticker_universe`.
- Implemented in `services/ingestion/repositories.py` using the persistence layer.

### Services
- `MarketIngestionService` orchestrates: select tickers → call provider (possibly in batches with concurrency) → persist via repository → return summary.
- `NewsIngestionService` similar but writes to both tables and handles caching logic (skip fetching when within cache window).
- `UniverseCuratorService` queries repositories & applies rules (volume thresholds etc.).

### Task Flow
1. Universe refresh populates `ticker_universe` (and optionally returns tickers).
2. Market ingestion obtains tickers (from service argument or repository) and fetches OHLCV for required window.
3. News ingestion obtains tickers & collects articles/sentiment.
4. `task_runs` entries record execution metrics via `TaskRegistry`.

## Migration Strategy
- Start with provider adapters wrapping legacy modules: e.g., adapt existing `src/data_ingestion/market_data.py` to the new `MarketDataProvider` interface without carrying over global state.
- Once providers are stable, gradually replace direct usage in legacy pipeline with calls into new services for testing.

## Next Implementation Steps
1. Create provider interfaces and repository implementations under `services/ingestion/providers/` and `repositories.py`.
2. Update service classes to use these abstractions; implement ingestion loops with proper persistence.
3. Port legacy logic into provider implementations (respecting new configuration settings).

This document guides the upcoming implementation work to ensure a clean separation of concerns.
