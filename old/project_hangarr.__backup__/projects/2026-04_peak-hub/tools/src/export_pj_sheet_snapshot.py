"""
Export Google Spreadsheet snapshots to local raw files.

- Exports the whole spreadsheet to XLSX via Drive API export.
- Optionally exports a specific sheet tab to CSV via Sheets API values.get.

OAuth credentials/token are compatible with `salse_consulting/scripts/sync_drive_full.py`.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
from pathlib import Path
from typing import Any, Sequence

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export PJ sheet snapshots (XLSX/CSV)")
    parser.add_argument("--spreadsheet-id", required=True, help="Spreadsheet ID (URL /d/<id>/)")
    parser.add_argument("--sheet-name", default="", help="Export only this tab to CSV as well")
    parser.add_argument(
        "--project-root",
        default="",
        help="PJ root directory. Default: inferred from this script location",
    )
    parser.add_argument(
        "--out-dir",
        default="",
        help="Output directory. Default: <project-root>/raw/gdrive_export",
    )
    parser.add_argument(
        "--base-name",
        default="PeakHub_PJシート",
        help="Base filename without extension",
    )
    parser.add_argument(
        "--format",
        choices=["xlsx", "csv", "both"],
        default="both",
        help="What to export (default: both)",
    )
    parser.add_argument(
        "--credentials",
        default="/home/mg_ogawa/DevelopmentRoom/salse_consulting/.secrets/google-drive-credentials.json",
        help="OAuth client credentials JSON path",
    )
    parser.add_argument(
        "--token",
        default="/home/mg_ogawa/DevelopmentRoom/salse_consulting/.secrets/google-drive-token.json",
        help="OAuth token cache path",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print outputs without writing")
    return parser.parse_args()


def infer_project_root(args: argparse.Namespace) -> Path:
    raw = (args.project_root or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def resolve_out_dir(args: argparse.Namespace, project_root: Path) -> Path:
    raw = (args.out_dir or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (project_root / "raw" / "gdrive_export").resolve()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def get_credentials(credentials_path: Path, token_path: Path, scopes: Sequence[str]) -> Credentials:
    creds: Credentials | None = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), scopes)
            print("\n--- Google認証 ---")
            print("ブラウザが自動で開かない場合、ターミナルに表示されるURLをコピーして開いてください。")
            print("※ Googleログイン後に http://127.0.0.1:<port>/ に戻る画面が出ます（それで成功です）")
            creds = flow.run_local_server(host="127.0.0.1", port=0, open_browser=False)
        ensure_parent(token_path)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds


def safe_component(name: str) -> str:
    sanitized = re.sub(r'[\\/*?:"<>|]', "_", name).strip()
    sanitized = sanitized.rstrip(" .")
    return sanitized or "_"


def download_request(request: Any, out_path: Path, dry_run: bool) -> None:
    if dry_run:
        print(f"[DRY] write: {out_path}")
        return
    ensure_parent(out_path)
    with out_path.open("wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def export_xlsx(drive_service: Any, spreadsheet_id: str, out_path: Path, dry_run: bool) -> None:
    request = drive_service.files().export_media(
        fileId=spreadsheet_id,
        mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    download_request(request, out_path, dry_run)


def export_sheet_csv(sheets_service: Any, spreadsheet_id: str, sheet_name: str, out_path: Path, dry_run: bool) -> None:
    res = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=sheet_name,
    ).execute()
    values = res.get("values", [])

    if dry_run:
        print(f"[DRY] write: {out_path} (rows={len(values)})")
        return

    ensure_parent(out_path)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for row in values:
            writer.writerow([str(cell) for cell in row])


def main() -> int:
    args = parse_args()
    project_root = infer_project_root(args)
    out_dir = resolve_out_dir(args, project_root)

    credentials_path = Path(args.credentials).expanduser().resolve()
    token_path = Path(args.token).expanduser().resolve()

    if not credentials_path.exists():
        raise SystemExit(
            f"credentials file not found: {credentials_path}\n"
            "Create OAuth client credentials and place JSON there."
        )

    creds = get_credentials(credentials_path, token_path, DEFAULT_SCOPES)
    drive = build("drive", "v3", credentials=creds)
    sheets = build("sheets", "v4", credentials=creds)

    stamp = dt.date.today().isoformat()
    base = safe_component(args.base_name)

    if args.format in ("xlsx", "both"):
        xlsx_path = out_dir / f"{stamp}_{base}.xlsx"
        export_xlsx(drive, args.spreadsheet_id.strip(), xlsx_path, args.dry_run)
        print(f"[OK] xlsx: {xlsx_path}")

    if args.format in ("csv", "both"):
        sheet_name = (args.sheet_name or "").strip()
        if not sheet_name:
            print("[SKIP] csv: --sheet-name is empty")
        else:
            csv_path = out_dir / f"{stamp}_{base}__{safe_component(sheet_name)}.csv"
            export_sheet_csv(sheets, args.spreadsheet_id.strip(), sheet_name, csv_path, args.dry_run)
            print(f"[OK] csv: {csv_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

