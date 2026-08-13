"""Googleカレンダーから当日の予定を取得し、種類ごとに分類する。

タイトルによる分類ルール(優先順位順):
1. 「貸し切り」「貸切」を含む → 貸し切り時間帯(一般利用不可)
2. 「イベント」を含む       → イベント(タイトルからイベント名を抽出)
3. 「開館」を含む           → 開館時間
それ以外の予定(打ち合わせ等)は無視する。

- 時刻は予定の開始/終了時刻から取得(タイトル内の時刻文字列はパースしない)
- 各種類とも複数予定はすべて列挙
- 「開館」も「イベント」も無い日は休館扱い
"""
import datetime
import json
import os
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

WEEKDAYS_JA = ["月", "火", "水", "木", "金", "土", "日"]

# イベント名抽出時に取り除く区切り文字(名前の一部になりうる括弧類は含めない)
_SEPARATORS = " 　::・-〜~/|"


def _credentials() -> service_account.Credentials:
    raw = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    info = json.loads(raw)
    return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)


def _extract_event_name(title: str, keyword: str) -> str:
    """「イベント:読書会」のようなタイトルからイベント名部分を取り出す。"""
    name = title.replace(keyword, "", 1).strip(_SEPARATORS)
    return name or keyword


def _merge_ranges(ranges: list) -> list:
    """重なり・連続する時間帯を1つに結合し、表示用の時刻文字列にして返す。

    例: [(11:00,16:00), (11:00,17:00)] → [{"start":"11:00","end":"17:00"}]
    """
    merged = []
    for start, end in sorted(ranges):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [
        {"start": s.strftime("%H:%M"), "end": e.strftime("%H:%M")} for s, e in merged
    ]


def get_today_schedule(config: dict, day_offset: int = 0) -> dict:
    """対象日(今日+day_offset日)の予定を分類して dict で返す。

    返り値例:
      {"date": "8/8(土)", "closed": False,
       "slots": [{"start": "17:00", "end": "21:00"}],
       "events": [{"name": "読書会", "start": "14:00", "end": "16:00"}],
       "reserved": [{"start": "10:00", "end": "12:00"}]}
    """
    tz = ZoneInfo(config.get("timezone", "Asia/Tokyo"))
    cal_conf = config["calendar"]
    open_kw = cal_conf.get("keyword", "開館")
    event_kw = cal_conf.get("event_keyword", "イベント")
    reserved_kws = cal_conf.get("reserved_keywords", ["貸し切り", "貸切"])
    calendar_id = os.environ["GOOGLE_CALENDAR_ID"]

    target = datetime.datetime.now(tz) + datetime.timedelta(days=day_offset)
    day_start = target.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + datetime.timedelta(days=1)

    service = build("calendar", "v3", credentials=_credentials(), cache_discovery=False)
    result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=day_start.isoformat(),
            timeMax=day_end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    open_ranges, reserved_ranges, events = [], [], []
    for item in result.get("items", []):
        title = item.get("summary", "")
        start_raw = item["start"].get("dateTime")
        end_raw = item["end"].get("dateTime")
        if not start_raw or not end_raw:
            # 終日予定は時刻が定まらないためスキップ(時刻付きで登録する運用)
            continue
        start_dt = datetime.datetime.fromisoformat(start_raw).astimezone(tz)
        end_dt = datetime.datetime.fromisoformat(end_raw).astimezone(tz)

        if any(kw in title for kw in reserved_kws):
            reserved_ranges.append((start_dt, end_dt))
        elif event_kw in title:
            events.append(
                {
                    "name": _extract_event_name(title, event_kw),
                    "start": start_dt.strftime("%H:%M"),
                    "end": end_dt.strftime("%H:%M"),
                }
            )
        elif open_kw in title:
            open_ranges.append((start_dt, end_dt))

    # 複数スタッフが重複して予定を入れた場合などに備え、重なる時間帯は結合する
    slots = _merge_ranges(open_ranges)
    reserved = _merge_ranges(reserved_ranges)

    date_str = f"{target.month}/{target.day}({WEEKDAYS_JA[target.weekday()]})"
    return {
        "date": date_str,
        "closed": not slots and not events,
        "slots": slots,
        "events": events,
        "reserved": reserved,
    }
