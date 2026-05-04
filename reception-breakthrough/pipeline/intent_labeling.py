"""自動インテントラベリングバッチジョブ (T-401).

冪等性
------
``transcripts`` に対して ``intent_labels`` が 0 件の行だけを処理する。

対象発話者
----------
``speaker = 'reception'`` の発話のみラベリングする。
AI 側の発話（``speaker = 'ai'``）は分類対象外。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from core.intent_classifier import IntentClassifier
from infra.db.local_db import get_connection
from infra.logging.logger import get_logger

_log = get_logger(__name__)


# ---------------------------------------------------------------------------
# 結果型
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LabelingResult:
    """1 件の transcript に対するラベリング結果。

    Attributes:
        transcript_id: ``transcripts.id``。
        predicted_intent: 分類器が出力したインテント ID。
        confidence: 分類信頼度 (0.0–1.0)。
        skipped: ``True`` の場合、既にラベルがあったためスキップした。
    """

    transcript_id: str
    predicted_intent: str
    confidence: float
    skipped: bool


# ---------------------------------------------------------------------------
# ジョブ本体
# ---------------------------------------------------------------------------


def run_intent_labeling(
    db_path: str | Path = "data/calls.db",
    classifier: IntentClassifier | None = None,
    max_records: int = 500,
) -> list[LabelingResult]:
    """未ラベルの reception transcript にインテントを自動付与する。

    Args:
        db_path: SQLite DB のパス。
        classifier: 使用する :class:`~core.intent_classifier.IntentClassifier`。
                    省略時はデフォルト設定で生成する。
        max_records: 1 実行で処理する最大件数。

    Returns:
        ラベリングした各 transcript の :class:`LabelingResult` リスト。
    """
    clf = classifier or IntentClassifier()
    results: list[LabelingResult] = []

    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT t.id, t.text
            FROM transcripts t
            WHERE t.speaker = 'reception'
              AND NOT EXISTS (
                  SELECT 1 FROM intent_labels il WHERE il.transcript_id = t.id
              )
            ORDER BY t.created_at ASC
            LIMIT ?
            """,
            (max_records,),
        ).fetchall()

    _log.info("intent_labeling_start", pending=len(rows))
    now = datetime.now(timezone.utc).isoformat()

    for transcript_id, text in rows:
        cr = clf.classify(text)
        label_id = str(uuid.uuid4())

        with get_connection(db_path) as conn:
            conn.execute(
                """
                INSERT INTO intent_labels
                  (id, transcript_id, predicted_intent, confidence, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    label_id,
                    transcript_id,
                    cr.intent_id,
                    cr.confidence,
                    now,
                    now,
                ),
            )

        results.append(
            LabelingResult(
                transcript_id=transcript_id,
                predicted_intent=cr.intent_id,
                confidence=cr.confidence,
                skipped=False,
            )
        )
        _log.info(
            "intent_labeled",
            transcript_id=transcript_id,
            intent=cr.intent_id,
            confidence=cr.confidence,
        )

    _log.info("intent_labeling_done", labeled=len(results))
    return results
