# Next-Gen Dashboard Plan

This directory contains the API surface that will power the new dashboard.

## Components

- `api.py` – FastAPI application exposing read-only endpoints backed by the next-gen SQLite database.
- `schemas.py` – Pydantic response models for serialization.
- `repository.py` – Shared query helpers used by the API endpoints.
- `__init__.py` – Package initializer so the dashboard can be served via `python -m nextgen_system.dashboard.api`.

## Endpoints

- `GET /status`
  - Returns latest task run info, feedback metrics summary, and active overrides.
- `GET /predictions`
  - Lists recent predictions with diagnostics, filterable by ticker/confidence.
- `GET /feedback`
  - Reports daily accuracy, bias, retrain signals, and insights.
- `GET /trades`
  - Shows recent trade plans/executions with reasoning.
- `GET /portfolio`
  - Provides latest portfolio snapshot and P&L.

All endpoints are read-only and designed for integration with a lightweight frontend or CLI dashboard.

## Running the API

```
python -m nextgen_system.dashboard.api
```

Use an ASGI server such as Uvicorn for production deployment.
