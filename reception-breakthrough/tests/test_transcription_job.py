"""T-400: transcription_job.py のユニットテスト."""

from __future__ import annotations

import struct
import wave
from pathlib import Path

import pytest

from infra.db.local_db import get_connection
from pipeline.transcription_job import TranscriptionJobResult, run_transcription_job


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _make_session(conn, session_id: str = "sess-001") -> str:
    from datetime import datetime, timezone

    conn.execute(
        "INSERT INTO call_sessions (id, lead_id, mode, started_at) VALUES (?, ?, ?, ?)",
        (session_id, "lead-001", "AI", datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return session_id


def _make_recording(
    conn, recording_id: str, session_id: str, audio_path: str
) -> None:
    conn.execute(
        """
        INSERT INTO call_recordings (id, session_id, audio_path, source_kind)
        VALUES (?, ?, ?, 'file')
        """,
        (recording_id, session_id, audio_path),
    )
    conn.commit()


def _write_wav(path: Path, duration_frames: int = 100) -> None:
    """最低限有効な 16kHz モノラル WAV ファイルを作成する。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        f.writeframes(struct.pack(f"<{duration_frames}h", *([0] * duration_frames)))


# ---------------------------------------------------------------------------
# テスト: 冪等性
# ---------------------------------------------------------------------------


def test_already_transcribed_recording_is_skipped(tmp_path: Path) -> None:
    """transcripts が既にある recording_id は処理されない。"""
    db = tmp_path / "test.db"
    wav = tmp_path / "call.wav"
    _write_wav(wav)

    with get_connection(db) as conn:
        session_id = _make_session(conn)
        _make_recording(conn, "rec-001", session_id, str(wav))
        # 事前に transcript を手動挿入（冪等テスト）
        from datetime import datetime, timezone
        import uuid

        conn.execute(
            """
            INSERT INTO transcripts (id, session_id, recording_id, speaker, text)
            VALUES (?, ?, ?, 'reception', 'ダミー')
            """,
            (str(uuid.uuid4()), session_id, "rec-001"),
        )
        conn.commit()

    results = run_transcription_job(db_path=db)
    assert results == []  # 未処理が 0 件なので何も返さない


def test_pending_recording_is_processed(tmp_path: Path) -> None:
    """未処理録音が whisper stub で処理され transcripts に 1 件入る。"""
    db = tmp_path / "test.db"
    wav = tmp_path / "call.wav"
    _write_wav(wav)

    with get_connection(db) as conn:
        session_id = _make_session(conn)
        _make_recording(conn, "rec-002", session_id, str(wav))

    results = run_transcription_job(db_path=db)

    assert len(results) == 1
    r = results[0]
    assert isinstance(r, TranscriptionJobResult)
    assert r.recording_id == "rec-002"
    assert r.skipped is False
    assert r.segments_count >= 1  # stub で最低 1 件


def test_missing_audio_file_is_skipped(tmp_path: Path) -> None:
    """録音ファイルが存在しない場合は skipped=True で結果を返す。"""
    db = tmp_path / "test.db"

    with get_connection(db) as conn:
        session_id = _make_session(conn)
        _make_recording(conn, "rec-003", session_id, "/nonexistent/path/call.wav")

    results = run_transcription_job(db_path=db)

    assert len(results) == 1
    assert results[0].skipped is True
    assert results[0].segments_count == 0


def test_max_records_limits_batch(tmp_path: Path) -> None:
    """max_records が機能していることを確認する。"""
    db = tmp_path / "test.db"

    with get_connection(db) as conn:
        session_id = _make_session(conn)
        for i in range(5):
            wav = tmp_path / f"call_{i}.wav"
            _write_wav(wav)
            _make_recording(conn, f"rec-{i:03d}", session_id, str(wav))

    results = run_transcription_job(db_path=db, max_records=2)
    assert len(results) == 2
