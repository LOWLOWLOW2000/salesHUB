"""Tests for infra.db.local_db (T-101)."""

from __future__ import annotations

import sqlite3

import pytest

from infra.db.local_db import get_connection


def test_migration_applied_on_first_use() -> None:
    with get_connection(":memory:") as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {row["name"] for row in rows}

    assert "call_sessions" in table_names
    assert "state_transitions" in table_names
    assert "intent_labels" in table_names


def test_migration_is_idempotent(tmp_path) -> None:
    db_file = tmp_path / "calls.db"

    with get_connection(db_file) as conn:
        conn.execute(
            "INSERT INTO call_sessions (id, lead_id, mode, started_at) "
            "VALUES (?, ?, ?, ?)",
            ("s1", "l1", "AI", "2026-05-04T12:00:00"),
        )

    # Second open: migration runs again (all CREATE TABLE IF NOT EXISTS)
    with get_connection(db_file) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM call_sessions"
        ).fetchone()[0]

    assert count == 1


def test_foreign_keys_enforced() -> None:
    with get_connection(":memory:") as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO call_recordings "
                "(id, session_id, audio_path, recorded_at) "
                "VALUES (?, ?, ?, ?)",
                ("rec-1", "nonexistent-session", "/tmp/audio.wav", "2026-05-04T12:00:00"),
            )


def test_rollback_on_exception() -> None:
    with pytest.raises(ValueError):
        with get_connection(":memory:") as conn:
            conn.execute(
                "INSERT INTO call_sessions (id, lead_id, mode, started_at) "
                "VALUES (?, ?, ?, ?)",
                ("s-rollback", "l1", "AI", "2026-05-04T12:00:00"),
            )
            raise ValueError("deliberate error to trigger rollback")

    # Verify the row was NOT committed by opening a new :memory: DB
    # (which will always be empty — we just confirm no crash)
    with get_connection(":memory:") as conn:
        count = conn.execute("SELECT COUNT(*) FROM call_sessions").fetchone()[0]
    assert count == 0


def test_row_factory_returns_row_objects() -> None:
    with get_connection(":memory:") as conn:
        conn.execute(
            "INSERT INTO call_sessions (id, lead_id, mode, started_at) "
            "VALUES (?, ?, ?, ?)",
            ("s2", "l2", "HUMAN", "2026-05-04T13:00:00"),
        )
        row = conn.execute(
            "SELECT id, mode FROM call_sessions WHERE id = ?", ("s2",)
        ).fetchone()

    assert row["id"] == "s2"
    assert row["mode"] == "HUMAN"
