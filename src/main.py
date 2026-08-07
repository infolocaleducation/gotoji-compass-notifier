"""全体制御。GitHub Actions から段階ごとに呼び出す。

  python -m src.main generate            カレンダー取得 + 画像生成 + status.json 保存
  python -m src.main post-x              status.json を読んで X へ投稿
  python -m src.main post-instagram --image-url <URL>
                                         IG ストーリーへ投稿(画像の公開URLが必要)

各ステップは独立して成功/失敗する(ひとつ失敗しても他は続行できる)よう
ワークフロー側で continue-on-error と組み合わせて使う。
"""
import argparse
import json
import sys

from .config import load_config, STATUS_PATH, OUTPUT_DIR


def _build_text(config: dict, status: dict) -> str:
    post = config["post"]
    if status["closed"]:
        return post["closed_template"].format(date=status["date"], times="")
    times = post["times_separator"].join(
        f"{s['start']}〜{s['end']}" for s in status["slots"]
    )
    return post["open_template"].format(date=status["date"], times=times)


def cmd_generate(config: dict) -> None:
    from .calendar_client import get_today_open_slots

    status = get_today_open_slots(config)
    status["text"] = _build_text(config, status)
    print(f"本日の状態: {'休館' if status['closed'] else status['slots']}")
    print(f"投稿文: {status['text']}")

    if config["features"]["attach_image"]:
        from .image import generate_image

        path = generate_image(config, status)
        print(f"画像を生成しました: {path}")

    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(STATUS_PATH, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)


def _load_status() -> dict:
    with open(STATUS_PATH, encoding="utf-8") as f:
        return json.load(f)


def cmd_post_x(config: dict) -> None:
    if not config["features"]["post_x"]:
        print("config.yml で post_x が無効のためスキップします。")
        return
    from .post_x import post_to_x

    status = _load_status()
    post_to_x(status["text"], with_image=config["features"]["attach_image"])


def cmd_post_instagram(config: dict, image_url: str) -> None:
    if not config["features"]["post_instagram"]:
        print("config.yml で post_instagram が無効のためスキップします。")
        return
    from .post_instagram import post_story

    post_story(image_url)


def main() -> None:
    parser = argparse.ArgumentParser(prog="gotoji-compass-notifier")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("generate")
    sub.add_parser("post-x")
    ig = sub.add_parser("post-instagram")
    ig.add_argument("--image-url", required=True)

    args = parser.parse_args()
    config = load_config()

    if args.command == "generate":
        cmd_generate(config)
    elif args.command == "post-x":
        cmd_post_x(config)
    elif args.command == "post-instagram":
        cmd_post_instagram(config, args.image_url)


if __name__ == "__main__":
    sys.exit(main())
