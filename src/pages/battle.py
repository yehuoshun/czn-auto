"""
战斗结算页面识别模块

识别战斗结束后的结算画面，包含「再次挑战」按钮。

单一职责：仅处理战斗结算识别，不涉及点击。
"""

import cv2
import logging
from typing import Optional, Tuple

import numpy as np

from .base import BasePage

logger = logging.getLogger("czn-auto.pages.battle")

# ---------- ROI 定义 ----------
# 结算文字区域
RESULT_LEFT = 0.25
RESULT_RIGHT = 0.75
RESULT_TOP = 0.25
RESULT_BOTTOM = 0.75

# 再次挑战按钮区域
REPEAT_LEFT = 0.55
REPEAT_RIGHT = 0.80
REPEAT_TOP = 0.70
REPEAT_BOTTOM = 0.90


class BattlePage(BasePage):
    """
    战斗结算页面识别。
    """

    name = "battle_result"

    def is_page(self, screenshot: np.ndarray) -> bool:
        """
        判断是否在战斗结算画面。
        """
        h, w = screenshot.shape[:2]
        x1 = int(w * RESULT_LEFT)
        y1 = int(h * RESULT_TOP)
        x2 = int(w * RESULT_RIGHT)
        y2 = int(h * RESULT_BOTTOM)

        text = self.rec.ocr_region(screenshot, x1, y1, x2 - x1, y2 - y1)
        if not text:
            return False

        keywords = ("胜利", "失败", "结算", "通关")
        return any(kw in text for kw in keywords)

    def find_repeat_button(self, screenshot: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        OCR 查找「再次挑战」按钮。

        Returns:
            基准坐标 (x, y) 或 None
        """
        h, w = screenshot.shape[:2]
        x1 = int(w * REPEAT_LEFT)
        y1 = int(h * REPEAT_TOP)
        x2 = int(w * REPEAT_RIGHT)
        y2 = int(h * REPEAT_BOTTOM)

        roi = screenshot[y1:y2, x1:x2]
        results = self.rec.ocr_full(roi)

        for bbox, text, conf in results:
            for kw in ("再次挑战", "重复", "再来", "继续", "再次"):
                if kw in text:
                    cx = x1 + int((bbox[0][0] + bbox[2][0]) / 2)
                    cy = y1 + int((bbox[0][1] + bbox[2][1]) / 2)
                    return int(cx * 1920 / w), int(cy * 1080 / h)
        return None