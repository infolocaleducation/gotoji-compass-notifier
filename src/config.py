"""config.yml の読み込み。"""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
STATUS_PATH = OUTPUT_DIR / "status.json"
IMAGE_PATH = OUTPUT_DIR / "latest.png"


def load_config() -> dict:
    with open(ROOT / "config.yml", encoding="utf-8") as f:
        return yaml.safe_load(f)
