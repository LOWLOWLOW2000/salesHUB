"""T-401: intent_labeling.py のユニットテスト."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from infra.db.local_db import get_connection
from pipeline.intent_labeling import LabelingResult, run_intent_labeling


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _insert_session(conn, session_id: str = "sess-001") -> str:
    conn.execute(
        "INSERT INTO call_sessions (id, lead_id, mode, started_at) VALUES (?, ?, ?, ?)",
        (session_id, "lead-001", "AI", _now()),
    )
    conn.commit()
    return session_id


def _insert_transcript(
    conn,
    session_id: str,
    text: str,
    speaker: str = "reception",
) -> str:
    tid = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO transcripts (id, session_id, speaker, text)
        VALUES (?, ?, ?, ?)
        """,
        (tid, session_id, speaker, text),
    )
    conn.commit()
    return tid


# ---------------------------------------------------------------------------
# テスト
# ---------------------------------------------------------------------------


def test_reception_transcript_gets_labeled(tmp_path: Path) -> None:
    """reception の transcript にインテントラベルが付与される。"""
    db = tmp_path / "test.db"
    with get_connection(db) as conn:
        session_id = _insert_session(conn)
        _insert_transcript(conn, session_id, "はい、田中でございます")

    results = run_intent_labeling(db_path=db)

    assert len(results) == 1
    r = results[0]
    assert isinstance(r, LabelingResult)
    assert r.skipped is False
    assert r.predicted_intent != ""
    assert 0.0 <= r.confidence <= 1.0


def test_ai_speaker_transcript_is_not_labeled(tmp_path: Path) -> None:
    """ai の transcript はラベリング対象外。"""
    db = tmp_path / "test.db"
    with get_connection(db) as conn:
        session_id = _insert_session(conn)
        _insert_transcript(conn, session_id, "田中様をお願いします", speaker="ai")

    results = run_intent_labeling(db_path=db)
    assert results == []


def test_idempotency_skips_already_labeled(tmp_path: Path) -> None:
    """既にラベルがある transcript は再処理されない。"""
    db = tmp_path / "test.db"
    with get_connection(db) as conn:
        session_id = _insert_session(conn)
        tid = _insert_transcript(conn, session_id, "結構です")
        # 事前にラベルを挿入
        conn.execute(
            """
            INSERT INTO intent_labels
              (id, transcript_id, predicted_intent, confidence, created_at, updated_at)
            VALUES (?, ?, 'C1_hard_reject', 0.9, ?, ?)
            """,
            (str(uuid.uuid4()), tid, _now(), _now()),
        )
        conn.commit()

    results = run_intent_labeling(db_path=db)
    assert results == []


def test_label_is_persisted_to_db(tmp_path: Path) -> None:
    """ラベルが intent_labels テーブルに書き込まれる。"""
    db = tmp_path / "test.db"
    with get_connection(db) as conn:
        session_id = _insert_session(conn)
        tid = _insert_transcript(conn, session_id, "担当者が不在です")

    run_intent_labeling(db_path=db)

    with get_connection(db) as conn:
        row = conn.execute(
            "SELECT predicted_intent, confidence FROM intent_labels WHERE transcript_id = ?",
            (tid,),
        ).fetchone()

    assert row is not None
    assert row[0] != ""
    assert 0.0 <= row[1] <= 1.0


def test_max_records_limits_batch(tmp_path: Path) -> None:
    """max_records 制限が機能する。"""
    db = tmp_path / "test.db"
    with get_connection(db) as conn:
        session_id = _insert_session(conn)
        for i in range(5):
            _insert_transcript(conn, session_id, f"テストテキスト{i}")

    results = run_intent_labeling(db_path=db, max_records=2)
    assert len(results) == 2
