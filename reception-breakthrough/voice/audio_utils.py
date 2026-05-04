"""Audio utility functions for the reception-breakthrough module.

Responsibilities (T-302):
  - RMS-based silence detection (``is_silent``)
  - Cumulative silence measurement (``measure_silence_ms``)
  - WAV file normalisation helpers (used by recorder.py)

All functions operate on standard-library ``wave`` module objects or raw
``bytes`` / ``bytearray`` PCM data so there are no heavy audio-library
dependencies.  The threshold values are configurable per call so the state
machine can pass its own ``EV_TIMEOUT`` budget.

Terminology
-----------
* **RMS (Root Mean Square)** — 音量の実効値。PCM サンプルの二乗平均平方根。
  値が小さいほど無音に近い。
* **silence_ms** — 無音が継続した累計ミリ秒。state machine に渡す値。
"""

from __future__ import annotations

import audioop
import math
import struct
import wave
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants / defaults
# ---------------------------------------------------------------------------

#: Default RMS threshold below which a frame is considered silent.
#: Tunable per deployment (lower = more sensitive).
DEFAULT_SILENCE_RMS_THRESHOLD: int = 500

#: Target sample rate for normalised WAV files (spec T-300 DoD).
TARGET_SAMPLE_RATE: int = 16_000

#: Target number of channels for normalised WAV files.
TARGET_CHANNELS: int = 1

#: Target sample width in bytes (16-bit PCM = 2 bytes).
TARGET_SAMPLE_WIDTH: int = 2


# ---------------------------------------------------------------------------
# PCM helpers
# ---------------------------------------------------------------------------


def rms_of_frame(pcm_frame: bytes, sample_width: int = 2) -> float:
    """Return the RMS amplitude of a raw PCM frame.

    Args:
        pcm_frame: Raw PCM bytes (little-endian signed integers).
        sample_width: Bytes per sample (1, 2, or 4).

    Returns:
        RMS value as a float.  Returns 0.0 for an empty frame.
    """
    if not pcm_frame:
        return 0.0
    return audioop.rms(pcm_frame, sample_width)


def is_silent(
    pcm_frame: bytes,
    sample_width: int = 2,
    threshold: int = DEFAULT_SILENCE_RMS_THRESHOLD,
) -> bool:
    """Return ``True`` if *pcm_frame* is below the silence threshold.

    Args:
        pcm_frame: Raw PCM bytes.
        sample_width: Bytes per sample.
        threshold: RMS value below which the frame is considered silent.

    Returns:
        ``True`` when the frame is silent.
    """
    return rms_of_frame(pcm_frame, sample_width) < threshold


def measure_silence_ms(
    wav_path: str | Path,
    threshold: int = DEFAULT_SILENCE_RMS_THRESHOLD,
    frame_duration_ms: int = 20,
) -> int:
    """Measure total silence duration (in ms) in a WAV file.

    Reads the file in *frame_duration_ms* chunks and sums up all silent
    frames.  Used by the state machine to accumulate ``silence_ms`` for the
    ``F2_silence`` threshold check.

    Args:
        wav_path: Path to a WAV file (any sample rate / channels; read as-is).
        threshold: RMS silence threshold.
        frame_duration_ms: Duration of each analysis frame in milliseconds.

    Returns:
        Total silent milliseconds (int).
    """
    path = Path(wav_path)
    if not path.exists():
        raise FileNotFoundError(f"WAV file not found: {path}")

    total_silent_ms = 0
    with wave.open(str(path), "rb") as wf:
        sample_rate = wf.getframerate()
        sample_width = wf.getsampwidth()
        n_channels = wf.getnchannels()
        frames_per_chunk = int(sample_rate * frame_duration_ms / 1000)
        bytes_per_frame = sample_width * n_channels * frames_per_chunk

        while True:
            raw = wf.readframes(frames_per_chunk)
            if not raw:
                break
            # Convert to mono by averaging channels if needed
            mono = audioop.tomono(raw, sample_width, 0.5, 0.5) if n_channels > 1 else raw
            if is_silent(mono, sample_width, threshold):
                # Actual duration of this chunk (may be shorter at file end)
                actual_ms = int(len(raw) / (sample_rate * sample_width * n_channels) * 1000)
                total_silent_ms += actual_ms

    return total_silent_ms


# ---------------------------------------------------------------------------
# WAV normalisation
# ---------------------------------------------------------------------------


def read_wav_info(wav_path: str | Path) -> dict:
    """Return basic metadata for a WAV file without loading audio data.

    Returns:
        Dict with keys: ``sample_rate``, ``channels``, ``sample_width``,
        ``n_frames``, ``duration_sec``.
    """
    with wave.open(str(Path(wav_path)), "rb") as wf:
        sr = wf.getframerate()
        ch = wf.getnchannels()
        sw = wf.getsampwidth()
        nf = wf.getnframes()
        return {
            "sample_rate": sr,
            "channels": ch,
            "sample_width": sw,
            "n_frames": nf,
            "duration_sec": nf / sr if sr > 0 else 0.0,
        }


def needs_normalisation(wav_path: str | Path) -> bool:
    """Return ``True`` if the WAV file is not already 16kHz / mono / 16-bit."""
    info = read_wav_info(wav_path)
    return (
        info["sample_rate"] != TARGET_SAMPLE_RATE
        or info["channels"] != TARGET_CHANNELS
        or info["sample_width"] != TARGET_SAMPLE_WIDTH
    )


def normalise_wav(src: str | Path, dst: str | Path) -> Path:
    """Resample and convert *src* WAV to 16kHz mono 16-bit PCM at *dst*.

    Uses only the standard-library ``audioop`` and ``wave`` modules (zero
    external dependencies).

    Args:
        src: Source WAV file path.
        dst: Destination WAV file path (created / overwritten).

    Returns:
        The destination :class:`Path`.

    Note:
        ``audioop.ratecv`` provides basic linear resampling.  For production
        quality, replace with ``sox`` or ``ffmpeg`` subprocess calls.
    """
    src, dst = Path(src), Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(src), "rb") as wf_in:
        sr_in = wf_in.getframerate()
        sw_in = wf_in.getsampwidth()
        ch_in = wf_in.getnchannels()
        raw = wf_in.readframes(wf_in.getnframes())

    # ── Convert to mono ────────────────────────────────────────────────────
    if ch_in > 1:
        raw = audioop.tomono(raw, sw_in, 0.5, 0.5)

    # ── Convert to 16-bit ─────────────────────────────────────────────────
    if sw_in != TARGET_SAMPLE_WIDTH:
        raw = audioop.lin2lin(raw, sw_in, TARGET_SAMPLE_WIDTH)

    # ── Resample to 16 kHz ────────────────────────────────────────────────
    if sr_in != TARGET_SAMPLE_RATE:
        raw, _ = audioop.ratecv(
            raw, TARGET_SAMPLE_WIDTH, 1, sr_in, TARGET_SAMPLE_RATE, None
        )

    with wave.open(str(dst), "wb") as wf_out:
        wf_out.setnchannels(TARGET_CHANNELS)
        wf_out.setsampwidth(TARGET_SAMPLE_WIDTH)
        wf_out.setframerate(TARGET_SAMPLE_RATE)
        wf_out.writeframes(raw)

    return dst
