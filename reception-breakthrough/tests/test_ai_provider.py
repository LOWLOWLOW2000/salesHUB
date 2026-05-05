"""AI プロバイダ境界（infra.external.ai_provider）のテスト。

検証ポイント:
  - 既定設定でファクトリがローカル実装を返す
  - クラウド選択は本フェーズでは未実装で初期化に失敗する
  - LocalRulesIntent.classify_topn の Top-N が confidence 降順で
    source="local" を持つ
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.config import (
    AiConfig,
    AiIntentConfig,
    AiSttConfig,
    get_config,
    reset_config_cache,
)
from infra.external.ai_provider import (
    CloudNotEnabledError,
    IntentCandidate,
    IntentProvider,
    LocalRulesIntent,
    LocalWhisperSTT,
    STTProvider,
    get_intent_provider,
    get_stt_provider,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    reset_config_cache()
    yield
    reset_config_cache()


# ---------------------------------------------------------------------------
# ファクトリ既定 = ローカル
# ---------------------------------------------------------------------------


def test_default_intent_provider_is_local() -> None:
    provider = get_intent_provider()
    assert provider.name == "local_rules"
    assert isinstance(provider, IntentProvider)
    assert isinstance(provider, LocalRulesIntent)


def test_default_stt_provider_is_local() -> None:
    provider = get_stt_provider()
    assert provider.name == "local_whisper"
    assert isinstance(provider, STTProvider)
    assert isinstance(provider, LocalWhisperSTT)


def test_explicit_local_intent_config_returns_local() -> None:
    cfg = AiConfig(intent=AiIntentConfig(provider="local_rules"))
    assert isinstance(get_intent_provider(cfg), LocalRulesIntent)


# ---------------------------------------------------------------------------
# クラウド選択は本フェーズで失敗する（事故防止）
# ---------------------------------------------------------------------------


def test_cloud_intent_provider_raises_in_this_phase() -> None:
    cfg = AiConfig(intent=AiIntentConfig(provider="cloud"))
    with pytest.raises(CloudNotEnabledError):
        get_intent_provider(cfg)


def test_cloud_stt_provider_raises_in_this_phase() -> None:
    cfg = AiConfig(stt=AiSttConfig(provider="cloud"))
    with pytest.raises(CloudNotEnabledError):
        get_stt_provider(cfg)


def test_unknown_intent_provider_raises_value_error() -> None:
    cfg = AiConfig(intent=AiIntentConfig(provider="bogus"))
    with pytest.raises(ValueError):
        get_intent_provider(cfg)


def test_unknown_stt_provider_raises_value_error() -> None:
    cfg = AiConfig(stt=AiSttConfig(provider="bogus"))
    with pytest.raises(ValueError):
        get_stt_provider(cfg)


# ---------------------------------------------------------------------------
# LocalRulesIntent の振る舞い
# ---------------------------------------------------------------------------


def test_local_rules_intent_returns_local_source_candidates() -> None:
    provider = LocalRulesIntent()
    out = provider.classify_topn("どのようなご用件でしょうか", n=3)
    assert len(out) >= 1
    assert all(isinstance(c, IntentCandidate) for c in out)
    assert all(c.source == "local" for c in out)


def test_local_rules_intent_topn_descending_confidence() -> None:
    provider = LocalRulesIntent()
    out = provider.classify_topn("間に合っております", n=5)
    confs = [c.confidence for c in out]
    assert confs == sorted(confs, reverse=True)


def test_local_rules_intent_unknown_text_returns_unclear() -> None:
    provider = LocalRulesIntent()
    out = provider.classify_topn("xyzxyz 全くわからない αβγ", n=3)
    assert out[0].intent_id == "F1_unclear"
    assert out[0].source == "local"


# ---------------------------------------------------------------------------
# 設定 YAML 経由
# ---------------------------------------------------------------------------


def test_factory_reads_yaml_default_to_local(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """空 YAML を ``RB_CONFIG_PATH`` 経由で読ませてもローカルが返ること。"""
    empty = tmp_path / "empty.yaml"
    empty.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("RB_CONFIG_PATH", str(empty))

    provider = get_intent_provider()
    assert provider.name == "local_rules"


def test_factory_yaml_cloud_provider_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``RB_CONFIG_PATH`` 経由で cloud を選ぶと初期化が失敗（事故防止）。"""
    custom = tmp_path / "cloud.yaml"
    custom.write_text(
        yaml.dump({"ai": {"intent": {"provider": "cloud"}}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("RB_CONFIG_PATH", str(custom))

    with pytest.raises(CloudNotEnabledError):
        get_intent_provider()
