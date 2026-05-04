"""T-402: failure_analysis.py のユニットテスト."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from infra.db.local_db import get_connection
from pipeline.failure_analysis import FailureCase, run_failure_analysis


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _insert_session(conn, session_id: str, outcome_id: str) -> str:
    conn.execute(
        """
        INSERT INTO call_sessions (id, lead_id, mode, started_at, ended_at,
                                   final_state_id, outcome_id)
        VALUES (?, 'lead-001', 'AI', ?, ?, 'S11', ?)
        """,
        (session_id, _now(), _now(), outcome_id),
    )
    conn.commit()
    return session_id


def _insert_outcome(conn, session_id: str, outcome_id: str) -> None:
    conn.execute(
        """
        INSERT INTO outcomes
          (id, session_id, outcome_id, final_state_id)
        VALUES (?, ?, ?, 'S11')
        """,
        (str(uuid.uuid4()), session_id, outcome_id),
    )
    conn.commit()


def _insert_transition(
    conn,
    session_id: str,
    seq: int,
    from_state: str,
    input_id: str,
    input_kind: str = "intent",
) -> None:
    conn.execute(
        """
        INSERT INTO state_transitions
          (id, session_id, seq, from_state, to_state, input_kind, input_id, at, mode)
        VALUES (?, ?, ?, ?, 'S11', ?, ?, ?, 'AI')
        """,
        (str(uuid.uuid4()), session_id, seq, from_state, input_kind, input_id, _now()),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# テスト
# ---------------------------------------------------------------------------


def test_rejected_session_is_extracted(tmp_path: Path) -> None:
    """OUT_REJECTED セッションが failure_cases に追加される。"""
    db = tmp_path / "test.db"
    export = tmp_path / "exports"

    with get_connection(db) as conn:
        sid = "sess-rej-001"
        _insert_session(conn, sid, "OUT_REJECTED")
        _insert_outcome(conn, sid, "OUT_REJECTED")
        _insert_transition(conn, sid, 0, "S3", "C1_hard_reject")

    cases = run_failure_analysis(db_path=db, export_dir=export)

    assert len(cases) == 1
    c = cases[0]
    assert isinstance(c, FailureCase)
    assert c.outcome_id == "OUT_REJECTED"
    assert c.session_id == sid


def test_connected_session_is_not_extracted(tmp_path: Path) -> None:
    """OUT_CONNECTED は失敗ではないので抽出されない。"""
    db = tmp_path / "test.db"
    export = tmp_path / "exports"

    with get_connection(db) as conn:
        sid = "sess-ok-001"
        _insert_session(conn, sid, "OUT_CONNECTED")
        _insert_outcome(conn, sid, "OUT_CONNECTED")

    cases = run_failure_analysis(db_path=db, export_dir=export)
    assert cases == []


def test_idempotency_skips_existing_failure_cases(tmp_path: Path) -> None:
    """同一 session_id を 2 回実行しても重複しない。"""
    db = tmp_path / "test.db"
    export = tmp_path / "exports"

    with get_connection(db) as conn:
        sid = "sess-rej-002"
        _insert_session(conn, sid, "OUT_REJECTED")
        _insert_outcome(conn, sid, "OUT_REJECTED")

    cases1 = run_failure_analysis(db_path=db, export_dir=export)
    cases2 = run_failure_analysis(db_path=db, export_dir=export)

    assert len(cases1) == 1
    assert cases2 == []  # 2 回目はスキップ

    with get_connection(db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM failure_cases").fetchone()[0]
    assert count == 1


def test_csv_is_exported(tmp_path: Path) -> None:
    """CSV ファイルが出力される。"""
    db = tmp_path / "test.db"
    export = tmp_path / "exports"

    with get_connection(db) as conn:
        sid = "sess-noise-001"
        _insert_session(conn, sid, "OUT_NOISE")
        _insert_outcome(conn, sid, "OUT_NOISE")

    run_failure_analysis(db_path=db, export_dir=export)

    csv_files = list(export.glob("failure_cases_*.csv"))
    assert len(csv_files) == 1

    content = csv_files[0].read_text(encoding="utf-8")
    assert "session_id" in content
    assert sid in content


def test_failure_cases_persist_last_transition_info(tmp_path: Path) -> None:
    """最後の state_transition の from_state が failure_state_id に入る。"""
    db = tmp_path / "test.db"
    export = tmp_path / "exports"

    with get_connection(db) as conn:
        sid = "sess-rej-003"
        _insert_session(conn, sid, "OUT_REJECTED")
        _insert_outcome(conn, sid, "OUT_REJECTED")
        _insert_transition(conn, sid, 0, "S2", "A1_listening")
        _insert_transition(conn, sid, 1, "S4", "C2_soft_reject")  # 最後

    cases = run_failure_analysis(db_path=db, export_dir=export)

    assert cases[0].failure_state_id == "S4"
    assert cases[0].last_input_id == "C2_soft_reject"
