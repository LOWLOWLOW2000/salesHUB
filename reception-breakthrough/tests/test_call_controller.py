"""Tests for core.call_controller (T-203).

DoD scenario tests:
  1. A1 → D3 → EV_HR → S7 → EV_TRANSFER_DONE → EV_HANGUP → OUT_CONNECTED
  2. B1 → C2 → EV_HR → S5 → C2 → S11 → OUT_REJECTED
  3. E1 → E3 → S10 → EV_HR → S11 → OUT_ABSENT

Additional:
  - classify_and_step: raw text goes through classifier → SM
  - DB persistence: call_sessions + outcomes written correctly
  - StepResult fields populated correctly
  - Termination guard: step after S11 raises TerminatedError
  - run() stops at S11 even if inputs list is longer
"""

from __future__ import annotations

import pytest

from core.call_controller import CallController, StepResult
from core.state_machine import TerminatedError
from infra.db.local_db import get_connection


# ---------------------------------------------------------------------------
# Helper: in-memory controller starting at a given state
# ---------------------------------------------------------------------------


def _ctrl(start_state: str = "S2", mode: str = "AI") -> CallController:
    ctrl = CallController(lead_id="lead-001", mode=mode, session_id="test-sess")
    ctrl._sm._state = start_state  # noqa: SLF001
    return ctrl


# ---------------------------------------------------------------------------
# Scenario 1: OUT_CONNECTED
# A1 → S3, D3 → S6, EV_HR → S7, EV_TRANSFER_DONE → S8, EV_HANGUP → S11
# ---------------------------------------------------------------------------


def test_scenario_connected_out_connected() -> None:
    ctrl = _ctrl("S2")
    steps = ctrl.run(
        ["A1_listening", "D3_name_request", "EV_HUMAN_RESPONDED",
         "EV_TRANSFER_DONE", "EV_HANGUP"]
    )

    assert ctrl.is_terminated
    assert ctrl.outcome_id == "OUT_CONNECTED"

    last = steps[-1]
    assert last.is_terminated
    assert last.outcome_id == "OUT_CONNECTED"


def test_scenario_connected_response_texts_present() -> None:
    ctrl = _ctrl("S2")
    steps = ctrl.run(["A1_listening"])
    assert steps[0].response is not None
    assert steps[0].response.template_id == "RT_ASK_TRANSFER_SHORT"


# ---------------------------------------------------------------------------
# Scenario 2: OUT_REJECTED
# B1 → S3, C2 → S4, EV_HR → S5, C2 → S11
# ---------------------------------------------------------------------------


def test_scenario_rejected_out_rejected() -> None:
    ctrl = _ctrl("S2")
    steps = ctrl.run(
        ["B1_simple_purpose", "C2_soft_reject", "EV_HUMAN_RESPONDED", "C2_soft_reject"]
    )

    assert ctrl.is_terminated
    assert ctrl.outcome_id == "OUT_REJECTED"

    last = steps[-1]
    assert last.is_terminated
    assert last.outcome_id == "OUT_REJECTED"


def test_scenario_rejected_rebuttal_response_routed() -> None:
    """RT_REBUTTAL_BY_C_TYPE must resolve to RT_REBUTTAL_C2 after C2 rejection."""
    ctrl = _ctrl("S2")
    ctrl.run(["B1_simple_purpose", "C2_soft_reject"])
    # Next: EV_HUMAN_RESPONDED should fire RT_REBUTTAL_BY_C_TYPE → RT_REBUTTAL_C2
    step = ctrl.step("EV_HUMAN_RESPONDED")
    assert step.response is not None
    assert step.response.template_id == "RT_REBUTTAL_C2"


# ---------------------------------------------------------------------------
# Scenario 3: OUT_ABSENT
# E1 → S9, E3 → S10, EV_HR → S11
# ---------------------------------------------------------------------------


def test_scenario_absent_out_absent() -> None:
    ctrl = _ctrl("S2")
    steps = ctrl.run(["E1_absent", "E3_schedule", "EV_HUMAN_RESPONDED"])

    assert ctrl.is_terminated
    assert ctrl.outcome_id == "OUT_ABSENT"

    last = steps[-1]
    assert last.is_terminated
    assert last.outcome_id == "OUT_ABSENT"


# ---------------------------------------------------------------------------
# classify_and_step — raw text path
# ---------------------------------------------------------------------------


def test_classify_and_step_routes_via_classifier() -> None:
    # C1 is defined from S3 onward (spec §4.1)
    ctrl = _ctrl("S3")
    result = ctrl.classify_and_step("営業はお断りしています")

    assert result.classifier_intent == "C1_hard_reject"
    assert result.classifier_confidence >= 0.80
    assert result.transition.to_state == "S4"


