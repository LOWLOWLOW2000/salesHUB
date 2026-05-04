"""失敗セッション分析バッチジョブ (T-402).

失敗の定義
----------
``outcome_id IN ('OUT_REJECTED', 'OUT_NOISE', 'OUT_ABSENT')``

処理内容
--------
1. ``outcomes`` テーブルから失敗セッションを抽出する。
2. 各セッションの最後の ``state_transitions`` 行を JOIN で取得する。
3. ``failure_cases`` テーブルに保存する（冪等: 既存 session_id はスキップ）。
4. CSV を ``data/exports/failure_cases_<date>.csv`` に出力する。
"""

from __future__ import annotations

import csv
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from infra.db.local_db import get_connection
from infra.logging.logger import get_logger

_log = get_logger(__name__)

_FAILURE_OUTCOMES = ("OUT_REJECTED", "OUT_NOISE", "OUT_ABSENT")


# ---------------------------------------------------------------------------
# 結果型
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FailureCase:
    """抽出した失敗ケース 1 件。

    Attributes:
        session_id: 対象セッションの UUID。
        outcome_id: アウトカムコード（``OUT_REJECTED`` 等）。
        failure_state_id: 最後の遷移の ``from_state``。
        last_input_kind: 最後の遷移の入力種別（``intent`` / ``event``）。
        last_input_id: 最後の遷移の入力 ID。
        summary: 人が読むサマリ文字列。
    """

    session_id: str
    outcome_id: str
    failure_state_id: str | None
    last_input_kind: str | None
    last_input_id: str | None
    summary: str


# ---------------------------------------------------------------------------
# ジョブ本体
# ---------------------------------------------------------------------------


def run_failure_analysis(
    db_path: str | Path = "data/calls.db",
    export_dir: str | Path = "data/exports",
    target_date: date | None = None,
) -> list[FailureCase]:
    """失敗セッションを抽出して failure_cases テーブルに保存し CSV を出力する。

    Args:
        db_path: SQLite DB のパス。
        export_dir: CSV 出力先ディレクトリ（存在しなければ作成）。
        target_date: 集計対象日（``None`` で全期間）。

    Returns:
        今回新規追加した :class:`FailureCase` リスト。
    """
    export_path = Path(export_dir)
    export_path.mkdir(parents=True, exist_ok=True)

    date_str = (target_date or datetime.now(timezone.utc).date()).isoformat()
    cases: list[FailureCase] = []

    with get_connection(db_path) as conn:
        # 最後の state_transition を session ごとに 1 行で取得するサブクエリ
        base_query = """
            SELECT
                o.session_id,
                o.outcome_id,
                st.from_state     AS failure_state_id,
                st.input_kind     AS last_input_kind,
                st.input_id       AS last_input_id
            FROM outcomes o
            LEFT JOIN (
                SELECT session_id, from_state, input_kind, input_id
                FROM state_transitions
                WHERE (session_id, seq) IN (
                    SELECT session_id, MAX(seq)
                    FROM state_transitions
                    GROUP BY session_id
                )
            ) st ON st.session_id = o.session_id
            WHERE o.outcome_id IN ({placeholders})
        """.format(placeholders=",".join("?" * len(_FAILURE_OUTCOMES)))

        if target_date:
            query = base_query + " AND DATE(o.created_at) = ?"
            rows = conn.execute(query, (*_FAILURE_OUTCOMES, date_str)).fetchall()
        else:
            rows = conn.execute(base_query, _FAILURE_OUTCOMES).fetchall()

        existing_ids: set[str] = {
            r[0]
            for r in conn.execute(
                "SELECT session_id FROM failure_cases"
            ).fetchall()
        }

        now = datetime.now(timezone.utc).isoformat()
        new_rows: list[tuple] = []

        for session_id, outcome_id, failure_state_id, last_input_kind, last_input_id in rows:
            if session_id in existing_ids:
                continue
            summary = _build_summary(outcome_id, failure_state_id, last_input_id)
            cases.append(
                FailureCase(
                    session_id=session_id,
                    outcome_id=outcome_id,
                    failure_state_id=failure_state_id,
                    last_input_kind=last_input_kind,
                    last_input_id=last_input_id,
                    summary=summary,
                )
            )
            new_rows.append(
                (
                    str(uuid.uuid4()),
                    session_id,
                    outcome_id,
                    failure_state_id,
                    last_input_kind,
                    last_input_id,
                    summary,
                    now,
                )
            )

        if new_rows:
            conn.executemany(
                """
                INSERT INTO failure_cases
                  (id, session_id, outcome_id, failure_state_id,
                   last_input_kind, last_input_id, summary, extracted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                new_rows,
            )

    _log.info("failure_analysis_done", new_cases=len(cases))

    if cases:
        _export_csv(cases, export_path / f"failure_cases_{date_str}.csv")

    return cases


def _build_summary(
    outcome_id: str,
    failure_state_id: str | None,
    last_input_id: str | None,
) -> str:
    return (
        f"outcome={outcome_id}"
        f" | last_state={failure_state_id or 'N/A'}"
        f" | last_input={last_input_id or 'N/A'}"
    )


def _export_csv(cases: list[FailureCase], path: Path) -> None:
    fields = [
        "session_id",
        "outcome_id",
        "failure_state_id",
        "last_input_kind",
        "last_input_id",
        "summary",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(
            {
                "session_id": c.session_id,
                "outcome_id": c.outcome_id,
                "failure_state_id": c.failure_state_id or "",
                "last_input_kind": c.last_input_kind or "",
                "last_input_id": c.last_input_id or "",
                "summary": c.summary,
            }
            for c in cases
        )
    _log.info("failure_csv_exported", path=str(path))
