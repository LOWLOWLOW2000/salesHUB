"""
投入用CSV生成スクリプト（PeakHUB PJシート準拠）

使い方:
  python generate_intake_csv.py --source <ソース名> --output <出力ディレクトリ>

例:
  python generate_intake_csv.py --source baseconnect
  # デフォルト出力: <PJルート>/derived/intake/（本スクリプトは tools/src/ 配下想定）

入力:
  - 標準入力 or --input でTSVファイルを指定（スプシからコピペしたTSV）
  - 変換・正規化して95列CSVとして出力

出力:
  - YYYY-MM-DD_<source>_<件数>件.csv（UTF-8 BOM付き）
"""

import csv
import re
import sys
import argparse
import hashlib
from datetime import date
from pathlib import Path

HEADERS: list[str] = [
    "郵便番号", "被保険者数", "アプローチ不可", "重複フラグ", "_ignore",
    "リストソース", "IS担当者", "企業名", "HP", "都道府県", "市区町村", "住所",
    "事業タグ", "資本金", "売上高", "事業内容", "サービス内容", "部署情報", "拠点情報",
    "代表者名", "上場区分", "メール", "電話番号", "検索URL", "従業員数増減6ヶ月",
    "lead_id",
    "予備②", "予備③", "予備④", "予備⑤", "予備⑥", "予備⑦", "予備⑧", "予備⑨",
    "役職", "担当者名", "アドレス", "繋がりやすい電話番号",
    "担当者メモ", "次回アクション内容", "次回アクション日", "次回アクション時間",
    "温度感ランク", "最新ステータス", "最新架電日",
    "架電日①", "架電時間①", "コンタクト①", "架電結果①", "NG理由①",
    "架電日②", "架電時間②", "コンタクト②", "架電結果②", "NG理由②",
    "架電日③", "架電時間③", "コンタクト③", "架電結果③", "NG理由③",
    "架電日④", "架電時間④", "コンタクト④", "架電結果④", "NG理由④",
    "架電日⑤", "架電時間⑤", "コンタクト⑤", "架電結果⑤", "NG理由⑤",
    "架電日⑥", "架電時間⑥", "コンタクト⑥", "架電結果⑥", "NG理由⑥",
    "架電日⑦", "架電時間⑦", "コンタクト⑦", "架電結果⑦", "NG理由⑦",
    "架電日⑧", "架電時間⑧", "コンタクト⑧", "架電結果⑧", "NG理由⑧",
    "架電日⑨", "架電時間⑨", "コンタクト⑨", "架電結果⑨", "NG理由⑨",
    "架電日⑩", "架電時間⑩", "コンタクト⑩", "架電結果⑩", "NG理由⑩",
]

REQUIRED_COLUMNS = {"lead_id", "リストソース", "IS担当者", "企業名", "電話番号", "都道府県", "市区町村"}

ALWAYS_EMPTY = {
    "_ignore", "検索URL",
    "重複フラグ",
    "予備②", "予備③", "予備④", "予備⑤", "予備⑥", "予備⑦", "予備⑧", "予備⑨",
    "役職", "担当者名", "アドレス", "繋がりやすい電話番号",
    "担当者メモ", "次回アクション内容", "次回アクション日", "次回アクション時間",
    "温度感ランク", "最新ステータス", "最新架電日",
    "架電日①", "架電時間①", "コンタクト①", "架電結果①", "NG理由①",
    "架電日②", "架電時間②", "コンタクト②", "架電結果②", "NG理由②",
    "架電日③", "架電時間③", "コンタクト③", "架電結果③", "NG理由③",
    "架電日④", "架電時間④", "コンタクト④", "架電結果④", "NG理由④",
    "架電日⑤", "架電時間⑤", "コンタクト⑤", "架電結果⑤", "NG理由⑤",
    "架電日⑥", "架電時間⑥", "コンタクト⑥", "架電結果⑥", "NG理由⑥",
    "架電日⑦", "架電時間⑦", "コンタクト⑦", "架電結果⑦", "NG理由⑦",
    "架電日⑧", "架電時間⑧", "コンタクト⑧", "架電結果⑧", "NG理由⑧",
    "架電日⑨", "架電時間⑨", "コンタクト⑨", "架電結果⑨", "NG理由⑨",
    "架電日⑩", "架電時間⑩", "コンタクト⑩", "架電結果⑩", "NG理由⑩",
}


def normalize_phone(raw: str) -> str:
    """電話番号をハイフンなし・半角数字に正規化する"""
    return re.sub(r"[^0-9]", "", raw)


def normalize_postal(raw: str) -> str:
    """郵便番号を123-4567形式に正規化する"""
    digits = re.sub(r"[^0-9]", "", raw)
    return f"{digits[:3]}-{digits[3:7]}" if len(digits) >= 7 else digits


def normalize_money(raw: str) -> str:
    """資本金/売上高のカンマを除去して整数文字列にする"""
    cleaned = re.sub(r"[,，\s]", "", raw)
    try:
        return str(int(float(cleaned)))
    except ValueError:
        return cleaned


def normalize_text(raw: str) -> str:
    """改行・タブを半角スペースに置換する"""
    return re.sub(r"[\r\n\t]+", " ", raw).strip()


def normalize_url(raw: str) -> str:
    """URLが http(s):// で始まっていない場合はそのまま返す"""
    stripped = raw.strip()
    if stripped and not stripped.startswith(("http://", "https://")):
        return f"https://{stripped}"
    return stripped


