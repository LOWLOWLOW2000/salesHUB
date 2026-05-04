"""T-601: 統合シナリオテスト — 録音ファイル投入から outcome 確定まで.

3 シナリオを通し、全パイプライン（DB → CallController → Pipeline → Metrics）
が end-to-end で動くことを確認する。

用語
----
「統合テスト」: 複数モジュールを本物の SQLite（インメモリ or tmpfile）で
              動かし、テスト境界が 1 モジュール内に収まらないテスト。
"""

from __future__ import annotations

import struct
import uuid
import wave
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from core.call_controller import CallController
from infra.db.local_db import get_connection
from pipeline.failure_analysis import run_failure_analysis
from pipeline.intent_labeling import run_intent_labeling
from pipeline.metrics import run_metrics
from pipeline.transcription_job import run_transcription_job


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _write_wav(path: Path, frames: int = 100) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        f.writeframes(struct.pack(f"<{frames}h", *([0] * frames)))


def _run_scenario(db: Path, inputs: list[str], lead_id: str = "L001") -> str:
    """CallController でシナリオを流してセッション ID を返す。"""
    with get_connection(db) as conn:
        ctrl = CallController(lead_id=lead_id, conn=conn)
        ctrl.step("EV_DIALED")
        for inp in inputs:
            if ctrl.is_terminated:
                break
            ctrl.step(inp)
        return ctrl.session_id


# ---------------------------------------------------------------------------
# シナリオ 1: 接続成功（OUT_CONNECTED）
# ---------------------------------------------------------------------------


def test_scenario_connected_end_to_end(tmp_path: Path) -> None:
    """S0→S1→S2→…→S7→S8→S11 (OUT_CONNECTED) のフルパイプライン。"""
    db = tmp_path / "calls.db"
    export = tmp_path / "exports"

    session_id = _run_scenario(
        db,
        [
            "EV_PICKED_UP",      # S1→S2 (reception_contact)
            "A1_listening",      # S2→S3 (purpose_inquiry)
            "D1_hold",           # S3→S7 (on_hold / waiting)
            "EV_TRANSFER_DONE",  # S7→S8 (dm_engaged, OUT_CONNECTED)
            "EV_HANGUP",         # S8→S11 (OUT_CONNECTED)
        ],
    )

    # outcome が DB に保存されている
    with get_connection(db) as conn:
        row = conn.execute(
            "SELECT outcome_id FROM outcomes WHERE session_id = ?", (session_id,)
        ).fetchone()
    assert row is not None
    assert row[0] == "OUT_CONNECTED"

    # メトリクスが生成される（UTC 基準日で集計）
    today_utc = datetime.now(timezone.utc).date()
    metrics = run_metrics(db_path=db, export_dir=export, target_date=today_utc)
    session_metrics = {r.metric_name: r.metric_value for r in metrics if r.scope_type == "session"}
    assert session_metrics["total_sessions"] >= 1.0
    assert session_metrics["connected_rate"] >= 1.0 / session_metrics["total_sessions"]


# ---------------------------------------------------------------------------
# シナリオ 2: 拒否（OUT_REJECTED）→ failure_analysis
# ---------------------------------------------------------------------------


def test_scenario_rejected_triggers_failure_analysis(tmp_path: Path) -> None:
    """OUT_REJECTED セッションが failure_cases に抽出される。"""
    db = tmp_path / "calls.db"
    export = tmp_path / "exports"

    session_id = _run_scenario(
        db,
        [
            "EV_PICKED_UP",          # S1→S2
            "A1_listening",          # S2→S3
            "C1_hard_reject",        # S3→S4
            "EV_HUMAN_RESPONDED",    # S4→S5 (rebuttal)
            "C1_hard_reject",        # S5→S11 (OUT_REJECTED)
        ],
    )

    with get_connection(db) as conn:
        outcome = conn.execute(
            "SELECT outcome_id FROM outcomes WHERE session_id = ?", (session_id,)
        ).fetchone()
    assert outcome[0] == "OUT_REJECTED"

    cases = run_failure_analysis(db_path=db, export_dir=export)
    assert any(c.session_id == session_id for c in cases)

    csv_files = list(export.glob("failure_cases_*.csv"))
    assert len(csv_files) == 1


