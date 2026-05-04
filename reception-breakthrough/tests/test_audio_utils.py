"""Tests for voice.audio_utils (T-302).

Strategy: generate synthetic WAV data in memory — no external audio files needed.
"""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

import pytest

from voice.audio_utils import (
    TARGET_CHANNELS,
    TARGET_SAMPLE_RATE,
    TARGET_SAMPLE_WIDTH,
    is_silent,
    measure_silence_ms,
    needs_normalisation,
    normalise_wav,
    read_wav_info,
    rms_of_frame,
)


# ---------------------------------------------------------------------------
# Helpers to generate synthetic WAV files
# ---------------------------------------------------------------------------


def _write_wav(
    path: Path,
    *,
    sample_rate: int = 16_000,
    channels: int = 1,
    sample_width: int = 2,
    duration_sec: float = 0.1,
    amplitude: int = 0,  # 0 = silence; >0 = sine wave
) -> Path:
    """Write a minimal WAV file for testing."""
    n_frames = int(sample_rate * duration_sec)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        for i in range(n_frames):
            if amplitude == 0:
                sample = 0
            else:
                sample = int(amplitude * math.sin(2 * math.pi * 440 * i / sample_rate))
            # Write for each channel
            frame = struct.pack(f"<{'h' * channels}", *([sample] * channels))
            wf.writeframes(frame)
    return path


# ---------------------------------------------------------------------------
# rms_of_frame
# ---------------------------------------------------------------------------


def test_rms_of_empty_frame_is_zero() -> None:
    assert rms_of_frame(b"") == 0.0


def test_rms_of_silent_frame_is_zero() -> None:
    silence = struct.pack("<" + "h" * 100, *([0] * 100))
    assert rms_of_frame(silence, sample_width=2) == 0.0


def test_rms_of_loud_frame_is_positive() -> None:
    loud = struct.pack("<" + "h" * 10, *([10000] * 10))
    assert rms_of_frame(loud, sample_width=2) > 0


# ---------------------------------------------------------------------------
# is_silent
# ---------------------------------------------------------------------------


def test_silent_pcm_detected() -> None:
    silence = struct.pack("<" + "h" * 50, *([0] * 50))
    assert is_silent(silence, threshold=500)


def test_loud_pcm_not_silent() -> None:
    loud = struct.pack("<" + "h" * 50, *([15000] * 50))
    assert not is_silent(loud, threshold=500)


# ---------------------------------------------------------------------------
# measure_silence_ms
# ---------------------------------------------------------------------------


def test_all_silent_wav_returns_full_duration(tmp_path: Path) -> None:
    wav = _write_wav(tmp_path / "silent.wav", amplitude=0, duration_sec=0.5)
    silence_ms = measure_silence_ms(wav)
    # Should be close to 500ms (some rounding allowed)
    assert 400 <= silence_ms <= 600


def test_loud_wav_returns_little_silence(tmp_path: Path) -> None:
    wav = _write_wav(tmp_path / "loud.wav", amplitude=20000, duration_sec=0.5)
    silence_ms = measure_silence_ms(wav, threshold=500)
    # A 440Hz sine at amplitude 20000 should produce RMS >> 500
    assert silence_ms < 100


def test_measure_silence_raises_for_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        measure_silence_ms(tmp_path / "nonexistent.wav")


# ---------------------------------------------------------------------------
# read_wav_info
# ---------------------------------------------------------------------------


def test_read_wav_info_returns_correct_metadata(tmp_path: Path) -> None:
    wav = _write_wav(tmp_path / "info.wav", sample_rate=8000, channels=1,
                     duration_sec=1.0)
    info = read_wav_info(wav)
    assert info["sample_rate"] == 8000
    assert info["channels"] == 1
    assert info["duration_sec"] == pytest.approx(1.0, abs=0.05)


# ---------------------------------------------------------------------------
# needs_normalisation / normalise_wav
# ---------------------------------------------------------------------------


def test_needs_normalisation_true_for_8khz(tmp_path: Path) -> None:
    wav = _write_wav(tmp_path / "8k.wav", sample_rate=8000)
    assert needs_normalisation(wav)


def test_needs_normalisation_false_for_16k_mono_16bit(tmp_path: Path) -> None:
    wav = _write_wav(
        tmp_path / "16k.wav",
        sample_rate=TARGET_SAMPLE_RATE,
        channels=TARGET_CHANNELS,
        sample_width=TARGET_SAMPLE_WIDTH,
    )
    assert not needs_normalisation(wav)


def test_normalise_wav_produces_16k_mono(tmp_path: Path) -> None:
    src = _write_wav(tmp_path / "src.wav", sample_rate=8000, channels=2, amplitude=5000)
    dst = normalise_wav(src, tmp_path / "dst.wav")

    info = read_wav_info(dst)
    assert info["sample_rate"] == TARGET_SAMPLE_RATE
    assert info["channels"] == TARGET_CHANNELS
    assert info["sample_width"] == TARGET_SAMPLE_WIDTH


def test_normalise_wav_creates_non_empty_file(tmp_path: Path) -> None:
    src = _write_wav(tmp_path / "src2.wav", sample_rate=44100, amplitude=8000,
                     duration_sec=0.2)
    dst = normalise_wav(src, tmp_path / "dst2.wav")
    assert dst.exists()
    assert dst.stat().st_size > 44  # WAV header is 44 bytes minimum
