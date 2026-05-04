"""Whisper.cpp wrapper for speech-to-text transcription (T-301).

Design
------
* ``whisper.cpp`` is an external binary — this module wraps it via
  ``subprocess`` so the Python code has zero dependency on C extensions.
* The interface is **port-like**: swapping ``whisper.cpp`` for another STT
  engine requires only changing :meth:`Transcriber._run_whisper`.
* Speaker diarisation is intentionally simple: the AI/caller's speech
  intervals are assumed to be *known* (passed in as ``ai_intervals_ms``),
  and everything else is labelled ``"reception"``.

When ``whisper_bin`` is not found on the system the transcriber operates in
**stub mode** — it returns a single ``"[transcription unavailable]"`` segment.
This keeps the rest of the pipeline functional on machines where
``whisper.cpp`` is not installed (CI, first-run dev setup).
"""

from __future__ import annotations

import json
import re
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from shutil import which
from typing import Sequence

from infra.logging.logger import Logger, get_logger

try:
    import sqlite3 as _sqlite3
    _Connection = _sqlite3.Connection
except ImportError:  # pragma: no cover
    _Connection = object  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    """One speaker turn in a transcript.

    Attributes:
        id: UUID primary key.
        session_id: Parent call session.
        recording_id: Source recording UUID (may be ``None`` for direct text).
        speaker: ``"ai"`` or ``"reception"``.
        text: Transcribed text (stripped).
        start_time_ms: Millisecond offset from start of audio.
        end_time_ms: Millisecond offset from start of audio.
    """

    id: str
    session_id: str
    recording_id: str | None
    speaker: str
    text: str
    start_time_ms: int | None
    end_time_ms: int | None


# ---------------------------------------------------------------------------
# Transcriber
# ---------------------------------------------------------------------------


