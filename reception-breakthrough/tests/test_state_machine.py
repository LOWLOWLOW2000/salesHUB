"""Tests for core.state_machine (T-200).

Coverage strategy:
- Table-driven: one parametrised case per row in _TRANSITIONS (§4 normal transitions)
- Exception transitions: F1_unclear / F2_silence / F3_disconnect / EV_TIMEOUT / EV_HANGUP
- unclear_count >= 3 → S11 (OUT_NOISE)
- silence accumulation → S11 (OUT_NOISE)
- undefined (state, input) → stays in state + WARN log
- S11 terminal guard → TerminatedError
- DB persistence smoke test
"""

from __future__ import annotations

import io

import pytest

from core.state_machine import (
    STATE_TIMEOUTS,
    StateMachine,
    TerminatedError,
    Transition,
    _TRANSITIONS,
)
from infra.db.local_db import get_connection
from infra.logging.logger import get_logger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sm(state: str = "S0", mode: str = "AI") -> StateMachine:
    """Return a StateMachine with its internal state preset."""
    sm = StateMachine(session_id="test-session", mode=mode)
    sm._state = state  # noqa: SLF001  (direct access for testing)
    return sm


def _advance_to(sm: StateMachine, *inputs: str) -> Transition:
    """Drive the SM through a sequence of inputs; return the last Transition."""
    t = None
    for inp in inputs:
        t = sm.send(inp)
    assert t is not None
    return t


# ---------------------------------------------------------------------------
# Table-driven: every row in _TRANSITIONS
# ---------------------------------------------------------------------------

_NORMAL_CASES = [
    (from_state, input_id, tdef.to_state, tdef.response_template_id)
    for (from_state, input_id), tdef in _TRANSITIONS.items()
]


@pytest.mark.parametrize(
    "from_state, input_id, expected_to, expected_rt",
    _NORMAL_CASES,
    ids=[f"{fs}+{inp}" for (fs, inp) in _TRANSITIONS],
)
def test_normal_transition(
    from_state: str,
    input_id: str,
    expected_to: str,
    expected_rt: str | None,
) -> None:
    sm = _sm(from_state)
    t = sm.send(input_id)

    assert t.from_state == from_state
    assert t.to_state == expected_to
    assert t.response_template_id == expected_rt
    assert sm.state == expected_to


# ---------------------------------------------------------------------------
# State timeout table completeness
# ---------------------------------------------------------------------------


def test_state_timeouts_exist_for_expected_states() -> None:
    expected = {"S1", "S2", "S3", "S5", "S6", "S7", "S9"}
    assert set(STATE_TIMEOUTS.keys()) == expected
    assert all(v > 0 for v in STATE_TIMEOUTS.values())


# ---------------------------------------------------------------------------
# Exception transitions — §5
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("from_state", ["S0", "S2", "S3", "S5", "S7"])
def test_ev_hangup_terminates_from_any_state(from_state: str) -> None:
    sm = _sm(from_state)
    t = sm.send("EV_HANGUP")
    assert t.to_state == "S11"
    assert sm.state == "S11"
    assert "outcome=OUT_NOISE" in t.side_effects


@pytest.mark.parametrize("from_state", ["S1", "S2", "S3", "S7"])
def test_ev_timeout_terminates_from_any_state(from_state: str) -> None:
    sm = _sm(from_state)
    t = sm.send("EV_TIMEOUT")
    assert t.to_state == "S11"
    assert "outcome=OUT_NOISE" in t.side_effects


def test_f3_disconnect_terminates() -> None:
    sm = _sm("S3")
    t = sm.send("F3_disconnect")
    assert t.to_state == "S11"
    assert "outcome=OUT_NOISE" in t.side_effects


# ---------------------------------------------------------------------------
# F1_unclear — stays in state; terminates after 3 consecutive
# ---------------------------------------------------------------------------


def test_f1_unclear_stays_in_state() -> None:
    sm = _sm("S2")
    t = sm.send("F1_unclear")
    assert t.from_state == "S2"
    assert t.to_state == "S2"
    assert t.response_template_id == "RT_RETRY_PROMPT"
    assert sm.unclear_count == 1


def test_f1_unclear_count_three_terminates() -> None:
    sm = _sm("S2")
    sm.send("F1_unclear")  # count=1
    sm.send("F1_unclear")  # count=2
    t = sm.send("F1_unclear")  # count=3 → S11
    assert t.to_state == "S11"
    assert "outcome=OUT_NOISE" in t.side_effects
    assert sm.state == "S11"


def test_f1_unclear_count_resets_on_valid_input() -> None:
    sm = _sm("S2")
    sm.send("F1_unclear")
    sm.send("F1_unclear")
    # Valid input resets count
    sm.send("A1_listening")
    assert sm.unclear_count == 0
    # Another unclear — count starts from 1 again
    sm._state = "S2"  # reset for test
    sm.send("F1_unclear")
    assert sm.unclear_count == 1


# ---------------------------------------------------------------------------
# F2_silence — accumulates; terminates at ≥ 8000 ms
# ---------------------------------------------------------------------------


