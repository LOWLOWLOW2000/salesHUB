"""Response text builder for the reception breakthrough module.

Implements spec §3 and §3.1 of intent-improvement-spec.md.

Responsibilities:
  - Map ``response_template_id`` → rendered text using YAML template config.
  - Apply suffix rotation per session (so the same session always hears the
    same variant, but different sessions get different ones).
  - Validate that every generated text ends with an "action request" suffix.
  - Handle the ``RT_REBUTTAL_BY_C_TYPE`` routing (delegates to
    ``RT_REBUTTAL_C1/C2/C3`` based on the last C-series intent).

The YAML config path is injectable for testing.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_DEFAULT_TEMPLATES_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "response_templates.yaml"
)

# ── Result type ───────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class BuildResult:
    """Output of :meth:`ResponseBuilder.build`.

    Args:
        template_id: The resolved template ID (e.g. ``"RT_REBUTTAL_C2"``).
        variant_id: Letter of the variant actually used (``"A"``, ``"B"``, ``"C"``).
        text: The fully rendered response string.
        template_variant_id: Composite key ``<template_id>/<variant_id>`` for
            A/B logging.
    """

    template_id: str
    variant_id: str
    text: str
    template_variant_id: str


# ── Exceptions ────────────────────────────────────────────────────────────────


class TemplateNotFoundError(KeyError):
    """Raised when the requested template_id does not exist in the config."""


class InvalidTemplateError(ValueError):
    """Raised when a template's generated text fails action-request validation."""


# ── Builder ───────────────────────────────────────────────────────────────────


class ResponseBuilder:
    """Build response texts from template IDs with suffix rotation.

    Args:
        config_path: Path to the YAML response templates config.  Defaults to
            ``data/response_templates.yaml``.
    """

    def __init__(
        self, config_path: str | Path = _DEFAULT_TEMPLATES_PATH
    ) -> None:
        self._config = self._load_config(Path(config_path))
        self._action_suffixes: list[str] = (
            self._config.get("validation", {}).get("action_request_suffixes", [])
        )

    # ── Public ───────────────────────────────────────────────────────────────

    def build(
        self,
        template_id: str,
        session_id: str,
        last_c_intent: str | None = None,
    ) -> BuildResult:
        """Render *template_id* to a response string.

        Args:
            template_id: One of the ``RT_*`` IDs defined in the YAML config.
            session_id: Used to deterministically pick a variant so the same
                session always receives the same variant (§3.1).
            last_c_intent: Only required when *template_id* is
                ``RT_REBUTTAL_BY_C_TYPE``.  Must be one of ``C1_hard_reject``,
                ``C2_soft_reject``, ``C3_policy_block``.

        Returns:
            A :class:`BuildResult` with the rendered text and variant metadata.

        Raises:
            TemplateNotFoundError: If *template_id* is not in the config.
            InvalidTemplateError: If the rendered text does not end with an
                action-request suffix (spec §3 末注).
        """
        resolved_id = self._resolve_id(template_id, last_c_intent)
        tmpl = self._config.get(resolved_id)
        if tmpl is None:
            raise TemplateNotFoundError(
                f"template_id={resolved_id!r} not found in config"
            )

        variants: list[dict] = tmpl.get("variants", [])
        base: str = tmpl.get("base", "")

        if not variants:
            text = base
            variant_id = "A"
        else:
            variant = self._pick_variant(variants, session_id, resolved_id)
            variant_id = variant.get("id", "A")
            suffix = variant.get("suffix", "")
            text = base + suffix

        if tmpl.get("validate", True):
            self._validate_action_request(resolved_id, text)

        return BuildResult(
            template_id=resolved_id,
            variant_id=variant_id,
            text=text,
            template_variant_id=f"{resolved_id}/{variant_id}",
        )

    def all_template_ids(self) -> list[str]:
        """Return all RT_* template IDs defined in the config (for testing)."""
        return [k for k in self._config if k.startswith("RT_")]

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _load_config(self, path: Path) -> dict[str, Any]:
        with path.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _resolve_id(self, template_id: str, last_c_intent: str | None) -> str:
        """Route RT_REBUTTAL_BY_C_TYPE → the concrete rebuttal template."""
        if template_id != "RT_REBUTTAL_BY_C_TYPE":
            return template_id

        routing: dict[str, str] = {
            "C1_hard_reject": "RT_REBUTTAL_C1",
            "C2_soft_reject": "RT_REBUTTAL_C2",
            "C3_policy_block": "RT_REBUTTAL_C3",
        }
        if last_c_intent is None or last_c_intent not in routing:
            return "RT_REBUTTAL_C1"  # safe default

        return routing[last_c_intent]

    def _pick_variant(
        self, variants: list[dict], session_id: str, template_id: str
    ) -> dict:
        """Pick a variant deterministically by hashing session_id + template_id.

        Same session always gets the same variant (§3.1); different sessions
        get uniformly distributed variants.
        """
        key = f"{session_id}:{template_id}"
        index = int(hashlib.md5(key.encode()).hexdigest(), 16) % len(variants)
        return variants[index]

    def _validate_action_request(self, template_id: str, text: str) -> None:
        """Raise InvalidTemplateError if *text* does not end with an action request.

        Validation is skipped for templates with empty text (e.g. RT_THANKS_QUIET
        variant A, RT_NAME_AND_PURPOSE variant A) since silence / acknowledgement
        is intentional.
        """
        stripped = text.strip()
        if not stripped:
            return  # empty text is allowed (e.g. pure silence cue)

        if not self._action_suffixes:
            return  # no validation config — skip

        if not any(stripped.endswith(sfx) for sfx in self._action_suffixes):
            raise InvalidTemplateError(
                f"template_id={template_id!r} generated text does not end with "
                f"an action-request suffix: {stripped!r}"
            )