def test_classify_and_step_c2_text() -> None:
    # C2 is defined from S3 onward (spec §4.1)
    ctrl = _ctrl("S3")
    result = ctrl.classify_and_step("間に合っております")

    assert result.classifier_intent == "C2_soft_reject"
    assert result.transition.to_state == "S4"


def test_classify_and_step_unknown_falls_to_f1() -> None:
    ctrl = _ctrl("S2")
    result = ctrl.classify_and_step("xyzxyz 全くわからないテキスト αβγ")

    assert result.classifier_intent == "F1_unclear"
    assert result.transition.to_state == "S2"  # stays in state (F1_unclear)


# ---------------------------------------------------------------------------
# StepResult fields
# ---------------------------------------------------------------------------


def test_step_result_has_no_response_when_no_template() -> None:
    ctrl = _ctrl("S3")
    result = ctrl.step("C2_soft_reject")  # S3 + C2 → S4, no template

    assert result.response is None
    assert result.transition.to_state == "S4"
    assert not result.is_terminated


def test_step_result_response_variant_id_is_deterministic() -> None:
    ctrl1 = CallController(lead_id="l1", session_id="fixed-sess-1")
    ctrl1._sm._state = "S2"  # noqa: SLF001
    r1 = ctrl1.step("A1_listening")

    ctrl2 = CallController(lead_id="l1", session_id="fixed-sess-1")
    ctrl2._sm._state = "S2"  # noqa: SLF001
    r2 = ctrl2.step("A1_listening")

    assert r1.response is not None
    assert r2.response is not None
    assert r1.response.variant_id == r2.response.variant_id


# ---------------------------------------------------------------------------
# run() stops at S11 even if inputs list is longer
# ---------------------------------------------------------------------------


def test_run_stops_at_termination() -> None:
    ctrl = _ctrl("S5")
    steps = ctrl.run(["C1_hard_reject", "A1_listening", "D3_name_request"])

    assert len(steps) == 1  # S5+C1 → S11 immediately
    assert ctrl.is_terminated


# ---------------------------------------------------------------------------
# Termination guard
# ---------------------------------------------------------------------------


def test_step_after_termination_raises() -> None:
    ctrl = _ctrl("S5")
    ctrl.step("C1_hard_reject")  # → S11

    with pytest.raises(TerminatedError):
        ctrl.step("EV_HANGUP")


# ---------------------------------------------------------------------------
# HUMAN mode — same logic, different mode tag
# ---------------------------------------------------------------------------


def test_human_mode_same_outcome() -> None:
    ctrl = CallController(lead_id="l1", mode="HUMAN", session_id="human-sess")
    ctrl._sm._state = "S5"  # noqa: SLF001
    result = ctrl.step("C1_hard_reject")

    assert result.transition.mode == "HUMAN"
    assert ctrl.outcome_id == "OUT_REJECTED"


# ---------------------------------------------------------------------------
# DB persistence — call_sessions + outcomes written correctly
# ---------------------------------------------------------------------------


def test_db_call_session_created_and_outcome_written() -> None:
    with get_connection(":memory:") as conn:
        ctrl = CallController(
            lead_id="lead-db",
            mode="AI",
            session_id="sess-db-ctrl",
            conn=conn,
        )
        ctrl._sm._state = "S2"  # noqa: SLF001
        ctrl.run(["E1_absent", "E3_schedule", "EV_HUMAN_RESPONDED"])

        # call_sessions must be present and closed
        session_row = conn.execute(
            "SELECT * FROM call_sessions WHERE id = ?", ("sess-db-ctrl",)
        ).fetchone()
        assert session_row is not None
        assert session_row["outcome_id"] == "OUT_ABSENT"
        assert session_row["ended_at"] is not None

        # outcomes must have 1 row
        outcome_row = conn.execute(
            "SELECT * FROM outcomes WHERE session_id = ?", ("sess-db-ctrl",)
        ).fetchone()
        assert outcome_row is not None
        assert outcome_row["outcome_id"] == "OUT_ABSENT"


def test_db_state_transitions_written() -> None:
    with get_connection(":memory:") as conn:
        ctrl = CallController(
            lead_id="lead-st",
            mode="AI",
            session_id="sess-st-ctrl",
            conn=conn,
        )
        ctrl._sm._state = "S2"  # noqa: SLF001
        ctrl.run(["A1_listening", "D3_name_request"])

        rows = conn.execute(
            "SELECT seq, from_state, to_state FROM state_transitions "
            "WHERE session_id = ? ORDER BY seq",
            ("sess-st-ctrl",),
        ).fetchall()

        assert len(rows) == 2
        assert rows[0]["from_state"] == "S2" and rows[0]["to_state"] == "S3"
        assert rows[1]["from_state"] == "S3" and rows[1]["to_state"] == "S6"
