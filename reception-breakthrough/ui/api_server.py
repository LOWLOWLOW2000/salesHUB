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

GET  /docs                        Swagger UI（英語 / 日本語スキーマ切替）
GET  /openapi-en.json             英語 OpenAPI
GET  /openapi-ja.json             日本語 OpenAPI
"""

from __future__ import annotations

import csv
import io
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel, Field

import sqlite3

from app.config import get_config
from core.call_controller import CallController
from core.suggestion_engine import Suggestion, SuggestionEngine
from infra.db.local_db import get_connection, open_persistent_connection
from infra.external.ai_provider import IntentCandidate, get_intent_provider
from infra.external.crm_adapter import InMemoryCRMAdapter
from ui.openapi_i18n import localized_openapi_schema
from ui.swagger_docs import DOCS_HTML

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

# AI プロバイダ境界（既定: ローカル）と SuggestionEngine
# 本フェーズではローカルルールベース。クラウド差し替えは config 経由。
_intent_provider = get_intent_provider()
_suggestion_engine = SuggestionEngine()


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


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
    docs_url=None,
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


# ── /review 用スキーマ ──────────────────────────────────────────────────────


class ReviewSuggestRequest(BaseModel):
    utterance: str = Field(..., description="受付担当者の発話テキスト（生テキスト）")
    n: int = Field(3, ge=1, le=5, description="返す候補の最大件数")


class SuggestionItem(BaseModel):
    intent_id: str
    confidence: float
    source: str = Field(..., description='"local" / "cloud" — 候補の出所')
    next_state: str
    template_id: str | None
    template_text: str | None
    side_effects: list[str]
    why: str
    matched_keywords: list[str] = Field(default_factory=list)


class ReviewSuggestResponse(BaseModel):
    session_id: str
    transcript_id: str = Field(..., description="保存された受付発話の transcripts.id")
    label_id: str = Field(..., description="保存された intent_labels.id（decide で更新）")
    current_state: str
    last_c_intent: str | None
    suggestions: list[SuggestionItem]


class ReviewDecideRequest(BaseModel):
    label_id: str = Field(..., description="suggest が返した intent_labels.id")
    chosen_input_id: str = Field(
        ...,
        description='オペが採択した intent_id / event_id（例: "C2_soft_reject"）',
    )
    correct_intent: str | None = Field(
        None,
        description="オペが「正解」とみなす intent。None なら chosen_input_id と同一とみなす",
    )
    reviewed_by: str | None = Field(None, description="レビュアー識別子（任意）")
    note: str | None = Field(None, description="自由記述メモ（任意）")


class ReviewDecideResponse(BaseModel):
    session_id: str
    label_id: str
    from_state: str
    to_state: str
    input_id: str
    response_text: str | None
    is_terminated: bool
    outcome_id: str | None


class ReviewTurn(BaseModel):
    transcript_id: str
    speaker: str
    text: str
    created_at: str
    label: dict[str, Any] | None = None


class ReviewTurnsResponse(BaseModel):
    session_id: str
    turns: list[ReviewTurn]


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


# ---------------------------------------------------------------------------
# /review/* — 半自動オペレータ補助 + 検証ループ
# ---------------------------------------------------------------------------


def _suggestion_to_item(s: Suggestion) -> SuggestionItem:
    return SuggestionItem(
        intent_id=s.intent_id,
        confidence=s.confidence,
        source=s.source,
        next_state=s.next_state,
        template_id=s.template_id,
        template_text=s.template_text,
        side_effects=list(s.side_effects),
        why=s.why,
        matched_keywords=list(s.matched_keywords),
    )


def _persist_review_transcript(
    conn: sqlite3.Connection, session_id: str, utterance: str
) -> str:
    """Insert a transcripts row (speaker='reception') and return its id."""
    transcript_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO transcripts
          (id, session_id, recording_id, speaker, text,
           start_time_ms, end_time_ms, source_path)
        VALUES (?, ?, NULL, 'reception', ?, NULL, NULL, NULL)
        """,
        (transcript_id, session_id, utterance.strip()),
    )
    conn.commit()
    return transcript_id


