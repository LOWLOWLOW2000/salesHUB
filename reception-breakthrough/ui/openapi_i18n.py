"""OpenAPI スキーマの英語 / 日本語ローカライズ（/docs の言語切り替え用）."""

from __future__ import annotations

import copy
from typing import Any, Literal

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

Lang = Literal["en", "ja"]

# ---------------------------------------------------------------------------
# info / tags
# ---------------------------------------------------------------------------

_INFO: dict[Lang, dict[str, str]] = {
    "en": {
        "title": "Reception Breakthrough API",
        "description": (
            "AI-assisted reception breakthrough — outbound call session REST API "
            "(T-500 self-call screen backend)."
        ),
    },
    "ja": {
        "title": "Reception Breakthrough API",
        "description": "受付突破 AI モジュール — 自己架電管理 REST API",
    },
}

_ORDERED_TAGS = ("system", "leads", "sessions", "review", "metrics")

_TAG_DESC: dict[Lang, dict[str, str]] = {
    "en": {
        "system": "Check whether the server is alive",
        "leads": "Get one “next lead” (mock CRM, for development)",
        "sessions": "Start / advance / inspect call sessions",
        "review": (
            "Operator-assist endpoints: get Top-N suggestions, decide, and "
            "export labels for offline improvement"
        ),
        "metrics": "Read daily aggregated-looking numbers from the DB",
    },
    "ja": {
        "system": "サーバーが生きているか確認する",
        "leads": "「次にかける相手（モック）」を 1 件もらう（開発用の仮 CRM）",
        "sessions": "架電セッションを開始・進行・確認する",
        "review": (
            "オペ補助：受付発話から候補を出す／採否を記録する／"
            "ラベル CSV を吐く（半自動 + 検証ループ用）"
        ),
        "metrics": "日次の集計っぽい数値を DB から読む",
    },
}

# operationId → summary / description（FastAPI は path + method で一意な id を付与）
_OPERATIONS: dict[str, dict[Lang, dict[str, str]]] = {
    "health_health_get": {
        "en": {
            "summary": "Check whether the server is alive",
            "description": "",
        },
        "ja": {
            "summary": "サーバーが生きているか確認する",
            "description": "",
        },
    },
    "get_next_lead_leads_next_get": {
        "en": {
            "summary": "Get one “next lead” (mock CRM, for development)",
            "description": "",
        },
        "ja": {
            "summary": "「次にかける相手（モック）」を 1 件もらう（開発用の仮 CRM）",
            "description": "",
        },
    },
    "create_session_sessions_post": {
        "en": {
            "summary": "Start a dialing session (state machine begins)",
            "description": "",
        },
        "ja": {
            "summary": "架電セッションを開始する（内部で状態マシンが動き始める）",
            "description": "",
        },
    },
    "list_sessions_sessions_get": {
        "en": {
            "summary": "View sessions: list / detail / transition log / outcome",
            "description": "",
        },
        "ja": {
            "summary": "過去や現在のセッションを一覧・詳細・遷移ログ・アウトカムで見る",
            "description": "",
        },
    },
    "get_session_sessions__session_id__get": {
        "en": {
            "summary": "View sessions: list / detail / transition log / outcome",
            "description": "",
        },
        "ja": {
            "summary": "過去や現在のセッションを一覧・詳細・遷移ログ・アウトカムで見る",
            "description": "",
        },
    },
    "get_transitions_sessions__session_id__transitions_get": {
        "en": {
            "summary": "View sessions: list / detail / transition log / outcome",
            "description": "",
        },
        "ja": {
            "summary": "過去や現在のセッションを一覧・詳細・遷移ログ・アウトカムで見る",
            "description": "",
        },
    },
    "get_outcome_sessions__session_id__outcome_get": {
        "en": {
            "summary": "View sessions: list / detail / transition log / outcome",
            "description": "",
        },
        "ja": {
            "summary": "過去や現在のセッションを一覧・詳細・遷移ログ・アウトカムで見る",
            "description": "",
        },
    },
    "step_session_sessions__session_id__step_post": {
        "en": {
            "summary": "Advance one step by explicit event/intent id (human mode)",
            "description": "",
        },
        "ja": {
            "summary": "「こういうイベント／インテントが起きた」として 1 手進める（人手モード向け）",
            "description": "",
        },
    },
    "step_session_text_sessions__session_id__step_text_post": {
        "en": {
            "summary": "Send utterance text; classify and advance one step (AI-ish flow)",
            "description": "",
        },
        "ja": {
            "summary": "受付の発話テキストを入れると、分類して 1 手進める（AI っぽい流れ）",
            "description": "",
        },
    },
    "get_latest_metrics_metrics_latest_get": {
        "en": {
            "summary": "Read daily aggregated-looking numbers from the DB",
            "description": "",
        },
        "ja": {
            "summary": "日次の集計っぽい数値を DB から読む",
            "description": "",
        },
    },
    "review_suggest_review__session_id__suggest_post": {
        "en": {
            "summary": "Classify utterance and return Top-N next-move suggestions (does not advance state)",
            "description": "",
        },
        "ja": {
            "summary": "受付発話を分類して「次の一手」候補を Top-N 返す（state machine は進めない）",
            "description": "",
        },
    },
    "review_decide_review__session_id__decide_post": {
        "en": {
            "summary": "Record operator decision (label correction) and advance state machine",
            "description": "",
        },
        "ja": {
            "summary": "オペの採否（必要ならラベル訂正）を記録して 1 手進める",
            "description": "",
        },
    },
    "review_turns_review__session_id__turns_get": {
        "en": {
            "summary": "List utterances and predicted/corrected labels for a session",
            "description": "",
        },
        "ja": {
            "summary": "セッションの発話と予測／訂正ラベル一覧を返す",
            "description": "",
        },
    },
    "review_labels_csv_review_labels_csv_get": {
        "en": {
            "summary": "Export intent labels as CSV (for offline rule/model improvement)",
            "description": "",
        },
        "ja": {
            "summary": "intent ラベルを CSV で書き出す（オフライン分析・ルール改善用）",
            "description": "",
        },
    },
}

