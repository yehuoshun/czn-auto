"""
出击页面识别模块

识别出击（次元奇点/精英关卡）页面，包含关卡等级、进入按钮。

单一职责：仅处理出击页面识别，不涉及点击。
"""

import re
import logging
from typing import Optional, Tuple

import numpy as np

from .base import BasePage

logger = logging.getLogger("czn-auto.pages.outing")

# ---------- ROI 定义 ----------
# 页面标题区域
TITLE_LEFT = 0.05
TITLE_RIGHT = 0.20
TITLE_TOP = 0.02
TITLE_BOTTOM = 0.08

# 中央关卡等级文字区域
LEVEL_TEXT_LEFT = 0.35
LEVEL_TEXT_RIGHT = 0.65
LEVEL_TEXT_TOP = 0.25
LEVEL_TEXT_BOTTOM = 0.45

# 箭头按钮固定坐标（基准）
ARROW_LEFT_X = 288
ARROW_LEFT_Y = 594
ARROW_RIGHT_X = 1632
ARROW_RIGHT_Y = 594

# 底部「进入」按钮区域
ENTER_BTN_LEFT = 0.30
ENTER_BTN_RIGHT = 0.70
ENTER_BTN_TOP = 0.75
ENTER_BTN_BOTTOM = 0.90

# 确认上阵按钮区域
CONFIRM_LEFT = 0.25
CONFIRM_RIGHT = 0.75
CONFIRM_TOP = 0.80
CONFIRM_BOTTOM = 0.95


class OutingPage(BasePage):
    """
    出击页面识别。
    """

    name = "outing"

    def is_page(self, screenshot: np.ndarray) -> bool:
        """
        判断是否在出击页面。

        检测标题区域是否包含「次元奇点」（关卡/页面标题）
        或页面其他关键区域包含「出击累计通关」等特征文字。
        """
        h, w = screenshot.shape[:2]

        # 检测 1：标题区域
        x1 = int(w * TITLE_LEFT)
        y1 = int(h * TITLE_TOP)
        x2 = int(w * TITLE_RIGHT)
        y2 = int(h * TITLE_BOTTOM)
        text = self.rec.ocr_region(screenshot, x1, y1, x2 - x1, y2 - y1)
        if text and ("次元奇点" in text or "出击累计" in text):
            return True

        # 检测 2：中间区域兜底
        cx1 = int(w * 0.30)
        cy1 = int(h * 0.40)
        cx2 = int(w * 0.70)
        cy2 = int(h * 0.60)
        ctext = self.rec.ocr_region(screenshot, cx1, cy1, cx2 - cx1, cy2 - cy1)
        if ctext and "次元奇点" in ctext:
            return True

        return False

    # ---------- 关卡等级 ----------

    def read_level(self, screenshot: np.ndarray) -> Optional[int]:
        """
        OCR 读取关卡等级数字。

        Returns:
            等级数字或 None
        """
        h, w = screenshot.shape[:2]
        x1 = int(w * LEVEL_TEXT_LEFT)
        y1 = int(h * LEVEL_TEXT_TOP)
        x2 = int(w * LEVEL_TEXT_RIGHT)
        y2 = int(h * LEVEL_TEXT_BOTTOM)

        text = self.rec.ocr_region(screenshot, x1, y1, x2 - x1, y2 - y1)
        if not text:
            return None

        logger.debug(f"等级区域 OCR: '{text}'")
        nums = re.findall(r'\d+', text)
        if nums:
            level = int(nums[0])
            logger.info(f"检测到关卡等级: LV.{level}")
            return level
        return None

    # ---------- 按钮 ----------

    def find_enter_button(self, screenshot: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        OCR 查找「进入」按钮。

        Returns:
            基准坐标 (x, y) 或 None
        """
        h, w = screenshot.shape[:2]
        x1 = int(w * ENTER_BTN_LEFT)
        y1 = int(h * ENTER_BTN_TOP)
        x2 = int(w * ENTER_BTN_RIGHT)
        y2 = int(h * ENTER_BTN_BOTTOM)

        roi = screenshot[y1:y2, x1:x2]
        results = self.rec.ocr_full(roi)

        for bbox, text, conf in results:
            if "进入" in text:
                cx = x1 + int((bbox[0][0] + bbox[2][0]) / 2)
                cy = y1 + int((bbox[0][1] + bbox[2][1]) / 2)
                return int(cx * 1920 / w), int(cy * 1080 / h)

        # 兜底坐标
        return 960, int(1080 * 0.82)

    def find_confirm_button(self, screenshot: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        OCR 查找确认上阵按钮。

        Returns:
            基准坐标 (x, y) 或 None
        """
        h, w = screenshot.shape[:2]
        x1 = int(w * CONFIRM_LEFT)
        y1 = int(h * CONFIRM_TOP)
        x2 = int(w * CONFIRM_RIGHT)
        y2 = int(h * CONFIRM_BOTTOM)

        roi = screenshot[y1:y2, x1:x2]
        results = self.rec.ocr_full(roi)

        for bbox, text, conf in results:
            for kw in ("确认", "出击", "开始", "出战"):
                if kw in text:
                    cx = x1 + int((bbox[0][0] + bbox[2][0]) / 2)
                    cy = y1 + int((bbox[0][1] + bbox[2][1]) / 2)
                    return int(cx * 1920 / w), int(cy * 1080 / h)
        return None

    def get_arrow_left_pos(self, screenshot: np.ndarray) -> Tuple[int, int]:
        """
        左侧切换箭头固定坐标（减小等级）。

        Returns:
            基准坐标 (x, y)
        """
        return ARROW_LEFT_X, ARROW_LEFT_Y

    def get_arrow_right_pos(self, screenshot: np.ndarray) -> Tuple[int, int]:
        """
        右侧切换箭头固定坐标（增大等级）。

        Returns:
            基准坐标 (x, y)
        """
        return ARROW_RIGHT_X, ARROW_RIGHT_Y

    def find_back_arrow(self, screenshot: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        模板匹配返回箭头。
        """
        result = self.rec.match_template(
            screenshot, "back_arrow",
            "src/images/commons/back_arrow.png",
            threshold=0.45,
        )
        if result:
            x, y, conf = result
            h, w = screenshot.shape[:2]
            return int(x * 1920 / w), int(y * 1080 / h)
        return None