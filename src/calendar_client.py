"""Googleカレンダーから当日の「開館」予定を取得する。

要件:
- タイトルに keyword(既定「開館」)を含む予定を開館時間として扱う
- 時刻は予定の開始/終了時刻から取得(タイトル内の時刻文字列はパースしない)
- 複数予定(昼休み休館など)はすべて列挙
- 該当予定がない日は休館扱い
"""
import datetime
import json
import os
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

WEEKDAYS_JA = ["月", "火", "水", "木", "金", "土", "日"]


def _credentials() -> service_account.Credentials:
    raw = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    info = json.loads(raw)
    return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)


def get_today_open_slots(config: dict) -> dict:
    """当日の開館時間帯を取得して dict で返す。

    返り値例:
      {"date": "8/7(金)", "closed": False,
       "slots": [{"start": "10:00", "end": "18:00"}]}
    """
    tz = ZoneInfo(config.get("timezone", "Asia/Tokyo"))
    keyword = config["calendar"]["keyword"]
    calendar_id = os.environ["GOOGLE_CALENDAR_ID"]

    now = datetime.datetime.now(tz)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
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

    slots = []
    for event in result.get("items", []):
        title = event.get("summary", "")
        if keyword not in title:
            continue
        start_raw = event["start"].get("dateTime")
        end_raw = event["end"].get("dateTime")
        if not start_raw or not end_raw:
            # 終日予定は時刻が定まらないためスキップ(開館は時刻付きで登録する運用)
            continue
        start = datetime.datetime.fromisoformat(start_raw).astimezone(tz)
        end = datetime.datetime.fromisoformat(end_raw).astimezone(tz)
        slots.append({"start": start.strftime("%H:%M"), "end": end.strftime("%H:%M")})

    date_str = f"{now.month}/{now.day}({WEEKDAYS_JA[now.weekday()]})"
    return {"date": date_str, "closed": not slots, "slots": slots}
