"""Tests for infra.logging.logger (T-102)."""

from __future__ import annotations

import io
import json
import threading

import pytest

from infra.logging.logger import (
    Logger,
    bind_session,
    get_logger,
    get_level,
    set_level,
)


def _captured_logger(name: str = "test") -> tuple[Logger, io.StringIO]:
    sink = io.StringIO()
    return get_logger(name, sink=sink), sink


def _parse_lines(sink: io.StringIO) -> list[dict]:
    return [json.loads(line) for line in sink.getvalue().splitlines() if line.strip()]


def test_info_message_emitted_with_required_fields() -> None:
    log, sink = _captured_logger("core.test")
    bind_session(None)

    log.info("state_transition", from_state="S2", to_state="S3")
    entries = _parse_lines(sink)

    assert len(entries) == 1
    entry = entries[0]
    assert entry["level"] == "INFO"
    assert entry["logger"] == "core.test"
    assert entry["msg"] == "state_transition"
    assert entry["from_state"] == "S2"
    assert entry["to_state"] == "S3"
    assert "session_id" not in entry


def test_session_id_included_after_bind() -> None:
    log, sink = _captured_logger()
    bind_session("session-abc")

    log.info("ping")
    entries = _parse_lines(sink)

    assert entries[0]["session_id"] == "session-abc"
    bind_session(None)


def test_warn_key_matches_spec() -> None:
    """WARN: undefined_transition must be grep-able as documented in spec."""
    log, sink = _captured_logger()
    bind_session(None)

    log.warn("undefined_transition", state="S2", input="UNKNOWN")
    entries = _parse_lines(sink)

    assert entries[0]["level"] == "WARN"
    assert entries[0]["msg"] == "undefined_transition"


def test_debug_suppressed_at_info_level() -> None:
    original = get_level()
    set_level("INFO")

    log, sink = _captured_logger()
    bind_session(None)
    log.debug("should not appear")

    assert _parse_lines(sink) == []
    set_level(original)


def test_debug_emitted_when_level_is_debug() -> None:
    original = get_level()
    set_level("DEBUG")

    log, sink = _captured_logger()
    bind_session(None)
    log.debug("debug_message")

    entries = _parse_lines(sink)
    assert len(entries) == 1
    assert entries[0]["level"] == "DEBUG"
    set_level(original)


def test_set_level_raises_for_unknown() -> None:
    with pytest.raises(ValueError, match="Unknown log level"):
        set_level("VERBOSE")


def test_session_id_is_thread_local() -> None:
    """Session IDs must not leak between threads."""
    results: dict[str, str | None] = {}

    def thread_a():
        bind_session("session-A")
        import time
        time.sleep(0.02)
        log, sink = _captured_logger("thread-a")
        log.info("ping")
        entries = _parse_lines(sink)
        results["a"] = entries[0].get("session_id")

    def thread_b():
        bind_session("session-B")
        log, sink = _captured_logger("thread-b")
        log.info("ping")
        entries = _parse_lines(sink)
        results["b"] = entries[0].get("session_id")

    ta = threading.Thread(target=thread_a)
    tb = threading.Thread(target=thread_b)
    ta.start()
    tb.start()
    ta.join()
    tb.join()

    assert results["a"] == "session-A"
    assert results["b"] == "session-B"


def test_timestamp_format() -> None:
    log, sink = _captured_logger()
    bind_session(None)
    log.info("ts_check")

    entry = _parse_lines(sink)[0]
    ts: str = entry["ts"]
    assert ts.endswith("Z")
    assert "T" in ts
