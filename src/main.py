"""エントリーポイント。CSVを読んでHTMLを生成して output/ に保存する。"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

# モジュール検索パス
sys.path.insert(0, str(Path(__file__).parent))

from parser import parse_csv, aggregate
from schedule import load_schedule
from generator import render_html


ROOT = Path(__file__).resolve().parent.parent


def main(csv_path: Path, today: date | None = None) -> Path:
    today = today or date.today()
    schedule = load_schedule(ROOT / "config" / "operating_schedule.yaml")
    reservations = parse_csv(csv_path)
    agg = aggregate(reservations)
    html = render_html(today=today, schedule=schedule, agg=agg)
    out_path = ROOT / "output" / "index.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path


if __name__ == "__main__":
    csv_arg = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "/Users/motokikumagai/Downloads/CHILLNN_予約情報_1779244590726.csv"
    )
    today_arg = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date(2026, 5, 20)
    path = main(csv_arg, today_arg)
    print(f"Generated: {path}")
