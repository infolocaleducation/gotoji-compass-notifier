"""開館時間カード画像(1080x1920 縦長PNG)の生成。

表示内容(status の中身に応じてセクションを出し分ける):
- 開館時間(または「本日休館」)
- 本日のイベント(イベント名 + 時間)
- 貸し切り(時間 + 「この時間は一般利用できません」)

templates/background_open.png / background_closed.png があればそれを背景に使い、
無ければ config.yml の色で単色背景を描く。
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

SIDE_MARGIN = 60  # 左右の最低余白


def _find_font(config: dict) -> str:
    configured = config["image"].get("font_path") or ""
    candidates = ([configured] if configured else []) + FONT_CANDIDATES
    for path in candidates:
        if pathlib.Path(path).exists():
            return path
    raise FileNotFoundError(
        "日本語フォントが見つかりません。config.yml の image.font_path を設定してください。"
    )


def _fit_font(draw, text, font_path, size, max_width):
    """テキストが幅に収まるまでフォントサイズを縮めて返す。"""
    while size > 24:
        font = ImageFont.truetype(font_path, size)
        box = draw.textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= max_width:
            return font
        size -= 4
    return ImageFont.truetype(font_path, size)


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
    font_date = ImageFont.truetype(font_path, 100)
    font_label = ImageFont.truetype(font_path, 54)
    font_time = ImageFont.truetype(font_path, 84)
    font_item_time = ImageFont.truetype(font_path, 60)
    font_note = ImageFont.truetype(font_path, 38)
    font_msg = ImageFont.truetype(font_path, 48)

    text, accent = theme["text"], theme["accent"]
    max_text_width = width - SIDE_MARGIN * 2

    events = status.get("events", [])
    reserved = status.get("reserved", [])
    # セクション数に応じて上部の余白を詰める
    compact = bool(events) or bool(reserved)

    y = 150 if compact else 220
    y = _center_text(draw, y, img_conf["title"], font_title, text, width) + 28
    y = _center_text(draw, y, img_conf["subtitle"], font_sub, text, width) + (80 if compact else 150)

    y = _center_text(draw, y, status["date"], font_date, text, width) + (70 if compact else 130)

    if status["closed"]:
        y = _center_text(draw, y, img_conf["closed_label"], font_label, accent, width) + 110
        y = _center_text(draw, y, img_conf["closed_message"], font_msg, text, width) + 60
    elif status["slots"]:
        y = _center_text(draw, y, img_conf["open_label"], font_label, text, width) + 50
        for slot in status["slots"]:
            line = f"{slot['start']}〜{slot['end']}"
            y = _center_text(draw, y, line, font_time, accent, width) + 40
        y += 30
    else:
        # 開館なしだがイベントはある日
        y = _center_text(draw, y, img_conf["no_regular_open"], font_note, text, width) + 60

    if events:
        y = _center_text(draw, y, f"― {img_conf['event_label']} ―", font_label, text, width) + 40
        for ev in events:
            name_font = _fit_font(draw, ev["name"], font_path, 60, max_text_width)
            y = _center_text(draw, y, ev["name"], name_font, accent, width) + 16
            y = _center_text(draw, y, f"{ev['start']}〜{ev['end']}", font_item_time, text, width) + 44
        y += 20

    if reserved:
        y = _center_text(draw, y, f"― {img_conf['reserved_label']} ―", font_label, text, width) + 40
        for slot in reserved:
            y = _center_text(draw, y, f"{slot['start']}〜{slot['end']}", font_item_time, text, width) + 14
        y = _center_text(draw, y, img_conf["reserved_note"], font_note, accent, width) + 30

    IMAGE_PATH.parent.mkdir(exist_ok=True)
    image.save(IMAGE_PATH)
    return IMAGE_PATH
