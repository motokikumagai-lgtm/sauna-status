"""Chillnn 管理画面に自動ログインし、CSVをダウンロードする。"""

from __future__ import annotations

import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


def load_env(env_path: Path = ROOT / ".env") -> dict:
    """シンプルな .env パーサ"""
    env = {}
    if not env_path.exists():
        return env
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def month_range(today: date) -> tuple[date, date]:
    """当月初日 〜 翌月末日 を返す"""
    start = today.replace(day=1)
    # 翌月初日 -1日 = 翌月末日 ではない。翌々月初日 -1日 = 翌月末日
    next_month_start = (start + timedelta(days=32)).replace(day=1)
    month_after_next = (next_month_start + timedelta(days=32)).replace(day=1)
    end = month_after_next - timedelta(days=1)
    return start, end


def download_csv(
    today: date | None = None,
    headless: bool = True,
    start_override: date | None = None,
    end_override: date | None = None,
    output_name: str = "latest.csv",
) -> Path:
    """Chillnn から CSV をダウンロードして data/<output_name> に保存する。

    start_override / end_override を渡すとチェックイン日の検索範囲を上書きできる
    （新規予約検知では先々の予約も取りこぼさないよう広めの範囲を使う）。
    """
    today = today or date.today()
    env = load_env()

    email = env.get("CHILLNN_EMAIL")
    password = env.get("CHILLNN_PASSWORD")
    # ホテルIDは固定（sui kawahigashi sauna）
    hotel_id = env.get("CHILLNN_HOTEL_ID", "192d3a509c089")
    reservation_url = f"https://admin.chillnn.com/{hotel_id}/management/reservation"

    if not email or not password:
        raise RuntimeError(".env に CHILLNN_EMAIL / CHILLNN_PASSWORD が設定されていません")

    if start_override and end_override:
        start, end = start_override, end_override
    else:
        start, end = month_range(today)
    filtered_url = (
        f"{reservation_url}?search_type=check_in"
        f"&start_date={start.isoformat()}"
        f"&end_date={end.isoformat()}"
    )

    DATA_DIR.mkdir(exist_ok=True)
    output_path = DATA_DIR / output_name

    debug_dir = DATA_DIR / "debug"
    debug_dir.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            accept_downloads=True,
            viewport={"width": 1400, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        try:
            # 1. ログインページ
            print("→ ログインページにアクセス中...")
            page.goto("https://admin.chillnn.com/auth/signIn", wait_until="domcontentloaded")
            page.wait_for_selector('input[type="email"]', timeout=15000)
            page.screenshot(path=str(debug_dir / "01_login_page.png"))

            print("→ 認証情報入力...")
            page.fill('input[type="email"]', email)
            page.fill('input[type="password"]', password)
            page.screenshot(path=str(debug_dir / "02_filled.png"))

            print("→ サインインクリック...")
            page.click('button:has-text("サインイン")')

            # ログイン後の遷移待ち
            page.wait_for_url(
                lambda url: "auth/signIn" not in url,
                timeout=20000,
            )
            print(f"→ 遷移完了: {page.url}")
            page.screenshot(path=str(debug_dir / "03_after_login.png"))

            # 2. ホテル選択画面が出る場合は対象ホテルをクリック
            hotel_name = env.get("CHILLNN_HOTEL_NAME", "sui kawahigashi sauna")
            try:
                page.wait_for_selector(f'text="{hotel_name}"', timeout=5000)
                print(f"→ ホテル選択: {hotel_name}")
                page.click(f'text="{hotel_name}"')
                # 選択後の遷移完了を待つ（URL が /<hotel_id> 配下になる）
                page.wait_for_url(re.compile(rf"admin\.chillnn\.com/{hotel_id}"), timeout=15000)
                page.wait_for_load_state("networkidle")
                print(f"→ ホテル選択完了: {page.url}")
                page.screenshot(path=str(debug_dir / "03b_hotel_selected.png"))
            except Exception as e:
                print(f"→ ホテル選択スキップ（{type(e).__name__}）、現在のURL: {page.url}")

            # 3. フィルタ済URLに直接遷移
            print(f"→ フィルタURL遷移: {filtered_url}")
            page.goto(filtered_url, wait_until="networkidle")
            page.wait_for_timeout(3000)  # JS描画待ち
            print(f"→ 遷移後URL: {page.url}")
            page.screenshot(path=str(debug_dir / "04_filtered.png"))

            # CSVボタンが出るまで待機
            print("→ CSVボタン待機...")
            page.wait_for_selector(
                'button:has-text("CSVダウンロード")', timeout=20000
            )
            page.screenshot(path=str(debug_dir / "05_button_ready.png"))

            # 3. ダウンロードイベントを待ち受けつつクリック
            print("→ ダウンロード実行...")
            with page.expect_download(timeout=30000) as download_info:
                page.click('button:has-text("CSVダウンロード（予約ごと）")')
            download = download_info.value
            download.save_as(output_path)
            print(f"→ 保存完了: {output_path}")

        except Exception as e:
            page.screenshot(path=str(debug_dir / "ERROR.png"))
            print(f"エラー時のURL: {page.url}")
            raise
        finally:
            browser.close()

    return output_path


if __name__ == "__main__":
    # 第1引数で --headed を渡せば実ブラウザで確認できる
    headless = "--headed" not in sys.argv
    path = download_csv(headless=headless)
    print(f"CSV saved: {path}")
    print(f"Size: {path.stat().st_size:,} bytes")
