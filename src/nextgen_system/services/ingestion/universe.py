"""Ticker universe curation service skeleton."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable, Optional

from nextgen_system.persistence.database import get_database, Database
from .repositories import UniverseRepository, UniverseRow
from .universe_builder import build_universe


@dataclass
class UniverseUpdateResult:
    tickers: Iterable[str]
    rows_written: int


class UniverseCuratorService:
    """Builds/updates the dynamic ticker universe based on rules and data availability."""

    def __init__(self, db: Optional[Database] = None, repository: Optional[UniverseRepository] = None):
        self.db = db or get_database()
        self.repository = repository or UniverseRepository(self.db)

    def refresh(self, *, force: bool = False, target_size: Optional[int] = None) -> UniverseUpdateResult:
        metrics = build_universe(force_refresh=force, target_size=target_size)
        rows = [
            UniverseRow(
                ticker=m.symbol,
                source="dynamic",
                market=None,
                min_date=None,
                metadata=json.dumps({
                    "last_close": m.last_close,
                    "avg_volume": m.avg_volume,
                    "dollar_volume": m.dollar_volume,
                }),
            )
            for m in metrics
        ]
        count = self.repository.upsert_rows(rows)
        return UniverseUpdateResult(tickers=[m.symbol for m in metrics], rows_written=count)


__all__ = ["UniverseCuratorService", "UniverseUpdateResult"]
