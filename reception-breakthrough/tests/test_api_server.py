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


# ---------------------------------------------------------------------------
# OpenAPI / ドキュメント UI
# ---------------------------------------------------------------------------


def test_swagger_docs_page(client: TestClient) -> None:
    resp = client.get("/docs")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert b"/openapi-en.json" in resp.content
    assert b"/openapi-ja.json" in resp.content
    assert b"swagger-ui-standalone-preset.js" in resp.content
    assert "まずこれだけ読む".encode("utf-8") in resp.content


def test_openapi_en_localized(client: TestClient) -> None:
    resp = client.get("/openapi-en.json")
    assert resp.status_code == 200
    data = resp.json()
    assert data["info"]["description"].startswith("AI-assisted")
    op = data["paths"]["/sessions"]["get"]
    assert op["summary"].startswith("View sessions")


def test_openapi_ja_localized(client: TestClient) -> None:
    resp = client.get("/openapi-ja.json")
    assert resp.status_code == 200
    data = resp.json()
    assert "受付突破" in data["info"]["description"]
    op = data["paths"]["/sessions"]["get"]
    assert "セッション" in op["summary"]


# ---------------------------------------------------------------------------
# /review/* — 半自動オペ補助
# ---------------------------------------------------------------------------


def _start_session_at_s2(client: TestClient, lead_id: str = "L-REV-1") -> str:
    """S2（受付応答待ち）まで進めて session_id を返すヘルパ。"""
    create = client.post("/sessions", json={"lead_id": lead_id, "mode": "HUMAN"})
    sid = create.json()["session_id"]
    client.post(f"/sessions/{sid}/step", json={"input_id": "EV_PICKED_UP"})
    return sid


def test_review_suggest_returns_topn_with_local_source(client: TestClient) -> None:
    sid = _start_session_at_s2(client)
    resp = client.post(
        f"/review/{sid}/suggest",
        json={"utterance": "ご担当の方にお繋ぎいただけますか", "n": 3},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == sid
    assert data["transcript_id"]
    assert data["label_id"]
    assert data["current_state"] == "S2"
    assert isinstance(data["suggestions"], list)
    assert len(data["suggestions"]) >= 1
    head = data["suggestions"][0]
    assert head["source"] == "local"
    assert "next_state" in head
    assert "why" in head


def test_review_suggest_persists_transcript_and_label(client: TestClient) -> None:
    """suggest が transcripts と intent_labels に行を残すこと。"""
    sid = _start_session_at_s2(client)
    resp = client.post(
        f"/review/{sid}/suggest",
        json={"utterance": "営業はお断りしています", "n": 3},
    )
    label_id = resp.json()["label_id"]

    turns = client.get(f"/review/{sid}/turns").json()["turns"]
    assert len(turns) == 1
    label = turns[0]["label"]
    assert label is not None
    assert label["label_id"] == label_id
    assert label["correct_intent"] is None  # decide 前なので未確定


def test_review_suggest_rejects_empty_utterance(client: TestClient) -> None:
    sid = _start_session_at_s2(client)
    resp = client.post(f"/review/{sid}/suggest", json={"utterance": "   "})
    assert resp.status_code == 422


def test_review_suggest_unknown_session_404(client: TestClient) -> None:
    resp = client.post(
        "/review/no-such-session/suggest", json={"utterance": "はい"}
    )
    assert resp.status_code == 404


def test_review_decide_advances_state_machine(client: TestClient) -> None:
    sid = _start_session_at_s2(client)
    sug = client.post(
        f"/review/{sid}/suggest",
        json={"utterance": "ご担当の方にお繋ぎいただけますか"},
    ).json()
    label_id = sug["label_id"]

    resp = client.post(
        f"/review/{sid}/decide",
        json={
            "label_id": label_id,
            "chosen_input_id": "B1_simple_purpose",
            "reviewed_by": "tester",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["from_state"] == "S2"
    assert data["to_state"] == "S3"
    assert data["input_id"] == "B1_simple_purpose"

    turns = client.get(f"/review/{sid}/turns").json()["turns"]
    label = turns[0]["label"]
    assert label["correct_intent"] == "B1_simple_purpose"
    assert label["reviewed_by"] == "tester"
    assert label["reviewed_at"]


def test_review_decide_records_label_correction(client: TestClient) -> None:
    """予測と異なる正解を渡すと correct_intent が予測と分離して保存される。"""
    sid = _start_session_at_s2(client)
    sug = client.post(
        f"/review/{sid}/suggest",
        json={"utterance": "ご担当の方にお繋ぎいただけますか"},
    ).json()

    client.post(
        f"/review/{sid}/decide",
        json={
            "label_id": sug["label_id"],
            "chosen_input_id": "A1_listening",
            "correct_intent": "A1_listening",
            "note": "AI は B1 と判定したが受付の様子的に A1",
        },
    )

    turns = client.get(f"/review/{sid}/turns").json()["turns"]
    label = turns[0]["label"]
    assert label["correct_intent"] == "A1_listening"
    assert label["note"]


def test_review_decide_unknown_label_404(client: TestClient) -> None:
    sid = _start_session_at_s2(client)
    resp = client.post(
        f"/review/{sid}/decide",
        json={"label_id": "no-such-label", "chosen_input_id": "A1_listening"},
    )
    assert resp.status_code == 404


def test_review_labels_csv_exports_rows(client: TestClient) -> None:
    sid = _start_session_at_s2(client)
    sug = client.post(
        f"/review/{sid}/suggest", json={"utterance": "営業はお断りしています"}
    ).json()
    client.post(
        f"/review/{sid}/decide",
        json={
            "label_id": sug["label_id"],
            "chosen_input_id": "C1_hard_reject",
            "reviewed_by": "tester",
        },
    )

    resp = client.get("/review/labels.csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    body = resp.text
    assert "predicted_intent,correct_intent" in body
    assert "C1_hard_reject" in body
    assert sid in body
