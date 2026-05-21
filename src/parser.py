"""Chillnn CSVを読み込み、(日付, 施設, 時間枠) ごとの予約状況を集計する。"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Iterable


SHARE_PLAN_RE = re.compile(r"シェアプラン.*?｜([ABC])")
PRIVATE_PLAN_RE = re.compile(r"プライベート貸切プラン.*?｜([DE])")
TIME_SLOT_RE = re.compile(r"利用時間([①-④])")

TIME_SLOT_MAP = {"①": 1, "②": 2, "③": 3, "④": 4}


@dataclass
class Reservation:
    checkin_date: date
    plan_type: str           # "share" or "private"
    facility_id: str         # A, B, C, D, E
    time_slot: int           # 1..4
    headcount: int           # 大人人数
    cancelled: bool


@dataclass
class Aggregated:
    share_booked: dict = field(default_factory=lambda: defaultdict(int))
    private_booked: dict = field(default_factory=lambda: defaultdict(int))

    def share_key(self, d: date, facility: str, slot: int) -> tuple:
        return (d, facility, slot)

    def private_key(self, d: date, facility: str, slot: int) -> tuple:
        return (d, facility, slot)


def parse_csv(path: Path) -> list[Reservation]:
    reservations: list[Reservation] = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            plan_name = row.get("プラン名称", "")
            options = row.get("オプション", "")
            checkin_str = row.get("チェックイン日", "")
            cancel_date = row.get("キャンセル日", "")
            headcount_str = row.get("大人人数", "0")

            if not checkin_str or not plan_name:
                continue

            try:
                checkin = date.fromisoformat(checkin_str)
            except ValueError:
                continue

            headcount = int(headcount_str) if headcount_str.isdigit() else 0
            cancelled = bool(cancel_date.strip())

            share_match = SHARE_PLAN_RE.search(plan_name)
            private_match = PRIVATE_PLAN_RE.search(plan_name)

            slot_match = TIME_SLOT_RE.search(options)
            if not slot_match:
                continue
            slot = TIME_SLOT_MAP[slot_match.group(1)]

            if share_match:
                reservations.append(Reservation(
                    checkin_date=checkin,
                    plan_type="share",
                    facility_id=share_match.group(1),
                    time_slot=slot,
                    headcount=headcount,
                    cancelled=cancelled,
                ))
            elif private_match:
                reservations.append(Reservation(
                    checkin_date=checkin,
                    plan_type="private",
                    facility_id=private_match.group(1),
                    time_slot=slot,
                    headcount=headcount,
                    cancelled=cancelled,
                ))
    return reservations


def aggregate(reservations: Iterable[Reservation]) -> Aggregated:
    agg = Aggregated()
    for r in reservations:
        if r.cancelled:
            continue
        if r.plan_type == "share":
            key = agg.share_key(r.checkin_date, r.facility_id, r.time_slot)
            agg.share_booked[key] += r.headcount
        else:
            key = agg.private_key(r.checkin_date, r.facility_id, r.time_slot)
            agg.private_booked[key] += 1
    return agg


if __name__ == "__main__":
    import sys
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "/Users/motokikumagai/Downloads/CHILLNN_予約情報_1779244590726.csv"
    )
    reservations = parse_csv(csv_path)
    print(f"Parsed {len(reservations)} reservations")
    agg = aggregate(reservations)
    print(f"Share bookings: {dict(agg.share_booked)}")
    print(f"Private bookings: {dict(agg.private_booked)}")
