"""Repository for dynamic configuration overrides."""

from __future__ import annotations

from typing import Optional

from nextgen_system.persistence.database import get_database, Database


class ConfigOverrideRepository:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_database()

    def set(self, key: str, value: str) -> None:
        self.db.execute(
            "INSERT INTO config_overrides (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP",
            (key, value),
        )

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        row = self.db.fetch_one("SELECT value FROM config_overrides WHERE key = ?", (key,))
        return row[0] if row and row[0] is not None else default


__all__ = ["ConfigOverrideRepository"]
