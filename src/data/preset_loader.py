"""
预设存档加载器
从 src/data/presets/{角色英文名}/*.json 加载预设卡组配置
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger("czn-auto.presets")

PRESETS_DIR = Path(__file__).parent / "presets"


def load_preset(character: str, preset_name: str) -> dict | None:
    """
    加载指定预设

    character: 角色英文名，如 "heidemarie"
    preset_name: 预设名（不含 .json），如 "aurora_sword"
    """
    path = PRESETS_DIR / character / f"{preset_name}.json"
    if not path.exists():
        logger.warning(f"预设不存在: {path}")
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    logger.info(f"已加载预设: {character}/{preset_name} ({data.get('流派', '?')})")
    return data


def list_presets(character: str) -> list[str]:
    """列出某角色的所有预设名"""
    char_dir = PRESETS_DIR / character
    if not char_dir.exists():
        return []
    return sorted([p.stem for p in char_dir.glob("*.json")])


def list_characters() -> list[str]:
    """列出所有有预设的角色英文名"""
    if not PRESETS_DIR.exists():
        return []
    return sorted([d.name for d in PRESETS_DIR.iterdir() if d.is_dir()])