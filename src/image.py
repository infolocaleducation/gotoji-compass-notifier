"""開館時間カード画像(1080x1920 縦長PNG)の生成。

templates/background_open.png / background_closed.png があればそれを背景に使い、
無ければ config.yml の色で単色背景を描く。テンプレート差し替えはファイルを
置くだけで反映される。
"""
import pathlib

from PIL import Image, ImageDraw, ImageFont

from .config import ROOT, IMAGE_PATH

# 日本語フォントの自動検出候補(GitHub Actions は fonts-noto-cjk を導入)
FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Bold.otf",
    "C:/Windows/Fonts/meiryob.ttc",
    "C:/Windows/Fonts/meiryo.ttc",
    "C:/Windows/Fonts/YuGothB.ttc",
]


def _find_font(config: dict) -> str:
    configured = config["image"].get("font_path") or ""
    candidates = ([configured] if configured else []) + FONT_CANDIDATES
    for path in candidates:
        if pathlib.Path(path).exists():
            return path
    raise FileNotFoundError(
        "日本語フォントが見つかりません。config.yml の image.font_path を設定してください。"
    )


def _center_text(draw, y, text, font, fill, width):
    box = draw.textbbox((0, 0), text, font=font)
    x = (width - (box[2] - box[0])) // 2
    draw.text((x, y), text, font=font, fill=fill)
    return y + (box[3] - box[1])


def generate_image(config: dict, status: dict) -> pathlib.Path:
    img_conf = config["image"]
    width, height = img_conf["width"], img_conf["height"]
    theme = img_conf["closed"] if status["closed"] else img_conf["open"]

    bg_name = "background_closed.png" if status["closed"] else "background_open.png"
    bg_path = ROOT / "templates" / bg_name
    if bg_path.exists():
        image = Image.open(bg_path).convert("RGB").resize((width, height))
    else:
        image = Image.new("RGB", (width, height), theme["background"])
    draw = ImageDraw.Draw(image)

    font_path = _find_font(config)
    font_title = ImageFont.truetype(font_path, 72)
    font_sub = ImageFont.truetype(font_path, 36)
    font_date = ImageFont.truetype(font_path, 110)
    font_label = ImageFont.truetype(font_path, 64)
    font_time = ImageFont.truetype(font_path, 96)
    font_msg = ImageFont.truetype(font_path, 48)

    text, accent = theme["text"], theme["accent"]

    y = 220
    y = _center_text(draw, y, img_conf["title"], font_title, text, width) + 30
    y = _center_text(draw, y, img_conf["subtitle"], font_sub, text, width) + 160

    y = _center_text(draw, y, status["date"], font_date, text, width) + 140

    if status["closed"]:
        y = _center_text(draw, y, img_conf["closed_label"], font_label, accent, width) + 120
        _center_text(draw, y, img_conf["closed_message"], font_msg, text, width)
    else:
        y = _center_text(draw, y, img_conf["open_label"], font_label, text, width) + 100
        for slot in status["slots"]:
            line = f"{slot['start']}〜{slot['end']}"
            y = _center_text(draw, y, line, font_time, accent, width) + 60

    IMAGE_PATH.parent.mkdir(exist_ok=True)
    image.save(IMAGE_PATH)
    return IMAGE_PATH
