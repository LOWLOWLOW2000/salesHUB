"""日次メトリクス集計バッチジョブ (T-403).

計算するメトリクス
------------------
- ``session / daily / total_sessions`` — 当日のセッション総数
- ``session / daily / connected_rate`` — OUT_CONNECTED の割合
- ``session / daily / rejected_rate``  — OUT_REJECTED の割合
- ``session / daily / absent_rate``    — OUT_ABSENT の割合
- ``session / daily / noise_rate``     — OUT_NOISE の割合
- ``session / daily / labels_reviewed`` — 人手レビュー済みラベル数
- ``session / daily / labels_corrected_ratio`` — レビュー済み中の訂正率
- ``session / daily / fallback_used_ratio`` — F1_unclear 予測の利用比率
- ``intent / <intent_id> / count``     — 当日のインテント別ラベリング件数
- ``intent / <intent_id> / correct_rate`` — 正解率（ヒューマンレビュー済みのみ）

冪等性
------
``metric_snapshots`` に ``UNIQUE(metric_date, scope_type, scope_key, metric_name)``
制約があるため ``INSERT OR REPLACE`` で何度実行しても OK。
"""

from __future__ import annotations

import csv
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

def _utc_today() -> date:
    """UTC 基準の今日の日付を返す（ローカル TZ のずれを避ける）。"""
    return datetime.now(timezone.utc).date()

from infra.db.local_db import get_connection
from infra.logging.logger import get_logger

_log = get_logger(__name__)


# ---------------------------------------------------------------------------
# 結果型
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MetricRow:
    """1 件のメトリクススナップショット。

    Attributes:
        metric_date: 集計日（ISO 8601 date 文字列）。
        scope_type: ``"session"`` / ``"intent"`` / ``"template"``。
        scope_key: スコープの識別子（例: ``"daily"``, ``"A1_listening"``）。
        metric_name: メトリクス名（例: ``"connected_rate"``）。
        metric_value: 値（件数は float にキャスト）。
    """

    metric_date: str
    scope_type: str
    scope_key: str
    metric_name: str
    metric_value: float


# ---------------------------------------------------------------------------
# ジョブ本体
# ---------------------------------------------------------------------------