def test_f2_silence_accumulates_below_threshold() -> None:
    sm = _sm("S2")
    t = sm.send("F2_silence", silence_ms=3_000)
    assert t.to_state == "S2"
    assert sm.silence_ms == 3_000


def test_f2_silence_terminates_at_threshold() -> None:
    sm = _sm("S2")
    sm.send("F2_silence", silence_ms=5_000)
    t = sm.send("F2_silence", silence_ms=3_000)  # total = 8000
    assert t.to_state == "S11"
    assert "outcome=OUT_NOISE" in t.side_effects
    assert sm.state == "S11"


def test_f2_silence_multiple_small_steps_accumulate() -> None:
    sm = _sm("S3")
    for _ in range(7):
        t = sm.send("F2_silence", silence_ms=1_000)
        assert t.to_state == "S3"
    t = sm.send("F2_silence", silence_ms=1_000)  # total = 8000
    assert t.to_state == "S11"


# ---------------------------------------------------------------------------
# Undefined (state, input) → treated as F1_unclear + WARN log
# ---------------------------------------------------------------------------


def test_undefined_transition_emits_warn_and_stays() -> None:
    sink = io.StringIO()
    log = get_logger("test_undef", sink=sink)
    sm = StateMachine("sess-undef", conn=None, logger=log)
    sm._state = "S2"

    t = sm.send("TOTALLY_UNKNOWN_INPUT")

    assert t.to_state == "S2"  # treated as F1_unclear → stay
    log_output = sink.getvalue()
    assert "undefined_transition" in log_output
    assert "WARN" in log_output


# ---------------------------------------------------------------------------
# S11 terminal guard
# ---------------------------------------------------------------------------


def test_send_after_s11_raises_terminated_error() -> None:
    sm = _sm("S5")
    sm.send("C1_hard_reject")  # → S11
    assert sm.state == "S11"
    with pytest.raises(TerminatedError):
        sm.send("EV_HANGUP")


# ---------------------------------------------------------------------------
# Sequence counter
# ---------------------------------------------------------------------------


def test_seq_increments_with_each_transition() -> None:
    sm = StateMachine("sess-seq")
    sm._state = "S1"
    t1 = sm.send("EV_PICKED_UP")
    t2 = sm.send("A1_listening")
    assert t1.seq == 1
    assert t2.seq == 2


# ---------------------------------------------------------------------------
# Mode field propagation
# ---------------------------------------------------------------------------


def test_mode_is_recorded_in_transition() -> None:
    sm = StateMachine("sess-mode", mode="HUMAN")
    sm._state = "S2"
    t = sm.send("A1_listening")
    assert t.mode == "HUMAN"


# ---------------------------------------------------------------------------
# DB persistence smoke test
# ---------------------------------------------------------------------------


def test_transitions_are_persisted_to_db() -> None:
    with get_connection(":memory:") as conn:
        conn.execute(
            "INSERT INTO call_sessions (id, lead_id, mode, started_at) VALUES (?,?,?,?)",
            ("sess-db", "lead-1", "AI", "2026-05-05T00:00:00"),
        )
        sm = StateMachine("sess-db", mode="AI", conn=conn)
        sm._state = "S1"
        sm.send("EV_PICKED_UP")
        sm.send("A1_listening")
        sm.send("D3_name_request")

        rows = conn.execute(
            "SELECT seq, from_state, to_state, input_id FROM state_transitions "
            "WHERE session_id = ? ORDER BY seq",
            ("sess-db",),
        ).fetchall()

    assert len(rows) == 3
    assert rows[0]["from_state"] == "S1"
    assert rows[0]["to_state"] == "S2"
    assert rows[1]["to_state"] == "S3"
    assert rows[2]["to_state"] == "S6"


# ---------------------------------------------------------------------------
# Scenario tests matching T-203 DoD (end-to-end trace through SM only)
# ---------------------------------------------------------------------------


def test_scenario_connected() -> None:
    """S2 → A1 → S3 → D3 → S6 → EV_HR → S7 → EV_TD → S8 → EV_HANGUP → S11 OUT_CONNECTED."""
    sm = StateMachine("sess-connected")
    sm._state = "S2"
    _advance_to(sm, "A1_listening", "D3_name_request", "EV_HUMAN_RESPONDED",
                "EV_TRANSFER_DONE", "EV_HANGUP")
    assert sm.state == "S11"


def test_scenario_rejected() -> None:
    """S2 → B1 → S3 → C2 → S4 → EV_HR → S5 → C2 → S11 OUT_REJECTED."""
    sm = StateMachine("sess-rejected")
    sm._state = "S2"
    t = _advance_to(
        sm,
        "B1_simple_purpose",
        "C2_soft_reject",
        "EV_HUMAN_RESPONDED",
        "C2_soft_reject",
    )
    assert sm.state == "S11"
    assert "outcome=OUT_REJECTED" in t.side_effects


def test_scenario_absent() -> None:
    """S2 → E1 → S9 → E3 → S10 → EV_HR → S11 OUT_ABSENT."""
    sm = StateMachine("sess-absent")
    sm._state = "S2"
    t = _advance_to(sm, "E1_absent", "E3_schedule", "EV_HUMAN_RESPONDED")
    assert sm.state == "S11"
    assert "outcome=OUT_ABSENT" in t.side_effects
