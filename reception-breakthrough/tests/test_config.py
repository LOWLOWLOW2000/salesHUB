"""T-600: app/config.py のユニットテスト."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.config import AppConfig, get_config, reset_config_cache


@pytest.fixture(autouse=True)
def clear_cache():
    """各テスト前後にキャッシュをクリアする。"""
    reset_config_cache()
    yield
    reset_config_cache()


def test_default_config_loads_without_error() -> None:
    """data/config.yaml が存在すればデフォルト設定が読み込まれる。"""
    cfg = get_config()
    assert isinstance(cfg, AppConfig)
    assert cfg.database.path != ""


def test_default_values_when_yaml_empty(tmp_path: Path) -> None:
    """空の YAML でもデフォルト値が適用される。"""
    empty = tmp_path / "empty.yaml"
    empty.write_text("{}", encoding="utf-8")

    cfg = get_config(str(empty))
    assert cfg.database.path == "data/calls.db"
    assert cfg.voice.sample_rate == 16000
    assert cfg.silence.rms_threshold == 300
    assert cfg.state_machine.unclear_limit == 3
    assert cfg.classifier.min_confidence == 0.3
    assert cfg.pipeline.transcription_job.max_records == 100
    assert cfg.api.port == 8000


def test_custom_yaml_overrides_defaults(tmp_path: Path) -> None:
    """YAML の値が AppConfig に反映される。"""
    custom = tmp_path / "custom.yaml"
    custom.write_text(
        yaml.dump(
            {
                "database": {"path": "custom/calls.db"},
                "voice": {"sample_rate": 8000},
                "state_machine": {"unclear_limit": 5},
                "api": {"port": 9090},
            }
        ),
        encoding="utf-8",
    )

    cfg = get_config(str(custom))
    assert cfg.database.path == "custom/calls.db"
    assert cfg.voice.sample_rate == 8000
    assert cfg.state_machine.unclear_limit == 5
    assert cfg.api.port == 9090


def test_config_is_cached(tmp_path: Path) -> None:
    """同じパスで 2 回呼んでも同一オブジェクトを返す。"""
    empty = tmp_path / "c.yaml"
    empty.write_text("{}", encoding="utf-8")

    cfg1 = get_config(str(empty))
    cfg2 = get_config(str(empty))
    assert cfg1 is cfg2


def test_failure_analysis_defaults(tmp_path: Path) -> None:
    """failure_outcomes のデフォルトに 3 種類のアウトカムが含まれる。"""
    empty = tmp_path / "e.yaml"
    empty.write_text("{}", encoding="utf-8")

    cfg = get_config(str(empty))
    fo = cfg.pipeline.failure_analysis.failure_outcomes
    assert "OUT_REJECTED" in fo
    assert "OUT_NOISE" in fo
    assert "OUT_ABSENT" in fo