def run_metrics(
    db_path: str | Path = "data/calls.db",
    export_dir: str | Path = "data/exports",
    target_date: date | None = None,
) -> list[MetricRow]:
    """日次メトリクスを集計して metric_snapshots に保存し CSV を出力する。

    Args:
        db_path: SQLite DB のパス。
        export_dir: CSV 出力先ディレクトリ（存在しなければ作成）。
        target_date: 集計対象日（``None`` で今日）。

    Returns:
        保存した :class:`MetricRow` リスト。
    """
    export_path = Path(export_dir)
    export_path.mkdir(parents=True, exist_ok=True)

    date_str = (target_date or _utc_today()).isoformat()
    rows: list[MetricRow] = []

    with get_connection(db_path) as conn:
        rows.extend(_compute_session_metrics(conn, date_str))
        rows.extend(_compute_review_metrics(conn, date_str))
        rows.extend(_compute_intent_metrics(conn, date_str))

        now = datetime.now(timezone.utc).isoformat()
        conn.executemany(
            """
            INSERT OR REPLACE INTO metric_snapshots
              (id, metric_date, scope_type, scope_key, metric_name, metric_value, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    str(uuid.uuid4()),
                    r.metric_date,
                    r.scope_type,
                    r.scope_key,
                    r.metric_name,
                    r.metric_value,
                    now,
                )
                for r in rows
            ],
        )

    _log.info("metrics_done", date=date_str, metrics=len(rows))

    if rows:
        _export_csv(rows, export_path / f"metrics_{date_str}.csv")

    return rows


# ---------------------------------------------------------------------------
# 集計ヘルパー
# ---------------------------------------------------------------------------


def _compute_session_metrics(conn, date_str: str) -> list[MetricRow]:
    """outcome 別セッション数と比率を集計する。"""
    total_row = conn.execute(
        "SELECT COUNT(*) FROM outcomes WHERE DATE(created_at) = ?",
        (date_str,),
    ).fetchone()
    total = total_row[0] if total_row else 0

    base = [MetricRow(date_str, "session", "daily", "total_sessions", float(total))]
    if total == 0:
        return base

    outcome_rows = conn.execute(
        """
        SELECT outcome_id, COUNT(*) AS cnt
        FROM outcomes
        WHERE DATE(created_at) = ?
        GROUP BY outcome_id
        """,
        (date_str,),
    ).fetchall()

    counts: dict[str, int] = {r[0]: r[1] for r in outcome_rows}

    rates = [
        ("OUT_CONNECTED", "connected_rate"),
        ("OUT_REJECTED", "rejected_rate"),
        ("OUT_ABSENT", "absent_rate"),
        ("OUT_NOISE", "noise_rate"),
    ]
    return base + [
        MetricRow(
            date_str,
            "session",
            "daily",
            label,
            round(counts.get(outcome_id, 0) / total, 4),
        )
        for outcome_id, label in rates
    ]


def _compute_intent_metrics(conn, date_str: str) -> list[MetricRow]:
    """インテント別ラベリング件数と正答率を集計する。"""
    rows = conn.execute(
        """
        SELECT
            il.predicted_intent,
            COUNT(*)                                                          AS cnt,
            SUM(CASE
                    WHEN il.correct_intent IS NOT NULL
                     AND il.correct_intent = il.predicted_intent THEN 1
                    ELSE 0
                END)                                                          AS correct,
            SUM(CASE WHEN il.correct_intent IS NOT NULL THEN 1 ELSE 0 END)   AS reviewed
        FROM intent_labels il
        WHERE DATE(il.created_at) = ?
        GROUP BY il.predicted_intent
        """,
        (date_str,),
    ).fetchall()

    metrics: list[MetricRow] = []
    for intent_id, cnt, correct, reviewed in rows:
        metrics.append(MetricRow(date_str, "intent", intent_id, "count", float(cnt)))
        if reviewed > 0:
            metrics.append(
                MetricRow(
                    date_str,
                    "intent",
                    intent_id,
                    "correct_rate",
                    round(correct / reviewed, 4),
                )
            )
    return metrics


def _compute_review_metrics(conn, date_str: str) -> list[MetricRow]:
    """レビュー系メトリクスを集計する。

    - labels_reviewed: ``correct_intent`` が埋まった件数
    - labels_corrected_ratio: reviewed のうち ``correct_intent != predicted_intent`` の割合
    - fallback_used_ratio: 予測 intent が ``F1_unclear`` だった割合
    """
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS total_labels,
            SUM(CASE WHEN correct_intent IS NOT NULL THEN 1 ELSE 0 END) AS reviewed_labels,
            SUM(
                CASE
                    WHEN correct_intent IS NOT NULL
                     AND correct_intent != predicted_intent THEN 1
                    ELSE 0
                END
            ) AS corrected_labels,
            SUM(CASE WHEN predicted_intent = 'F1_unclear' THEN 1 ELSE 0 END) AS fallback_labels
        FROM intent_labels
        WHERE DATE(created_at) = ?
        """,
        (date_str,),
    ).fetchone()

    total_labels = float(row[0] or 0)
    reviewed_labels = float(row[1] or 0)
    corrected_labels = float(row[2] or 0)
    fallback_labels = float(row[3] or 0)

    corrected_ratio = round(corrected_labels / reviewed_labels, 4) if reviewed_labels else 0.0
    fallback_ratio = round(fallback_labels / total_labels, 4) if total_labels else 0.0

    return [
        MetricRow(
            date_str,
            "session",
            "daily",
            "labels_reviewed",
            reviewed_labels,
        ),
        MetricRow(
            date_str,
            "session",
            "daily",
            "labels_corrected_ratio",
            corrected_ratio,
        ),
        MetricRow(
            date_str,
            "session",
            "daily",
            "fallback_used_ratio",
            fallback_ratio,
        ),
    ]


# ---------------------------------------------------------------------------
# CSV エクスポート
# ---------------------------------------------------------------------------


def _export_csv(rows: list[MetricRow], path: Path) -> None:
    fields = [
        "metric_date",
        "scope_type",
        "scope_key",
        "metric_name",
        "metric_value",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(
            {
                "metric_date": r.metric_date,
                "scope_type": r.scope_type,
                "scope_key": r.scope_key,
                "metric_name": r.metric_name,
                "metric_value": r.metric_value,
            }
            for r in rows
        )
    _log.info("metrics_csv_exported", path=str(path))
