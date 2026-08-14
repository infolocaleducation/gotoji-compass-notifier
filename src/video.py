"""背景動画に開館時間オーバーレイを合成してストーリー用動画を作る。

- templates/videos/*.mp4 を日替わりでローテーション(対象日から決定的に選ぶ)
- output/overlay.png(半透明の暗幕+文字)を全面に重ねる
- 1080x1920 に正規化し、最大15秒に収める
- ffmpeg が必要(GitHub Actions の ubuntu ランナーには標準搭載)
"""
import hashlib
import json
import subprocess

from .config import ROOT, OUTPUT_DIR, STATUS_PATH

VIDEO_DIR = ROOT / "templates" / "videos"
STORY_PATH = OUTPUT_DIR / "story.mp4"
OVERLAY_PATH = OUTPUT_DIR / "overlay.png"
MAX_SECONDS = "15"


def compose_story_video() -> None:
    videos = sorted(VIDEO_DIR.glob("*.mp4"))
    if not videos:
        raise SystemExit("templates/videos に背景動画がありません。")
    if not OVERLAY_PATH.exists():
        raise SystemExit("output/overlay.png がありません。先に generate を実行してください。")

    with open(STATUS_PATH, encoding="utf-8") as f:
        status = json.load(f)

    # 対象日から決定的に1本選ぶ(同じ日は何度実行しても同じ動画になる)
    key = status.get("date_iso", status["date"])
    idx = int(hashlib.md5(key.encode()).hexdigest(), 16) % len(videos)
    src = videos[idx]

    cmd = [
        "ffmpeg", "-y",
        "-i", str(src),
        "-i", str(OVERLAY_PATH),
        "-filter_complex",
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,setsar=1[bg];[bg][1:v]overlay=0:0",
        "-t", MAX_SECONDS,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        str(STORY_PATH),
    ]
    subprocess.run(cmd, check=True)
    print(f"ストーリー動画を生成しました: {STORY_PATH}(背景: {src.name})")
