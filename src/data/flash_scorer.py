"""
神光一闪 / 灵光一闪 选择引擎

预设存档定义 prefer 优先级列表，OCR 选项按列表顺序匹配，排最前面的命中即选。

使用方式:
    from src.data.card_loader import load_all_cards
    from src.data.preset_loader import load_preset
    from src.data.flash_scorer import FlashScorer

    cards = load_all_cards()
    preset = load_preset("heidemarie", "aurora_sword")
    scorer = FlashScorer(cards, preset)
    best = scorer.pick_best(ocr_texts, card_name)  # → (ocr_index, prefer_index, text)
"""

import re
import logging

logger = logging.getLogger("czn-auto.flash_scorer")


class FlashScorer:
    """灵光/神光闪选择器，按预设 prefer 列表匹配"""

    def __init__(self, cards_db: dict, preset: dict = None):
        self.cards_db = cards_db
        self.preset = preset or {}
        self.prefers = self.preset.get("闪选", {})
        if self.prefers:
            logger.info(f"评分器就绪: {len(self.prefers)} 张卡牌有预设")

    def pick_best(self, ocr_texts: list[str], card_name: str) -> tuple | None:
        """
        从 OCR 选项中选择最优：先匹配图鉴分支确定是哪个，再查 prefer 列表位置

        返回: (ocr_index, prefer_index, matched_text) 或 None
        """
        card = self.cards_db.get(card_name)
        if not card:
            logger.warning(f"卡牌数据库中未找到: {card_name}")
            return None

        branches = card.get("神光一闪", [])
        if not branches:
            logger.warning(f"卡牌 {card_name} 无神光一闪数据")
            return None

        prefer_list = self.prefers.get(card_name, [])
        if not prefer_list:
            logger.warning(f"卡牌 {card_name} 无预设 prefer 列表")
            return None

        # 1. 每个 OCR 选项匹配最佳分支
        matched = []  # [(ocr_idx, branch_idx, similarity)]
        for oi, ocr_text in enumerate(ocr_texts):
            best_sim = 0
            best_bi = -1
            for bi, branch in enumerate(branches):
                sim = self._similarity(ocr_text, branch.get("effect", ""))
                if sim > best_sim:
                    best_sim = sim
                    best_bi = bi
            if best_sim >= 0.3:
                matched.append((oi, best_bi, best_sim))
                logger.debug(f"  {card_name} 选项{oi} → 分支{best_bi} (sim={best_sim:.2f})")

        if not matched:
            logger.warning(f"{card_name}: 无选项匹配任何分支")
            return None

        # 2. 按 prefer 列表排序：prefer 位置越前越优先，同位置比相似度
        def sort_key(item):
            oi, bi, sim = item
            branch_effect = branches[bi].get("effect", "")
            # 找这个分支在 prefer 列表中的位置
            for pi, prefer_text in enumerate(prefer_list):
                if self._similarity(branch_effect, prefer_text) >= 0.8:
                    return (pi, -sim)  # pi 越小越优先，sim 越大越优先
            return (999, -sim)  # 不在 prefer 列表中排最后

        matched.sort(key=sort_key)
        best_oi, best_bi, best_sim = matched[0]
        branch_effect = branches[best_bi].get("effect", "")

        # 找到 prefer 位置
        prefer_idx = -1
        for pi, prefer_text in enumerate(prefer_list):
            if self._similarity(branch_effect, prefer_text) >= 0.8:
                prefer_idx = pi
                break

        logger.info(f"{card_name}: 选项{best_oi} 命中 prefer[{prefer_idx}] (sim={best_sim:.2f})")
        return (best_oi, prefer_idx, branch_effect)

    def _similarity(self, a: str, b: str) -> float:
        """字符级相似度（最长公共子序列 / 较短文本长度）"""
        # 去空格和标点
        def clean(s):
            return re.sub(r'[\s，。、（）%×+\-]', '', s)
        a = clean(a)
        b = clean(b)
        if not a or not b:
            return 0
        # LCS 长度
        m, n = len(a), len(b)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m):
            for j in range(n):
                if a[i] == b[j]:
                    dp[i + 1][j + 1] = dp[i][j] + 1
                else:
                    dp[i + 1][j + 1] = max(dp[i + 1][j], dp[i][j + 1])
        return dp[m][n] / min(m, n)