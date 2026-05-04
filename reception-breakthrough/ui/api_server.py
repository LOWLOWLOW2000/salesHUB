"""自己架電画面用 REST API サーバー (T-500).

起動方法::

    cd reception-breakthrough
    source .venv/bin/activate
    uvicorn ui.api_server:app --reload --port 8000

主なエンドポイント
------------------
GET  /sessions                    セッション一覧（ページネーション）
GET  /sessions/{id}               セッション詳細
GET  /sessions/{id}/transitions   状態遷移一覧
GET  /sessions/{id}/outcome       アウトカム
POST /sessions                    セッション開始
POST /sessions/{id}/step          1 ステップ進める（インテント / イベント入力）
POST /sessions/{id}/step_text     発話テキストを分類してステップ進める
GET  /leads/next                  次架電リード（InMemory モック）
GET  /metrics/latest              直近日次メトリクス
GET  /health                      ヘルスチェック
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import sqlite3

from app.config import get_config
from core.call_controller import CallController
from infra.db.local_db import get_connection, open_persistent_connection
from infra.external.crm_adapter import InMemoryCRMAdapter

# ---------------------------------------------------------------------------
# アプリ設定
# ---------------------------------------------------------------------------

_cfg = get_config()
_DB_PATH = Path(_cfg.database.path)

# 稼働中セッション (session_id → (CallController, sqlite3.Connection))
# 注意: 本番ではプロセス間共有のために Redis 等を使う。開発・デモ用。
# コネクションはセッション終了時に close() する。
_active_sessions: dict[str, tuple[CallController, sqlite3.Connection]] = {}

# CRM アダプター（モック）
_crm = InMemoryCRMAdapter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """起動時にサンプルリードを登録する。"""
    for i in range(5):
        _crm.register_lead(
            lead_id=f"LEAD-{i+1:04d}",
            company="テスト株式会社",
            contact_name=f"担当者{i+1}",
            phone=f"03-0000-{i+1:04d}",
        )
    yield


app = FastAPI(
    title="Reception Breakthrough API",
    version="0.1.0",
    description="受付突破 AI モジュール — 自己架電管理 REST API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# リクエスト / レスポンス スキーマ
# ---------------------------------------------------------------------------


class SessionCreateRequest(BaseModel):
    lead_id: str = Field(..., description="CRM のリード ID")
    mode: str = Field("AI", description='"AI" または "HUMAN"')


class StepRequest(BaseModel):
    input_id: str = Field(..., description='インテント ID または イベント ID (例: "A1_listening")')


class StepTextRequest(BaseModel):
    utterance: str = Field(..., description="受付担当者の発話テキスト（生テキスト）")


class SessionResponse(BaseModel):
    session_id: str
    lead_id: str
    mode: str
    state: str
    is_terminated: bool
    outcome_id: str | None


class StepResponse(BaseModel):
    session_id: str
    from_state: str
    to_state: str
    input_id: str
    classifier_intent: str | None
    classifier_confidence: float
    response_text: str | None
    is_terminated: bool
    outcome_id: str | None


# ---------------------------------------------------------------------------
# ヘルスチェック
# ---------------------------------------------------------------------------


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """サービスの死活確認。"""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# リード
# ---------------------------------------------------------------------------


@app.get("/leads/next", tags=["leads"])
def get_next_lead() -> dict[str, Any]:
    """次に架電すべきリードを 1 件返す（InMemory モック）。

    全リードが架電済みの場合は 204 の代わりに ``{"lead_id": null}`` を返す。
    """
    lead = _crm.pop_next_lead()
    if lead is None:
        return {"lead_id": None, "message": "no leads available"}
    return {
        "lead_id": lead["lead_id"],
        "company": lead.get("company"),
        "contact_name": lead.get("contact_name"),
        "phone": lead.get("phone"),
    }


# ---------------------------------------------------------------------------
# セッション管理
# ---------------------------------------------------------------------------


@app.post("/sessions", tags=["sessions"], status_code=201)
def create_session(body: SessionCreateRequest) -> SessionResponse:
    """新しい架電セッションを開始して CallController を初期化する。"""
    if body.mode not in ("AI", "HUMAN"):
        raise HTTPException(status_code=422, detail='mode は "AI" または "HUMAN" のみ有効')

    # セッションが生きている間、接続を保持する（呼び出し側が close 責任を持つ）
    conn = open_persistent_connection(_DB_PATH)
    try:
        ctrl = CallController(
            lead_id=body.lead_id,
            mode=body.mode,
            conn=conn,
        )
        # 最初の遷移 (EV_DIALED) を自動で送る
        ctrl.step("EV_DIALED")
    except Exception:
        conn.close()
        raise

    _active_sessions[ctrl.session_id] = (ctrl, conn)

    return SessionResponse(
        session_id=ctrl.session_id,
        lead_id=body.lead_id,
        mode=body.mode,
        state=ctrl.state,
        is_terminated=ctrl.is_terminated,
        outcome_id=ctrl.outcome_id,
    )


@app.get("/sessions", tags=["sessions"])
def list_sessions(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    outcome_id: str | None = Query(None),
) -> dict[str, Any]:
    """セッション一覧を返す（ページネーション付き）。"""
    with get_connection(_DB_PATH) as conn:
        if outcome_id:
            rows = conn.execute(
                """
                SELECT id, lead_id, mode, started_at, ended_at,
                       final_state_id, outcome_id, created_at
                FROM call_sessions
                WHERE outcome_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (outcome_id, limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, lead_id, mode, started_at, ended_at,
                       final_state_id, outcome_id, created_at
                FROM call_sessions
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()

    sessions = [
        {
            "session_id": r[0],
            "lead_id": r[1],
            "mode": r[2],
            "started_at": r[3],
            "ended_at": r[4],
            "final_state_id": r[5],
            "outcome_id": r[6],
            "created_at": r[7],
        }
        for r in rows
    ]
    return {"sessions": sessions, "limit": limit, "offset": offset}


@app.get("/sessions/{session_id}", tags=["sessions"])
def get_session(session_id: str) -> dict[str, Any]:
    """セッション詳細を返す。"""
    with get_connection(_DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT id, lead_id, mode, started_at, ended_at,
                   final_state_id, outcome_id, rejection_reason, created_at, updated_at
            FROM call_sessions WHERE id = ?
            """,
            (session_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="session not found")

    return {
        "session_id": row[0],
        "lead_id": row[1],
        "mode": row[2],
        "started_at": row[3],
        "ended_at": row[4],
        "final_state_id": row[5],
        "outcome_id": row[6],
        "rejection_reason": row[7],
        "created_at": row[8],
        "updated_at": row[9],
    }


@app.get("/sessions/{session_id}/transitions", tags=["sessions"])
def get_transitions(session_id: str) -> dict[str, Any]:
    """セッションの状態遷移一覧を返す。"""
    with get_connection(_DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT seq, from_state, to_state, input_kind, input_id,
                   response_template_id, at, mode
            FROM state_transitions
            WHERE session_id = ?
            ORDER BY seq ASC
            """,
            (session_id,),
        ).fetchall()

    return {
        "session_id": session_id,
        "transitions": [
            {
                "seq": r[0],
                "from_state": r[1],
                "to_state": r[2],
                "input_kind": r[3],
                "input_id": r[4],
                "response_template_id": r[5],
                "at": r[6],
                "mode": r[7],
            }
            for r in rows
        ],
    }


@app.get("/sessions/{session_id}/outcome", tags=["sessions"])
def get_outcome(session_id: str) -> dict[str, Any]:
    """セッションのアウトカムを返す。未終了の場合は 404。"""
    with get_connection(_DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT outcome_id, final_state_id, rejection_reason,
                   last_input_kind, last_input_id, created_at
            FROM outcomes WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="outcome not found — session may still be active",
        )

    return {
        "session_id": session_id,
        "outcome_id": row[0],
        "final_state_id": row[1],
        "rejection_reason": row[2],
        "last_input_kind": row[3],
        "last_input_id": row[4],
        "created_at": row[5],
    }


# ---------------------------------------------------------------------------
# ステップ制御
# ---------------------------------------------------------------------------


def _get_active_ctrl(session_id: str) -> tuple[CallController, sqlite3.Connection]:
    """稼働中セッションを取得する。見つからない場合は 404。"""
    entry = _active_sessions.get(session_id)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "active session not found — "
                "session may be terminated or server was restarted"
            ),
        )
    return entry