# ---------------------------------------------------------------------------
# シナリオ 3: 不在（OUT_ABSENT）→ 録音投入 → 文字起こし → ラベリング
# ---------------------------------------------------------------------------


def test_scenario_absent_voice_pipeline(tmp_path: Path) -> None:
    """S9（absent_confirmed）→ OUT_ABSENT の後、録音投入〜ラベリングまで通す。"""
    db = tmp_path / "calls.db"
    export = tmp_path / "exports"
    wav = tmp_path / "recordings" / "call.wav"
    _write_wav(wav)

    session_id = _run_scenario(
        db,
        [
            "EV_PICKED_UP",          # S1→S2
            "E1_absent",             # S2→S9 (absent_confirmed)
            "EV_HUMAN_RESPONDED",    # S9→S11 (OUT_ABSENT)
        ],
    )

    with get_connection(db) as conn:
        outcome = conn.execute(
            "SELECT outcome_id FROM outcomes WHERE session_id = ?", (session_id,)
        ).fetchone()
    assert outcome[0] == "OUT_ABSENT"

    # 録音を DB に登録
    with get_connection(db) as conn:
        conn.execute(
            """
            INSERT INTO call_recordings
              (id, session_id, audio_path, source_kind)
            VALUES (?, ?, ?, 'file')
            """,
            (str(uuid.uuid4()), session_id, str(wav)),
        )

    # T-400: 文字起こしジョブ
    t400_results = run_transcription_job(db_path=db)
    assert len(t400_results) == 1
    assert t400_results[0].segments_count >= 1

    # T-401: インテントラベリング
    t401_results = run_intent_labeling(db_path=db)
    # whisper stub が "[transcription unavailable]" を返すのでラベリングは 1 件
    assert len(t401_results) >= 1

    # DB に intent_labels が書き込まれている
    with get_connection(db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM intent_labels").fetchone()[0]
    assert count >= 1


# ---------------------------------------------------------------------------
# パイプライン冪等性
# ---------------------------------------------------------------------------


def test_pipeline_idempotency(tmp_path: Path) -> None:
    """T-400〜T-403 を同じ DB で 2 回実行しても重複しない。"""
    db = tmp_path / "calls.db"
    export = tmp_path / "exports"
    wav = tmp_path / "r.wav"
    _write_wav(wav)

    _run_scenario(
        db,
        [
            "EV_PICKED_UP",
            "A1_listening",
            "C1_hard_reject",
            "EV_HUMAN_RESPONDED",
            "C1_hard_reject",
        ],
    )

    with get_connection(db) as conn:
        sid = conn.execute("SELECT id FROM call_sessions LIMIT 1").fetchone()[0]
        conn.execute(
            "INSERT INTO call_recordings (id, session_id, audio_path, source_kind)"
            " VALUES (?, ?, ?, 'file')",
            (str(uuid.uuid4()), sid, str(wav)),
        )

    # 1 回目
    run_transcription_job(db_path=db)
    run_intent_labeling(db_path=db)
    run_failure_analysis(db_path=db, export_dir=export)
    run_metrics(db_path=db, export_dir=export)

    # 2 回目
    r2_t = run_transcription_job(db_path=db)
    r2_l = run_intent_labeling(db_path=db)
    r2_f = run_failure_analysis(db_path=db, export_dir=export)

    assert r2_t == []   # 既処理済
    assert r2_l == []   # 既ラベル済
    assert r2_f == []   # 既抽出済

    # メトリクス重複なし
    with get_connection(db) as conn:
        count_before = conn.execute("SELECT COUNT(*) FROM metric_snapshots").fetchone()[0]
    run_metrics(db_path=db, export_dir=export)
    with get_connection(db) as conn:
        count_after = conn.execute("SELECT COUNT(*) FROM metric_snapshots").fetchone()[0]
    assert count_before == count_after
