"""Tests for core.intent_classifier (T-201).

Coverage:
- Each L2 intent has at least one positive example from the spec
- C2 boundary cases: question form, reason suffix, C1 vs C2 collision
- Unknown text → F1_unclear
- confidence threshold gate
"""

from __future__ import annotations

import pytest

from core.intent_classifier import ClassifierResult, IntentClassifier

# Classifier is stateless — reuse one instance for the whole test session
_clf = IntentClassifier()


def _classify(text: str) -> ClassifierResult:
    return _clf.classify(text)


# ---------------------------------------------------------------------------
# A 系
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "はい",
        "はい、どうぞ",
    ],
)
def test_a1_listening_detected(text: str) -> None:
    result = _classify(text)
    assert result.intent_id == "A1_listening", f"got {result.intent_id!r} for {text!r}"
    assert result.confidence >= 0.60


# ---------------------------------------------------------------------------
# B 系
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text, expected",
    [
        ("ご用件は何でしょうか", "B1_simple_purpose"),
        ("どのようなご用件でしょうか", "B1_simple_purpose"),
        ("具体的には何の件ですか", "B2_detailed_purpose"),
        ("どの部署宛ですか", "B2_detailed_purpose"),
    ],
)
def test_b_purpose_inquiry_detected(text: str, expected: str) -> None:
    result = _classify(text)
    assert result.intent_id == expected, f"got {result.intent_id!r} for {text!r}"


# ---------------------------------------------------------------------------
# C 系 — 正常ケース
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "営業はお断りしています",
        "必要ありません",
        "結構です",
    ],
)
def test_c1_hard_reject_detected(text: str) -> None:
    result = _classify(text)
    assert result.intent_id == "C1_hard_reject", f"got {result.intent_id!r} for {text!r}"
    assert result.confidence >= 0.80


@pytest.mark.parametrize(
    "text",
    [
        "間に合っております",
        "今は必要ないです",
        "今のところ大丈夫です",
        "特にございません",
        # 「そういうのは結構です」は C2+C1 両キー → §4.4 により C1 優先（別ケースでテスト）
    ],
)
def test_c2_soft_reject_detected(text: str) -> None:
    result = _classify(text)
    assert result.intent_id == "C2_soft_reject", f"got {result.intent_id!r} for {text!r}"
    assert result.confidence >= 0.60


@pytest.mark.parametrize(
    "text",
    [
        "そういったお電話はお繋ぎしていません",
        "ご案内は受けておりません",
        "お取り次ぎしておりません",
    ],
)
def test_c3_policy_block_detected(text: str) -> None:
    result = _classify(text)
    assert result.intent_id == "C3_policy_block", f"got {result.intent_id!r} for {text!r}"


# ---------------------------------------------------------------------------
# C2 境界ケース — 仕様書 §4.1, §4.4
# ---------------------------------------------------------------------------


def test_c2_question_form_excluded() -> None:
    """「間に合いますか？」は疑問形なので C2 にならない（B 系に倒れる）。"""
    result = _classify("間に合いますか？")
    assert result.intent_id != "C2_soft_reject", (
        f"question form should not be C2, got {result.intent_id!r}"
    )


def test_c2_reason_suffix_boosts_confidence() -> None:
    """「大丈夫ですので」のように理由後置パターンがあると C2 確度が上がる。"""
    result_without = _classify("大丈夫です")
    result_with = _classify("大丈夫ですので")
    assert result_with.intent_id == "C2_soft_reject"
    assert result_with.confidence >= result_without.confidence


def test_c1_beats_c2_when_both_present() -> None:
    """C1 と C2 のキーワードが共存するときは C1 優先（spec §4.4）。"""
    result = _classify("必要ありません、間に合っております")
    assert result.intent_id == "C1_hard_reject", (
        f"C1 should win, got {result.intent_id!r}"
    )


def test_kekkou_desu_is_c1() -> None:
    """「結構です」単独は C1 として扱う（spec §4.4 末項）。"""
    result = _classify("結構です")
    assert result.intent_id == "C1_hard_reject"


# ---------------------------------------------------------------------------
# D 系
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text, expected",
    [
        ("少々お待ちください", "D1_hold"),
        ("確認いたします", "D2_internal_check"),
        ("どちら様でしょうか", "D3_name_request"),
        ("お名前をお聞かせいただけますか", "D3_name_request"),
    ],
)
def test_d_transfer_action_detected(text: str, expected: str) -> None:
    result = _classify(text)
    assert result.intent_id == expected, f"got {result.intent_id!r} for {text!r}"


# ---------------------------------------------------------------------------
# E 系
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text, expected",
    [
        ("席を外しております", "E1_absent"),
        ("本日不在です", "E1_absent"),
        ("今対応できません", "E2_busy"),
        ("明日の午後なら対応できます", "E3_schedule"),
        ("何時頃でしたら", "E3_schedule"),
    ],
)
def test_e_absence_detected(text: str, expected: str) -> None:
    result = _classify(text)
    assert result.intent_id == expected, f"got {result.intent_id!r} for {text!r}"


# ---------------------------------------------------------------------------
# F1 fallback: unknown text
# ---------------------------------------------------------------------------


def test_unknown_text_returns_f1_unclear() -> None:
    result = _classify("xyzxyz 全くわからないテキスト αβγ")
    assert result.intent_id == "F1_unclear"
    assert result.confidence < 0.60


def test_empty_text_returns_f1_unclear() -> None:
    result = _classify("")
    assert result.intent_id == "F1_unclear"


# ---------------------------------------------------------------------------
# classify_topn — 半自動オペ補助で利用する Top-N API
# ---------------------------------------------------------------------------


def test_topn_returns_at_least_one_result() -> None:
    """空テキストでも必ず非空の F1_unclear リストが返る（呼び出し側の null 排除）。"""
    out = _clf.classify_topn("", n=3)
    assert len(out) == 1
    assert out[0].intent_id == "F1_unclear"


def test_topn_first_matches_classify_for_clear_input() -> None:
    """明確な入力では classify_topn[0] == classify() （後方互換）。"""
    text = "営業はお断りしています"
    top = _clf.classify_topn(text, n=3)
    head = _clf.classify(text)
    assert top[0].intent_id == head.intent_id
    assert top[0].confidence == head.confidence


def test_topn_returns_descending_confidence() -> None:
    """Top-N は confidence 降順で返る。"""
    out = _clf.classify_topn("どのようなご用件でしょうか", n=5)
    confs = [c.confidence for c in out]
    assert confs == sorted(confs, reverse=True)


def test_topn_n_caps_result_length() -> None:
    """n=1 のときは長さ 1（既存テスト互換）。"""
    out = _clf.classify_topn("結構です", n=1)
    assert len(out) == 1
    assert out[0].intent_id == "C1_hard_reject"


def test_topn_low_confidence_falls_back_to_single_unclear() -> None:
    """top が閾値未満なら F1_unclear 単独（classify と同じ振る舞い）。"""
    out = _clf.classify_topn("xyzxyz 全くわからないテキスト", n=5)
    assert len(out) == 1
    assert out[0].intent_id == "F1_unclear"


def test_topn_question_form_excludes_c2() -> None:
    """疑問形では C2 が候補から落ちる（B1 に降格）こと。"""
    out = _clf.classify_topn("間に合いますか？", n=5)
    intent_ids = [c.intent_id for c in out]
    assert "C2_soft_reject" not in intent_ids
