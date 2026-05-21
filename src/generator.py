"""集計データ + 営業カレンダー設定 から HTMLカレンダーを生成する。"""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from parser import Aggregated
from schedule import Schedule


# プラン定義（plans.yamlの内容をハードコード。後でyaml読込にしてもOK）
SHARE_PLANS = [
    {"id": "A", "label": "シェアプランA", "color": "#F39C5A", "capacity": 6},
    {"id": "B", "label": "シェアサウナB", "color": "#3B6BC5", "capacity": 6},
    {"id": "C", "label": "シェアサウナC", "color": "#39A85B", "capacity": 6},
]
PRIVATE_PLANS = [
    {"id": "D", "label": "プライベートエリア貸切プランD", "color": "#E74C9C"},
    {"id": "E", "label": "プライベートエリア貸切プランE", "color": "#9B59B6"},
]
SLOTS = [
    {"num": 1, "label": "10:00〜"},
    {"num": 2, "label": "13:00〜"},
    {"num": 3, "label": "16:00〜"},
    {"num": 4, "label": "19:00〜"},
]

WEEKDAY_JA = ["月", "火", "水", "木", "金", "土", "日"]
HEADER_DAYS = ["日", "月", "火", "水", "木", "金", "土"]  # 日曜始まり


def month_weeks(year: int, month: int) -> list[list[Optional[date]]]:
    """月のカレンダーを週ごとの配列にする（日曜始まり、月外はNone）。"""
    cal = calendar.Calendar(firstweekday=6)  # 6=日曜
    weeks: list[list[Optional[date]]] = []
    for week in cal.monthdatescalendar(year, month):
        row = [d if d.month == month else None for d in week]
        weeks.append(row)
    return weeks


def _share_cell(d: date, slot: int, schedule: Schedule, agg: Aggregated, today: date) -> str:
    """シェア施設の1セル（A B C の数字3つ）をHTMLで返す。"""
    if d < today:
        return '<span class="dash">-</span> <span class="dash">-</span> <span class="dash">-</span>'
    if slot not in schedule.open_slots(d):
        return '<span class="dash">-</span> <span class="dash">-</span> <span class="dash">-</span>'

    parts = []
    for plan in SHARE_PLANS:
        booked = agg.share_booked.get((d, plan["id"], slot), 0)
        remaining = max(0, plan["capacity"] - booked)
        parts.append(f'<span class="num" style="color:{plan["color"]}">{remaining}</span>')
    return " ".join(parts)


def _private_cell(d: date, slot: int, schedule: Schedule, agg: Aggregated, today: date) -> str:
    """プライベート施設の1セル（D E の●×）をHTMLで返す。"""
    if d < today:
        return '<span class="dash">-</span> <span class="dash">-</span>'
    if slot not in schedule.open_slots(d):
        return '<span class="dash">-</span> <span class="dash">-</span>'

    parts = []
    for plan in PRIVATE_PLANS:
        booked = agg.private_booked.get((d, plan["id"], slot), 0)
        if booked > 0:
            parts.append(f'<span class="cross" style="color:{plan["color"]}">×</span>')
        else:
            parts.append(f'<span class="circle" style="color:{plan["color"]}">●</span>')
    return " ".join(parts)


