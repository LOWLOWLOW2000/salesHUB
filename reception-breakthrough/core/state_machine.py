"""Reception breakthrough call state machine.

Implements §4–§8 of docs/reception-breakthrough/state-machine-spec.md.

Design decisions
----------------
* Transition table is a **module-level dict** (data, not logic) so entries can
  be added/removed without touching control flow.
* AI and HUMAN modes share the same table — ``mode`` is a logging tag only.
* Exception inputs (F*, EV_TIMEOUT, EV_HANGUP) are handled *before* the table
  lookup so they apply from any state.
* Undefined (state, input) pairs are treated as ``F1_unclear`` and emit a
  ``WARN: undefined_transition`` log entry (§8, invariant 1).
* S11 is a terminal state — calling :meth:`StateMachine.send` after S11 raises
  :exc:`TerminatedError` (§8, invariant 3).
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import NamedTuple

from infra.logging.logger import Logger, get_logger

# ---------------------------------------------------------------------------
# Input classification helpers
# ---------------------------------------------------------------------------

_INTENT_INPUTS: frozenset[str] = frozenset(
    {
        "A1_listening",
        "B1_simple_purpose",
        "B2_detailed_purpose",
        "C1_hard_reject",
        "C2_soft_reject",
        "C3_policy_block",
        "D1_hold",
        "D2_internal_check",
        "D3_name_request",
        "E1_absent",
        "E2_busy",
        "E3_schedule",
        "F1_unclear",
        "F2_silence",
        "F3_disconnect",
    }
)

_EVENT_INPUTS: frozenset[str] = frozenset(
    {
        "EV_DIALED",
        "EV_PICKED_UP",
        "EV_NO_ANSWER",
        "EV_HUMAN_RESPONDED",
        "EV_TRANSFER_DONE",
        "EV_TIMEOUT",
        "EV_HANGUP",
    }
)

_KIND_INTENT = "intent"
_KIND_EVENT = "event"


def _input_kind(input_id: str) -> str:
    if input_id in _INTENT_INPUTS:
        return _KIND_INTENT
    return _KIND_EVENT


# ---------------------------------------------------------------------------
# Transition table (data layer — add/remove rows without touching logic)
# ---------------------------------------------------------------------------

class _TDef(NamedTuple):
    """Internal transition definition stored in _TRANSITIONS."""

    to_state: str
    response_template_id: str | None = None
    side_effects: tuple[str, ...] = ()


#: Normal transitions: (from_state, input_id) → _TDef
#: Source: state-machine-spec.md §4
_TRANSITIONS: dict[tuple[str, str], _TDef] = {
    # S0 ─────────────────────────────────────────────────────────────────────
    ("S0", "EV_DIALED"): _TDef("S1", side_effects=("log:dial_started",)),
    # S1 ─────────────────────────────────────────────────────────────────────
    ("S1", "EV_PICKED_UP"): _TDef("S2", side_effects=("start_recording",)),
    ("S1", "EV_NO_ANSWER"): _TDef("S11", side_effects=("outcome=OUT_NOISE",)),
    # S2 ─────────────────────────────────────────────────────────────────────
    ("S2", "A1_listening"): _TDef("S3", "RT_ASK_TRANSFER_SHORT"),
    ("S2", "B1_simple_purpose"): _TDef("S3", "RT_PURPOSE_SHORT"),
    ("S2", "B2_detailed_purpose"): _TDef("S3", "RT_PURPOSE_DETAILED"),
    ("S2", "D1_hold"): _TDef("S7", "RT_THANKS_QUIET"),
    ("S2", "D2_internal_check"): _TDef("S7", "RT_THANKS_QUIET"),
    ("S2", "D3_name_request"): _TDef("S6", "RT_NAME_AND_PURPOSE"),
    ("S2", "E1_absent"): _TDef("S9", "RT_ASK_CALLBACK_SLOT"),
    ("S2", "E2_busy"): _TDef("S9", "RT_ASK_CALLBACK_SLOT"),
    # S3 ─────────────────────────────────────────────────────────────────────
    ("S3", "EV_HUMAN_RESPONDED"): _TDef("S2", side_effects=("wait_for_reception_reply",)),
    ("S3", "C1_hard_reject"): _TDef("S4"),
    ("S3", "C2_soft_reject"): _TDef("S4"),
    ("S3", "C3_policy_block"): _TDef("S4"),
    ("S3", "D1_hold"): _TDef("S7", "RT_THANKS_QUIET"),
    ("S3", "D2_internal_check"): _TDef("S7", "RT_THANKS_QUIET"),
    ("S3", "D3_name_request"): _TDef("S6", "RT_NAME_AND_PURPOSE"),
    ("S3", "E1_absent"): _TDef("S9", "RT_ASK_CALLBACK_SLOT"),
    ("S3", "E2_busy"): _TDef("S9", "RT_ASK_CALLBACK_SLOT"),
    # S4 ─────────────────────────────────────────────────────────────────────
    ("S4", "EV_HUMAN_RESPONDED"): _TDef("S5", "RT_REBUTTAL_BY_C_TYPE"),
    # S5 ─────────────────────────────────────────────────────────────────────
    ("S5", "A1_listening"): _TDef("S6", "RT_THANKS_AND_TRANSFER"),
    ("S5", "D1_hold"): _TDef("S7", "RT_THANKS_QUIET"),
    ("S5", "D2_internal_check"): _TDef("S7", "RT_THANKS_QUIET"),
    ("S5", "D3_name_request"): _TDef("S6", "RT_NAME_AND_PURPOSE"),
    ("S5", "C1_hard_reject"): _TDef("S11", "RT_POLITE_CLOSE", ("outcome=OUT_REJECTED",)),
    ("S5", "C2_soft_reject"): _TDef("S11", "RT_POLITE_CLOSE", ("outcome=OUT_REJECTED",)),
    ("S5", "C3_policy_block"): _TDef("S11", "RT_POLITE_CLOSE", ("outcome=OUT_REJECTED",)),
    # S6 ─────────────────────────────────────────────────────────────────────
    ("S6", "EV_HUMAN_RESPONDED"): _TDef("S7"),
    # S7 ─────────────────────────────────────────────────────────────────────
    ("S7", "EV_TRANSFER_DONE"): _TDef("S8", side_effects=("outcome=OUT_CONNECTED",)),
    ("S7", "E1_absent"): _TDef("S9"),
    ("S7", "E2_busy"): _TDef("S9"),
    # S8 ─────────────────────────────────────────────────────────────────────
    ("S8", "EV_HANGUP"): _TDef("S11", side_effects=("outcome=OUT_CONNECTED",)),
    # S9 ─────────────────────────────────────────────────────────────────────
    ("S9", "E3_schedule"): _TDef("S10", "RT_CONFIRM_SCHEDULE", ("record:callback_at",)),
    ("S9", "EV_HUMAN_RESPONDED"): _TDef("S11", side_effects=("outcome=OUT_ABSENT",)),
    # S10 ────────────────────────────────────────────────────────────────────
    ("S10", "EV_HUMAN_RESPONDED"): _TDef(
        "S11", side_effects=("outcome=OUT_ABSENT", "schedule_callback")
    ),
}

#: State-level timeout values (seconds) — spec §5.2
STATE_TIMEOUTS: dict[str, int] = {
    "S1": 30,
    "S2": 12,
    "S3": 15,
    "S5": 12,
    "S6": 10,
    "S7": 60,
    "S9": 20,
}

_MAX_UNCLEAR_COUNT: int = 3
_SILENCE_THRESHOLD_MS: int = 8_000


# ---------------------------------------------------------------------------
# Public result type
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Transition:
    """Result of a single :meth:`StateMachine.send` call.

    All fields map 1-to-1 to the ``state_transitions`` table columns defined
    in spec §7.
    """

    session_id: str
    seq: int
    from_state: str
    to_state: str
    input_kind: str
    input_id: str
    response_template_id: str | None
    side_effects: tuple[str, ...]
    mode: str
    at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    extra: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TerminatedError(Exception):
    """Raised when :meth:`StateMachine.send` is called after S11."""


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------


class StateMachine:
    """Reception breakthrough call state machine.

    Args:
        session_id: UUID of the active call session.  Used as the foreign key
            in ``state_transitions`` rows.
        mode: ``"AI"`` or ``"HUMAN"``.  Does **not** change transition logic.
        conn: Optional SQLite connection.  When provided every transition is
            persisted to ``state_transitions``.  Pass ``None`` for in-memory
            operation (e.g. unit tests).
        logger: Structured logger.  Defaults to the module logger.
    """

    def __init__(
        self,
        session_id: str,
        mode: str = "AI",
        conn: sqlite3.Connection | None = None,
        logger: Logger | None = None,
    ) -> None:
        self._session_id = session_id
        self._mode = mode
        self._conn = conn
        self._log = logger or get_logger(__name__)
        self._state = "S0"
        self._seq = 0
        self._unclear_count = 0
        self._silence_ms = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def state(self) -> str:
        """Current state_id."""
        return self._state

    @property
    def unclear_count(self) -> int:
        """Consecutive ``F1_unclear`` count (resets on any other input)."""
        return self._unclear_count

    @property
    def silence_ms(self) -> int:
        """Accumulated silence in milliseconds (resets when threshold reached)."""
        return self._silence_ms

    def send(self, input_id: str, silence_ms: int = 1_000) -> Transition:
        """Apply *input_id* to the current state and return the Transition.

        Args:
            input_id: An intent_id (e.g. ``"A1_listening"``) or event_id
                (e.g. ``"EV_DIALED"``).
            silence_ms: Only used when ``input_id == "F2_silence"``.
                Specifies how many milliseconds of silence to accumulate
                (default 1000 ms).

        Returns:
            A :class:`Transition` describing the state change.

        Raises:
            TerminatedError: If the session is already in ``S11``.
        """
        if self._state == "S11":
            raise TerminatedError(
                f"session={self._session_id} is already terminated (S11)"
            )

        # ── Exception inputs: applied before table lookup UNLESS a specific
        # table entry exists for (current_state, input_id).  E.g. S8+EV_HANGUP
        # must resolve to OUT_CONNECTED, not the generic OUT_NOISE (§4.3 vs §4.3 任意).
        if input_id in ("EV_HANGUP", "EV_TIMEOUT"):
            tdef = _TRANSITIONS.get((self._state, input_id))
            if tdef:
                return self._apply_tdef(input_id, _input_kind(input_id), tdef)
            return self._terminate(input_id, _input_kind(input_id), "OUT_NOISE")

        if input_id == "F3_disconnect":
            return self._terminate(input_id, _KIND_INTENT, "OUT_NOISE")

        if input_id == "F1_unclear":
            return self._handle_unclear()

        if input_id == "F2_silence":
            return self._handle_silence(silence_ms)

        # ── Normal table lookup
        tdef = _TRANSITIONS.get((self._state, input_id))
        if tdef is None:
            self._log.warn(
                "undefined_transition",
                session_id=self._session_id,
                from_state=self._state,
                input_id=input_id,
            )
            return self._handle_unclear()

        return self._apply_tdef(input_id, _input_kind(input_id), tdef)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _apply_tdef(
        self,
        input_id: str,
        input_kind: str,
        tdef: _TDef,
        extra: dict | None = None,
    ) -> Transition:
        from_state = self._state
        self._state = tdef.to_state
        self._unclear_count = 0  # reset on any successful transition
        self._seq += 1

        t = Transition(
            session_id=self._session_id,
            seq=self._seq,
            from_state=from_state,
            to_state=tdef.to_state,
            input_kind=input_kind,
            input_id=input_id,
            response_template_id=tdef.response_template_id,
            side_effects=tdef.side_effects,
            mode=self._mode,
            extra=extra or {},
        )
        self._persist(t)
        return t

    def _terminate(
        self, input_id: str, input_kind: str, outcome: str
    ) -> Transition:
        return self._apply_tdef(
            input_id,
            input_kind,
            _TDef("S11", side_effects=(f"outcome={outcome}",)),
        )

    def _handle_unclear(self) -> Transition:
        self._unclear_count += 1
        extra = {"unclear_count": self._unclear_count}

        if self._unclear_count >= _MAX_UNCLEAR_COUNT:
            self._unclear_count = 0
            return self._terminate("F1_unclear", _KIND_INTENT, "OUT_NOISE")

        # Stay in same state
        from_state = self._state
        self._seq += 1
        t = Transition(
            session_id=self._session_id,
            seq=self._seq,
            from_state=from_state,
            to_state=from_state,
            input_kind=_KIND_INTENT,
            input_id="F1_unclear",
            response_template_id="RT_RETRY_PROMPT",
            side_effects=(),
            mode=self._mode,
            extra=extra,
        )
        self._persist(t)
        return t

    def _handle_silence(self, silence_ms: int) -> Transition:
        self._silence_ms += silence_ms
        extra = {"silence_ms": self._silence_ms}

        if self._silence_ms >= _SILENCE_THRESHOLD_MS:
            self._silence_ms = 0
            return self._terminate("F2_silence", _KIND_INTENT, "OUT_NOISE")

        from_state = self._state
        self._seq += 1
        t = Transition(
            session_id=self._session_id,
            seq=self._seq,
            from_state=from_state,
            to_state=from_state,
            input_kind=_KIND_INTENT,
            input_id="F2_silence",
            response_template_id=None,
            side_effects=(),
            mode=self._mode,
            extra=extra,
        )
        self._persist(t)
        return t

    def _persist(self, t: Transition) -> None:
        if self._conn is None:
            return
        extra_json = json.dumps(t.extra, ensure_ascii=False) if t.extra else None
        self._conn.execute(
            """
            INSERT INTO state_transitions
              (id, session_id, seq, from_state, to_state, input_kind, input_id,
               response_template_id, at, mode, extra_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                t.session_id,
                t.seq,
                t.from_state,
                t.to_state,
                t.input_kind,
                t.input_id,
                t.response_template_id,
                t.at.isoformat(),
                t.mode,
                extra_json,
            ),
        )
