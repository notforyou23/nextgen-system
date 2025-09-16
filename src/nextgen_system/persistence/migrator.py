"""Simple migration runner for the next-generation system."""

from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path
from typing import Callable, Iterable, List, Tuple

from nextgen_system.config import settings
from .database import get_database

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def _ensure_registry(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id TEXT PRIMARY KEY,
            description TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )


def _list_migration_files() -> List[Path]:
    paths = sorted(MIGRATIONS_DIR.glob("*.sql"))
    paths += sorted(MIGRATIONS_DIR.glob("*.py"))
    return paths


def _migration_id(path: Path) -> str:
    return path.stem


def _load_sql(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_py(path: Path) -> Callable[[sqlite3.Connection], None]:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)  # type: ignore[arg-type]
    if not hasattr(module, "upgrade"):
        raise RuntimeError(f"Migration {path} must define an upgrade(conn) function")
    return getattr(module, "upgrade")


def applied_migrations(conn: sqlite3.Connection) -> Iterable[str]:
    _ensure_registry(conn)
    rows = conn.execute("SELECT id FROM schema_migrations ORDER BY applied_at").fetchall()
    return [row[0] for row in rows]


def upgrade() -> None:
    db = get_database()
    conn = db.connection()
    _ensure_registry(conn)
    applied = set(applied_migrations(conn))

    for path in _list_migration_files():
        mig_id = _migration_id(path)
        if mig_id in applied:
            continue
        if path.suffix == ".sql":
            sql = _load_sql(path)
            conn.executescript(sql)
        elif path.suffix == ".py":
            upgrade_fn = _load_py(path)
            upgrade_fn(conn)
        else:
            continue
        conn.execute(
            "INSERT INTO schema_migrations (id, description) VALUES (?, ?)",
            (mig_id, path.name),
        )
        conn.commit()


if __name__ == "__main__":
    upgrade()
