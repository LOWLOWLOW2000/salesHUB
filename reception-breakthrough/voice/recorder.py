"""Recording manager for the reception-breakthrough module (T-300).

Responsibilities:
  - Accept an existing audio file path (file-injection mode — the primary
    mode for this module's 0-cost, no-telephony-API design).
  - Normalise the file to 16 kHz / mono / 16-bit WAV (via ``audio_utils``).
  - Persist a row in ``call_recordings`` and return the recording ID.

Future extension (not implemented here):
  - Live mic capture (``sounddevice`` / ``pyaudio``) for human-dialling mode.
  - Streaming ingestion from a softphone.

The recorder does **not** know about the CRM or the state machine.  It is a
pure infrastructure component.
"""

from __future__ import annotations

import hashlib
import shutil
import uuid
import wave
from datetime import datetime, timezone
from pathlib import Path

from infra.logging.logger import Logger, get_logger
from voice.audio_utils import needs_normalisation, normalise_wav

try:
    import sqlite3 as _sqlite3
    _Connection = _sqlite3.Connection
except ImportError:  # pragma: no cover
    _Connection = object  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Default storage root (relative to project root)
# ---------------------------------------------------------------------------

_DEFAULT_RECORDINGS_DIR = Path(__file__).resolve().parents[1] / "data" / "recordings"


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


class RecordingRecord:
    """Metadata for a stored recording.

    Attributes:
        id: UUID primary key (matches ``call_recordings.id``).
        session_id: Parent call session.
        audio_path: Absolute path to the normalised WAV file.
        duration_sec: Duration in seconds (integer, may be None for raw imports).
        audio_hash: SHA-256 hex digest of the normalised file.
        source_kind: ``"file"`` for injected files, ``"live"`` for future live capture.
    """

    __slots__ = ("id", "session_id", "audio_path", "duration_sec", "audio_hash", "source_kind")

    def __init__(
        self,
        id: str,
        session_id: str,
        audio_path: Path,
        duration_sec: int | None,
        audio_hash: str,
        source_kind: str,
    ) -> None:
        self.id = id
        self.session_id = session_id
        self.audio_path = audio_path
        self.duration_sec = duration_sec
        self.audio_hash = audio_hash
        self.source_kind = source_kind


# ---------------------------------------------------------------------------
# Recorder
# ---------------------------------------------------------------------------


class Recorder:
    """Manage audio file ingestion for a call session.

    Args:
        session_id: UUID of the parent call session.
        recordings_dir: Root directory where normalised WAV files are stored.
            Defaults to ``data/recordings/`` inside the project.
        conn: SQLite connection.  Pass ``None`` to skip DB persistence.
        logger: Structured logger.
    """

    def __init__(
        self,
        session_id: str,
        recordings_dir: str | Path = _DEFAULT_RECORDINGS_DIR,
        conn: _Connection | None = None,
        logger: Logger | None = None,
    ) -> None:
        self._session_id = session_id
        self._recordings_dir = Path(recordings_dir)
        self._recordings_dir.mkdir(parents=True, exist_ok=True)
        self._conn = conn
        self._log = logger or get_logger(__name__)

    # ── Public ───────────────────────────────────────────────────────────────

    def ingest_file(self, src_path: str | Path) -> RecordingRecord:
        """Ingest an existing audio file into the recordings store.

        The file is normalised to 16 kHz / mono / 16-bit WAV if needed, then
        copied to ``recordings_dir/<session_id>/<uuid>.wav``.  A row is
        inserted into ``call_recordings``.

        Args:
            src_path: Path to an existing audio file (WAV format).

        Returns:
            A :class:`RecordingRecord` with all metadata.

        Raises:
            FileNotFoundError: If *src_path* does not exist.
            ValueError: If the file is not a valid WAV.
        """
        src = Path(src_path)
        if not src.exists():
            raise FileNotFoundError(f"Source audio file not found: {src}")

        recording_id = str(uuid.uuid4())
        session_dir = self._recordings_dir / self._session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        dst = session_dir / f"{recording_id}.wav"

        # ── Normalise ──────────────────────────────────────────────────────
        if self._is_wav(src) and not needs_normalisation(src):
            shutil.copy2(src, dst)
            self._log.info("recording_copied", src=str(src), dst=str(dst))
        else:
            normalise_wav(src, dst)
            self._log.info("recording_normalised", src=str(src), dst=str(dst))

        # ── Duration + hash ────────────────────────────────────────────────
        duration_sec = self._wav_duration(dst)
        audio_hash = self._sha256(dst)

        record = RecordingRecord(
            id=recording_id,
            session_id=self._session_id,
            audio_path=dst,
            duration_sec=duration_sec,
            audio_hash=audio_hash,
            source_kind="file",
        )
        self._persist(record)
        self._log.info(
            "recording_ingested",
            recording_id=recording_id,
            duration_sec=duration_sec,
            audio_hash=audio_hash[:8],
        )
        return record

    # ── Internal helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _is_wav(path: Path) -> bool:
        try:
            with wave.open(str(path), "rb"):
                return True
        except (wave.Error, EOFError, OSError):
            return False

    @staticmethod
    def _wav_duration(path: Path) -> int | None:
        try:
            with wave.open(str(path), "rb") as wf:
                return int(wf.getnframes() / wf.getframerate())
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _sha256(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def _persist(self, rec: RecordingRecord) -> None:
        if self._conn is None:
            return
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            INSERT INTO call_recordings
              (id, session_id, audio_path, duration_sec, audio_hash,
               source_kind, recorded_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rec.id,
                rec.session_id,
                str(rec.audio_path),
                rec.duration_sec,
                rec.audio_hash,
                rec.source_kind,
                now,
                now,
            ),
        )
        self._conn.commit()