@app.post("/sessions/{session_id}/step", tags=["sessions"])
def step_session(session_id: str, body: StepRequest) -> StepResponse:
    """インテント ID / イベント ID を直接与えて 1 ステップ進める。

    HUMAN モードで担当者が手動でインテントを選択する場合に使用する。
    """
    ctrl, conn = _get_active_ctrl(session_id)

    if ctrl.is_terminated:
        raise HTTPException(status_code=409, detail="session already terminated")

    result = ctrl.step(body.input_id)

    if result.is_terminated:
        _active_sessions.pop(session_id, None)
        conn.close()

    return StepResponse(
        session_id=session_id,
        from_state=result.transition.from_state,
        to_state=result.transition.to_state,
        input_id=result.transition.input_id,
        classifier_intent=result.classifier_intent,
        classifier_confidence=result.classifier_confidence,
        response_text=result.response.text if result.response else None,
        is_terminated=result.is_terminated,
        outcome_id=result.outcome_id,
    )


@app.post("/sessions/{session_id}/step_text", tags=["sessions"])
def step_session_text(session_id: str, body: StepTextRequest) -> StepResponse:
    """受付の発話テキストを分類してステップを進める。

    AI モードで音声認識テキストを受け取り、インテント分類 → SM 遷移までを一括で行う。
    """
    ctrl, conn = _get_active_ctrl(session_id)

    if ctrl.is_terminated:
        raise HTTPException(status_code=409, detail="session already terminated")

    result = ctrl.classify_and_step(body.utterance)

    if result.is_terminated:
        _active_sessions.pop(session_id, None)
        conn.close()

    return StepResponse(
        session_id=session_id,
        from_state=result.transition.from_state,
        to_state=result.transition.to_state,
        input_id=result.transition.input_id,
        classifier_intent=result.classifier_intent,
        classifier_confidence=result.classifier_confidence,
        response_text=result.response.text if result.response else None,
        is_terminated=result.is_terminated,
        outcome_id=result.outcome_id,
    )


# ---------------------------------------------------------------------------
# メトリクス
# ---------------------------------------------------------------------------


@app.get("/metrics/latest", tags=["metrics"])
def get_latest_metrics(
    target_date: str | None = Query(None, description="YYYY-MM-DD 形式。省略時は今日"),
) -> dict[str, Any]:
    """指定日（省略時は今日）の metric_snapshots を全件返す。"""
    date_str = target_date or date.today().isoformat()

    with get_connection(_DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT scope_type, scope_key, metric_name, metric_value
            FROM metric_snapshots
            WHERE metric_date = ?
            ORDER BY scope_type, scope_key, metric_name
            """,
            (date_str,),
        ).fetchall()

    return {
        "metric_date": date_str,
        "metrics": [
            {
                "scope_type": r[0],
                "scope_key": r[1],
                "metric_name": r[2],
                "metric_value": r[3],
            }
            for r in rows
        ],
    }
