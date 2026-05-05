"""
Zoom Phone 録音一括ダウンロードスクリプト

認証（優先順）:
  A. ZOOM_CDP_URL — 既存ChromeにCDP接続（ログイン済みCookieをそのまま利用）
  B. ZOOM_STORAGE_STATE または tools/zoom_auth.json — Playwright storage_state
  C. ZOOM_COOKIES_FILE — Cookie JSON（Playwright形式の配列）
  D. ZOOM_EMAIL + ZOOM_PASSWORD — メール/パスワード（後方互換）

使い方（tools/ 直下から）:
  .venv/bin/python src/zoom_recording_downloader.py [--dry-run] [--from DATE] [--to DATE]

セッション保存（SSO等は手動ログイン後にEnter）:
  .venv/bin/python src/zoom_recording_downloader.py --save-auth
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    sync_playwright,
    TimeoutError as PWTimeout,
)

TOOLS_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AUTH_JSON = TOOLS_DIR / "zoom_auth.json"
ENV_PATH = TOOLS_DIR / ".env"

load_dotenv(ENV_PATH)

ZOOM_EMAIL = os.getenv("ZOOM_EMAIL", "")
ZOOM_PASSWORD = os.getenv("ZOOM_PASSWORD", "")
ZOOM_HEADLESS = os.getenv("ZOOM_HEADLESS", "false").lower() == "true"
ZOOM_FROM_DATE = os.getenv("ZOOM_FROM_DATE", "")
ZOOM_TO_DATE = os.getenv("ZOOM_TO_DATE", "")
ZOOM_CDP_URL = os.getenv("ZOOM_CDP_URL", "").strip()
ZOOM_STORAGE_STATE_ENV = os.getenv("ZOOM_STORAGE_STATE", "").strip()
ZOOM_COOKIES_FILE = os.getenv("ZOOM_COOKIES_FILE", "").strip()

RECORDINGS_URL = "https://zoom.us/account/recording/phone"

HUMAN_WAIT_SHORT = (0.4, 1.2)
HUMAN_WAIT_MEDIUM = (1.5, 3.5)
HUMAN_WAIT_LONG = (3.0, 6.0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Zoom Phone 録音一括ダウンロード")
    parser.add_argument(
        "--project-root",
        default="",
        help="PJ ルート（省略時は本ファイルから自動算出: …/projects/<slug>/）",
    )
    parser.add_argument("--from", dest="from_date", default=ZOOM_FROM_DATE or "")
    parser.add_argument("--to", dest="to_date", default=ZOOM_TO_DATE or "")
    parser.add_argument("--headless", action="store_true", default=ZOOM_HEADLESS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--save-auth",
        action="store_true",
        help="手動でZoomにログインした後、storage_state を保存して終了",
    )
    parser.add_argument(
        "--save-auth-path",
        default="",
        help="--save-auth 時の保存先（省略時は ZOOM_STORAGE_STATE または zoom_auth.json）",
    )
    return parser.parse_args()


def resolve_project_root(args: argparse.Namespace) -> Path:
    """--project-root があればそれを使い、なければスクリプト配置から PJ ルートを推定する"""
    raw = getattr(args, "project_root", "") or ""
    if str(raw).strip():
        return Path(raw).expanduser().resolve()
    return PROJECT_ROOT


def resolve_download_dir(args: argparse.Namespace) -> Path:
    """ZOOM_DOWNLOAD_DIR が設定されていれば優先。未設定なら <PJ>/raw/zoom_recordings"""
    env_dir = os.getenv("ZOOM_DOWNLOAD_DIR", "").strip()
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    root = resolve_project_root(args)
    return (root / "raw" / "zoom_recordings").resolve()


def resolve_dates(from_date: str, to_date: str) -> tuple[str, str]:
    today = date.today()
    resolved_to = date.fromisoformat(to_date) if to_date else today
    resolved_from = date.fromisoformat(from_date) if from_date else today - timedelta(days=30)
    return resolved_from.isoformat(), resolved_to.isoformat()


def human_wait(range_sec: tuple[float, float] = HUMAN_WAIT_SHORT) -> None:
    time.sleep(random.uniform(*range_sec))


def human_type(page: Page, selector: str, text: str) -> None:
    el = page.query_selector(selector)
    if not el:
        return
    el.click()
    human_wait(HUMAN_WAIT_SHORT)
    for char in text:
        el.type(char)
        time.sleep(random.uniform(0.05, 0.18))


def human_scroll(page: Page) -> None:
    viewport_height = page.viewport_size["height"] if page.viewport_size else 800
    scroll_times = random.randint(1, 3)
    for _ in range(scroll_times):
        delta = random.randint(200, viewport_height)
        page.mouse.wheel(0, delta)
        human_wait(HUMAN_WAIT_SHORT)
    page.mouse.wheel(0, -random.randint(50, 200))
    human_wait(HUMAN_WAIT_SHORT)


def human_move_mouse(page: Page) -> None:
    vp = page.viewport_size or {"width": 1280, "height": 800}
    x = random.randint(100, vp["width"] - 100)
    y = random.randint(100, vp["height"] - 100)
    page.mouse.move(x, y)


def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip()


def storage_state_path_resolved() -> Path | None:
    """Bモード: 環境変数またはデフォルト zoom_auth.json"""
    if ZOOM_STORAGE_STATE_ENV:
        p = Path(ZOOM_STORAGE_STATE_ENV).expanduser()
        return p if p.is_file() else None
    if DEFAULT_AUTH_JSON.is_file():
        return DEFAULT_AUTH_JSON
    return None


def resolve_auth_mode() -> str:
    if ZOOM_CDP_URL:
        return "cdp"
    if ZOOM_STORAGE_STATE_ENV:
        p = Path(ZOOM_STORAGE_STATE_ENV).expanduser()
        if not p.is_file():
            print(
                f"[ERROR] ZOOM_STORAGE_STATE が指定されていますがファイルがありません: {p}",
                file=sys.stderr,
            )
            sys.exit(1)
        return "storage_state"
    if DEFAULT_AUTH_JSON.is_file():
        return "storage_state"
    if ZOOM_COOKIES_FILE:
        cf = Path(ZOOM_COOKIES_FILE).expanduser()
        if not cf.is_file():
            print(
                f"[ERROR] ZOOM_COOKIES_FILE が指定されていますがファイルがありません: {cf}",
                file=sys.stderr,
            )
            sys.exit(1)
        return "cookies"
    if ZOOM_EMAIL and ZOOM_PASSWORD:
        return "password"
    return "none"


def load_cookies_from_file(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "cookies" in raw:
        raw = raw["cookies"]
    if not isinstance(raw, list):
        raise ValueError("Cookie JSON は配列、または { \"cookies\": [...] } 形式である必要があります")
    return raw


def download_with_context(context: BrowserContext, url: str, dest: Path) -> bool:
    """同一BrowserContextのCookieでHTTP取得（urllibよりサブドメイン跨ぎに強い）"""
    if dest.exists():
        print(f"  [SKIP] すでに存在: {dest.name}")
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        resp = context.request.get(url, timeout=120_000)
        if not resp.ok:
            print(f"  [ERR]  {dest.name}: HTTP {resp.status} {resp.status_text}", file=sys.stderr)
            return False
        dest.write_bytes(resp.body())
        print(f"  [OK]   {dest.name}")
        return True
    except Exception as e:
        print(f"  [ERR]  {dest.name}: {e}", file=sys.stderr)
        return False


def login(page: Page, email: str, password: str) -> None:
    print("ログイン中（メール/パスワード）...")
    page.goto("https://zoom.us/signin")
    page.wait_for_load_state("networkidle")
    human_wait(HUMAN_WAIT_MEDIUM)
    human_move_mouse(page)
    human_wait(HUMAN_WAIT_SHORT)
    human_type(page, "#email", email)
    human_wait(HUMAN_WAIT_SHORT)
    human_type(page, "#password", password)
    human_wait(HUMAN_WAIT_SHORT)
    submit = page.query_selector('[type="submit"]')
    if submit:
        box = submit.bounding_box()
        if box:
            page.mouse.move(
                box["x"] + box["width"] / 2 + random.uniform(-5, 5),
                box["y"] + box["height"] / 2 + random.uniform(-3, 3),
            )
            human_wait(HUMAN_WAIT_SHORT)
        submit.click()
    try:
        page.wait_for_url(re.compile(r"zoom\.us/(profile|account)"), timeout=25000)
        human_wait(HUMAN_WAIT_LONG)
        print("ログイン完了")
    except PWTimeout:
        print("[WARNING] ログイン後のリダイレクトを確認できませんでした。手動で確認してください。")
        input("Enterキーを押して続行...")


def extract_recordings(page: Page) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    rows = page.query_selector_all("tr[data-qa], .recording-row, tbody tr")
    for row in rows:
        audio_btn = row.query_selector(
            "a[download], a[href*='.mp3'], a[href*='.m4a'], button[data-download-url]"
        )
        if not audio_btn:
            continue
        audio_url = (
            audio_btn.get_attribute("href")
            or audio_btn.get_attribute("data-download-url")
            or ""
        )
        if not audio_url:
            continue
        transcript_url = ""
        transcript_btn = row.query_selector(
            "a[href*='.vtt'], a[href*='.txt'], "
            "a[href*='transcript'], button[data-transcript-url], "
            "a[data-type='transcript']"
        )
        if transcript_btn:
            transcript_url = (
                transcript_btn.get_attribute("href")
                or transcript_btn.get_attribute("data-transcript-url")
                or ""
            )
        date_el = row.query_selector("[data-qa='date'], .date, td:first-child")
        caller_el = row.query_selector("[data-qa='caller'], .caller, td:nth-child(2)")
        rec_date = date_el.inner_text().strip() if date_el else "unknown"
        caller = caller_el.inner_text().strip() if caller_el else "unknown"
        entries.append({
            "audio_url": audio_url,
            "transcript_url": transcript_url,
            "date": rec_date,
            "caller": caller,
        })
    return entries


def navigate_to_recordings(page: Page, from_date: str, to_date: str) -> None:
    print(f"録音一覧ページへ移動（{from_date} 〜 {to_date}）")
    page.goto(RECORDINGS_URL)
    page.wait_for_load_state("networkidle")
    human_wait(HUMAN_WAIT_LONG)
    human_scroll(page)
    try:
        date_from = page.query_selector("input[placeholder*='開始'], input[name='from'], #dateFrom")
        date_to = page.query_selector("input[placeholder*='終了'], input[name='to'], #dateTo")
        if date_from and date_to:
            human_move_mouse(page)
            human_wait(HUMAN_WAIT_SHORT)
            date_from.triple_click()
            date_from.type(from_date)
            human_wait(HUMAN_WAIT_SHORT)
            date_to.triple_click()
            date_to.type(to_date)
            human_wait(HUMAN_WAIT_SHORT)
            search_btn = page.query_selector(
                "button[type='submit'], button:has-text('検索'), button:has-text('Search')"
            )
            if search_btn:
                box = search_btn.bounding_box()
                if box:
                    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                    human_wait(HUMAN_WAIT_SHORT)
                search_btn.click()
                page.wait_for_load_state("networkidle")
                human_wait(HUMAN_WAIT_MEDIUM)
    except Exception as e:
        print(f"[WARNING] 日付フィルタの設定をスキップ: {e}")


def new_browser_context(
    playwright: Playwright,
    args: argparse.Namespace,
    *,
    storage_state: str | Path | None,
    cookies: list[dict[str, Any]] | None,
) -> tuple[Browser, BrowserContext, Page, bool]:
    """
    Returns (browser, context, page, owns_browser).
    owns_browser=False のときは CDP 接続（browser.close() は切断のみ）。
    """
    if ZOOM_CDP_URL:
        browser = playwright.chromium.connect_over_cdp(ZOOM_CDP_URL)
        if not browser.contexts:
            print("[ERROR] CDP接続先にブラウザコンテキストがありません。Chromeを起動してから再試行してください。")
            sys.exit(1)
        ctx = browser.contexts[0]
        page = ctx.new_page()
        return browser, ctx, page, False

    browser = playwright.chromium.launch(
        headless=args.headless,
        args=["--disable-blink-features=AutomationControlled"],
    )
    ctx_opts: dict[str, Any] = {
        "accept_downloads": True,
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "viewport": {"width": 1366, "height": 768},
        "locale": "ja-JP",
        "timezone_id": "Asia/Tokyo",
    }
    if storage_state:
        ctx_opts["storage_state"] = str(storage_state)
    context = browser.new_context(**ctx_opts)
    if cookies:
        context.add_cookies(cookies)
    context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    page = context.new_page()
    return browser, context, page, True


def run_save_auth(playwright: Playwright, args: argparse.Namespace) -> None:
    """手動ログイン後に storage_state を保存"""
    out = args.save_auth_path or ZOOM_STORAGE_STATE_ENV or str(DEFAULT_AUTH_JSON)
    out_path = Path(out).expanduser().resolve()

    browser = playwright.chromium.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled"],
    )
    context = browser.new_context(
        accept_downloads=True,
        viewport={"width": 1366, "height": 768},
        locale="ja-JP",
        timezone_id="Asia/Tokyo",
    )
    context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    page = context.new_page()
    page.goto("https://zoom.us/signin")
    page.wait_for_load_state("domcontentloaded")
    print(
        "\nブラウザで Zoom にログインしてください（SSO / Google / 社内IdP など可）。\n"
        "必要なら録音一覧ページまで開いても構いません。\n"
    )
    input("ログインが完了したら Enter キーを押してください...")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    context.storage_state(path=str(out_path))
    print(f"\n[OK] storage_state を保存しました: {out_path}")
    print("次回からはこのファイルがあれば自動でログイン済み扱いになります（ZOOM_STORAGE_STATE でパス指定も可）。")
    browser.close()


def run(playwright: Playwright, args: argparse.Namespace) -> None:
    mode = resolve_auth_mode()
    if mode == "none":
        print(
            "[ERROR] 認証方法が設定されていません。次のいずれかを設定してください:\n"
            "  A. .env に ZOOM_CDP_URL=http://127.0.0.1:9222 （既存Chromeに接続）\n"
            "  B. --save-auth で zoom_auth.json を作成、または ZOOM_STORAGE_STATE にパス指定\n"
            "  C. ZOOM_COOKIES_FILE に Playwright形式の Cookie JSON\n"
            "  D. ZOOM_EMAIL + ZOOM_PASSWORD（メールログインのみ）",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"[認証モード] {mode}")

    from_date, to_date = resolve_dates(args.from_date, args.to_date)
    download_dir = resolve_download_dir(args)

    storage_path: Path | None = None
    cookie_list: list[dict[str, Any]] | None = None

    if mode == "storage_state":
        storage_path = storage_state_path_resolved()
        assert storage_path is not None
    elif mode == "cookies":
        cookie_list = load_cookies_from_file(Path(ZOOM_COOKIES_FILE).expanduser())

    browser, context, page, owns_browser = new_browser_context(
        playwright,
        args,
        storage_state=storage_path,
        cookies=cookie_list,
    )

    try:
        if mode == "password":
            login(page, ZOOM_EMAIL, ZOOM_PASSWORD)
        elif mode == "cdp":
            print("CDPモード: 既存ブラウザのセッションを使用します（ログイン操作はスキップ）。")
        elif mode == "storage_state":
            print(f"storage_state を読み込みました: {storage_path}")
        elif mode == "cookies":
            print(f"Cookie を読み込みました: {ZOOM_COOKIES_FILE}")

        navigate_to_recordings(page, from_date, to_date)

        all_entries: list[dict[str, str]] = []
        page_num = 1
        while True:
            print(f"ページ {page_num} を解析中...")
            human_scroll(page)
            human_move_mouse(page)
            entries = extract_recordings(page)
            all_entries.extend(entries)
            print(f"  {len(entries)} 件取得")
            next_btn = page.query_selector(
                "button[aria-label='次のページ'], .pagination-next:not([disabled]), a:has-text('Next')"
            )
            if not next_btn or not next_btn.is_enabled():
                break
            box = next_btn.bounding_box()
            if box:
                page.mouse.move(
                    box["x"] + box["width"] / 2 + random.uniform(-4, 4),
                    box["y"] + box["height"] / 2 + random.uniform(-4, 4),
                )
                human_wait(HUMAN_WAIT_SHORT)
            next_btn.click()
            page.wait_for_load_state("networkidle")
            human_wait(HUMAN_WAIT_MEDIUM)
            page_num += 1

        print(f"\n合計 {len(all_entries)} 件の録音を検出")

        if args.dry_run:
            print("\n[DRY-RUN] ダウンロードURLリスト:")
            for e in all_entries:
                has_t = "文字起こしあり" if e["transcript_url"] else "文字起こしなし"
                print(f"  {e['date']} | {e['caller']} | {has_t}")
                print(f"    音声     : {e['audio_url']}")
                if e["transcript_url"]:
                    print(f"    文字起こし: {e['transcript_url']}")
            return

        downloaded = 0
        skipped = 0
        for e in all_entries:
            rec_date = sanitize_filename(e["date"])
            caller = sanitize_filename(e["caller"])
            folder = download_dir / rec_date
            audio_url = e["audio_url"]
            transcript_url = e["transcript_url"]
            audio_ext = ".m4a" if ".m4a" in audio_url else ".mp3"
            audio_dest = folder / f"{rec_date}_{caller}{audio_ext}"
            if download_with_context(context, audio_url, audio_dest):
                downloaded += 1
            else:
                skipped += 1
            if transcript_url:
                transcript_ext = ".vtt" if ".vtt" in transcript_url else ".txt"
                transcript_dest = folder / f"{rec_date}_{caller}_transcript{transcript_ext}"
                if download_with_context(context, transcript_url, transcript_dest):
                    downloaded += 1
                else:
                    skipped += 1
            human_wait(HUMAN_WAIT_MEDIUM)

        print(f"\n完了: ダウンロード {downloaded} 件 / スキップ {skipped} 件")
        print(f"保存先: {download_dir}")
    finally:
        browser.close()


def main() -> None:
    args = parse_args()
    with sync_playwright() as playwright:
        if args.save_auth:
            run_save_auth(playwright, args)
        else:
            run(playwright, args)


if __name__ == "__main__":
    main()
