"""Orchestrator for a single call session.

Wires together :class:`~core.state_machine.StateMachine`,
:class:`~core.intent_classifier.IntentClassifier`, and
:class:`~core.response_builder.ResponseBuilder` for one end-to-end call.

Entry points
------------
:meth:`CallController.step`
    Feed a pre-classified *intent_id* or *event_id* and receive the response
    text (if any) plus the :class:`~core.state_machine.Transition`.

:meth:`CallController.classify_and_step`
    Feed raw receptionist utterance text — the controller runs the classifier
    first, then feeds the result to the state machine.

:meth:`CallController.run`
    Drive the session through a list of inputs and return all transitions.
    Useful for scripted scenario tests.

Persistence
-----------
When a SQLite connection is supplied the controller writes:

* ``call_sessions`` — one row created on construction, updated on termination.
* ``state_transitions`` — one row per :meth:`step` (delegated to SM).
* ``outcomes`` — one row written when the session reaches ``S11``.

Passing ``conn=None`` runs entirely in memory (useful for unit tests).
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterator, Sequence

from core.intent_classifier import IntentClassifier
from core.response_builder import BuildResult, ResponseBuilder
from core.state_machine import StateMachine, TerminatedError, Transition
from infra.logging.logger import Logger, bind_session, get_logger

try:
    import sqlite3 as _sqlite3
    _Connection = _sqlite3.Connection
except ImportError:  # pragma: no cover
    _Connection = object  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Result type for one step
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class StepResult:
    """Outcome of a single :meth:`CallController.step` call.

    Args:
        transition: State machine transition that was applied.
        classifier_intent: Intent chosen by the classifier (``None`` if the
            input was a pre-labelled intent_id or event_id).
        classifier_confidence: Confidence of the classification (0.0 when N/A).
        response: Response built from the template, or ``None`` if no template
            was associated with this transition.
        is_terminated: ``True`` when the session has reached ``S11``.
        outcome_id: Final outcome code (non-``None`` only when ``is_terminated``).
    """

    transition: Transition
    classifier_intent: str | None
    classifier_confidence: float
    response: BuildResult | None
    is_terminated: bool
    outcome_id: str | None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_OUTCOME_SIDE_EFFECT_RE = re.compile(r"outcome=(\w+)")


def _extract_outcome(side_effects: tuple[str, ...]) -> str | None:
    for effect in side_effects:
        m = _OUTCOME_SIDE_EFFECT_RE.match(effect)
        if m:
            return m.group(1)
    return None


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------


class CallController:
    """Orchestrator for one reception-breakthrough call session.

    Args:
        lead_id: The CRM lead identifier.  Stored in ``call_sessions`` but the
            controller does not call the CRM adapter directly — the caller is
            responsible for locking the lead and writing the final result.
        mode: ``"AI"`` or ``"HUMAN"``.  Propagated to every state_transitions
            row as a logging tag; does not change transition logic.
        session_id: Optional explicit session UUID.  Generated if omitted.
        conn: SQLite connection for persistence.  Pass ``None`` for in-memory.
        classifier: :class:`~core.intent_classifier.IntentClassifier` instance.
            A default instance (using the project-level YAML) is created if
            omitted.
        builder: :class:`~core.response_builder.ResponseBuilder` instance.
            A default instance is created if omitted.
        logger: Structured logger.  Defaults to the module logger.
    """

    def __init__(
        self,
        lead_id: str,
        mode: str = "AI",
        session_id: str | None = None,
        conn: _Connection | None = None,
        classifier: IntentClassifier | None = None,
        builder: ResponseBuilder | None = None,
        logger: Logger | None = None,
    ) -> None:
        self._lead_id = lead_id
        self._mode = mode
        self._session_id = session_id or str(uuid.uuid4())
        self._conn = conn
        self._classifier = classifier or IntentClassifier()
        self._builder = builder or ResponseBuilder()
        self._log = logger or get_logger(__name__)

        # MDC: every log line from this thread will carry session_id
        bind_session(self._session_id)

        self._sm = StateMachine(
            session_id=self._session_id,
            mode=mode,
            conn=conn,
            logger=self._log,
        )

        # Track last C-series intent for RT_REBUTTAL_BY_C_TYPE routing
        self._last_c_intent: str | None = None

        # Final outcome — set once when S11 is reached
        self._outcome_id: str | None = None

        self._started_at = _now_iso()
        self._persist_session_start()

    # ── Properties ──────────────────────────────────────────────────────────

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def state(self) -> str:
        return self._sm.state

    @property
    def outcome_id(self) -> str | None:
        """Final outcome code, available after the session reaches ``S11``."""
        return self._outcome_id

    @property
    def is_terminated(self) -> bool:
        return self._sm.state == "S11"

    # ── Public entry points ──────────────────────────────────────────────────

    def step(self, input_id: str) -> StepResult:
        """Apply a pre-labelled *input_id* (intent or event) to the session.

        Args:
            input_id: An ``intent_id`` (e.g. ``"C2_soft_reject"``) or
                ``event_id`` (e.g. ``"EV_DIALED"``).

        Returns:
            A :class:`StepResult` with the transition, optional response, and
            termination flag.

        Raises:
            TerminatedError: If the session is already in ``S11``.
        """
        return self._apply(input_id, classifier_intent=None, confidence=0.0)

    def classify_and_step(self, utterance: str) -> StepResult:
        """Classify *utterance* then feed the result into the state machine.

        If the classifier confidence is below threshold (returns ``F1_unclear``),
        ``F1_unclear`` is forwarded to the SM directly.

        Args:
            utterance: Raw receptionist speech text.

        Returns:
            A :class:`StepResult`.  ``classifier_intent`` and
            ``classifier_confidence`` are always populated.
        """
        result = self._classifier.classify(utterance)
        return self._apply(
            result.intent_id,
            classifier_intent=result.intent_id,
            confidence=result.confidence,
        )

    def run(self, inputs: Sequence[str]) -> list[StepResult]:
        """Drive the session through a sequence of *inputs* and return all steps.

        Stops early if the session reaches ``S11`` before the sequence ends.

        Args:
            inputs: Ordered list of intent_id / event_id strings.

        Returns:
            List of :class:`StepResult`, one per input consumed.
        """
        results: list[StepResult] = []
        for inp in inputs:
            results.append(self.step(inp))
            if self.is_terminated:
                break
        return results

    def run_text(self, utterances: Sequence[str]) -> list[StepResult]:
        """Like :meth:`run` but each item is raw text passed through the classifier."""
        results: list[StepResult] = []
        for text in utterances:
            results.append(self.classify_and_step(text))
            if self.is_terminated:
                break
        return results

    # ── Internal ────────────────────────────────────────────────────────────

    def _apply(
        self,
        input_id: str,
        classifier_intent: str | None,
        confidence: float,
    ) -> StepResult:
        transition = self._sm.send(input_id)

        # Track last C intent for rebuttal routing
        if input_id.startswith("C"):
            self._last_c_intent = input_id

        # Build response text if a template is attached
        response: BuildResult | None = None
        rt_id = transition.response_template_id
        if rt_id:
            try:
                response = self._builder.build(
                    rt_id,
                    session_id=self._session_id,
                    last_c_intent=self._last_c_intent,
                )
            except Exception as exc:  # noqa: BLE001
                self._log.error(
                    "response_build_failed",
                    template_id=rt_id,
                    error=str(exc),
                )

        # Determine and persist outcome when session terminates
        outcome: str | None = None
        if transition.to_state == "S11":
            outcome = _extract_outcome(transition.side_effects) or "OUT_NOISE"
            self._outcome_id = outcome
            self._persist_outcome(transition, outcome)
            self._persist_session_end(transition)

        self._log.info(
            "step",
            from_state=transition.from_state,
            to_state=transition.to_state,
            input_id=input_id,
            template_id=rt_id,
            outcome=outcome,
        )

        return StepResult(
            transition=transition,
            classifier_intent=classifier_intent,
            classifier_confidence=confidence,
            response=response,
            is_terminated=transition.to_state == "S11",
            outcome_id=outcome,
        )

    # ── DB persistence ───────────────────────────────────────────────────────

    def _persist_session_start(self) -> None:
        if self._conn is None:
            return
        self._conn.execute(
            """
            INSERT INTO call_sessions (id, lead_id, mode, started_at)
            VALUES (?, ?, ?, ?)
            """,
            (self._session_id, self._lead_id, self._mode, self._started_at),
        )
        self._conn.commit()

    def _persist_session_end(self, last_transition: Transition) -> None:
        if self._conn is None:
            return
        ended_at = _now_iso()
        self._conn.execute(
            """
            UPDATE call_sessions
               SET ended_at = ?,
                   final_state_id = ?,
                   outcome_id = ?,
                   rejection_reason = ?,
                   updated_at = ?
             WHERE id = ?
            """,
            (
                ended_at,
                last_transition.to_state,
                self._outcome_id,
                self._last_c_intent,  # rejection_reason = last C-series intent
                ended_at,
                self._session_id,
            ),
        )
        self._conn.commit()

    def _persist_outcome(
        self, last_transition: Transition, outcome_id: str
    ) -> None:
        if self._conn is None:
            return
        self._conn.execute(
            """
            INSERT INTO outcomes
              (id, session_id, outcome_id, final_state_id,
               rejection_reason, last_input_kind, last_input_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                self._session_id,
                outcome_id,
                last_transition.from_state,  # state just before S11
                self._last_c_intent,
                last_transition.input_kind,
                last_transition.input_id,
            ),
        )
        self._conn.commit()
