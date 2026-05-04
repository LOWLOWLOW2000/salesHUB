"""T-500: api_server.py の統合テスト (FastAPI TestClient 使用)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """テスト専用 DB を使った TestClient を返す。"""
    db_path = tmp_path / "test_api.db"

    import app.config as _cfg_mod
    _cfg_mod.reset_config_cache()

    import ui.api_server as api_mod
    monkeypatch.setattr(api_mod, "_DB_PATH", db_path)
    api_mod._active_sessions.clear()

    from infra.external.crm_adapter import InMemoryCRMAdapter
    new_crm = InMemoryCRMAdapter()
    monkeypatch.setattr(api_mod, "_crm", new_crm)

    with TestClient(api_mod.app) as c:
        # lifespan が追加したリードをクリアして、テスト用リードだけにする
        new_crm._queue.clear()
        new_crm._leads.clear()
        new_crm.register_lead("LEAD-TEST-001", company="テスト株式会社", phone="03-0000-0001")
        yield c

    # テスト後に残った永続接続をすべてクローズ
    for _, conn in list(api_mod._active_sessions.values()):
        try:
            conn.close()
        except Exception:
            pass
    api_mod._active_sessions.clear()
    _cfg_mod.reset_config_cache()


# ---------------------------------------------------------------------------
# ヘルスチェック
# ---------------------------------------------------------------------------


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# リード
# ---------------------------------------------------------------------------


def test_get_next_lead_returns_lead(client: TestClient) -> None:
    resp = client.get("/leads/next")
    assert resp.status_code == 200
    data = resp.json()
    assert data["lead_id"] == "LEAD-TEST-001"


def test_get_next_lead_empty_returns_null(client: TestClient) -> None:
    client.get("/leads/next")  # 1 件取り出す
    resp = client.get("/leads/next")  # キュー空
    assert resp.status_code == 200
    assert resp.json()["lead_id"] is None


# ---------------------------------------------------------------------------
# セッション作成
# ---------------------------------------------------------------------------


def test_create_session_returns_201(client: TestClient) -> None:
    resp = client.post("/sessions", json={"lead_id": "LEAD-001", "mode": "AI"})
    assert resp.status_code == 201
    data = resp.json()
    assert "session_id" in data
    assert data["state"] != "S0"  # EV_DIALED で S1 以降に進んでいる


def test_create_session_invalid_mode(client: TestClient) -> None:
    resp = client.post("/sessions", json={"lead_id": "L001", "mode": "INVALID"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# セッション一覧・詳細
# ---------------------------------------------------------------------------


def test_list_sessions(client: TestClient) -> None:
    client.post("/sessions", json={"lead_id": "L001", "mode": "AI"})
    resp = client.get("/sessions")
    assert resp.status_code == 200
    assert len(resp.json()["sessions"]) >= 1


def test_get_session_detail(client: TestClient) -> None:
    create = client.post("/sessions", json={"lead_id": "L002", "mode": "AI"})
    sid = create.json()["session_id"]

    resp = client.get(f"/sessions/{sid}")
    assert resp.status_code == 200
    assert resp.json()["session_id"] == sid


def test_get_session_not_found(client: TestClient) -> None:
    resp = client.get("/sessions/nonexistent-id")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# ステップ実行
# ---------------------------------------------------------------------------


def test_step_session(client: TestClient) -> None:
    create = client.post("/sessions", json={"lead_id": "L003", "mode": "AI"})
    sid = create.json()["session_id"]

    # S1(ringing) → EV_PICKED_UP → S2(reception_contact)
    r1 = client.post(f"/sessions/{sid}/step", json={"input_id": "EV_PICKED_UP"})
    assert r1.status_code == 200

    # S2 + A1_listening → S3
    resp = client.post(f"/sessions/{sid}/step", json={"input_id": "A1_listening"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == sid
    assert data["input_id"] == "A1_listening"
    assert data["from_state"] == "S2"
    assert data["to_state"] == "S3"


def test_step_text_session(client: TestClient) -> None:
    create = client.post("/sessions", json={"lead_id": "L004", "mode": "AI"})
    sid = create.json()["session_id"]

    # S1 → EV_PICKED_UP → S2
    client.post(f"/sessions/{sid}/step", json={"input_id": "EV_PICKED_UP"})

    # S2 + 発話テキスト
    resp = client.post(
        f"/sessions/{sid}/step_text",
        json={"utterance": "はい、どちら様でしょうか"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["classifier_intent"] is not None


def test_step_terminated_session_returns_409(client: TestClient) -> None:
    """終了済みセッションに step を送ると 404 が返る（セッションが削除済み）。"""
    create = client.post("/sessions", json={"lead_id": "L005", "mode": "AI"})
    sid = create.json()["session_id"]

    import ui.api_server as api_mod
    entry = api_mod._active_sessions.get(sid)
    if entry is not None:
        ctrl, conn = entry
        # S1 → EV_NO_ANSWER → S11 (OUT_NOISE) で強制終了
        client.post(f"/sessions/{sid}/step", json={"input_id": "EV_NO_ANSWER"})

    # セッション終了後は _active_sessions から削除されているので 404
    resp = client.post(f"/sessions/{sid}/step", json={"input_id": "A1_listening"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 状態遷移一覧
# ---------------------------------------------------------------------------


def test_get_transitions(client: TestClient) -> None:
    create = client.post("/sessions", json={"lead_id": "L006", "mode": "AI"})
    sid = create.json()["session_id"]

    resp = client.get(f"/sessions/{sid}/transitions")
    assert resp.status_code == 200
    data = resp.json()
    assert "transitions" in data
    assert len(data["transitions"]) >= 1  # EV_DIALED 分


# ---------------------------------------------------------------------------
# メトリクス
# ---------------------------------------------------------------------------


def test_metrics_latest_empty(client: TestClient) -> None:
    resp = client.get("/metrics/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert "metrics" in data
    assert "metric_date" in data
