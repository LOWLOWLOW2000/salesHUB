"""AI プロバイダ境界（intent / STT）。

このフェーズの方針:
  - 既定は **完全ローカル**（whisper.cpp + ルールベース分類）
  - 「実用に耐えなかった場合」のクラウド差し替え用に、抽象（Protocol）と
    スケルトン（NotImplementedError を投げるクラウド実装）だけ用意する
  - クラウド呼び出しは本フェーズでは行わない（鍵もコードに入れない）

設定（``data/config.yaml`` の ``ai`` セクション）から
:func:`get_intent_provider` / :func:`get_stt_provider` で取得する想定。
state_machine / SuggestionEngine / API はすべてこの境界経由でしか AI を
触らないため、将来クラウドに切り替える際に本体ロジックには手を入れない。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from app.config import AiConfig
from core.intent_classifier import IntentClassifier


# ---------------------------------------------------------------------------
# 共通レスポンス型
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class IntentCandidate:
    """1 件の intent 候補。

    Attributes:
        intent_id: 例: ``"A1_listening"``。
        confidence: 0.0–1.0。
        source: ``"local"`` または ``"cloud"``。UI / ログで「どのプロバイダが
            出した候補か」を区別するため。
        matched_keywords: ローカルルールで一致したキーワード（クラウド時は空）。
    """

    intent_id: str
    confidence: float
    source: str
    matched_keywords: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Protocol（境界）
# ---------------------------------------------------------------------------


@runtime_checkable
class IntentProvider(Protocol):
    """受付発話を Top-N の intent 候補に分類する境界。"""

    name: str

    def classify_topn(self, text: str, n: int = 3) -> list[IntentCandidate]: ...


@runtime_checkable
class STTProvider(Protocol):
    """音声 → テキスト境界。

    返り値は ``voice.transcriber.TranscriptSegment`` リストと同形に揃える
    （既存パイプライン互換のため）。
    """

    name: str

    def transcribe(self, wav_path: str | Path, *, session_id: str): ...


# ---------------------------------------------------------------------------
# ローカル既定実装
# ---------------------------------------------------------------------------


class LocalRulesIntent:
    """既存 :class:`IntentClassifier` をラップしたローカル既定 intent プロバイダ。"""

    name = "local_rules"

    def __init__(self, classifier: IntentClassifier | None = None) -> None:
        self._clf = classifier or IntentClassifier()

    def classify_topn(self, text: str, n: int = 3) -> list[IntentCandidate]:
        results = self._clf.classify_topn(text, n=n)
        return [
            IntentCandidate(
                intent_id=r.intent_id,
                confidence=r.confidence,
                source="local",
                matched_keywords=r.matched_keywords,
            )
            for r in results
        ]


class LocalWhisperSTT:
    """既存 :class:`Transcriber` をラップしたローカル既定 STT プロバイダ。

    Note:
        セッション ID をコンストラクタで受け取る既存実装に合わせ、
        ``transcribe`` に ``session_id`` を渡せるようにしている。
    """

    name = "local_whisper"

    def __init__(
        self,
        whisper_bin: str | Path | None = None,
        model_path: str | Path | None = None,
    ) -> None:
        self._whisper_bin = whisper_bin
        self._model_path = model_path

    def transcribe(self, wav_path: str | Path, *, session_id: str):
        from voice.transcriber import Transcriber

        t = Transcriber(
            session_id=session_id,
            whisper_bin=self._whisper_bin,
            model_path=self._model_path,
        )
        return t.transcribe(wav_path)


# ---------------------------------------------------------------------------
# クラウド差し替え用スケルトン（本フェーズでは実装しない）
# ---------------------------------------------------------------------------


class CloudNotEnabledError(NotImplementedError):
    """クラウド AI を選んだが本フェーズでは未実装であることを示す例外。"""


class CloudIntent:
    """クラウド intent プロバイダのスケルトン。

    ローカルが「実用に耐えない」と判断された段階で実装する。本フェーズでは
    インスタンス化された時点で :class:`CloudNotEnabledError` を投げ、
    ネットワーク呼び出しが**絶対に**走らないことを保証する。
    """

    name = "cloud"

    def __init__(self, *_: object, **__: object) -> None:
        raise CloudNotEnabledError(
            "CloudIntent is not enabled in this phase. "
            "Keep ai.intent.provider = 'local_rules'."
        )

    def classify_topn(self, text: str, n: int = 3) -> list[IntentCandidate]:
        raise CloudNotEnabledError("CloudIntent.classify_topn is not implemented")


class CloudSTT:
    """クラウド STT プロバイダのスケルトン（同上）。"""

    name = "cloud"

    def __init__(self, *_: object, **__: object) -> None:
        raise CloudNotEnabledError(
            "CloudSTT is not enabled in this phase. "
            "Keep ai.stt.provider = 'local_whisper'."
        )

    def transcribe(self, wav_path: str | Path, *, session_id: str):
        raise CloudNotEnabledError("CloudSTT.transcribe is not implemented")


# ---------------------------------------------------------------------------
# ファクトリ
# ---------------------------------------------------------------------------


def get_intent_provider(cfg: AiConfig | None = None) -> IntentProvider:
    """設定に応じた :class:`IntentProvider` を返す。

    Args:
        cfg: 省略時は ``app.config.get_config().ai`` を読む。
    """
    cfg = cfg or _load_ai_config()
    name = cfg.intent.provider
    if name == "local_rules":
        return LocalRulesIntent()
    if name == "cloud":
        return CloudIntent()
    raise ValueError(f"unknown intent provider: {name!r}")


def get_stt_provider(cfg: AiConfig | None = None) -> STTProvider:
    """設定に応じた :class:`STTProvider` を返す。"""
    cfg = cfg or _load_ai_config()
    name = cfg.stt.provider
    if name == "local_whisper":
        from app.config import get_config

        voice = get_config().voice
        return LocalWhisperSTT(
            whisper_bin=voice.whisper_bin, model_path=voice.model_path
        )
    if name == "cloud":
        return CloudSTT()
    raise ValueError(f"unknown stt provider: {name!r}")


def _load_ai_config() -> AiConfig:
    from app.config import get_config

    return get_config().ai
