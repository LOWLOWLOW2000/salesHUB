"""Tests for voice.recorder (T-300)."""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

import pytest

from infra.db.local_db import get_connection
from voice.recorder import Recorder, RecordingRecord


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_wav(path: Path, sample_rate: int = 16_000, duration_sec: float = 0.1,
              amplitude: int = 0) -> Path:
    n = int(sample_rate * duration_sec)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for i in range(n):
            s = int(amplitude * math.sin(2 * math.pi * 440 * i / sample_rate))
            wf.writeframes(struct.pack("<h", s))
    return path


# ---------------------------------------------------------------------------
# ingest_file — no-DB mode
# ---------------------------------------------------------------------------


def test_ingest_already_normalised_file(tmp_path: Path) -> None:
    src = _make_wav(tmp_path / "src.wav", sample_rate=16_000)
    rec = Recorder(session_id="sess-rec", recordings_dir=tmp_path / "store")
    result = rec.ingest_file(src)

    assert isinstance(result, RecordingRecord)
    assert result.audio_path.exists()
    assert result.audio_hash != ""
    assert result.source_kind == "file"


def test_ingest_non_normalised_file_is_converted(tmp_path: Path) -> None:
    # 8kHz stereo — should be converted to 16kHz mono
    src = _make_wav(tmp_path / "8k.wav", sample_rate=8_000, amplitude=5000)
    # Rewrite as stereo
    import audioop
    with wave.open(str(src), "rb") as wf:
        raw = wf.readframes(wf.getnframes())
    stereo_src = tmp_path / "8k_stereo.wav"
    with wave.open(str(stereo_src), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(8_000)
        stereo_raw = audioop.tostereo(raw, 2, 1.0, 1.0)
        wf.writeframes(stereo_raw)

    rec = Recorder(session_id="sess-norm", recordings_dir=tmp_path / "store")
    result = rec.ingest_file(stereo_src)

    with wave.open(str(result.audio_path), "rb") as wf_out:
        assert wf_out.getframerate() == 16_000
        assert wf_out.getnchannels() == 1


def test_ingest_missing_file_raises(tmp_path: Path) -> None:
    rec = Recorder(session_id="sess-miss", recordings_dir=tmp_path / "store")
    with pytest.raises(FileNotFoundError):
        rec.ingest_file(tmp_path / "ghost.wav")


# ---------------------------------------------------------------------------
# ingest_file — DB persistence
# ---------------------------------------------------------------------------


def test_ingest_persists_to_db(tmp_path: Path) -> None:
    src = _make_wav(tmp_path / "src.wav")
    with get_connection(":memory:") as conn:
        conn.execute(
            "INSERT INTO call_sessions (id, lead_id, mode, started_at) VALUES (?,?,?,?)",
            ("sess-db", "lead-1", "AI", "2026-05-05T00:00:00"),
        )
        rec = Recorder(
            session_id="sess-db",
            recordings_dir=tmp_path / "store",
            conn=conn,
        )
        result = rec.ingest_file(src)

        row = conn.execute(
            "SELECT * FROM call_recordings WHERE id = ?", (result.id,)
        ).fetchone()

    assert row is not None
    assert row["session_id"] == "sess-db"
    assert row["source_kind"] == "file"
    assert row["audio_hash"] == result.audio_hash


# ---------------------------------------------------------------------------
# Duration calculation
# ---------------------------------------------------------------------------


def test_duration_is_calculated(tmp_path: Path) -> None:
    src = _make_wav(tmp_path / "dur.wav", duration_sec=1.0)
    rec = Recorder(session_id="sess-dur", recordings_dir=tmp_path / "store")
    result = rec.ingest_file(src)
    assert result.duration_sec is not None
    assert result.duration_sec >= 1


# ---------------------------------------------------------------------------
# Transcriber stub mode (whisper not available)
# ---------------------------------------------------------------------------


def test_transcriber_stub_when_whisper_unavailable() -> None:
    from voice.transcriber import Transcriber
    t = Transcriber(session_id="sess-stub", whisper_bin="/nonexistent/whisper")
    assert not t.available


def test_transcriber_stub_returns_placeholder(tmp_path: Path) -> None:
    from voice.transcriber import Transcriber
    wav = _make_wav(tmp_path / "audio.wav")
    t = Transcriber(session_id="sess-stub2", whisper_bin="/nonexistent/whisper")
    segments = t.transcribe(wav)
    assert len(segments) == 1
    assert "unavailable" in segments[0].text


def test_transcriber_stub_persists_to_db(tmp_path: Path) -> None:
    from voice.transcriber import Transcriber
    wav = _make_wav(tmp_path / "audio2.wav")
    with get_connection(":memory:") as conn:
        conn.execute(
            "INSERT INTO call_sessions (id, lead_id, mode, started_at) VALUES (?,?,?,?)",
            ("sess-tr", "lead-1", "AI", "2026-05-05T00:00:00"),
        )
        t = Transcriber(
            session_id="sess-tr",
            whisper_bin="/nonexistent/whisper",
            conn=conn,
        )
        segments = t.transcribe(wav)

        rows = conn.execute(
            "SELECT * FROM transcripts WHERE session_id = ?", ("sess-tr",)
        ).fetchall()

    assert len(rows) == 1
    assert rows[0]["speaker"] == "reception"
