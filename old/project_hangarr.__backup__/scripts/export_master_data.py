"""
DB → data_project/master/ 一括エクスポートスクリプト

使い方:
  python export_master_data.py

出力先:
  ../master/accounts/all_accounts_YYYY-MM-DD.csv   全案件の企業リスト
  ../master/call_logs/all_call_logs_YYYY-MM-DD.csv 全案件の架電LOG

必要な環境変数:
  DATABASE_URL  例: postgresql://user:pass@localhost:5432/dbname

.env.local を data_project/scripts/.env.local に置いても読み込む。
"""

import csv
import os
import sys
from datetime import date
from pathlib import Path

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("[ERROR] psycopg2 が未インストールです: pip install psycopg2-binary", file=sys.stderr)
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env.local", override=False)
except ImportError:
    pass

SCRIPT_DIR = Path(__file__).parent
MASTER_DIR = SCRIPT_DIR.parent / "master"
TODAY = date.today().strftime("%Y-%m-%d")

ACCOUNTS_DIR = MASTER_DIR / "accounts"
CALL_LOGS_DIR = MASTER_DIR / "call_logs"


def get_connection():
    """DATABASE_URL から psycopg2 接続を作成する"""
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        print("[ERROR] DATABASE_URL が設定されていません", file=sys.stderr)
        sys.exit(1)
    return psycopg2.connect(url)


def export_accounts(cur: "psycopg2.extensions.cursor") -> Path:
    """
    全企業リストを CSV に出力する。

    SalesAccount は Company 単位で一意（複数プロジェクトで再利用される可能性がある）ため、
    特定の Project には紐付けない。プロジェクト別の利用履歴は call_logs から辿る。
    lead_id を持つレコードを優先的に上位に並べる。
    """
    ACCOUNTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ACCOUNTS_DIR / f"all_accounts_{TODAY}.csv"

    cur.execute("""
        SELECT
            sa."leadId"            AS lead_id,
            sa."clientRowId"       AS client_row_id,
            sa."displayName"       AS company_name,
            sa."phoneNorm"         AS phone,
            sa."headOfficeAddress" AS address,
            sa."domain"            AS domain,
            sa."corporateNumber"   AS corporate_number,
            c."name"               AS company_owner,
            sa."createdAt"         AS imported_at,
            sa."updatedAt"         AS updated_at
        FROM "SalesAccount" sa
        INNER JOIN "Company" c ON c."id" = sa."companyId"
        ORDER BY
            CASE WHEN sa."leadId" IS NOT NULL THEN 0 ELSE 1 END,
            sa."leadId",
            sa."createdAt"
    """)
    rows = cur.fetchall()
    col_names = [desc[0] for desc in cur.description]

    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=col_names)
        writer.writeheader()
        writer.writerows([dict(zip(col_names, row)) for row in rows])

    print(f"[OK] 企業リスト: {out_path} ({len(rows)}件)")
    return out_path


def export_call_logs(cur: "psycopg2.extensions.cursor") -> Path:
    """
    全架電 LOG を CSV に出力する。

    project / account / 最初の録音 を join して横持ちにする。
    audio_path / transcript_path は PJ_asset_Data 配下のパスを保存している前提
    （DB 側が相対パスで保持していればそのまま CSV に出る）。
    """
    CALL_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = CALL_LOGS_DIR / f"all_call_logs_{TODAY}.csv"

    cur.execute("""
        SELECT
            cl."id"               AS call_log_id,
            cl."startedAt"        AS started_at,
            cl."endedAt"          AS ended_at,
            p."slug"              AS project_slug,
            p."name"              AS project_name,
            u."email"             AS user_email,
            sa."leadId"           AS lead_id,
            sa."clientRowId"      AS client_row_id,
            sa."displayName"      AS company_name,
            sa."phoneNorm"        AS phone,
            cl."result"           AS result,
            cl."memo"             AS memo,
            cl."zoomMeetingId"    AS zoom_meeting_id,
            cr."sourceRecordingRef" AS recording_ref,
            cr."audioPath"        AS audio_path,
            cr."transcriptPath"   AS transcript_path
        FROM "CallLog" cl
        INNER JOIN "Project" p      ON p."id"  = cl."projectId"
        INNER JOIN "User" u         ON u."id"  = cl."userId"
        INNER JOIN "SalesAccount" sa ON sa."id" = cl."accountId"
        LEFT JOIN LATERAL (
            SELECT cr1."sourceRecordingRef", cr1."audioPath", cr1."transcriptPath"
            FROM "CallRecording" cr1
            WHERE cr1."callLogId" = cl."id"
            ORDER BY cr1."recordedAt" ASC
            LIMIT 1
        ) cr ON TRUE
        ORDER BY cl."startedAt" DESC
    """)
    rows = cur.fetchall()
    col_names = [desc[0] for desc in cur.description]

    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=col_names)
        writer.writeheader()
        writer.writerows([dict(zip(col_names, row)) for row in rows])

    print(f"[OK] 架電LOG: {out_path} ({len(rows)}件)")
    return out_path


def main() -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            export_accounts(cur)
            export_call_logs(cur)
    finally:
        conn.close()

    print(f"\n出力先: {MASTER_DIR}/")


if __name__ == "__main__":
    main()