# components.schemas.*.properties.*.description
_SCHEMA_PROP_DESC: dict[str, dict[Lang, str]] = {
    "SessionCreateRequest.lead_id": {
        "en": "CRM lead identifier.",
        "ja": "CRM のリード ID",
    },
    "SessionCreateRequest.mode": {
        "en": 'Dialing mode: `"AI"` or `"HUMAN"`.',
        "ja": '"AI" または "HUMAN"',
    },
    "StepRequest.input_id": {
        "en": 'Intent id or event id (e.g. `"A1_listening"`).',
        "ja": 'インテント ID または イベント ID (例: "A1_listening")',
    },
    "StepTextRequest.utterance": {
        "en": "Raw receptionist utterance text.",
        "ja": "受付担当者の発話テキスト（生テキスト）",
    },
}


def _base_schema(app: FastAPI) -> dict[str, Any]:
    """キャッシュに依存せず routes から OpenAPI を生成する。"""
    return get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description or "",
        routes=app.routes,
    )


def _apply_info_and_tags(schema: dict[str, Any], lang: Lang) -> None:
    info = schema.setdefault("info", {})
    info["title"] = _INFO[lang]["title"]
    info["description"] = _INFO[lang]["description"]

    desc_map = _TAG_DESC[lang]
    schema["tags"] = [
        {"name": name, "description": desc_map.get(name, "")} for name in _ORDERED_TAGS
    ]


def _apply_operations(schema: dict[str, Any], lang: Lang) -> None:
    paths = schema.get("paths")
    if not isinstance(paths, dict):
        return
    for _path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for _method, op in methods.items():
            if not isinstance(op, dict):
                continue
            oid = op.get("operationId")
            if not isinstance(oid, str):
                continue
            block = _OPERATIONS.get(oid, {}).get(lang)
            if not block:
                continue
            if "summary" in block:
                op["summary"] = block["summary"]
            if "description" in block:
                op["description"] = block["description"]
            _localize_parameters(op.get("parameters"), lang)


def _localize_parameters(params: Any, lang: Lang) -> None:
    if not isinstance(params, list):
        return
    for p in params:
        if not isinstance(p, dict):
            continue
        name = p.get("name")
        if not isinstance(name, str):
            continue
        if lang == "en":
            if name == "limit":
                p["description"] = "Page size (1–200)."
            elif name == "offset":
                p["description"] = "Zero-based row offset."
            elif name == "outcome_id":
                p["description"] = "Filter by final outcome id."
            elif name == "target_date":
                p["description"] = "Metric date `YYYY-MM-DD`; omit for today."
        elif lang == "ja":
            if name == "limit":
                p["description"] = "取得件数上限（1–200）。"
            elif name == "offset":
                p["description"] = "スキップ件数（0 始まり）。"
            elif name == "outcome_id":
                p["description"] = "アウトカム ID で絞り込み。"
            elif name == "target_date":
                p["description"] = "YYYY-MM-DD 形式。省略時は今日"


def _apply_schema_property_descriptions(schema: dict[str, Any], lang: Lang) -> None:
    comps = schema.get("components")
    if not isinstance(comps, dict):
        return
    schemas = comps.get("schemas")
    if not isinstance(schemas, dict):
        return
    for model_name, model in schemas.items():
        if not isinstance(model, dict) or model.get("type") != "object":
            continue
        props = model.get("properties")
        if not isinstance(props, dict):
            continue
        for prop_name, prop in props.items():
            if not isinstance(prop, dict):
                continue
            key = f"{model_name}.{prop_name}"
            row = _SCHEMA_PROP_DESC.get(key)
            if row and lang in row:
                prop["description"] = row[lang]


def localized_openapi_schema(app: FastAPI, lang: Lang) -> dict[str, Any]:
    """英語または日本語に揃えた OpenAPI 3 スキーマを返す。"""
    out = copy.deepcopy(_base_schema(app))
    _apply_info_and_tags(out, lang)
    _apply_operations(out, lang)
    _apply_schema_property_descriptions(out, lang)
    return out
