"""Database connection management for the next-generation system."""

from __future__ import annotations

import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

from nextgen_system.config import settings

_DEFAULT_TIMEOUT = 60.0
_HEALTH_INTERVAL = 30.0


class DatabaseError(RuntimeError):
    pass


class Database:
    """Singleton-ish SQLite connection manager with health checks."""

    _instance: Optional["Database"] = None
    _instance_lock = threading.RLock()

    def __new__(cls, db_path: Optional[Path] = None):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init(db_path)
            return cls._instance

    def _init(self, db_path: Optional[Path]):
        self._db_path = Path(db_path or settings.get("paths", "db_path"))
        self._connection_lock = threading.RLock()
        self._connection: Optional[sqlite3.Connection] = None
        self._last_health_check = 0.0
        self._open_connection()

    def _open_connection(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(
            str(self._db_path),
            timeout=_DEFAULT_TIMEOUT,
            detect_types=sqlite3.PARSE_DECLTYPES,
            check_same_thread=False,
            isolation_level=None,
        )
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA cache_size=10000;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute(f"PRAGMA busy_timeout={int(_DEFAULT_TIMEOUT * 1000)};")
        conn.execute("PRAGMA optimize;")
        self._connection = conn
        self._last_health_check = time.time()

    def _ensure_connection(self) -> sqlite3.Connection:
        with self._connection_lock:
            if self._connection is None:
                self._open_connection()
            elif time.time() - self._last_health_check > _HEALTH_INTERVAL:
                try:
                    self._connection.execute("SELECT 1;")
                    self._last_health_check = time.time()
                except sqlite3.Error:
                    self._open_connection()
            return self._connection

    def connection(self) -> sqlite3.Connection:
        """Expose raw connection for migration tooling."""
        return self._ensure_connection()

    @contextmanager
    def cursor(self):
        conn = self._ensure_connection()
        cur = conn.cursor()
        try:
            yield cur
        except sqlite3.Error as exc:
            raise DatabaseError(str(exc)) from exc
        finally:
            cur.close()

    def execute(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Cursor:
        conn = self._ensure_connection()
        try:
            return conn.execute(sql, params)
        except sqlite3.Error as exc:
            raise DatabaseError(str(exc)) from exc

    def executemany(self, sql: str, params_seq: Iterable[Sequence[Any]]):
        conn = self._ensure_connection()
        try:
            return conn.executemany(sql, params_seq)
        except sqlite3.Error as exc:
            raise DatabaseError(str(exc)) from exc

    def fetch_all(self, sql: str, params: Sequence[Any] = ()):
        with self.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def fetch_one(self, sql: str, params: Sequence[Any] = ()):
        with self.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()


def get_database() -> Database:
    return Database()


__all__ = ["Database", "DatabaseError", "get_database"]
