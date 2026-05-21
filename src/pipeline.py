"""フル自動パイプライン: Chillnn DL → 集計 → HTML生成。

朝8時にcronから実行することを想定。
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from downloader import download_csv
from main import main as generate_html
from screenshots import generate_png_screenshots


ROOT = Path(__file__).resolve().parent.parent


def run(today: date | None = None, skip_download: bool = False) -> Path:
    """全体パイプラインを実行する。

    Args:
        today: 基準日（デフォルト=実行日）
        skip_download: True ならダウンロードをスキップし、既存CSVを使う

    Returns:
        生成されたHTMLのパス
    """
    today = today or date.today()
    print(f"=== Pipeline start: {today} ===")

    if skip_download:
        csv_path = ROOT / "data" / "latest.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"既存CSVが見つかりません: {csv_path}")
        print(f"[1/3] DLスキップ、既存CSV使用: {csv_path}")
    else:
        print("[1/3] Chillnn から CSV ダウンロード...")
        csv_path = download_csv(today=today)
        print(f"      → {csv_path} ({csv_path.stat().st_size:,} bytes)")

    print("[2/3] HTML生成...")
    html_path = generate_html(csv_path, today=today)
    print(f"      → {html_path} ({html_path.stat().st_size:,} bytes)")

    print("[3/3] PNG生成...")
    png_files = generate_png_screenshots(ROOT / "output")
    for f in png_files:
        print(f"      → {f.name} ({f.stat().st_size:,} bytes)")

    print(f"=== Pipeline done ===")
    return html_path


if __name__ == "__main__":
    skip = "--skip-download" in sys.argv
    run(skip_download=skip)
