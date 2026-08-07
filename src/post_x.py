"""X(旧Twitter)への投稿。X API v2 無料枠を使用。"""
import os

import tweepy

from .config import IMAGE_PATH


def post_to_x(text: str, with_image: bool) -> None:
    consumer_key = os.environ["X_API_KEY"]
    consumer_secret = os.environ["X_API_SECRET"]
    access_token = os.environ["X_ACCESS_TOKEN"]
    access_secret = os.environ["X_ACCESS_SECRET"]

    client = tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_secret,
    )

    media_ids = None
    if with_image and IMAGE_PATH.exists():
        # メディアアップロードは v1.1 エンドポイント(無料枠でも利用可)
        auth = tweepy.OAuth1UserHandler(
            consumer_key, consumer_secret, access_token, access_secret
        )
        api = tweepy.API(auth)
        media = api.media_upload(str(IMAGE_PATH))
        media_ids = [media.media_id]

    response = client.create_tweet(text=text, media_ids=media_ids)
    print(f"X への投稿に成功しました: tweet id = {response.data['id']}")
