"""sui の新規予約を検知して LINE に通知する。

Chillnn には webhook が無いため、CSV を定期取得し「前回までに見た予約ID集合」との
差分で新規を検知する。リポジトリは public のため、予約ID は SHA256 でハッシュ化して
保存し、LINE 文面には日付・金額・件数のみを載せる（氏名・電話等は一切含めない）。

通知内容（ユーザー要望）:
    ・その日（新規予約の利用日）の予約総額
    ・その月（新規予約の利用月）の売上総額

環境変数:
    LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID  （notifier.py 参照）
    CHILLNN_EMAIL, CHILLNN_PASSWORD          （downloader.py 参照）
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from downloader import download_csv  # noqa: E402
from notifier import send_line  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
STATE_PATH = DATA_DIR / "seen_hashes.json"
NOTIFY_CSV = "notify.csv"

WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]
MAX_INDIVIDUAL_NOTIFICATIONS = 8  # これを超える新規はまとめて1通に


def _hash(reservation_id: str) -> str:
    return hashlib.sha256(reservation_id.strip().encode("utf-8")).hexdigest()


def _yen(n: int) -> str:
    return f"¥{n:,}"


def _amount(raw: str) -> int:
    v = (raw or "").replace(",", "").strip()
    if not v:
        return 0
    try:
        return int(float(v))
    except ValueError:
        return 0


def load_state() -> set[str]:
    if not STATE_PATH.exists():
        return set()
    try:
        return set(json.loads(STATE_PATH.read_text(encoding="utf-8")))
    except Exception:  # noqa: BLE001
        return set()


def save_state(hashes: set[str]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(sorted(hashes), ensure_ascii=False, indent=0),
        encoding="utf-8",
    )


class Row:
    __slots__ = ("rid", "rhash", "checkin", "amount", "cancelled")

    def __init__(self, rid, checkin, amount, cancelled):
        self.rid = rid
        self.rhash = _hash(rid)
        self.checkin = checkin  # date or None
        self.amount = amount
        self.cancelled = cancelled


def parse_rows(csv_path: Path) -> list[Row]:
    rows: list[Row] = []
    with open(csv_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rid = (r.get("予約ID") or "").strip()
            if not rid:
                continue
            checkin_str = (r.get("チェックイン日") or "").strip()
            try:
                checkin = date.fromisoformat(checkin_str) if checkin_str else None
            except ValueError:
                checkin = None
            amount = _amount(r.get("請求料金", ""))
            cancelled = bool((r.get("キャンセル日") or "").strip())
            rows.append(Row(rid, checkin, amount, cancelled))
    return rows


def day_total(active: list[Row], d: date) -> tuple[int, int]:
    """利用日 d の予約総額と件数（キャンセル除く）。"""
    sel = [r for r in active if r.checkin == d]
    return sum(r.amount for r in sel), len(sel)


def month_total(active: list[Row], y: int, m: int) -> tuple[int, int]:
    """利用月 (y, m) の売上総額と件数（キャンセル除く）。"""
    sel = [r for r in active if r.checkin and r.checkin.year == y and r.checkin.month == m]
    return sum(r.amount for r in sel), len(sel)


def build_message(r: Row, active: list[Row]) -> str:
    d = r.checkin
    if d is None:
        head = "🛁 sui 新規予約（利用日未設定）"
        return f"{head}\n金額: {_yen(r.amount)}"
    wd = WEEKDAY_JP[d.weekday()]
    d_sum, d_cnt = day_total(active, d)
    m_sum, m_cnt = month_total(active, d.year, d.month)
    return (
        "🛁 sui 新規予約が入りました\n"
        f"利用日: {d.month}/{d.day}（{wd}）\n"
        f"　この予約: {_yen(r.amount)}\n"
        f"　{d.month}/{d.day} の予約計: {_yen(d_sum)}（{d_cnt}件）\n"
        f"　{d.month}月の売上累計: {_yen(m_sum)}（{m_cnt}件）"
    )


def build_summary(news: list[Row], active: list[Row]) -> str:
    total = sum(r.amount for r in news)
    lines = ["🛁 sui 新規予約 まとめ", f"新規 {len(news)}件 / 計 {_yen(total)}", ""]
    # 利用月ごとの累計も付ける
    months = sorted({(r.checkin.year, r.checkin.month) for r in news if r.checkin})
    for y, m in months:
        m_sum, m_cnt = month_total(active, y, m)
        lines.append(f"{m}月 売上累計: {_yen(m_sum)}（{m_cnt}件）")
    return "\n".join(lines)


def run(seed_only: bool = False, dry_run: bool = False) -> int:
    today = date.today()
    # 当月初日 〜 先々まで（遠い未来の予約も取りこぼさない）
    start = today.replace(day=1)
    end = today + timedelta(days=310)

    print(f"=== notify_reservations: {today} (seed_only={seed_only}, dry_run={dry_run}) ===")
    csv_path = download_csv(
        today=today,
        start_override=start,
        end_override=end,
        output_name=NOTIFY_CSV,
    )
    rows = parse_rows(csv_path)
    active = [r for r in rows if not r.cancelled]
    active_hashes = {r.rhash for r in active}
    print(f"取得: {len(rows)}行 / 有効(キャンセル除く): {len(active)}件")

    seen = load_state()
    first_run = not STATE_PATH.exists()

    if first_run or seed_only:
        save_state(active_hashes)
        print(f"[seed] 既読として {len(active_hashes)} 件を登録（通知なし）。次回から新規のみ通知します。")
        return 0

    new_hashes = active_hashes - seen
    news = [r for r in active if r.rhash in new_hashes]
    # 同一予約IDの重複を排除（保険）
    uniq = {}
    for r in news:
        uniq.setdefault(r.rhash, r)
    news = list(uniq.values())
    news.sort(key=lambda r: (r.checkin or date.max))
    print(f"新規検知: {len(news)}件")

    if not news:
        save_state(seen | active_hashes)
        print("新規なし。状態のみ更新。")
        return 0

    if len(news) <= MAX_INDIVIDUAL_NOTIFICATIONS:
        messages = [build_message(r, active) for r in news]
    else:
        messages = [build_summary(news, active)]

    sent = 0
    for msg in messages:
        if dry_run:
            print("--- (dry-run) 送信予定 ---")
            print(msg)
            sent += 1
        else:
            if send_line(msg):
                sent += 1

    print(f"通知 {sent}/{len(messages)} 件送信")

    if not dry_run:
        # 送信できた場合のみ既読更新（失敗時は次回再送を狙う）
        if sent > 0 or not messages:
            save_state(seen | active_hashes)
    return 0


if __name__ == "__main__":
    args = set(sys.argv[1:])
    sys.exit(run(seed_only="--seed" in args, dry_run="--dry-run" in args))
