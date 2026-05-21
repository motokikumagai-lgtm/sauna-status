"""エントリーポイント。CSVを読んでHTMLを生成して output/ に保存する。"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

# モジュール検索パス
sys.path.insert(0, str(Path(__file__).parent))

from parser import parse_csv, aggregate
from schedule import load_schedule
from generator import render_html, render_html_split


ROOT = Path(__file__).resolve().parent.parent


def main(csv_path: Path, today: date | None = None) -> Path:
    today = today or date.today()
    schedule = load_schedule(ROOT / "config" / "operating_schedule.yaml")
    reservations = parse_csv(csv_path)
    agg = aggregate(reservations)
    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)

    # 結合版（後方互換）
    html = render_html(today=today, schedule=schedule, agg=agg)
    (out_dir / "index.html").write_text(html, encoding="utf-8")

    # 4分割版（各 Carousel スライド用）
    split_pages = render_html_split(today=today, schedule=schedule, agg=agg)
    for slug, page_html in split_pages.items():
        (out_dir / f"{slug}.html").write_text(page_html, encoding="utf-8")

    return out_dir / "index.html"


if __name__ == "__main__":
    csv_arg = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "/Users/motokikumagai/Downloads/CHILLNN_予約情報_1779244590726.csv"
    )
    today_arg = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date(2026, 5, 20)
    path = main(csv_arg, today_arg)
    print(f"Generated: {path}")
