"""SQLite connection layer for the local module database.

Each call to :func:`get_connection` returns a context-managed
:class:`sqlite3.Connection`.  The first call against a new database file
applies the migration SQL so callers don't have to think about schema
initialisation.

Usage::

    from infra.db.local_db import get_connection

    with get_connection() as conn:
        conn.execute("INSERT INTO call_sessions ...")

Thread safety: SQLite ``check_same_thread=False`` is enabled so that the
connection can be shared across threads as long as callers use the context
manager (which ensures the connection is not used concurrently by accident).
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

_MIGRATIONS_SQL = (
    Path(__file__).resolve().parent / "migrations.sql"
).read_text(encoding="utf-8")

_SCHEMA_MARKER_TABLE = "call_sessions"


def _is_migration_applied(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (_SCHEMA_MARKER_TABLE,),
    ).fetchone()
    return row is not None


def _apply_migration(conn: sqlite3.Connection) -> None:
    conn.executescript(_MIGRATIONS_SQL)


def _configure(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.row_factory = sqlite3.Row


def open_persistent_connection(
    db_path: str | Path = "data/calls.db",
) -> sqlite3.Connection:
    """Migration 適用済みの永続接続を返す（呼び出し側が `conn.close()` を担当する）。

    API サーバーやワーカーのように、接続を 1 リクエストを超えて保持したい場合に使う。
    通常のコードでは :func:`get_connection` のコンテキストマネージャーを使うこと。

    Args:
        db_path: SQLite DB のパス。

    Returns:
        設定済みの :class:`sqlite3.Connection`。

    Raises:
        sqlite3.OperationalError: DB ファイルを開けない場合。
    """
    path = Path(db_path) if db_path != ":memory:" else db_path
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path, check_same_thread=False)
    _configure(conn)
    if not _is_migration_applied(conn):
        _apply_migration(conn)
        conn.commit()
    return conn


@contextmanager
def get_connection(
    db_path: str | Path = "data/calls.db",
) -> Generator[sqlite3.Connection, None, None]:
    """Yield a configured, migration-applied SQLite connection.

    The migration is applied idempotently (``CREATE TABLE IF NOT EXISTS``),
    so re-running against an existing database is safe.

    Args:
        db_path: Path to the SQLite database file.  Use ``":memory:"`` in
            tests for a throw-away in-memory database.

    Yields:
        A :class:`sqlite3.Connection` with foreign keys and WAL mode enabled.

    Raises:
        sqlite3.OperationalError: If the database file cannot be opened.
    """
    path = Path(db_path) if db_path != ":memory:" else db_path
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path, check_same_thread=False)
    try:
        _configure(conn)
        if not _is_migration_applied(conn):
            _apply_migration(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
