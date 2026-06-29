"""
赛季页面识别模块

识别赛季卡厄思入口页面，查找「卡厄思」按钮位置。

单一职责：仅处理赛季页面识别，不涉及点击。
"""

import cv2
import logging
from typing import Optional, Tuple

import numpy as np

from .base import BasePage

logger = logging.getLogger("czn-auto.pages.season")

# ---------- ROI 定义 ----------
# 卡厄思按钮搜索区域（左下角）
CZN_BUTTON_LEFT = 0.0
CZN_BUTTON_RIGHT = 0.50
CZN_BUTTON_TOP = 0.50
CZN_BUTTON_BOTTOM = 0.95


class SeasonPage(BasePage):
    """
    赛季页面识别。

    通过 OCR 查找左下角「卡厄思」文字位置。
    """

    name = "season"

    def is_page(self, screenshot: np.ndarray) -> bool:
        """
        判断是否在赛季页面。

        当前实现：依赖 HomePage 的 detect_page() 返回 "season"。
        此方法主要用于验证。
        """
        # 简化：不单独实现，由 HomePage._detect_sub_page() 识别
        return False

    def find_czn_button(self, screenshot: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        OCR 查找「卡厄思」按钮位置。

        Returns:
            基准坐标 (x, y) 或 None
        """
        h, w = screenshot.shape[:2]
        x1 = int(w * CZN_BUTTON_LEFT)
        y1 = int(h * CZN_BUTTON_TOP)
        x2 = int(w * CZN_BUTTON_RIGHT)
        y2 = int(h * CZN_BUTTON_BOTTOM)

        roi = screenshot[y1:y2, x1:x2]
        results = self.rec.ocr_full(roi)

        texts_debug = []
        for bbox, text, conf in results:
            texts_debug.append(f"'{text}'")
            if "卡厄思" in text:
                cx = x1 + int((bbox[0][0] + bbox[2][0]) / 2)
                cy = y1 + int((bbox[0][1] + bbox[2][1]) / 2)
                base_x = int(cx * 1920 / w)
                base_y = int(cy * 1080 / h)
                logger.info(f"卡厄思按钮: '{text}' 基准({base_x},{base_y})")
                return base_x, base_y

        logger.debug(f"卡厄思 OCR 结果: {', '.join(texts_debug) if texts_debug else '(空)'}")

        # 保存调试图
        cv2.imwrite("test_output/season_czn_roi.png", roi)

        return None