"""未処理録音の文字起こしバッチジョブ (T-400).

冪等性
------
``call_recordings`` に対して ``transcripts`` が 0 件の行だけを処理する。
既にトランスクリプトがある ``recording_id`` はスキップする。

stub モード
-----------
``whisper.cpp`` が未インストールの環境では :class:`~voice.transcriber.Transcriber`
がスタブセグメント（``[transcription unavailable]``）を返す。
その場合も冪等性チェック用のレコードは挿入されるので、次回も処理対象外になる。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from infra.db.local_db import get_connection
from infra.logging.logger import get_logger
from voice.transcriber import Transcriber

_log = get_logger(__name__)


# ---------------------------------------------------------------------------
# 結果型
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TranscriptionJobResult:
    """1 件の録音に対する処理結果。

    Attributes:
        recording_id: ``call_recordings.id``。
        session_id: 親セッションの UUID。
        audio_path: 録音ファイルのパス。
        segments_count: 生成されたトランスクリプトセグメント数。
        skipped: ``True`` の場合、ファイルが見つからなかったためスキップした。
    """

    recording_id: str
    session_id: str
    audio_path: str
    segments_count: int
    skipped: bool


# ---------------------------------------------------------------------------
# ジョブ本体
# ---------------------------------------------------------------------------


def run_transcription_job(
    db_path: str | Path = "data/calls.db",
    whisper_bin: str | Path | None = None,
    model_path: str | Path | None = None,
    max_records: int = 100,
) -> list[TranscriptionJobResult]:
    """未処理録音を Transcriber に流してトランスクリプトを保存する。

    Args:
        db_path: SQLite DB のパス。
        whisper_bin: whisper.cpp バイナリのパス（``None`` で PATH 自動検索）。
        model_path: GGML モデルのパス。
        max_records: 1 実行で処理する最大録音数（安全弁）。

    Returns:
        処理した各録音の :class:`TranscriptionJobResult` リスト。
    """
    results: list[TranscriptionJobResult] = []

    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT cr.id, cr.session_id, cr.audio_path
            FROM call_recordings cr
            WHERE NOT EXISTS (
                SELECT 1 FROM transcripts t WHERE t.recording_id = cr.id
            )
            ORDER BY cr.recorded_at ASC
            LIMIT ?
            """,
            (max_records,),
        ).fetchall()

    _log.info("transcription_job_start", pending=len(rows))

    for recording_id, session_id, audio_path in rows:
        with get_connection(db_path) as conn:
            transcriber = Transcriber(
                session_id=session_id,
                whisper_bin=whisper_bin,
                model_path=model_path,
                conn=conn,
            )
            try:
                segments = transcriber.transcribe(
                    audio_path, recording_id=recording_id
                )
                results.append(
                    TranscriptionJobResult(
                        recording_id=recording_id,
                        session_id=session_id,
                        audio_path=audio_path,
                        segments_count=len(segments),
                        skipped=False,
                    )
                )
                _log.info(
                    "transcription_done",
                    recording_id=recording_id,
                    segments=len(segments),
                )
            except FileNotFoundError as exc:
                _log.error(
                    "transcription_file_not_found",
                    recording_id=recording_id,
                    error=str(exc),
                )
                results.append(
                    TranscriptionJobResult(
                        recording_id=recording_id,
                        session_id=session_id,
                        audio_path=audio_path,
                        segments_count=0,
                        skipped=True,
                    )
                )

    _log.info("transcription_job_done", processed=len(results))
    return results