class Transcriber:
    """Wrap whisper.cpp to produce :class:`TranscriptSegment` lists.

    Args:
        session_id: UUID of the parent call session.
        whisper_bin: Path to the ``whisper-cli`` or ``main`` binary.
            Defaults to ``whisper-cli`` discovered via ``PATH``.
        model_path: Path to the GGML model file (e.g. ``ggml-small.bin``).
        ai_intervals_ms: List of ``(start_ms, end_ms)`` tuples representing
            the AI/caller's speech segments.  Everything outside these
            intervals is labelled ``"reception"``.
        conn: SQLite connection for persisting ``transcripts`` rows.
        logger: Structured logger.
    """

    _WHISPER_BINS = ("whisper-cli", "whisper.cpp", "main")

    def __init__(
        self,
        session_id: str,
        whisper_bin: str | Path | None = None,
        model_path: str | Path | None = None,
        ai_intervals_ms: list[tuple[int, int]] | None = None,
        conn: _Connection | None = None,
        logger: Logger | None = None,
    ) -> None:
        self._session_id = session_id
        self._whisper_bin = self._resolve_bin(whisper_bin)
        self._model_path = Path(model_path) if model_path else None
        self._ai_intervals_ms: list[tuple[int, int]] = ai_intervals_ms or []
        self._conn = conn
        self._log = logger or get_logger(__name__)

    # ── Public ───────────────────────────────────────────────────────────────

    @property
    def available(self) -> bool:
        """Return ``True`` if ``whisper.cpp`` binary was found."""
        return self._whisper_bin is not None

    def transcribe(
        self,
        wav_path: str | Path,
        recording_id: str | None = None,
    ) -> list[TranscriptSegment]:
        """Transcribe *wav_path* and return a list of :class:`TranscriptSegment`.

        Args:
            wav_path: Path to a normalised 16kHz mono WAV file.
            recording_id: Optional UUID of the ``call_recordings`` row.

        Returns:
            List of segments ordered by ``start_time_ms``.  In stub mode,
            returns a single placeholder segment.
        """
        wav_path = Path(wav_path)
        if not wav_path.exists():
            raise FileNotFoundError(f"WAV file not found: {wav_path}")

        if not self.available:
            self._log.warn(
                "whisper_unavailable",
                detail="whisper.cpp not found — returning stub transcript",
            )
            return self._stub_segment(recording_id)

        raw_segments = self._run_whisper(wav_path)
        segments = [
            self._make_segment(raw, recording_id) for raw in raw_segments
        ]
        self._persist_all(segments)
        return segments

    # ── Whisper runner ───────────────────────────────────────────────────────

    def _run_whisper(self, wav_path: Path) -> list[dict]:
        """Run whisper.cpp and parse its JSON output.

        whisper-cli flags used:
          -m  model path
          -f  input file
          --output-json  output JSON to stdout
          --language ja
        """
        if self._model_path is None or not self._model_path.exists():
            self._log.warn("model_not_found", model=str(self._model_path))
            return []

        cmd = [
            str(self._whisper_bin),
            "-m", str(self._model_path),
            "-f", str(wav_path),
            "--output-json",
            "--language", "ja",
            "--no-timestamps",  # we compute ms from the JSON timestamps field
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            self._log.error("whisper_failed", stderr=exc.stderr[:200])
            return []
        except subprocess.TimeoutExpired:
            self._log.error("whisper_timeout", wav=str(wav_path))
            return []

        return self._parse_json(result.stdout)

    @staticmethod
    def _parse_json(stdout: str) -> list[dict]:
        """Parse whisper.cpp JSON output into a list of segment dicts."""
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return []

        segments = data.get("transcription", [])
        result = []
        for seg in segments:
            offsets = seg.get("offsets", {})
            result.append(
                {
                    "text": seg.get("text", "").strip(),
                    "start_ms": offsets.get("from", 0),
                    "end_ms": offsets.get("to", 0),
                }
            )
        return result

    # ── Speaker diarisation ──────────────────────────────────────────────────

    def _speaker_for(self, start_ms: int, end_ms: int) -> str:
        """Return ``"ai"`` if the segment overlaps any known AI interval, else ``"reception"``."""
        mid = (start_ms + end_ms) // 2
        for ai_start, ai_end in self._ai_intervals_ms:
            if ai_start <= mid <= ai_end:
                return "ai"
        return "reception"

    # ── Segment construction ─────────────────────────────────────────────────

    def _make_segment(self, raw: dict, recording_id: str | None) -> TranscriptSegment:
        start_ms = raw.get("start_ms")
        end_ms = raw.get("end_ms")
        speaker = (
            self._speaker_for(start_ms, end_ms)
            if start_ms is not None and end_ms is not None
            else "reception"
        )
        return TranscriptSegment(
            id=str(uuid.uuid4()),
            session_id=self._session_id,
            recording_id=recording_id,
            speaker=speaker,
            text=raw.get("text", ""),
            start_time_ms=start_ms,
            end_time_ms=end_ms,
        )

    def _stub_segment(self, recording_id: str | None) -> list[TranscriptSegment]:
        seg = TranscriptSegment(
            id=str(uuid.uuid4()),
            session_id=self._session_id,
            recording_id=recording_id,
            speaker="reception",
            text="[transcription unavailable — whisper.cpp not installed]",
            start_time_ms=None,
            end_time_ms=None,
        )
        self._persist_all([seg])
        return [seg]

    # ── DB persistence ───────────────────────────────────────────────────────

    def _persist_all(self, segments: list[TranscriptSegment]) -> None:
        if self._conn is None or not segments:
            return
        now = datetime.now(timezone.utc).isoformat()
        self._conn.executemany(
            """
            INSERT INTO transcripts
              (id, session_id, recording_id, speaker, text,
               start_time_ms, end_time_ms, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    seg.id,
                    seg.session_id,
                    seg.recording_id,
                    seg.speaker,
                    seg.text,
                    seg.start_time_ms,
                    seg.end_time_ms,
                    now,
                )
                for seg in segments
            ],
        )
        self._conn.commit()

    # ── Binary resolution ────────────────────────────────────────────────────

    @classmethod
    def _resolve_bin(cls, hint: str | Path | None) -> Path | None:
        if hint is not None:
            p = Path(hint)
            return p if p.exists() else None
        for name in cls._WHISPER_BINS:
            found = which(name)
            if found:
                return Path(found)
        return None
