"""Instagram(Meta)長期アクセストークンの有効期限チェックと更新。

- 有効期限を debug_token で確認
- 残り21日を切っていたら fb_exchange_token で新しい60日トークンを取得
- 結果を output/token_result.json に書き出す(ワークフロー側で
  GitHub Secret の更新 or リマインドIssue作成に使う)
"""
import datetime
import json
import os

import requests

from .config import OUTPUT_DIR

GRAPH = "https://graph.facebook.com/v21.0"
REFRESH_THRESHOLD_DAYS = 21


def main() -> None:
    token = os.environ["IG_ACCESS_TOKEN"]
    app_id = os.environ["META_APP_ID"]
    app_secret = os.environ["META_APP_SECRET"]

    res = requests.get(
        f"{GRAPH}/debug_token",
        params={"input_token": token, "access_token": f"{app_id}|{app_secret}"},
        timeout=60,
    )
    res.raise_for_status()
    data = res.json()["data"]
    expires_at = data.get("expires_at", 0)

    result = {"days_left": None, "refreshed": False, "new_token": None}
    if expires_at:
        expiry = datetime.datetime.fromtimestamp(expires_at, datetime.timezone.utc)
        days_left = (expiry - datetime.datetime.now(datetime.timezone.utc)).days
        result["days_left"] = days_left
        print(f"IG_ACCESS_TOKEN の残り有効日数: {days_left} 日")

        if days_left <= REFRESH_THRESHOLD_DAYS:
            res = requests.get(
                f"{GRAPH}/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": app_id,
                    "client_secret": app_secret,
                    "fb_exchange_token": token,
                },
                timeout=60,
            )
            res.raise_for_status()
            result["new_token"] = res.json()["access_token"]
            result["refreshed"] = True
            print("新しい長期トークンを取得しました。")
    else:
        print("このトークンに有効期限はありません(無期限トークン)。")

    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(OUTPUT_DIR / "token_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f)


if __name__ == "__main__":
    main()
