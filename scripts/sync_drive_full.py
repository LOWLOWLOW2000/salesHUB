"""
Synchronize a Google Drive folder tree to local filesystem.

- Downloads every non-Google file as-is.
- Exports Google native files to business-friendly formats:
  - Sheets -> .xlsx
  - Docs -> .docx
  - Slides -> .pptx
  - Drawings -> .pdf
- Writes .url shortcuts for unsupported native types.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
from pathlib import Path
from typing import Any, Dict, Iterable

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

EXPORT_RULES: Dict[str, Dict[str, str]] = {
    "application/vnd.google-apps.spreadsheet": {
        "ext": ".xlsx",
        "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    },
    "application/vnd.google-apps.document": {
        "ext": ".docx",
        "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
    "application/vnd.google-apps.presentation": {
        "ext": ".pptx",
        "mime": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    },
    "application/vnd.google-apps.drawing": {
        "ext": ".pdf",
        "mime": "application/pdf",
    },
}

GOOGLE_NATIVE_PREFIX = "application/vnd.google-apps."

INVALID_WINDOWS_CHARS = '<>:"/\\\\|?*'
RESERVED_WINDOWS_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def safe_windows_component(name: str) -> str:
    """
    Make a filename component safe for Windows/DriveFS.

    Drive can contain names that Windows can't represent (e.g. trailing dot/space).
    """
    sanitized = "".join("_" if c in INVALID_WINDOWS_CHARS else c for c in name)
    sanitized = sanitized.replace("\x00", "_")
    sanitized = sanitized.rstrip(" .")
    if not sanitized:
        sanitized = "_"
    if sanitized.upper() in RESERVED_WINDOWS_NAMES:
        sanitized = f"_{sanitized}"
    return sanitized


def safe_join(parent: Path, child_name: str) -> Path:
    safe_name = safe_windows_component(child_name)
    if safe_name != child_name:
        print(f"[WARN] renamed for Windows: {child_name!r} -> {safe_name!r}")
    return parent / safe_name


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root-folder-id",
        required=True,
        help="Google Drive folder ID to sync recursively",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Local output directory for mirrored files",
    )
    parser.add_argument(
        "--credentials",
        default=".secrets/google-drive-credentials.json",
        help="OAuth client credentials JSON path",
    )
    parser.add_argument(
        "--token",
        default=".secrets/google-drive-token.json",
        help="OAuth token cache path",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without writing files",
    )
    return parser.parse_args()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def get_credentials(credentials_path: Path, token_path: Path) -> Credentials:
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            print("\n--- Google認証 ---")
            print("ブラウザが自動で開かない場合、ターミナルに表示されるURLをコピーして開いてください。")
            print("※ Googleログイン後に http://127.0.0.1:<port>/ に戻る画面が出ます（それで成功です）")
            creds = flow.run_local_server(
                host="127.0.0.1",
                port=0,
                open_browser=False,
            )
        ensure_parent(token_path)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def iter_children(service: Any, folder_id: str) -> Iterable[Dict[str, Any]]:
    page_token = None
    while True:
        response = (
            service.files()
            .list(
                q=f"'{folder_id}' in parents and trashed = false",
                fields=(
                    "nextPageToken, files("
                    "id, name, mimeType, modifiedTime, md5Checksum, size, shortcutDetails"
                    ")"
                ),
                orderBy="folder,name",
                pageSize=1000,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                pageToken=page_token,
            )
            .execute()
        )
        yield from response.get("files", [])
        page_token = response.get("nextPageToken")
        if not page_token:
            break


def google_time_to_epoch(iso_text: str) -> float:
    normalized = iso_text.replace("Z", "+00:00")
    return dt.datetime.fromisoformat(normalized).timestamp()


def write_shortcut_url(path: Path, target_url: str, dry_run: bool) -> None:
    content = f"[InternetShortcut]\nURL={target_url}\n"
    if dry_run:
        print(f"[DRY] write shortcut: {path}")
        return
    ensure_parent(path)
    path.write_text(content, encoding="utf-8")


def download_binary(service: Any, file_id: str, out_path: Path, dry_run: bool) -> None:
    if dry_run:
        print(f"[DRY] download file: {out_path}")
        return
    ensure_parent(out_path)
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    with out_path.open("wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def export_native(service: Any, file_id: str, out_path: Path, export_mime: str, dry_run: bool) -> None:
    if dry_run:
        print(f"[DRY] export file: {out_path}")
        return
    ensure_parent(out_path)
    request = service.files().export_media(fileId=file_id, mimeType=export_mime)
    with out_path.open("wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def set_mtime(path: Path, modified_time: str) -> None:
    ts = google_time_to_epoch(modified_time)
    path.touch(exist_ok=True)
    os.utime(path, (ts, ts))


def should_download_binary(path: Path, remote: Dict[str, Any]) -> bool:
    if not path.exists():
        return True
    remote_size = int(remote.get("size", "0") or "0")
    local_size = path.stat().st_size
    if remote_size != local_size:
        return True
    if "modifiedTime" not in remote:
        return False
    remote_epoch = int(google_time_to_epoch(remote["modifiedTime"]))
    local_epoch = int(path.stat().st_mtime)
    return abs(remote_epoch - local_epoch) > 2


def sync_folder(service: Any, folder_id: str, local_dir: Path, dry_run: bool) -> None:
    local_dir.mkdir(parents=True, exist_ok=True)
    for item in iter_children(service, folder_id):
        name = item["name"]
        mime_type = item["mimeType"]
        item_id = item["id"]
        modified = item.get("modifiedTime")

        if mime_type == "application/vnd.google-apps.folder":
            sync_folder(service, item_id, safe_join(local_dir, name), dry_run)
            continue

        if mime_type == "application/vnd.google-apps.shortcut":
            shortcut = item.get("shortcutDetails") or {}
            target_id = shortcut.get("targetId", "")
            out_path = safe_join(local_dir, f"{name}.url")
            target_url = f"https://drive.google.com/file/d/{target_id}/view"
            write_shortcut_url(out_path, target_url, dry_run)
            if not dry_run and modified:
                set_mtime(out_path, modified)
            print(f"[OK] shortcut -> {out_path}")
            continue

        if mime_type.startswith(GOOGLE_NATIVE_PREFIX):
            rule = EXPORT_RULES.get(mime_type)
            if not rule:
                out_path = safe_join(local_dir, f"{name}.url")
                target_url = f"https://drive.google.com/file/d/{item_id}/view"
                write_shortcut_url(out_path, target_url, dry_run)
                if not dry_run and modified:
                    set_mtime(out_path, modified)
                print(f"[WARN] unsupported native type, wrote shortcut: {out_path}")
                continue

            out_path = safe_join(local_dir, f"{name}{rule['ext']}")
            try:
                export_native(service, item_id, out_path, rule["mime"], dry_run)
                if not dry_run and modified:
                    set_mtime(out_path, modified)
                print(f"[OK] exported: {out_path}")
            except HttpError as error:
                print(f"[ERR] export failed: {name} ({mime_type}) -> {error}")
            continue

        out_path = safe_join(local_dir, name)
        try:
            if should_download_binary(out_path, item):
                download_binary(service, item_id, out_path, dry_run)
                if not dry_run and modified:
                    set_mtime(out_path, modified)
                print(f"[OK] downloaded: {out_path}")
            else:
                print(f"[SKIP] unchanged: {out_path}")
        except HttpError as error:
            print(f"[ERR] download failed: {name} ({mime_type}) -> {error}")


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()
    credentials_path = Path(args.credentials).expanduser().resolve()
    token_path = Path(args.token).expanduser().resolve()

    if not credentials_path.exists():
        raise SystemExit(
            f"credentials file not found: {credentials_path}\n"
            "Create OAuth client credentials and place JSON there."
        )

    creds = get_credentials(credentials_path, token_path)
    service = build("drive", "v3", credentials=creds)

    print(f"[INFO] sync start: folder={args.root_folder_id}")
    print(f"[INFO] output: {output_dir}")
    sync_folder(service, args.root_folder_id, output_dir, args.dry_run)
    print("[INFO] sync done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

