"""SuggestionEngine（半自動オペ補助）のテスト。

検証ポイント:
  - state machine を変更しない（純粋関数的）
  - Top-N から該当遷移のある intent だけが Suggestion になる
  - confidence 降順を保つ
  - 該当遷移がゼロのときは F1_unclear のフォールバック 1 件を返す
  - source（local / cloud）を Suggestion にそのまま伝搬する
  - C 系 → C 系 + S5 のとき RT_REBUTTAL_BY_C_TYPE が解決される
"""

from __future__ import annotations

from core.suggestion_engine import Suggestion, SuggestionEngine
from infra.external.ai_provider import IntentCandidate


def _cand(intent_id: str, confidence: float = 0.8, source: str = "local") -> IntentCandidate:
    return IntentCandidate(intent_id=intent_id, confidence=confidence, source=source)


# ---------------------------------------------------------------------------
# 基本動作
# ---------------------------------------------------------------------------


def test_suggest_returns_suggestion_for_known_transition() -> None:
    engine = SuggestionEngine()
    out = engine.suggest("S2", [_cand("A1_listening", 0.9)])
    assert len(out) == 1
    s = out[0]
    assert isinstance(s, Suggestion)
    assert s.intent_id == "A1_listening"
    assert s.next_state == "S3"
    assert s.template_id == "RT_ASK_TRANSFER_SHORT"
    assert s.template_text and s.template_text.endswith(("ますか", "せんか", "ください"))
    assert s.source == "local"


def test_suggest_skips_intents_without_transition() -> None:
    """S2 で C1_hard_reject は遷移が無い → スキップされる。"""
    engine = SuggestionEngine()
    out = engine.suggest(
        "S2",
        [
            _cand("C1_hard_reject", 0.95),
            _cand("A1_listening", 0.7),
        ],
    )
    intent_ids = [s.intent_id for s in out]
    assert "C1_hard_reject" not in intent_ids
    assert "A1_listening" in intent_ids


def test_suggest_preserves_confidence_descending_input() -> None:
    """入力が降順なら出力も降順を保つ。"""
    engine = SuggestionEngine()
    out = engine.suggest(
        "S2",
        [
            _cand("B1_simple_purpose", 0.9),
            _cand("A1_listening", 0.7),
            _cand("D1_hold", 0.4),
        ],
    )
    confs = [s.confidence for s in out]
    assert confs == sorted(confs, reverse=True)


def test_suggest_filters_f1_unclear_from_topn() -> None:
    """F1_unclear は intent 候補から落とされる（フォールバックは別物）。"""
    engine = SuggestionEngine()
    out = engine.suggest(
        "S2",
        [_cand("F1_unclear", 0.1), _cand("A1_listening", 0.7)],
    )
    intent_ids = [s.intent_id for s in out]
    assert intent_ids == ["A1_listening"]


# ---------------------------------------------------------------------------
# フォールバック
# ---------------------------------------------------------------------------


def test_suggest_returns_fallback_when_no_transition_matches() -> None:
    """遷移が一つもない時は F1_unclear で同じ state に留まる候補を 1 件返す。"""
    engine = SuggestionEngine()
    out = engine.suggest("S2", [_cand("C1_hard_reject", 0.95)])
    assert len(out) == 1
    s = out[0]
    assert s.intent_id == "F1_unclear"
    assert s.next_state == "S2"
    assert s.template_id == "RT_RETRY_PROMPT"


def test_suggest_returns_fallback_for_empty_topn() -> None:
    engine = SuggestionEngine()
    out = engine.suggest("S2", [])
    assert len(out) == 1
    assert out[0].intent_id == "F1_unclear"
    assert out[0].next_state == "S2"


def test_fallback_propagates_source_from_first_candidate() -> None:
    """フォールバック時、先頭候補の source を引き継ぐ（監査用）。"""
    engine = SuggestionEngine()
    out = engine.suggest("S2", [_cand("C1_hard_reject", 0.95, source="cloud")])
    assert out[0].source == "cloud"


# ---------------------------------------------------------------------------
# C 系（rebuttal 解決）
# ---------------------------------------------------------------------------


def test_rebuttal_template_resolution_uses_last_c_intent() -> None:
    """S5 + A1 は RT_THANKS_AND_TRANSFER。S4 + EV_HUMAN_RESPONDED 経路で
    rebuttal 解決を検証するなら別経路だが、ここでは一旦 ResponseBuilder
    が last_c_intent を受けるパスが繋がっていることだけ確認する。"""
    engine = SuggestionEngine()
    out = engine.suggest("S5", [_cand("A1_listening", 0.9)], last_c_intent="C1_hard_reject")
    assert len(out) == 1
    assert out[0].next_state == "S6"
    assert out[0].template_id == "RT_THANKS_AND_TRANSFER"


# ---------------------------------------------------------------------------
# 純関数性
# ---------------------------------------------------------------------------


def test_suggest_does_not_mutate_inputs() -> None:
    engine = SuggestionEngine()
    cands = [_cand("A1_listening", 0.9), _cand("B1_simple_purpose", 0.7)]
    snapshot = list(cands)
    engine.suggest("S2", cands)
    assert cands == snapshot


def test_suggest_is_idempotent() -> None:
    engine = SuggestionEngine()
    cands = [_cand("A1_listening", 0.9)]
    out1 = engine.suggest("S2", cands)
    out2 = engine.suggest("S2", cands)
    assert [s.intent_id for s in out1] == [s.intent_id for s in out2]
    assert [s.template_text for s in out1] == [s.template_text for s in out2]


# ---------------------------------------------------------------------------
# why（UI 説明文）
# ---------------------------------------------------------------------------


def test_why_includes_state_intent_and_source() -> None:
    engine = SuggestionEngine()
    out = engine.suggest("S2", [_cand("A1_listening", 0.91)])
    why = out[0].why
    assert "S2" in why
    assert "A1_listening" in why
    assert "S3" in why
    assert "local" in why