def render_share_calendar(year: int, month: int, schedule: Schedule, agg: Aggregated, today: date) -> str:
    """シェアプラン用カレンダーのHTMLを返す。"""
    weeks = month_weeks(year, month)
    snapshot = f"{today.strftime('%-m月%-d日 8時')}時点"

    rows_html = []
    for week in weeks:
        cells_html = []
        for d in week:
            if d is None:
                cells_html.append('<td class="empty"></td>')
                continue
            day_num = d.day
            if schedule.is_closed(d):
                inner = f'<div class="day-num">{day_num}</div><div class="closed">休</div>'
            elif d < today:
                inner = (
                    f'<div class="day-num">{day_num}</div>'
                    f'<div class="slots">'
                    f'<div class="slot-row dash-row">-</div>'
                    f'<div class="slot-row dash-row">-</div>'
                    f'<div class="slot-row dash-row">-</div>'
                    f'<div class="slot-row dash-row">-</div>'
                    f'</div>'
                )
            else:
                slot_lines = []
                for slot in SLOTS:
                    cell = _share_cell(d, slot["num"], schedule, agg, today)
                    slot_lines.append(f'<div class="slot-row">{cell}</div>')
                inner = f'<div class="day-num">{day_num}</div><div class="slots">{"".join(slot_lines)}</div>'
            cells_html.append(f'<td class="day">{inner}</td>')
        rows_html.append(f'<tr>{"".join(cells_html)}</tr>')

    time_col_html = (
        '<td class="time-col">'
        '<div class="day-num-spacer"></div>'
        '<div class="time-list">'
        '<div class="slot-row">10:00〜</div>'
        '<div class="slot-row">13:00〜</div>'
        '<div class="slot-row">16:00〜</div>'
        '<div class="slot-row">19:00〜</div>'
        '</div></td>'
    )
    rows_html_with_time = []
    for tr in rows_html:
        # 各行の先頭に時間列を挿入
        rows_html_with_time.append(tr.replace('<tr>', f'<tr>{time_col_html}', 1))

    header = '<tr><th class="snapshot">' + snapshot + '</th>' + \
        "".join(f'<th class="dow">{d}</th>' for d in HEADER_DAYS) + '</tr>'

    return f"""
<div class="calendar share-calendar">
  <div class="cal-header">
    <div class="note">表示されている数字は、<br>予約可能な人数を示しています。</div>
    <div class="title">{month}月｜シェアプラン空き情報</div>
    <div class="legend">
      <span class="legend-item" style="background:{SHARE_PLANS[0]['color']}">シェアプランA</span>
      <span class="legend-item" style="background:{SHARE_PLANS[1]['color']}">シェアサウナB</span>
      <span class="legend-item" style="background:{SHARE_PLANS[2]['color']}">シェアサウナC</span>
    </div>
  </div>
  <table class="cal-table">
    {header}
    {"".join(rows_html_with_time)}
  </table>
</div>
"""


def render_private_calendar(year: int, month: int, schedule: Schedule, agg: Aggregated, today: date) -> str:
    weeks = month_weeks(year, month)
    snapshot = f"{today.strftime('%-m月%-d日 8時')}時点"

    rows_html = []
    for week in weeks:
        cells_html = []
        for d in week:
            if d is None:
                cells_html.append('<td class="empty"></td>')
                continue
            day_num = d.day
            if schedule.is_closed(d):
                inner = f'<div class="day-num">{day_num}</div><div class="closed">休</div>'
            elif d < today:
                inner = (
                    f'<div class="day-num">{day_num}</div>'
                    f'<div class="slots">'
                    f'<div class="slot-row dash-row">-</div>'
                    f'<div class="slot-row dash-row">-</div>'
                    f'<div class="slot-row dash-row">-</div>'
                    f'<div class="slot-row dash-row">-</div>'
                    f'</div>'
                )
            else:
                slot_lines = []
                for slot in SLOTS:
                    cell = _private_cell(d, slot["num"], schedule, agg, today)
                    slot_lines.append(f'<div class="slot-row">{cell}</div>')
                inner = f'<div class="day-num">{day_num}</div><div class="slots">{"".join(slot_lines)}</div>'
            cells_html.append(f'<td class="day">{inner}</td>')
        rows_html.append(f'<tr>{"".join(cells_html)}</tr>')

    time_col_html = (
        '<td class="time-col">'
        '<div class="day-num-spacer"></div>'
        '<div class="time-list">'
        '<div class="slot-row">10:00〜</div>'
        '<div class="slot-row">13:00〜</div>'
        '<div class="slot-row">16:00〜</div>'
        '<div class="slot-row">19:00〜</div>'
        '</div></td>'
    )
    rows_html_with_time = []
    for tr in rows_html:
        rows_html_with_time.append(tr.replace('<tr>', f'<tr>{time_col_html}', 1))

    header = '<tr><th class="snapshot">' + snapshot + '</th>' + \
        "".join(f'<th class="dow">{d}</th>' for d in HEADER_DAYS) + '</tr>'

    return f"""
<div class="calendar private-calendar">
  <div class="cal-header">
    <div class="title">{month}月｜プライベートエリア空き情報</div>
    <div class="legend">
      <span class="legend-item" style="background:{PRIVATE_PLANS[0]['color']}">プライベートエリア貸切プランD</span>
      <span class="legend-item" style="background:{PRIVATE_PLANS[1]['color']}">プライベートエリア貸切プランE</span>
    </div>
  </div>
  <table class="cal-table">
    {header}
    {"".join(rows_html_with_time)}
  </table>
</div>
"""


