"""営業カレンダー設定を読み込む。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Union

import yaml


@dataclass
class Schedule:
    weekly_default: dict[int, list[int]]
    overrides: dict[str, Union[list[int], str]]

    def open_slots(self, d: date) -> list[int]:
        """指定日の営業中の時間枠（部）リストを返す。空配列なら休業。"""
        key = d.isoformat()
        if key in self.overrides:
            val = self.overrides[key]
            if val == "closed":
                return []
            if isinstance(val, list):
                return val
        return self.weekly_default.get(d.weekday(), [])

    def is_closed(self, d: date) -> bool:
        return len(self.open_slots(d)) == 0


def load_schedule(path: Path) -> Schedule:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Schedule(
        weekly_default={int(k): v for k, v in data["weekly_default"].items()},
        overrides=data.get("overrides", {}) or {},
    )