def make_lead_id(prefix: str, seq: int) -> str:
    """lead_id を PEAK-000001 形式で生成する"""
    return f"{prefix}-{seq:06d}"


def deduplicate_key(row: dict) -> str:
    """重複判定用キー（電話番号 or 企業名+都道府県）"""
    phone = normalize_phone(row.get("電話番号", ""))
    name = row.get("企業名", "").strip()
    pref = row.get("都道府県", "").strip()
    base = phone if phone else f"{name}{pref}"
    return hashlib.md5(base.encode()).hexdigest()


def build_output_row(
    input_row: dict,
    source: str,
    lead_id: str,
) -> dict:
    """入力行を正規化して出力行（95列）を組み立てる"""
    row: dict[str, str] = {h: "" for h in HEADERS}

    # 常に空の列は空のまま
    for col in ALWAYS_EMPTY:
        row[col] = ""

    # デフォルト値
    row["アプローチ不可"] = "FALSE"
    row["_ignore"] = ""
    row["検索URL"] = ""
    row["リストソース"] = source
    row["lead_id"] = lead_id

    # 入力から転写（正規化つき）
    mapping = {
        "郵便番号": lambda v: normalize_postal(v),
        "被保険者数": lambda v: v.strip(),
        "企業名": lambda v: v.strip(),
        "HP": lambda v: normalize_url(v),
        "都道府県": lambda v: v.strip(),
        "市区町村": lambda v: v.strip(),
        "住所": lambda v: normalize_text(v),
        "事業タグ": lambda v: v.strip(),
        "資本金": lambda v: normalize_money(v),
        "売上高": lambda v: normalize_money(v),
        "事業内容": lambda v: normalize_text(v),
        "サービス内容": lambda v: normalize_text(v),
        "部署情報": lambda v: normalize_text(v),
        "拠点情報": lambda v: normalize_text(v),
        "代表者名": lambda v: v.strip(),
        "上場区分": lambda v: v.strip(),
        "メール": lambda v: v.strip(),
        "電話番号": lambda v: normalize_phone(v),
        "従業員数増減6ヶ月": lambda v: v.strip(),
        "IS担当者": lambda v: v.strip(),
    }

    for col, fn in mapping.items():
        raw = input_row.get(col, "")
        if raw:
            row[col] = fn(raw)

    return row


def validate_row(row: dict, seq: int) -> list[str]:
    """必須列チェック。問題があればエラーメッセージのリストを返す"""
    return [
        f"行{seq}: 必須列 '{col}' が空です"
        for col in REQUIRED_COLUMNS
        if not row.get(col, "").strip()
    ]


def generate_intake_csv(
    input_rows: list[dict],
    source: str,
    output_dir: Path,
    lead_prefix: str = "PEAK",
    start_seq: int = 1,
) -> Path:
    """投入用CSVを生成してファイルパスを返す"""
    output_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().strftime("%Y-%m-%d")
    count = len(input_rows)
    output_path = output_dir / f"{today}_{source}_{count}件.csv"

    seen_keys: set[str] = set()
    errors: list[str] = []
    output_rows: list[dict] = []

    for i, input_row in enumerate(input_rows, start=1):
        lead_id = make_lead_id(lead_prefix, start_seq + i - 1)
        out = build_output_row(input_row, source, lead_id)

        errors.extend(validate_row(out, i))

        dup_key = deduplicate_key(out)
        if dup_key in seen_keys:
            out["重複フラグ"] = "TRUE"
        else:
            seen_keys.add(dup_key)

        output_rows.append(out)

    if errors:
        for e in errors:
            print(f"[WARNING] {e}", file=sys.stderr)

    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"[OK] {output_path} ({count}行) を出力しました")
    return output_path


def parse_tsv_stdin() -> list[dict]:
    """標準入力からTSV（スプシのコピペ）を読み込む"""
    lines = sys.stdin.read().splitlines()
    if not lines:
        return []
    headers = lines[0].split("\t")
    return [
        dict(zip(headers, line.split("\t")))
        for line in lines[1:]
        if line.strip()
    ]


def parse_tsv_file(path: Path) -> list[dict]:
    """TSVファイルを読み込む"""
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter="\t")
        return list(reader)


def default_intake_output_dir() -> Path:
    """tools/src/ から見た PJ ルート直下の derived/intake"""
    return Path(__file__).resolve().parents[2] / "derived" / "intake"


def main() -> None:
    parser = argparse.ArgumentParser(description="PeakHUB 投入用CSV生成スクリプト")
    parser.add_argument("--source", required=True, help="リストソース名（例: baseconnect）")
    parser.add_argument(
        "--output",
        default=str(default_intake_output_dir()),
        help="出力ディレクトリ（デフォルト: <PJルート>/derived/intake）",
    )
    parser.add_argument("--input", help="入力TSVファイルパス（省略時は標準入力）")
    parser.add_argument("--prefix", default="PEAK", help="lead_idのプレフィックス（デフォルト: PEAK）")
    parser.add_argument("--start-seq", type=int, default=1, help="lead_idの開始連番（デフォルト: 1）")
    args = parser.parse_args()

    input_rows = (
        parse_tsv_file(Path(args.input))
        if args.input
        else parse_tsv_stdin()
    )

    if not input_rows:
        print("[ERROR] 入力データがありません", file=sys.stderr)
        sys.exit(1)

    generate_intake_csv(
        input_rows=input_rows,
        source=args.source,
        output_dir=Path(args.output),
        lead_prefix=args.prefix,
        start_seq=args.start_seq,
    )


if __name__ == "__main__":
    main()
