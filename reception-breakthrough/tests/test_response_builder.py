"""Tests for core.response_builder (T-202).

Coverage:
- All RT_* template IDs generate text without error
- RT_REBUTTAL_BY_C_TYPE routes to the correct concrete template
- Same session_id always gets the same variant (determinism)
- Different session_ids get different distributions
- All generated texts pass action-request validation
- InvalidTemplateError is raised for bad custom templates
"""

from __future__ import annotations

import io
import textwrap
from pathlib import Path

import pytest
import yaml

from core.response_builder import (
    BuildResult,
    InvalidTemplateError,
    ResponseBuilder,
    TemplateNotFoundError,
)

_builder = ResponseBuilder()


# ---------------------------------------------------------------------------
# All templates produce valid text
# ---------------------------------------------------------------------------


def test_all_template_ids_build_without_error() -> None:
    for tid in _builder.all_template_ids():
        if tid == "RT_REBUTTAL_BY_C_TYPE":
            continue  # routing template — needs last_c_intent
        result = _builder.build(tid, session_id="sess-test")
        assert isinstance(result, BuildResult)
        assert result.text  # never None
        assert result.template_id == tid
        assert result.variant_id in ("A", "B", "C")
        assert result.template_variant_id == f"{tid}/{result.variant_id}"


# ---------------------------------------------------------------------------
# RT_REBUTTAL_BY_C_TYPE routing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "c_intent, expected_resolved",
    [
        ("C1_hard_reject", "RT_REBUTTAL_C1"),
        ("C2_soft_reject", "RT_REBUTTAL_C2"),
        ("C3_policy_block", "RT_REBUTTAL_C3"),
    ],
)
def test_rebuttal_by_c_type_routes_correctly(
    c_intent: str, expected_resolved: str
) -> None:
    result = _builder.build(
        "RT_REBUTTAL_BY_C_TYPE",
        session_id="sess-route",
        last_c_intent=c_intent,
    )
    assert result.template_id == expected_resolved


def test_rebuttal_by_c_type_without_c_intent_defaults_to_c1() -> None:
    result = _builder.build("RT_REBUTTAL_BY_C_TYPE", session_id="sess-default")
    assert result.template_id == "RT_REBUTTAL_C1"


# ---------------------------------------------------------------------------
# Variant determinism — same session → same variant
# ---------------------------------------------------------------------------


def test_same_session_gets_same_variant() -> None:
    results = [
        _builder.build("RT_ASK_TRANSFER_SHORT", session_id="stable-sess")
        for _ in range(5)
    ]
    variant_ids = {r.variant_id for r in results}
    assert len(variant_ids) == 1, "same session should always pick same variant"


def test_different_sessions_may_get_different_variants() -> None:
    variants = {
        _builder.build("RT_ASK_TRANSFER_SHORT", session_id=f"sess-{i}").variant_id
        for i in range(30)
    }
    # With 3 variants and 30 sessions we expect all 3 to appear
    assert len(variants) >= 2, "expected variant distribution across sessions"


# ---------------------------------------------------------------------------
# Action-request validation
# ---------------------------------------------------------------------------


def test_action_request_validation_passes_for_all_default_templates() -> None:
    """Every built text must end with a known action-request suffix."""
    for tid in _builder.all_template_ids():
        if tid == "RT_REBUTTAL_BY_C_TYPE":
            continue
        for sess in ["s1", "s2", "s3"]:
            result = _builder.build(tid, session_id=sess)
            # Just building without InvalidTemplateError is the assertion
            assert result is not None


def test_invalid_template_raises_for_custom_bad_config(tmp_path: Path) -> None:
    """A template whose all variants end mid-sentence should raise."""
    bad_yaml = textwrap.dedent(
        """
        RT_BAD_TEMPLATE:
          base: "ご説明します"
          variants:
            - suffix: "（終わり）"
              id: "A"
        validation:
          action_request_suffixes:
            - "いただけますか"
        """
    )
    cfg_path = tmp_path / "bad_templates.yaml"
    cfg_path.write_text(bad_yaml, encoding="utf-8")
    builder = ResponseBuilder(config_path=cfg_path)

    with pytest.raises(InvalidTemplateError):
        builder.build("RT_BAD_TEMPLATE", session_id="sess-bad")


def test_template_not_found_raises() -> None:
    with pytest.raises(TemplateNotFoundError):
        _builder.build("RT_NONEXISTENT_TEMPLATE", session_id="sess-x")