def _persist_predicted_label(
    conn: sqlite3.Connection,
    transcript_id: str,
    predicted_intent: str,
    confidence: float,
) -> str:
    """Insert a fresh intent_labels row (correct_intent NULL)."""
    label_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO intent_labels
          (id, transcript_id, predicted_intent, correct_intent, confidence)
        VALUES (?, ?, ?, NULL, ?)
        """,
        (label_id, transcript_id, predicted_intent, max(0.0, min(1.0, confidence))),
    )
    conn.commit()
    return label_id


@app.post(
    "/review/{session_id}/suggest",
    tags=["review"],
    response_model=ReviewSuggestResponse,
)
def review_suggest(session_id: str, body: ReviewSuggestRequest) -> ReviewSuggestResponse:
    """受付発話を分類して Top-N 候補を返す（state machine は進めない）。

    記録: transcripts に発話を 1 行、intent_labels に予測ラベルを 1 行追加する。
    返却 ``label_id`` を ``/review/{id}/decide`` に渡すと、その行を更新しつつ
    state machine が前進する。
    """
    ctrl, conn = _get_active_ctrl(session_id)
    if ctrl.is_terminated:
        raise HTTPException(status_code=409, detail="session already terminated")

    utterance = body.utterance.strip()
    if not utterance:
        raise HTTPException(status_code=422, detail="utterance must not be empty")

    candidates: list[IntentCandidate] = _intent_provider.classify_topn(
        utterance, n=body.n
    )
    suggestions = _suggestion_engine.suggest(
        ctrl.state, candidates, last_c_intent=ctrl.last_c_intent
    )

    transcript_id = _persist_review_transcript(conn, session_id, utterance)
    head = candidates[0] if candidates else IntentCandidate("F1_unclear", 0.0, "local")
    label_id = _persist_predicted_label(
        conn, transcript_id, head.intent_id, head.confidence
    )

    return ReviewSuggestResponse(
        session_id=session_id,
        transcript_id=transcript_id,
        label_id=label_id,
        current_state=ctrl.state,
        last_c_intent=ctrl.last_c_intent,
        suggestions=[_suggestion_to_item(s) for s in suggestions],
    )


@app.post(
    "/review/{session_id}/decide",
    tags=["review"],
    response_model=ReviewDecideResponse,
)
def review_decide(session_id: str, body: ReviewDecideRequest) -> ReviewDecideResponse:
    """オペの採択結果で intent_labels を更新し、state machine を 1 ステップ進める。

    ``correct_intent`` を None のままにすると ``chosen_input_id`` と同一として
    記録する（= AI 予測どおりにオペが採択した、またはオペが手動で
    intent を選んだケース）。違うときは ``correct_intent`` で正解側を上書き
    保存（= ラベル訂正）。
    """
    ctrl, conn = _get_active_ctrl(session_id)
    if ctrl.is_terminated:
        raise HTTPException(status_code=409, detail="session already terminated")

    correct_intent = body.correct_intent or body.chosen_input_id
    cur = conn.execute(
        """
        UPDATE intent_labels
           SET correct_intent = ?,
               reviewed_by = ?,
               reviewed_at = ?,
               note = ?,
               updated_at = ?
         WHERE id = ?
        """,
        (
            correct_intent,
            body.reviewed_by,
            _now_iso(),
            body.note,
            _now_iso(),
            body.label_id,
        ),
    )
    conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="label_id not found")

    result = ctrl.step(body.chosen_input_id)
    if result.is_terminated:
        _active_sessions.pop(session_id, None)
        conn.close()

    return ReviewDecideResponse(
        session_id=session_id,
        label_id=body.label_id,
        from_state=result.transition.from_state,
        to_state=result.transition.to_state,
        input_id=result.transition.input_id,
        response_text=result.response.text if result.response else None,
        is_terminated=result.is_terminated,
        outcome_id=result.outcome_id,
    )


@app.get(
    "/review/{session_id}/turns",
    tags=["review"],
    response_model=ReviewTurnsResponse,
)
def review_turns(session_id: str) -> ReviewTurnsResponse:
    """セッションの発話 + 予測ラベル一覧を新しい順 → 古い順で返す。"""
    with get_connection(_DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT t.id,
                   t.speaker,
                   t.text,
                   t.created_at,
                   l.id,
                   l.predicted_intent,
                   l.correct_intent,
                   l.confidence,
                   l.reviewed_by,
                   l.reviewed_at,
                   l.note
              FROM transcripts t
              LEFT JOIN intent_labels l ON l.transcript_id = t.id
             WHERE t.session_id = ?
             ORDER BY t.created_at ASC, t.id ASC
            """,
            (session_id,),
        ).fetchall()

    turns: list[ReviewTurn] = []
    for r in rows:
        label: dict[str, Any] | None = None
        if r[4] is not None:
            label = {
                "label_id": r[4],
                "predicted_intent": r[5],
                "correct_intent": r[6],
                "confidence": r[7],
                "reviewed_by": r[8],
                "reviewed_at": r[9],
                "note": r[10],
            }
        turns.append(
            ReviewTurn(
                transcript_id=r[0],
                speaker=r[1],
                text=r[2],
                created_at=r[3],
                label=label,
            )
        )
    return ReviewTurnsResponse(session_id=session_id, turns=turns)


@app.get("/review/labels.csv", tags=["review"])
def review_labels_csv(
    limit: int = Query(1000, ge=1, le=10000),
) -> PlainTextResponse:
    """intent_labels を CSV で書き出す（オフライン分析・ルール改善用）。"""
    with get_connection(_DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT l.created_at,
                   t.session_id,
                   t.id,
                   t.text,
                   l.predicted_intent,
                   l.correct_intent,
                   l.confidence,
                   l.reviewed_by,
                   l.reviewed_at,
                   l.note
              FROM intent_labels l
              JOIN transcripts t ON t.id = l.transcript_id
             ORDER BY l.created_at DESC
             LIMIT ?
            """,
            (limit,),
        ).fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "created_at",
            "session_id",
            "transcript_id",
            "text",
            "predicted_intent",
            "correct_intent",
            "confidence",
            "reviewed_by",
            "reviewed_at",
            "note",
        ]
    )
    for r in rows:
        writer.writerow(["" if v is None else v for v in r])

    return PlainTextResponse(buf.getvalue(), media_type="text/csv; charset=utf-8")


# ---------------------------------------------------------------------------
# OpenAPI / Swagger（英語・日本語）
# ---------------------------------------------------------------------------


@app.get("/docs", include_in_schema=False)
def swagger_ui_docs() -> HTMLResponse:
    """Swagger UI。ツールバーで英語 / 日本語の OpenAPI を切り替える。"""
    return HTMLResponse(content=DOCS_HTML, media_type="text/html; charset=utf-8")


@app.get("/openapi-en.json", include_in_schema=False)
def openapi_schema_en() -> dict[str, Any]:
    """英語の OpenAPI 3 スキーマ。"""
    return localized_openapi_schema(app, "en")


@app.get("/openapi-ja.json", include_in_schema=False)
def openapi_schema_ja() -> dict[str, Any]:
    """日本語の OpenAPI 3 スキーマ。"""
    return localized_openapi_schema(app, "ja")
