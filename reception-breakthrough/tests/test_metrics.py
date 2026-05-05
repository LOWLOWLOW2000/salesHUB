"""T-403: metrics.py のユニットテスト."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from infra.db.local_db import get_connection
from pipeline.metrics import MetricRow, run_metrics


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

_TODAY = datetime.now(timezone.utc).date().isoformat()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _insert_outcome(conn, session_id: str, outcome_id: str) -> None:
    conn.execute(
        """
        INSERT INTO call_sessions (id, lead_id, mode, started_at)
        VALUES (?, 'lead-x', 'AI', ?)
        """,
        (session_id, _now()),
    )
    conn.execute(
        """
        INSERT INTO outcomes (id, session_id, outcome_id, final_state_id)
        VALUES (?, ?, ?, 'S11')
        """,
        (str(uuid.uuid4()), session_id, outcome_id),
    )
    conn.commit()


def _insert_intent_label(
    conn,
    session_id: str,
    intent_id: str,
    correct_intent: str | None = None,
) -> None:
    tid = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO transcripts (id, session_id, speaker, text)
        VALUES (?, ?, 'reception', 'テスト')
        """,
        (tid, session_id),
    )
    conn.execute(
        """
        INSERT INTO intent_labels
          (id, transcript_id, predicted_intent, confidence,
           correct_intent, created_at, updated_at)
        VALUES (?, ?, ?, 0.8, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            tid,
            intent_id,
            correct_intent,
            _now(),
            _now(),
        ),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# テスト
# ---------------------------------------------------------------------------


def test_session_metrics_are_computed(tmp_path: Path) -> None:
    """セッションメトリクス (total_sessions / connected_rate 等) が計算される。"""
    db = tmp_path / "test.db"
    export = tmp_path / "exports"

    with get_connection(db) as conn:
        _insert_outcome(conn, "s1", "OUT_CONNECTED")
        _insert_outcome(conn, "s2", "OUT_CONNECTED")
        _insert_outcome(conn, "s3", "OUT_REJECTED")
        _insert_outcome(conn, "s4", "OUT_NOISE")

    rows = run_metrics(db_path=db, export_dir=export)

    names = {r.metric_name: r.metric_value for r in rows if r.scope_type == "session"}

    assert names["total_sessions"] == 4.0
    assert abs(names["connected_rate"] - 0.5) < 1e-4
    assert abs(names["rejected_rate"] - 0.25) < 1e-4
    assert abs(names["noise_rate"] - 0.25) < 1e-4


def test_intent_count_metrics(tmp_path: Path) -> None:
    """インテント件数メトリクスが生成される。"""
    db = tmp_path / "test.db"
    export = tmp_path / "exports"

    with get_connection(db) as conn:
        _insert_outcome(conn, "s1", "OUT_CONNECTED")
        _insert_intent_label(conn, "s1", "A1_listening")
        _insert_intent_label(conn, "s1", "A1_listening")
        _insert_intent_label(conn, "s1", "C1_hard_reject")

    rows = run_metrics(db_path=db, export_dir=export)

    intent_rows = {
        (r.scope_key, r.metric_name): r.metric_value
        for r in rows
        if r.scope_type == "intent"
    }

    assert intent_rows.get(("A1_listening", "count")) == 2.0
    assert intent_rows.get(("C1_hard_reject", "count")) == 1.0


def test_correct_rate_computed_only_when_reviewed(tmp_path: Path) -> None:
    """correct_intent が設定された行だけで correct_rate を計算する。"""
    db = tmp_path / "test.db"
    export = tmp_path / "exports"

    with get_connection(db) as conn:
        _insert_outcome(conn, "s1", "OUT_CONNECTED")
        _insert_intent_label(conn, "s1", "A1_listening", correct_intent="A1_listening")
        _insert_intent_label(conn, "s1", "A1_listening", correct_intent="B1_simple_purpose")

    rows = run_metrics(db_path=db, export_dir=export)

    intent_rows = {
        (r.scope_key, r.metric_name): r.metric_value
        for r in rows
        if r.scope_type == "intent"
    }

    # 2 件中 1 件正解 → 0.5
    assert abs(intent_rows.get(("A1_listening", "correct_rate"), -1) - 0.5) < 1e-4


def test_idempotency_insert_or_replace(tmp_path: Path) -> None:
    """同じ日を 2 回実行しても metric_snapshots の行数が増えない。"""
    db = tmp_path / "test.db"
    export = tmp_path / "exports"

    with get_connection(db) as conn:
        _insert_outcome(conn, "s1", "OUT_CONNECTED")

    rows1 = run_metrics(db_path=db, export_dir=export)
    rows2 = run_metrics(db_path=db, export_dir=export)

    with get_connection(db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM metric_snapshots").fetchone()[0]

    assert count == len(rows1)  # 重複しない


def test_csv_is_exported(tmp_path: Path) -> None:
    """CSV ファイルが出力される。"""
    db = tmp_path / "test.db"
    export = tmp_path / "exports"

    with get_connection(db) as conn:
        _insert_outcome(conn, "s1", "OUT_NOISE")

    run_metrics(db_path=db, export_dir=export)

    csv_files = list(export.glob("metrics_*.csv"))
    assert len(csv_files) == 1

    content = csv_files[0].read_text(encoding="utf-8")
    assert "metric_date" in content
    assert "total_sessions" in content


def test_no_data_returns_total_sessions_zero(tmp_path: Path) -> None:
    """データがない日は total_sessions=0 の行のみ返る。"""
    db = tmp_path / "test.db"
    export = tmp_path / "exports"

    rows = run_metrics(db_path=db, export_dir=export)

    session_rows = [r for r in rows if r.scope_type == "session"]
    total = next((r for r in session_rows if r.metric_name == "total_sessions"), None)
    assert total is not None
    assert total.metric_value == 0.0


def test_review_metrics_are_computed(tmp_path: Path) -> None:
    """レビュー件数・訂正率・fallback 比率が算出される。"""
    db = tmp_path / "test.db"
    export = tmp_path / "exports"

    with get_connection(db) as conn:
        _insert_outcome(conn, "s1", "OUT_CONNECTED")
        _insert_intent_label(conn, "s1", "A1_listening", correct_intent="A1_listening")
        _insert_intent_label(conn, "s1", "A1_listening", correct_intent="B1_simple_purpose")
        _insert_intent_label(conn, "s1", "F1_unclear", correct_intent=None)

    rows = run_metrics(db_path=db, export_dir=export)
    session_rows = {
        r.metric_name: r.metric_value for r in rows if r.scope_type == "session"
    }

    # reviewed = 2（correct_intent が埋まっている 2 件）
    assert session_rows.get("labels_reviewed") == 2.0
    # corrected = 1 / reviewed 2 = 0.5
    assert abs(session_rows.get("labels_corrected_ratio", -1) - 0.5) < 1e-4
    # fallback predicted(F1_unclear)=1 / total_labels 3 = 0.3333...
    assert abs(session_rows.get("fallback_used_ratio", -1) - 0.3333) < 1e-4


def test_review_metrics_default_to_zero_without_labels(tmp_path: Path) -> None:
    """ラベルが無い日は review 系 3 指標が 0 で返る。"""
    db = tmp_path / "test.db"
    export = tmp_path / "exports"

    rows = run_metrics(db_path=db, export_dir=export)
    session_rows = {
        r.metric_name: r.metric_value for r in rows if r.scope_type == "session"
    }
    assert session_rows.get("labels_reviewed") == 0.0
    assert session_rows.get("labels_corrected_ratio") == 0.0
    assert session_rows.get("fallback_used_ratio") == 0.0
