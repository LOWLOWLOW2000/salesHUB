"""Rule-based intent classifier for reception utterances.

Implements spec §2–§4 of docs/reception-breakthrough/intent-improvement-spec.md.

Classification pipeline (Phase 1 — rule-based only):
  1. Text matching against keyword dict loaded from ``data/intent_keywords.yaml``
  2. C2 sentence-pattern boost (reason-suffix patterns, §4.2)
  3. Conflict resolution (§4.4): C1 > C2 > others; question form → B1
  4. Confidence threshold: below ``thresholds.f1_fallback`` → ``F1_unclear``

The YAML config path is injectable so tests can supply fixtures without
touching the project-level file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_DEFAULT_KEYWORDS_PATH = Path(__file__).resolve().parents[1] / "data" / "intent_keywords.yaml"

# ── Result type ───────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ClassifierResult:
    """Output of a single classification call.

    Args:
        intent_id: The winning intent label.
        confidence: Float in [0, 1].  Below the configured threshold the SM
            should treat this as ``F1_unclear``.
        matched_keywords: Keywords that triggered the classification (for logs).
    """

    intent_id: str
    confidence: float
    matched_keywords: tuple[str, ...]


# ── Classifier ────────────────────────────────────────────────────────────────


class IntentClassifier:
    """Classify a single receptionist utterance into one intent_id.

    Args:
        config_path: Path to the YAML keyword config.  Defaults to
            ``data/intent_keywords.yaml`` relative to the project root.
    """

    def __init__(
        self, config_path: str | Path = _DEFAULT_KEYWORDS_PATH
    ) -> None:
        self._config = self._load_config(Path(config_path))
        self._thresholds: dict[str, Any] = self._config.get("thresholds", {})
        self._fallback_threshold: float = float(
            self._thresholds.get("f1_fallback", 0.60)
        )
        self._question_marks: list[str] = self._thresholds.get(
            "question_marks", ["？", "?", "でしょうか", "ますか", "ませんか"]
        )
        self._c2_reason_patterns: list[re.Pattern] = [
            re.compile(p)
            for p in self._config.get("C2_reason_suffix_patterns", [])
        ]

    # ── Public ───────────────────────────────────────────────────────────────

    def classify(self, text: str) -> ClassifierResult:
        """Classify *text* and return a :class:`ClassifierResult`.

        Args:
            text: A single receptionist utterance (plain text, stripped).

        Returns:
            :class:`ClassifierResult` with ``intent_id`` and ``confidence``.
            If confidence < threshold, callers should treat as ``F1_unclear``.
        """
        is_question = self._is_question(text)
        candidates: list[tuple[str, float, list[str]]] = []

        for intent_id in [
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
        ]:
            rule = self._config.get(intent_id)
            if rule is None:
                continue
            conf, matched = self._score(text, rule, is_question)
            if conf > 0:
                candidates.append((intent_id, conf, matched))

        if not candidates:
            return ClassifierResult("F1_unclear", 0.0, ())

        # ── Conflict resolution §4.4 ──────────────────────────────────────
        # 1. If C2 candidate and text is a question → downgrade to B1
        candidate_ids = {c[0] for c in candidates}
        if "C2_soft_reject" in candidate_ids and is_question:
            candidates = [c for c in candidates if c[0] != "C2_soft_reject"]
            if not any(c[0].startswith("B") for c in candidates):
                candidates.append(("B1_simple_purpose", 0.62, []))

        # 2. C2 boost from sentence pattern (reason suffix)
        if "C2_soft_reject" in {c[0] for c in candidates}:
            for pat in self._c2_reason_patterns:
                if pat.search(text):
                    candidates = [
                        (iid, conf + 0.10, kw) if iid == "C2_soft_reject" else (iid, conf, kw)
                        for iid, conf, kw in candidates
                    ]
                    break

        # 3. C1 > C2 when both present (spec §4.4)
        if "C1_hard_reject" in {c[0] for c in candidates} and "C2_soft_reject" in {
            c[0] for c in candidates
        }:
            candidates = [c for c in candidates if c[0] != "C2_soft_reject"]

        # 4. "結構です" alone is ambiguous C1/C2 → treat as C1 (spec §4.4)
        #    (already covered by C1 keyword; just ensure C2 is not promoted above C1)

        # ── Pick winner: highest confidence ──────────────────────────────
        candidates.sort(key=lambda c: c[1], reverse=True)
        winner_id, winner_conf, winner_kw = candidates[0]
        winner_conf = min(winner_conf, 1.0)

        if winner_conf < self._fallback_threshold:
            return ClassifierResult("F1_unclear", winner_conf, tuple(winner_kw))

        return ClassifierResult(winner_id, winner_conf, tuple(winner_kw))

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _load_config(self, path: Path) -> dict[str, Any]:
        with path.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _is_question(self, text: str) -> bool:
        """Return True if *text* contains a question marker (spec §4.1 note)."""
        return any(marker in text for marker in self._question_marks)

    def _score(
        self, text: str, rule: dict[str, Any], is_question: bool
    ) -> tuple[float, list[str]]:
        """Return (confidence, matched_keywords) for one intent rule."""
        keywords: list[str] = rule.get("keywords", [])
        exclude_if_q: bool = rule.get("exclude_if_question", False)
        base: float = float(rule.get("confidence_base", 0.60))

        if exclude_if_q and is_question:
            return 0.0, []

        matched = [kw for kw in keywords if kw in text]
        if not matched:
            return 0.0, []

        # Scale confidence by match density (up to +0.10)
        density_bonus = min(len(matched) * 0.05, 0.10)
        return base + density_bonus, matched