CSS = """
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  font-family: "Hiragino Sans", "Yu Gothic", system-ui, sans-serif;
  background: #fff;
  margin: 0;
  padding: 6px;
  color: #1a3a3a;
  font-size: 14px;
}
.calendar { margin-bottom: 8px; }
.cal-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 2px 0;
  align-items: center;
}
.note { font-size: 10px; line-height: 1.3; color: #333; text-align: center; }
.title { font-size: 17px; font-weight: 700; text-align: center; color: #1a3a3a; }
.legend { display: flex; gap: 4px; justify-content: center; flex-wrap: wrap; }
.legend-item {
  color: #fff;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 700;
  letter-spacing: 0.03em;
}
.cal-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}
.cal-table th, .cal-table td {
  border: 1px solid #e6d4b8;
  padding: 2px 1px;
  vertical-align: top;
  text-align: center;
}
.cal-table th {
  background: #ead7be;
  font-weight: 700;
  padding: 4px 2px;
  font-size: 13px;
}
.cal-table th.snapshot {
  background: transparent;
  border: none;
  font-weight: 600;
  font-size: 13px;
  text-align: center;
  padding: 2px;
  color: #333;
}
.time-col {
  background: #f4e5cf;
  width: 12%;
  text-align: center;
  font-size: 11px;
  font-weight: 600;
  color: #5a4a30;
  vertical-align: top;
  padding: 2px 1px !important;
  white-space: nowrap;
  overflow: visible;
}
.time-col .day-num-spacer { height: 22px; }
.time-list { display: flex; flex-direction: column; align-items: center; }
.day { width: 12.5%; vertical-align: top; overflow: hidden; }
.empty { background: #fafafa; border: 1px solid #e6d4b8; }
.day-num {
  font-size: 15px;
  font-weight: 700;
  color: #1a3a3a;
  text-align: center;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.slots {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
}
.slot-row {
  font-size: 18px;
  height: 24px;
  display: flex;
  gap: 3px;
  align-items: center;
  justify-content: center;
  letter-spacing: 0;
  width: 100%;
}
.slot-row.dash-row { color: #aaa; }
.num {
  font-weight: 700;
  font-size: 18px;
  min-width: 13px;
  text-align: center;
  flex: 1;
}
.circle, .cross {
  font-size: 19px;
  font-weight: 700;
  min-width: 13px;
  text-align: center;
  flex: 1;
}
.dash {
  color: #aaa;
  min-width: 13px;
  text-align: center;
  flex: 1;
  display: inline-block;
}
.closed {
  font-size: 14px;
  font-weight: 700;
  text-align: center;
  padding: 20px 0;
  color: #888;
}
/* Tablet以上（5週分が縦800px程度に収まる設計） */
@media (min-width: 600px) {
  body { padding: 10px 16px; font-size: 14px; }
  .cal-header {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    gap: 12px;
    padding: 4px 0;
  }
  .note { text-align: left; }
  .legend { justify-content: flex-end; }
  .title { font-size: 20px; }
  .cal-table th { font-size: 14px; padding: 6px 2px; }
  .cal-table th.snapshot { font-size: 14px; }
  .day-num, .time-col .day-num-spacer { height: 22px; }
  .day-num { font-size: 15px; }
  .slot-row { height: 24px; font-size: 17px; gap: 6px; }
  .num { font-size: 17px; }
  .circle, .cross { font-size: 19px; }
  .time-col { font-size: 12px; }
  .calendar { margin-bottom: 12px; }
}
/* スマホ縦向き（モバイル前提のメインデバイス）
   iPhone 視認可能領域 ~700px に5週分のカレンダーが収まる設計 */
@media (max-width: 480px) {
  html, body { overflow-x: hidden; }
  body { padding: 4px; }
  .title { font-size: 15px; }
  .note { font-size: 9px; line-height: 1.2; }
  .cal-header { gap: 2px; padding: 1px 0; }
  .calendar { margin-bottom: 6px; }
  .cal-table th { font-size: 11px; padding: 3px 1px; }
  .cal-table th.snapshot { font-size: 12px; padding: 2px 1px; }
  .time-col { font-size: 9px; width: 13%; padding: 1px !important; }
  .day { width: 12.4%; }
  .day-num, .time-col .day-num-spacer { height: 20px; }
  .day-num { font-size: 14px; }
  .slot-row { font-size: 15px; height: 22px; gap: 1px; }
  .num { font-size: 15px; min-width: 10px; }
  .circle, .cross { font-size: 16px; min-width: 10px; }
  .dash { min-width: 10px; }
  .legend-item { font-size: 10px; padding: 2px 6px; }
}
"""


