"""アプリ全体の設定読み込み (T-600).

``data/config.yaml`` を読んで型付きの設定オブジェクトを提供する。
環境変数で上書きしたい場合は ``RB_CONFIG_PATH`` を設定する。

使い方::

    from app.config import get_config
    cfg = get_config()
    db_path = cfg.database.path
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# 型定義
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    path: str = "data/calls.db"


@dataclass(frozen=True, slots=True)
class VoiceConfig:
    whisper_bin: str | None = None
    model_path: str | None = None
    sample_rate: int = 16000
    channels: int = 1
    sample_width: int = 2


@dataclass(frozen=True, slots=True)
class SilenceConfig:
    rms_threshold: int = 300
    silence_limit_ms: int = 8000


@dataclass(frozen=True, slots=True)
class StateMachineConfig:
    unclear_limit: int = 3
    timeout_ms: int = 30000


@dataclass(frozen=True, slots=True)
class ClassifierConfig:
    min_confidence: float = 0.3
    keywords_yaml: str = "data/intent_keywords.yaml"


@dataclass(frozen=True, slots=True)
class ResponseBuilderConfig:
    templates_yaml: str = "data/response_templates.yaml"


@dataclass(frozen=True, slots=True)
class TranscriptionJobConfig:
    max_records: int = 100


@dataclass(frozen=True, slots=True)
class IntentLabelingConfig:
    max_records: int = 500


@dataclass(frozen=True, slots=True)
class FailureAnalysisConfig:
    failure_outcomes: tuple[str, ...] = (
        "OUT_REJECTED",
        "OUT_NOISE",
        "OUT_ABSENT",
    )


@dataclass(frozen=True, slots=True)
class MetricsConfig:
    export_dir: str = "data/exports"


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    transcription_job: TranscriptionJobConfig = field(
        default_factory=TranscriptionJobConfig
    )
    intent_labeling: IntentLabelingConfig = field(
        default_factory=IntentLabelingConfig
    )
    failure_analysis: FailureAnalysisConfig = field(
        default_factory=FailureAnalysisConfig
    )
    metrics: MetricsConfig = field(default_factory=MetricsConfig)


@dataclass(frozen=True, slots=True)
class ApiConfig:
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = True


@dataclass(frozen=True, slots=True)
class AiIntentFallbackConfig:
    """ローカル分類の confidence が低い時にクラウドへ回すためのスイッチ。

    本フェーズでは ``enabled=False`` 固定（クラウド未実装）。将来の差し替えで
    有効化する。
    """

    enabled: bool = False
    confidence_threshold: float = 0.55


@dataclass(frozen=True, slots=True)
class AiIntentConfig:
    """intent 分類プロバイダの設定。"""

    provider: str = "local_rules"
    fallback: AiIntentFallbackConfig = field(default_factory=AiIntentFallbackConfig)


@dataclass(frozen=True, slots=True)
class AiSttConfig:
    """音声→テキスト プロバイダの設定。"""

    provider: str = "local_whisper"


@dataclass(frozen=True, slots=True)
class AiConfig:
    """AI プロバイダ全体設定の root。

    既定はこのマシン上の完全ローカル（``local_rules`` / ``local_whisper``）。
    """

    intent: AiIntentConfig = field(default_factory=AiIntentConfig)
    stt: AiSttConfig = field(default_factory=AiSttConfig)


@dataclass(frozen=True, slots=True)
class AppConfig:
    """アプリ全体設定の root オブジェクト。"""

    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    silence: SilenceConfig = field(default_factory=SilenceConfig)
    state_machine: StateMachineConfig = field(default_factory=StateMachineConfig)
    classifier: ClassifierConfig = field(default_factory=ClassifierConfig)
    response_builder: ResponseBuilderConfig = field(
        default_factory=ResponseBuilderConfig
    )
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    api: ApiConfig = field(default_factory=ApiConfig)
    ai: AiConfig = field(default_factory=AiConfig)
    crm_adapter: str = "memory"


# ---------------------------------------------------------------------------
# ローダー
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "data" / "config.yaml"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _build_config(raw: dict[str, Any]) -> AppConfig:
    db_raw = raw.get("database", {})
    voice_raw = raw.get("voice", {})
    silence_raw = raw.get("silence", {})
    sm_raw = raw.get("state_machine", {})
    clf_raw = raw.get("classifier", {})
    rb_raw = raw.get("response_builder", {})
    pipe_raw = raw.get("pipeline", {})
    api_raw = raw.get("api", {})
    ai_raw = raw.get("ai", {})

    tj_raw = pipe_raw.get("transcription_job", {})
    il_raw = pipe_raw.get("intent_labeling", {})
    fa_raw = pipe_raw.get("failure_analysis", {})
    mt_raw = pipe_raw.get("metrics", {})

    ai_intent_raw = ai_raw.get("intent", {})
    ai_intent_fb_raw = ai_intent_raw.get("fallback", {})
    ai_stt_raw = ai_raw.get("stt", {})

    return AppConfig(
        database=DatabaseConfig(path=db_raw.get("path", "data/calls.db")),
        voice=VoiceConfig(
            whisper_bin=voice_raw.get("whisper_bin"),
            model_path=voice_raw.get("model_path"),
            sample_rate=voice_raw.get("sample_rate", 16000),
            channels=voice_raw.get("channels", 1),
            sample_width=voice_raw.get("sample_width", 2),
        ),
        silence=SilenceConfig(
            rms_threshold=silence_raw.get("rms_threshold", 300),
            silence_limit_ms=silence_raw.get("silence_limit_ms", 8000),
        ),
        state_machine=StateMachineConfig(
            unclear_limit=sm_raw.get("unclear_limit", 3),
            timeout_ms=sm_raw.get("timeout_ms", 30000),
        ),
        classifier=ClassifierConfig(
            min_confidence=clf_raw.get("min_confidence", 0.3),
            keywords_yaml=clf_raw.get(
                "keywords_yaml", "data/intent_keywords.yaml"
            ),
        ),
        response_builder=ResponseBuilderConfig(
            templates_yaml=rb_raw.get(
                "templates_yaml", "data/response_templates.yaml"
            ),
        ),
        pipeline=PipelineConfig(
            transcription_job=TranscriptionJobConfig(
                max_records=tj_raw.get("max_records", 100)
            ),
            intent_labeling=IntentLabelingConfig(
                max_records=il_raw.get("max_records", 500)
            ),
            failure_analysis=FailureAnalysisConfig(
                failure_outcomes=tuple(
                    fa_raw.get(
                        "failure_outcomes",
                        ["OUT_REJECTED", "OUT_NOISE", "OUT_ABSENT"],
                    )
                )
            ),
            metrics=MetricsConfig(
                export_dir=mt_raw.get("export_dir", "data/exports")
            ),
        ),
        api=ApiConfig(
            host=api_raw.get("host", "127.0.0.1"),
            port=api_raw.get("port", 8000),
            reload=api_raw.get("reload", True),
        ),
        ai=AiConfig(
            intent=AiIntentConfig(
                provider=ai_intent_raw.get("provider", "local_rules"),
                fallback=AiIntentFallbackConfig(
                    enabled=bool(ai_intent_fb_raw.get("enabled", False)),
                    confidence_threshold=float(
                        ai_intent_fb_raw.get("confidence_threshold", 0.55)
                    ),
                ),
            ),
            stt=AiSttConfig(
                provider=ai_stt_raw.get("provider", "local_whisper"),
            ),
        ),
        crm_adapter=raw.get("crm", {}).get("adapter", "memory"),
    )


@lru_cache(maxsize=1)
def get_config(config_path: str | None = None) -> AppConfig:
    """設定を読み込んでキャッシュして返す。

    Args:
        config_path: YAML ファイルのパス。省略時は環境変数 ``RB_CONFIG_PATH`` →
                     ``data/config.yaml`` の順に探す。

    Returns:
        :class:`AppConfig` インスタンス（キャッシュ済み）。
    """
    path_str = config_path or os.environ.get("RB_CONFIG_PATH")
    path = Path(path_str) if path_str else _DEFAULT_CONFIG_PATH
    raw = _load_yaml(path)
    return _build_config(raw)


def reset_config_cache() -> None:
    """テスト用: キャッシュをクリアする。"""
    get_config.cache_clear()
