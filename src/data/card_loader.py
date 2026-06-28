"""
卡牌数据加载器
从 src/data/cards/*.json 加载所有角色卡牌，合并为 {卡名: 数据} 平铺 dict
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger("czn-auto.cards")

CARDS_DIR = Path(__file__).parent / "cards"


def load_all_cards() -> dict:
    """加载所有卡牌，返回 {卡名: {...}} """
    all_cards = {}
    for fpath in sorted(CARDS_DIR.glob("*.json")):
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        character = data.get("角色", fpath.stem)
        cards = data.get("卡牌", {})
        for name, card in cards.items():
            card["角色"] = character
            all_cards[name] = card
        logger.debug(f"已加载: {character} ({len(cards)} 张)")
    logger.info(f"卡牌数据库: {len(all_cards)} 张")
    return all_cards


def get_by_character(cards: dict, char_name: str) -> dict:
    """返回指定角色的所有卡牌"""
    return {name: c for name, c in cards.items() if c.get("角色") == char_name}


def get_by_type(cards: dict, card_type: str) -> dict:
    """返回指定类型的所有卡牌（攻击/技能/强化）"""
    return {name: c for name, c in cards.items() if c.get("type") == card_type}