def _wrap_page(title: str, body_html: str) -> str:
    """単一カレンダー用の最小HTMLでラップする。"""
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>{CSS}</style>
</head>
<body>
{body_html}
</body>
</html>
"""


def render_html(today: date, schedule: Schedule, agg: Aggregated) -> str:
    """今月+来月の両方を含む完全なHTMLを返す（後方互換用 index.html）。"""
    this_month_first = today.replace(day=1)
    next_month_first = (this_month_first + timedelta(days=32)).replace(day=1)

    share_this = render_share_calendar(this_month_first.year, this_month_first.month, schedule, agg, today)
    share_next = render_share_calendar(next_month_first.year, next_month_first.month, schedule, agg, today)
    priv_this = render_private_calendar(this_month_first.year, this_month_first.month, schedule, agg, today)
    priv_next = render_private_calendar(next_month_first.year, next_month_first.month, schedule, agg, today)

    return _wrap_page(
        title="シェアプラン・プライベートエリア 空き情報",
        body_html=f"{share_this}\n{share_next}\n{priv_this}\n{priv_next}",
    )


def render_html_split(today: date, schedule: Schedule, agg: Aggregated) -> dict[str, str]:
    """個別 + 結合カレンダーHTMLを返す。
    - share-this / share-next / private-this / private-next : 単月単一カテゴリ
    - share / private : 両月（5月+6月）まとめページ ← STUDIO のセクションに埋め込む用
    """
    this_month_first = today.replace(day=1)
    next_month_first = (this_month_first + timedelta(days=32)).replace(day=1)

    share_this = render_share_calendar(this_month_first.year, this_month_first.month, schedule, agg, today)
    share_next = render_share_calendar(next_month_first.year, next_month_first.month, schedule, agg, today)
    priv_this = render_private_calendar(this_month_first.year, this_month_first.month, schedule, agg, today)
    priv_next = render_private_calendar(next_month_first.year, next_month_first.month, schedule, agg, today)

    pages = {
        "share-this": share_this,
        "share-next": share_next,
        "private-this": priv_this,
        "private-next": priv_next,
        "share": f"{share_this}\n{share_next}",
        "private": f"{priv_this}\n{priv_next}",
    }
    titles = {
        "share-this": f"{this_month_first.month}月 シェアプラン空き情報",
        "share-next": f"{next_month_first.month}月 シェアプラン空き情報",
        "private-this": f"{this_month_first.month}月 プライベートエリア空き情報",
        "private-next": f"{next_month_first.month}月 プライベートエリア空き情報",
        "share": "シェアプラン空き情報",
        "private": "プライベートエリア空き情報",
    }
    return {key: _wrap_page(titles[key], body) for key, body in pages.items()}
