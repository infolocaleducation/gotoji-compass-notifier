"""公式サイト用のInstagram最新投稿フィードを生成する。

Graph API で最新3投稿を取得し、サムネイル画像と feed.json を
output/ig_feed/ に書き出す。GitHub Actions(ig-feed.yml)が毎日実行して
コミットし、公式サイト(gotoji-compassリポジトリ)のJSが
raw.githubusercontent.com 経由で読み込む。
"""
import io
import json
import os
from pathlib import Path

import requests
from PIL import Image

from .config import OUTPUT_DIR

GRAPH = "https://graph.facebook.com/v21.0"
FEED_DIR = OUTPUT_DIR / "ig_feed"
POST_COUNT = 3
THUMB_SIZE = 800  # 長辺px。公式サイトでの表示用なのでこれで十分


def main() -> None:
    ig_user_id = os.environ["IG_USER_ID"]
    token = os.environ["IG_ACCESS_TOKEN"]

    res = requests.get(
        f"{GRAPH}/{ig_user_id}/media",
        params={
            "fields": "id,caption,permalink,media_url,thumbnail_url,media_type,timestamp",
            "limit": POST_COUNT,
            "access_token": token,
        },
        timeout=60,
    )
    res.raise_for_status()
    posts = res.json().get("data", [])[:POST_COUNT]

    FEED_DIR.mkdir(parents=True, exist_ok=True)

    feed = []
    keep_files = {"feed.json"}
    for post in posts:
        media_id = post["id"]
        filename = f"{media_id}.jpg"
        keep_files.add(filename)
        path = FEED_DIR / filename

        # 既に取得済みの投稿は再ダウンロードしない(不要なコミット差分を防ぐ)
        if not path.exists():
            image_url = (
                post.get("thumbnail_url")
                if post.get("media_type") == "VIDEO"
                else post.get("media_url")
            )
            if not image_url:
                continue
            img_res = requests.get(image_url, timeout=60)
            img_res.raise_for_status()
            img = Image.open(io.BytesIO(img_res.content)).convert("RGB")
            img.thumbnail((THUMB_SIZE, THUMB_SIZE))
            img.save(path, "JPEG", quality=80, optimize=True)

        feed.append(
            {
                "id": media_id,
                "caption": (post.get("caption") or "")[:200],
                "permalink": post["permalink"],
                "timestamp": post.get("timestamp", ""),
                "image": filename,
            }
        )

    # 最新3件に含まれなくなった古い画像を削除
    for f in FEED_DIR.iterdir():
        if f.name not in keep_files:
            f.unlink()

    with open(FEED_DIR / "feed.json", "w", encoding="utf-8") as f:
        json.dump({"posts": feed}, f, ensure_ascii=False, indent=2)

    print(f"Instagramフィードを更新しました: {len(feed)}件")


if __name__ == "__main__":
    main()
