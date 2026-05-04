from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


MIGRATIONS_PATH = (
    Path(__file__).resolve().parents[1] / "infra" / "db" / "migrations.sql"
)


@pytest.fixture
def conn() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.executescript(MIGRATIONS_PATH.read_text())
    try:
        yield connection
    finally:
        connection.close()


def test_migrations_create_expected_tables(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    table_names = {row[0] for row in rows}

    assert {
        "call_sessions",
        "call_recordings",
        "transcripts",
        "intent_labels",
        "state_transitions",
        "outcomes",
        "failure_cases",
        "template_variants",
        "metric_snapshots",
    }.issubset(table_names)


def test_call_sessions_rejects_invalid_state_id(conn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO call_sessions (
                id, lead_id, mode, started_at, final_state_id, outcome_id
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "session-invalid-state",
                "lead-1",
                "AI",
                "2026-05-04T12:00:00",
                "S99",
                "OUT_NOISE",
            ),
        )


def test_call_sessions_rejects_invalid_outcome_id(conn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO call_sessions (
                id, lead_id, mode, started_at, final_state_id, outcome_id
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "session-invalid-outcome",
                "lead-1",
                "HUMAN",
                "2026-05-04T12:00:00",
                "S11",
                "OUT_UNKNOWN",
            ),
        )


def test_intent_labels_accepts_arbitrary_text_intent(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT INTO call_sessions (id, lead_id, mode, started_at)
        VALUES (?, ?, ?, ?)
        """,
        ("session-1", "lead-1", "AI", "2026-05-04T12:00:00"),
    )
    conn.execute(
        """
        INSERT INTO transcripts (
            id, session_id, speaker, text, start_time_ms, end_time_ms
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("tr-1", "session-1", "RECEPTION", "custom utterance", 0, 1000),
    )
    conn.execute(
        """
        INSERT INTO intent_labels (
            id, transcript_id, predicted_intent, confidence
        ) VALUES (?, ?, ?, ?)
        """,
        ("il-1", "tr-1", "X9_custom_future_intent", 0.55),
    )

    predicted = conn.execute(
        "SELECT predicted_intent FROM intent_labels WHERE id = ?",
        ("il-1",),
    ).fetchone()

    assert predicted == ("X9_custom_future_intent",)


def test_state_transitions_rejects_invalid_from_state(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT INTO call_sessions (id, lead_id, mode, started_at)
        VALUES (?, ?, ?, ?)
        """,
        ("session-2", "lead-2", "HUMAN", "2026-05-04T12:10:00"),
    )

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO state_transitions (
                id, session_id, seq, from_state, to_state, input_kind, input_id, at, mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "st-1",
                "session-2",
                0,
                "S999",
                "S1",
                "event",
                "EV_DIALED",
                "2026-05-04T12:10:01",
                "HUMAN",
            ),
        )
