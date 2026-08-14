"""Instagram ストーリーへの投稿(Meta Graph API / Content Publishing API)。

前提: Instagramビジネス/クリエイターアカウント + Facebookページ紐付け済み。
画像は公開URL必須のため、GitHub Actions 側で生成画像をコミットし
raw.githubusercontent.com のURLを --image-url で渡す。
"""
import os
import time

import requests

GRAPH = "https://graph.facebook.com/v21.0"


def post_story(image_url: str = None, video_url: str = None) -> None:
    ig_user_id = os.environ["IG_USER_ID"]
    token = os.environ["IG_ACCESS_TOKEN"]

    # 1. メディアコンテナ作成(ストーリー)
    data = {"media_type": "STORIES", "access_token": token}
    if video_url:
        data["video_url"] = video_url
    elif image_url:
        data["image_url"] = image_url
    else:
        raise ValueError("image_url か video_url のどちらかが必要です")
    res = requests.post(f"{GRAPH}/{ig_user_id}/media", data=data, timeout=60)
    res.raise_for_status()
    creation_id = res.json()["id"]

    # 2. メディア処理完了を待つ(動画は時間がかかるため最大5分)
    for _ in range(30):
        status = requests.get(
            f"{GRAPH}/{creation_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=60,
        ).json()
        if status.get("status_code") == "FINISHED":
            break
        if status.get("status_code") == "ERROR":
            raise RuntimeError(f"Instagram メディア処理エラー: {status}")
        time.sleep(10)

    # 3. 公開
    res = requests.post(
        f"{GRAPH}/{ig_user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=60,
    )
    res.raise_for_status()
    print(f"Instagram ストーリー投稿に成功しました: media id = {res.json()['id']}")
