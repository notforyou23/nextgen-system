"""Feature repositories for next-gen system."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from nextgen_system.config import settings
from nextgen_system.persistence.database import get_database, Database


class FeatureRepository:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_database()

    def _feature_id(self, ticker: str, as_of: datetime, version: str) -> str:
        key = f"{ticker}|{as_of.isoformat()}|{version}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def store_window(
        self,
        *,
        ticker: str,
        as_of: datetime,
        version: str,
        tensor: np.ndarray,
        context: Dict[str, Any],
    ) -> str:
        feature_id = self._feature_id(ticker, as_of, version)
        data_path = self._write_tensor(feature_id, tensor)
        self.db.execute(
            """
            INSERT OR REPLACE INTO feature_windows
                (id, ticker, as_of, sequence_length, feature_count, feature_version, data_path, context, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                feature_id,
                ticker,
                as_of.date(),
                tensor.shape[0],
                tensor.shape[1] if tensor.ndim > 1 else 1,
                version,
                data_path,
                json.dumps(context),
            ),
        )
        return feature_id

    def _write_tensor(self, feature_id: str, tensor: np.ndarray) -> str:
        base = Path(settings.get("paths", "data_dir")) / "features"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"{feature_id}.npy"
        np.save(path, tensor)
        return str(path)

    def list_windows(self, ticker: str, limit: Optional[int] = None, descending: bool = False) -> List[Dict[str, Any]]:
        query = """
            SELECT id, as_of, feature_version, data_path, context
            FROM feature_windows
            WHERE ticker = ?
            ORDER BY as_of {order}
        """
        order = "DESC" if descending else "ASC"
        query = query.format(order=order)
        if limit:
            query += " LIMIT ?"
            rows = self.db.fetch_all(query, (ticker, limit))
        else:
            rows = self.db.fetch_all(query, (ticker,))
        results = []
        for row in rows:
            results.append(
                {
                    "id": row[0],
                    "as_of": datetime.fromisoformat(str(row[1])),
                    "feature_version": row[2],
                    "data_path": row[3],
                    "context": json.loads(row[4]) if row[4] else {},
                }
            )
        return results

    def load_tensor(self, data_path: str) -> np.ndarray:
        return np.load(data_path)

    def latest_window(self, ticker: str) -> Optional[Dict[str, Any]]:
        windows = self.list_windows(ticker, limit=1, descending=True)
        return windows[0] if windows else None


__all__ = ["FeatureRepository"]
