"""Operator suggestion engine（半自動オペ補助）.

オペレータが受付の発話を見ながら次の一手を選べるよう、

  ``(current_state, top_intents)``  →  上位 N 件の :class:`Suggestion`

を返す純関数的なエンジン。state machine を **進めない**（読み取り専用に
``lookup_transition`` を使うだけ）ことが本モジュールの大事な制約で、
オペが採否を決めた後で初めて :class:`StateMachine` の ``send`` を呼ぶ。

設計メモ:
  - intent 候補は :class:`infra.external.ai_provider.IntentCandidate`
    （``source = "local" / "cloud"`` を保持）を入力にする。UI で
    「どのプロバイダの提案か」と「どれくらい自信があるか」を出すため。
  - レスポンステンプレートは :class:`core.response_builder.ResponseBuilder`
    で実テキストにレンダリング（プレビュー用に固定の擬似 session_id を使用）。
  - 該当する遷移が無い候補はスキップ。すべてスキップされた時は
    F1_unclear 系のフォールバック候補（同じ state に留まり再質問）を返す。
"""

from __future__ import annotations

from dataclasses import dataclass

from core.response_builder import (
    InvalidTemplateError,
    ResponseBuilder,
    TemplateNotFoundError,
)
from core.state_machine import lookup_transition
from infra.external.ai_provider import IntentCandidate

# ResponseBuilder.build にはセッション ID が必須だが、suggestion はセッション
# ごとに変えたくない（同じ画面で同じ候補が安定して見えてほしい）ので固定値。
_PREVIEW_SESSION_ID = "__suggestion_preview__"

# 「ぜんぶ該当遷移なし」だった時のフォールバック template_id
_FALLBACK_RETRY_TEMPLATE_ID = "RT_RETRY_PROMPT"


@dataclass(frozen=True, slots=True)
class Suggestion:
    """オペに提示する 1 件の「次の一手」候補。

    Attributes:
        intent_id: 受付発話に対する分類結果（例: ``"C1_hard_reject"``）。
        confidence: AI の確信度（0.0–1.0）。
        source: ``"local"`` または ``"cloud"``。UI / 監査ログでの区別用。
        next_state: この候補を採択した時に遷移する先（例: ``"S4"``）。
        template_id: レスポンステンプレート ID（``None`` なら無発話）。
        template_text: 上記テンプレートをレンダリングした実テキスト
            （``None`` または空文字なら無発話）。
        side_effects: state machine が記録するサイドエフェクト
            （例: ``("outcome=OUT_REJECTED",)``）。
        why: 「なぜこの候補か」の短い説明（UI 表示用）。
        matched_keywords: ローカル分類でヒットしたキーワード（クラウド時は空）。
    """

    intent_id: str
    confidence: float
    source: str
    next_state: str
    template_id: str | None
    template_text: str | None
    side_effects: tuple[str, ...]
    why: str
    matched_keywords: tuple[str, ...] = ()


class SuggestionEngine:
    """Top-N intent 候補から、状態遷移込みの「次の一手」候補を組み立てる。

    Args:
        response_builder: レスポンステンプレート描画用。省略時は
            :class:`ResponseBuilder` を新規生成する。
        preview_session_id: テンプレート variant 選択を安定させるための疑似 ID。
            通常は変更しない。
    """

    def __init__(
        self,
        response_builder: ResponseBuilder | None = None,
        preview_session_id: str = _PREVIEW_SESSION_ID,
    ) -> None:
        self._rb = response_builder or ResponseBuilder()
        self._preview_session_id = preview_session_id

    def suggest(
        self,
        current_state: str,
        top_intents: list[IntentCandidate],
        last_c_intent: str | None = None,
    ) -> list[Suggestion]:
        """Top-N 候補ごとに :class:`Suggestion` を返す。

        Args:
            current_state: 現在の state（例: ``"S2"``）。
            top_intents: :meth:`IntentProvider.classify_topn` が返した候補。
                confidence 降順で並んでいる前提（中身は再ソートしない）。
            last_c_intent: 直近の C 系 intent（``RT_REBUTTAL_BY_C_TYPE`` 解決用）。

        Returns:
            confidence 降順の :class:`Suggestion` リスト。空にはならない
            （該当遷移がなければ retry プロンプトのフォールバックを返す）。
        """
        suggestions: list[Suggestion] = []

        for cand in top_intents:
            if cand.intent_id == "F1_unclear":
                continue
            preview = lookup_transition(current_state, cand.intent_id)
            if preview is None:
                continue

            template_text = self._render_template(
                preview.response_template_id, last_c_intent
            )
            why = self._explain(current_state, cand, preview)
            suggestions.append(
                Suggestion(
                    intent_id=cand.intent_id,
                    confidence=cand.confidence,
                    source=cand.source,
                    next_state=preview.next_state,
                    template_id=preview.response_template_id,
                    template_text=template_text,
                    side_effects=preview.side_effects,
                    why=why,
                    matched_keywords=cand.matched_keywords,
                )
            )

        if suggestions:
            return suggestions

        return [self._fallback_suggestion(current_state, top_intents)]

    # ── Internal ────────────────────────────────────────────────────────────

    def _render_template(
        self, template_id: str | None, last_c_intent: str | None
    ) -> str | None:
        """テンプレートを実テキストにレンダリング（失敗時は ``None``）。"""
        if template_id is None:
            return None
        try:
            result = self._rb.build(
                template_id, self._preview_session_id, last_c_intent=last_c_intent
            )
        except (TemplateNotFoundError, InvalidTemplateError):
            return None
        return result.text or None

    def _explain(
        self, state: str, cand: IntentCandidate, preview
    ) -> str:
        """UI に出す短い理由文（決定的、英語コードを含む）。"""
        kw = (
            f", matched={list(cand.matched_keywords)}"
            if cand.matched_keywords
            else ""
        )
        tmpl = preview.response_template_id or "(no template)"
        return (
            f"{state} + {cand.intent_id} -> {preview.next_state} "
            f"via {tmpl} (confidence={cand.confidence:.2f}, "
            f"source={cand.source}{kw})"
        )

    def _fallback_suggestion(
        self, current_state: str, top_intents: list[IntentCandidate]
    ) -> Suggestion:
        """すべての intent 候補が遷移を持たなかった時の退却用 1 件。"""
        head_source = top_intents[0].source if top_intents else "local"
        text = self._render_template(_FALLBACK_RETRY_TEMPLATE_ID, last_c_intent=None)
        return Suggestion(
            intent_id="F1_unclear",
            confidence=0.0,
            source=head_source,
            next_state=current_state,
            template_id=_FALLBACK_RETRY_TEMPLATE_ID if text else None,
            template_text=text,
            side_effects=(),
            why=(
                f"no transition matched (state={current_state}); "
                "ask reception to repeat"
            ),
        )
