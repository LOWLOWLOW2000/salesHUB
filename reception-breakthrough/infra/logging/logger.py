"""Structured JSON-Lines logger for the reception-breakthrough module.

Each log entry is a single JSON object written to stdout (or a supplied sink).
The session_id is stored in a thread-local MDC (Mapped Diagnostic Context) so
it is automatically included in every message emitted from the same thread.

Typical usage::

    from infra.logging.logger import get_logger, bind_session

    bind_session("session-uuid-here")
    log = get_logger(__name__)

    log.info("state_transition", from_state="S2", to_state="S3")
    log.warn("undefined_transition", state="S2", input="X9_unknown")

Each emitted line looks like::

    {"ts": "2026-05-05T00:00:00.000Z", "level": "INFO", "logger": "core.state_machine",
     "session_id": "session-uuid-here", "msg": "state_transition",
     "from_state": "S2", "to_state": "S3"}

Levels (lowest to highest): DEBUG < INFO < WARN < ERROR.
Set the effective level via :func:`set_level` or the ``LOG_LEVEL`` env-var.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from datetime import datetime, timezone
from typing import IO, Any, TextIO

_LEVELS: dict[str, int] = {
    "DEBUG": 10,
    "INFO": 20,
    "WARN": 30,
    "WARNING": 30,
    "ERROR": 40,
}

_level_lock = threading.Lock()
_effective_level: int = _LEVELS.get(
    os.environ.get("LOG_LEVEL", "INFO").upper(), _LEVELS["INFO"]
)

_mdc: threading.local = threading.local()


def set_level(level: str) -> None:
    """Set the module-wide log level.

    Args:
        level: One of ``DEBUG``, ``INFO``, ``WARN``, ``ERROR`` (case-insensitive).

    Raises:
        ValueError: If *level* is not recognised.
    """
    level = level.upper()
    if level not in _LEVELS:
        raise ValueError(f"Unknown log level: {level!r}. Choose from {list(_LEVELS)}")
    global _effective_level
    with _level_lock:
        _effective_level = _LEVELS[level]


def get_level() -> str:
    """Return the current effective level name."""
    for name, value in _LEVELS.items():
        if value == _effective_level and name != "WARNING":
            return name
    return "INFO"


def bind_session(session_id: str | None) -> None:
    """Attach (or clear) a session_id to the current thread's MDC.

    Call ``bind_session(None)`` at the end of a session to clean up.

    Args:
        session_id: The UUID string of the active call session, or ``None``
            to clear the binding.
    """
    _mdc.session_id = session_id


def _current_session() -> str | None:
    return getattr(_mdc, "session_id", None)


def _emit(
    level: str,
    logger_name: str,
    msg: str,
    sink: TextIO,
    extra: dict[str, Any],
) -> None:
    numeric = _LEVELS.get(level, 0)
    if numeric < _effective_level:
        return

    entry: dict[str, Any] = {
        "ts": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
        + "Z",
        "level": level,
        "logger": logger_name,
    }
    session = _current_session()
    if session is not None:
        entry["session_id"] = session
    entry["msg"] = msg
    entry.update(extra)

    sink.write(json.dumps(entry, ensure_ascii=False) + "\n")
    sink.flush()


class Logger:
    """Thin structured logger bound to a module name."""

    def __init__(self, name: str, sink: IO[str] | None = None) -> None:
        self._name = name
        self._sink: TextIO = sink or sys.stdout

    def debug(self, msg: str, **kwargs: Any) -> None:
        _emit("DEBUG", self._name, msg, self._sink, kwargs)

    def info(self, msg: str, **kwargs: Any) -> None:
        _emit("INFO", self._name, msg, self._sink, kwargs)

    def warn(self, msg: str, **kwargs: Any) -> None:
        _emit("WARN", self._name, msg, self._sink, kwargs)

    def error(self, msg: str, **kwargs: Any) -> None:
        _emit("ERROR", self._name, msg, self._sink, kwargs)


def get_logger(name: str, sink: IO[str] | None = None) -> Logger:
    """Return a :class:`Logger` bound to *name*.

    Args:
        name: Typically ``__name__`` of the calling module.
        sink: Optional file-like object to write to. Defaults to ``sys.stdout``.

    Returns:
        A :class:`Logger` instance ready to use.
    """
    return Logger(name=name, sink=sink)
