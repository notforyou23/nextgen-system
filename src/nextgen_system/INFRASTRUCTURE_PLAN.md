# Shared Infrastructure Plan

This document outlines the foundational modules that every next-gen service will rely on: configuration management, persistence primitives, and task orchestration scaffolding. The goal is to stabilise these pieces before migrating any business logic.

## 1. Configuration Layer (`nextgen_system/config`)

### Objectives
- Provide a single source of truth for runtime settings across services.
- Support environment-specific overrides without duplicating constants.
- Offer type-checked access and validation to catch misconfiguration early.

### Approach
1. **Settings Definition**: create `settings.py` exporting a `Settings` dataclass (or Pydantic BaseSettings if we add the dependency) with nested sections (data_paths, ingestion, prediction, trading, scheduler).
2. **Loading Order**:
   - Defaults loaded from `defaults.yaml` (checked into repo).
   - Optional profile files (`development.yaml`, `production.yaml`) under `config/profiles/`.
   - Environment variables override using `ENV_VAR_PREFIX` (e.g., `NEXTGEN__PREDICTION__CONCURRENCY`).
   - Local `.env` (if present) read last for developer overrides.
3. **Access Pattern**: modules import `from nextgen_system.config import settings` which performs lazy singleton instantiation. Settings object is immutable after load (frozen dataclass) to prevent runtime drift.
4. **Runtime Introspection**: provide helper `dump()` to render effective configuration for logging/debugging.

### Deliverables
- `config/defaults.yaml` with baseline values (paths, DB filename, concurrency caps, thresholds).
- `config/settings.py` implementing the loader + environment override logic.
- `config/__init__.py` exposing `settings` and `load_settings(profile=None)`.

## 2. Persistence Layer (`nextgen_system/persistence`)

### Objectives
- Centralise database access with consistent connection management and migrations.
- Expose typed DAO utilities for common operations (select, insert_many) while allowing raw SQL when needed.
- Provide migration tooling to evolve schema defined in `DATA_CONTRACTS.md`.

### Approach
1. **Connection Manager** (`database.py`):
   - Wrap SQLite connection using `sqlite3` with WAL settings, busy timeout, and thread safety.
   - Manage a singleton connection per process with health checks (adapted from existing `bulletproof_database` but simplified and documented).
   - Expose context manager `get_cursor()` plus helper methods (`execute`, `fetch_all`, `fetch_one`, `executemany`).
2. **Migration Engine** (`migrator.py`):
   - Maintain a `_migrations` table storing ID, description, applied_at.
   - Load SQL files from `nextgen_system/migrations/*.sql` or Python migration scripts implementing `upgrade(conn)`.
   - Provide CLI entry `python -m nextgen_system.persistence.migrator upgrade` for orchestration.
3. **Data Access Helpers** (`repositories.py`):
   - Optional typed wrappers for common tables (e.g., `PredictionsRepository`). Keep lightweight to avoid rigid ORM.
4. **Testing Utilities**: helper to create an in-memory database with migrations applied for unit tests.

### Deliverables
- `persistence/database.py` skeleton with connection class + context manager.
- `persistence/migrator.py` with migration registry.
- First migration file `migrations/0001_initial.sql` stub aligning with `DATA_CONTRACTS.md` (to be filled when ready).

## 3. Task Orchestration Scaffold (`nextgen_system/orchestration`)

### Objectives
- Provide a thin layer for scheduling/monitoring tasks, independent from cron/launchd.
- Record task execution metadata in `task_runs`.

### Approach
- Implement `TaskRegistry` allowing registration of callable tasks with metadata (name, cadence, dependencies).
- Provide `run_task(name)` for manual invocation and `run_due_tasks(now)` for scheduler loops.
- Integrate with control plane later; initial version may use synchronous loops (e.g., invoked by launchd script).

### Deliverables (initial skeleton)
- Create directory `nextgen_system/orchestration/` with `__init__.py` and `registry.py` placeholder (to be fleshed out in subsequent steps).

## 4. Directory Layout (initialized now)
```
nextgen_system/
  ARCHITECTURE_BLUEPRINT.md
  DATA_CONTRACTS.md
  INFRASTRUCTURE_PLAN.md
  config/
    __init__.py  (placeholder)
    settings.py  (to implement)
    defaults.yaml (to create)
  persistence/
    __init__.py (placeholder)
    database.py (to implement)
    migrator.py (to implement)
  migrations/
    0001_initial.sql (placeholder)
  orchestration/
    __init__.py
    registry.py (placeholder)
```

## 5. Next Actions After This Plan
1. Populate `config/__init__.py` and `settings.py` with the loader logic.
2. Port the robust portions of `bulletproof_database` into `persistence/database.py`, keeping only necessary complexity.
3. Draft the initial migration file mirroring the tables from `DATA_CONTRACTS.md` and implement the migrator CLI.
4. Stub `orchestration/registry.py` with task registration/data logging tied to `task_runs` schema.

With this infrastructure scaffolding locked in, subsequent work (ingestion refactors, prediction service rebuild) can target concrete APIs rather than ad-hoc utilities.
