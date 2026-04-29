"""
IS_01_hangar/<project_slug>/ をスキャンして asset_manifest.csv を生成する。

使い方:
  python build_asset_manifest.py --slug 2026-04_peak-hub
  python build_asset_manifest.py --slug 2026-04_peak-hub --hangar /path/to/IS_01_hangar
  python build_asset_manifest.py --all

出力:
  data_project/by_project/<slug>/03_data_processed/asset_manifest.csv

挙動:
  - 既存の asset_manifest.csv があれば asset_id を維持
  - 実ファイルが消えた行は status=missing に更新
  - 新規ファイルは AST-XXXXXX を採番して追加
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_HANGAR = REPO_ROOT / "IS_01_hangar"
BY_PROJECT_DIR = REPO_ROOT / "data_project" / "by_project"
MANIFEST_FILENAME = "asset_manifest.csv"

HEADERS = [
    "asset_id",
    "asset_type",
    "lead_id",
    "call_log_id",
    "recording_ref",
    "project_slug",
    "relative_path",
    "bytes",
    "recorded_at",
    "created_at",
    "status",
    "sha1",
    "notes",
]

ASSET_TYPE_BY_TOPDIR: dict[str, str] = {
    "zoom_recordings": "zoom_recording",
    "reports": "report",
    "slides": "slide",
    "internal": "other",
}

AUDIO_EXTS = {".mp3", ".mp4", ".m4a", ".wav", ".aac", ".flac"}
TRANSCRIPT_EXTS = {".vtt", ".txt", ".json", ".srt"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

LEAD_ID_RE = re.compile(r"\b([A-Z][A-Z0-9]+-\d{4,})\b")
RECORDED_AT_RE = re.compile(r"(\d{8})_(\d{6})")


@dataclass
class ManifestRow:
    """asset_manifest.csv 1行ぶんのデータ"""

    asset_id: str
    asset_type: str
    project_slug: str
    relative_path: str
    status: str = "final"
    lead_id: str = ""
    call_log_id: str = ""
    recording_ref: str = ""
    bytes: str = ""
    recorded_at: str = ""
    created_at: str = ""
    sha1: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, str]:
        return {h: getattr(self, h) for h in HEADERS}


@dataclass
class ScanResult:
    """1PJ分のスキャン結果サマリー"""

    slug: str
    new_count: int = 0
    updated_count: int = 0
    missing_count: int = 0
    total_count: int = 0
    output_path: Path = field(default_factory=Path)


def detect_asset_type(rel_path: Path) -> str:
    """相対パスから asset_type を判定する"""
    top = rel_path.parts[0] if rel_path.parts else ""
    base = ASSET_TYPE_BY_TOPDIR.get(top, "")
    if base:
        if base == "zoom_recording" and rel_path.suffix.lower() in TRANSCRIPT_EXTS:
            return "transcript"
        return base

    suffix = rel_path.suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix in AUDIO_EXTS:
        return "zoom_recording"
    if suffix in TRANSCRIPT_EXTS:
        return "transcript"
    if suffix in IMAGE_EXTS:
        return "image"
    return "other"


def extract_lead_id(filename: str) -> str:
    """ファイル名から lead_id（PEAK-000123 等）を抽出する"""
    m = LEAD_ID_RE.search(filename)
    return m.group(1) if m else ""


def extract_recorded_at(filename: str) -> str:
    """ファイル名から YYYYMMDD_HHMMSS を抜き出して ISO8601 文字列にする"""
    m = RECORDED_AT_RE.search(filename)
    if not m:
        return ""
    try:
        dt = datetime.strptime(f"{m.group(1)}{m.group(2)}", "%Y%m%d%H%M%S")
        return dt.isoformat()
    except ValueError:
        return ""


def compute_sha1(path: Path, max_bytes: int = 50 * 1024 * 1024) -> str:
    """先頭 50MB だけ SHA1 を取る（大ファイル対策）"""
    try:
        h = hashlib.sha1()
        with path.open("rb") as f:
            h.update(f.read(max_bytes))
        return h.hexdigest()
    except OSError:
        return ""


def iter_files(root: Path) -> Iterable[Path]:
    """resource ディレクトリ配下のファイルを再帰的に列挙（隠しファイルは除外）"""
    if not root.is_dir():
        return
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part.startswith(".") for part in p.relative_to(root).parts):
            continue
        yield p


def load_existing_manifest(path: Path) -> dict[str, ManifestRow]:
    """既存の asset_manifest.csv を relative_path をキーに読み込む"""
    if not path.exists():
        return {}
    out: dict[str, ManifestRow] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row_norm = {h: (row.get(h) or "").strip() for h in HEADERS}
            rp = row_norm.get("relative_path", "")
            if not rp:
                continue
            out[rp] = ManifestRow(**row_norm)
    return out


def next_asset_id(existing_ids: set[str], used_seq: list[int]) -> str:
    """既存IDと衝突しない次の AST-XXXXXX を採番する"""
    seq = (max(used_seq) if used_seq else 0) + 1
    while True:
        candidate = f"AST-{seq:06d}"
        if candidate not in existing_ids:
            used_seq.append(seq)
            return candidate
        seq += 1


def parse_seq_from_id(asset_id: str) -> int:
    m = re.match(r"AST-(\d+)$", asset_id)
    return int(m.group(1)) if m else 0


def build_manifest_for_project(
    slug: str,
    hangar_root: Path,
    by_project_dir: Path,
    compute_hash: bool = False,
) -> ScanResult:
    """1PJ分の asset_manifest.csv を生成する"""
    project_hangar = hangar_root / slug
    out_dir = by_project_dir / slug / "03_data_processed"
    out_path = out_dir / MANIFEST_FILENAME

    if not project_hangar.is_dir():
        print(f"[WARN] hangar フォルダが存在しません: {project_hangar}", file=sys.stderr)

    existing = load_existing_manifest(out_path)
    existing_ids = {row.asset_id for row in existing.values()}
    used_seq = [parse_seq_from_id(aid) for aid in existing_ids]

    now = datetime.now().isoformat(timespec="seconds")
    rows: dict[str, ManifestRow] = {}
    new_count = 0
    updated_count = 0

    for absolute in iter_files(project_hangar):
        rel = absolute.relative_to(project_hangar)
        rel_str = rel.as_posix()
        prev = existing.get(rel_str)

        try:
            size = absolute.stat().st_size
        except OSError:
            size = 0

        if prev is not None:
            row = ManifestRow(
                asset_id=prev.asset_id,
                asset_type=prev.asset_type or detect_asset_type(rel),
                project_slug=slug,
                relative_path=rel_str,
                status=prev.status if prev.status not in {"missing", ""} else "final",
                lead_id=prev.lead_id or extract_lead_id(rel.name),
                call_log_id=prev.call_log_id,
                recording_ref=prev.recording_ref,
                bytes=str(size),
                recorded_at=prev.recorded_at or extract_recorded_at(rel.name),
                created_at=prev.created_at or now,
                sha1=prev.sha1 or (compute_sha1(absolute) if compute_hash else ""),
                notes=prev.notes,
            )
            if (
                row.bytes != prev.bytes
                or row.status != prev.status
                or row.lead_id != prev.lead_id
            ):
                updated_count += 1
        else:
            row = ManifestRow(
                asset_id=next_asset_id(existing_ids, used_seq),
                asset_type=detect_asset_type(rel),
                project_slug=slug,
                relative_path=rel_str,
                status="final",
                lead_id=extract_lead_id(rel.name),
                bytes=str(size),
                recorded_at=extract_recorded_at(rel.name),
                created_at=now,
                sha1=compute_sha1(absolute) if compute_hash else "",
            )
            existing_ids.add(row.asset_id)
            new_count += 1

        rows[rel_str] = row

    missing_count = 0
    for rel_str, prev in existing.items():
        if rel_str in rows:
            continue
        prev.status = "missing"
        prev.bytes = ""
        rows[rel_str] = prev
        missing_count += 1

    out_dir.mkdir(parents=True, exist_ok=True)
    sorted_rows = sorted(rows.values(), key=lambda r: r.asset_id)
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        for row in sorted_rows:
            writer.writerow(row.to_dict())

    return ScanResult(
        slug=slug,
        new_count=new_count,
        updated_count=updated_count,
        missing_count=missing_count,
        total_count=len(rows),
        output_path=out_path,
    )


def discover_project_slugs(by_project_dir: Path) -> list[str]:
    """data_project/by_project/ 配下のフォルダ名を PJ slug として列挙する"""
    if not by_project_dir.is_dir():
        return []
    return sorted(
        p.name for p in by_project_dir.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="IS_01_hangar スキャン -> asset_manifest.csv 生成")
    parser.add_argument("--slug", help="対象PJ slug（例: 2026-04_peak-hub）")
    parser.add_argument("--all", action="store_true", help="by_project/ 配下の全PJに対して実行")
    parser.add_argument("--hangar", default=str(DEFAULT_HANGAR), help="IS_01_hangar のパス")
    parser.add_argument("--with-sha1", action="store_true", help="SHA1 を計算する（重い）")
    args = parser.parse_args()

    if not args.slug and not args.all:
        parser.error("--slug か --all のどちらかを指定してください")

    hangar_root = Path(args.hangar).resolve()
    targets = (
        discover_project_slugs(BY_PROJECT_DIR) if args.all else [args.slug]
    )

    if not targets:
        print("[ERROR] 対象のPJが見つかりません", file=sys.stderr)
        sys.exit(1)

    for slug in targets:
        result = build_manifest_for_project(
            slug=slug,
            hangar_root=hangar_root,
            by_project_dir=BY_PROJECT_DIR,
            compute_hash=args.with_sha1,
        )
        print(
            f"[OK] {result.slug}: total={result.total_count} "
            f"new={result.new_count} updated={result.updated_count} "
            f"missing={result.missing_count} -> {result.output_path}"
        )


if __name__ == "__main__":
    main()
