"""
常驻卡厄思页面识别模块

识别幻象剧场关卡界面，包含关卡列表、难度选择、确认按钮。

单一职责：仅处理 CZN 页面识别，不涉及点击。

注意：ROI 为占位符，需在实际游戏运行时用校准脚本微调。
"""

import cv2
import logging
from typing import Optional, Tuple, List, Dict

import numpy as np

from .base import BasePage

logger = logging.getLogger("czn-auto.pages.czn")

# ---------- ROI 定义（屏幕比例） ----------
# 页面标题区域（验证是否在 CZN 页面）
TITLE_LEFT = 0.05
TITLE_RIGHT = 0.35
TITLE_TOP = 0.02
TITLE_BOTTOM = 0.08

# 关卡列表区域（TODO: 截图后精确调整）
STAGE_AREA_LEFT = 0.10
STAGE_AREA_RIGHT = 0.85
STAGE_AREA_TOP = 0.15
STAGE_AREA_BOTTOM = 0.90

# 难度选择区域（TODO: 截图后精确调整）
DIFFICULTY_AREA_LEFT = 0.10
DIFFICULTY_AREA_RIGHT = 0.90
DIFFICULTY_AREA_TOP = 0.80
DIFFICULTY_AREA_BOTTOM = 0.95

# 确认按钮区域（TODO: 截图后精确调整）
CONFIRM_BTN_LEFT = 0.35
CONFIRM_BTN_RIGHT = 0.65
CONFIRM_BTN_TOP = 0.85
CONFIRM_BTN_BOTTOM = 0.95

# 难度关键词
DIFFICULTY_KEYWORDS = ["简单", "普通", "困难", "噩梦", "地狱"]


class CznPage(BasePage):
    """
    常驻卡厄思（幻象剧场）页面识别。
    """

    name = "czn"

    def is_page(self, screenshot: np.ndarray) -> bool:
        """
        判断是否在 CZN 页面。

        OCR 左上角标题区域检测「卡厄思」关键字。
        """
        h, w = screenshot.shape[:2]
        x1 = int(w * TITLE_LEFT)
        y1 = int(h * TITLE_TOP)
        x2 = int(w * TITLE_RIGHT)
        y2 = int(h * TITLE_BOTTOM)

        text = self.rec.ocr_region(screenshot, x1, y1, x2 - x1, y2 - y1)
        if not text:
            return False

        if "卡厄思" in text:
            logger.debug(f"CZN 页面标题: '{text}'")
            return True

        return False

    # ---------- 关卡识别 ----------

    def find_stages(self, screenshot: np.ndarray) -> List[Dict]:
        """
        OCR 识别关卡列表。

        Returns:
            [{ "text": "关卡名", "center": (x, y), "conf": float }, ...]
        """
        h, w = screenshot.shape[:2]
        x1 = int(w * STAGE_AREA_LEFT)
        y1 = int(h * STAGE_AREA_TOP)
        x2 = int(w * STAGE_AREA_RIGHT)
        y2 = int(h * STAGE_AREA_BOTTOM)

        roi = screenshot[y1:y2, x1:x2]
        results = self.rec.ocr_full(roi)

        stages = []
        for bbox, text, conf in results:
            cx = x1 + int((bbox[0][0] + bbox[2][0]) / 2)
            cy = y1 + int((bbox[0][1] + bbox[2][1]) / 2)
            base_x = int(cx * 1920 / w)
            base_y = int(cy * 1080 / h)
            stages.append({
                "text": text,
                "center": (base_x, base_y),
                "conf": conf,
            })
            logger.debug(f"关卡: '{text}' pos=({base_x},{base_y}) conf={conf:.2f}")

        return stages

    def find_stage_by_name(self, screenshot: np.ndarray, keyword: str) -> Optional[Tuple[int, int]]:
        """
        按名称查找关卡。

        Args:
            keyword: 关卡名称关键词（模糊匹配）

        Returns:
            基准坐标 (x, y) 或 None
        """
        stages = self.find_stages(screenshot)
        for s in stages:
            if keyword in s["text"] or s["text"] in keyword:
                logger.info(f"找到关卡: '{s['text']}' pos=({s['center'][0]},{s['center'][1]})")
                return s["center"]
        return None

    # ---------- 难度识别 ----------

    def find_difficulty(self, screenshot: np.ndarray) -> Optional[Dict]:
        """
        OCR 识别当前选中难度。

        Returns:
            { "text": "困难", "center": (x, y) } 或 None
        """
        h, w = screenshot.shape[:2]
        x1 = int(w * DIFFICULTY_AREA_LEFT)
        y1 = int(h * DIFFICULTY_AREA_TOP)
        x2 = int(w * DIFFICULTY_AREA_RIGHT)
        y2 = int(h * DIFFICULTY_AREA_BOTTOM)

        roi = screenshot[y1:y2, x1:x2]
        results = self.rec.ocr_full(roi)

        for bbox, text, conf in results:
            for kw in DIFFICULTY_KEYWORDS:
                if kw in text:
                    cx = x1 + int((bbox[0][0] + bbox[2][0]) / 2)
                    cy = y1 + int((bbox[0][1] + bbox[2][1]) / 2)
                    base_x = int(cx * 1920 / w)
                    base_y = int(cy * 1080 / h)
                    logger.info(f"当前难度: '{text}' pos=({base_x},{base_y})")
                    return {"text": text, "center": (base_x, base_y)}

        return None

    def find_difficulty_button(self, screenshot: np.ndarray, target: str) -> Optional[Tuple[int, int]]:
        """
        查找指定难度按钮。

        Args:
            target: 难度名称（如 "困难"）

        Returns:
            基准坐标 (x, y) 或 None
        """
        h, w = screenshot.shape[:2]
        x1 = int(w * DIFFICULTY_AREA_LEFT)
        y1 = int(h * DIFFICULTY_AREA_TOP)
        x2 = int(w * DIFFICULTY_AREA_RIGHT)
        y2 = int(h * DIFFICULTY_AREA_BOTTOM)

        roi = screenshot[y1:y2, x1:x2]
        results = self.rec.ocr_full(roi)

        for bbox, text, conf in results:
            if target in text:
                cx = x1 + int((bbox[0][0] + bbox[2][0]) / 2)
                cy = y1 + int((bbox[0][1] + bbox[2][1]) / 2)
                base_x = int(cx * 1920 / w)
                base_y = int(cy * 1080 / h)
                logger.info(f"难度按钮 '{text}': pos=({base_x},{base_y})")
                return base_x, base_y

        return None

    # ---------- 确认按钮 ----------

    def find_confirm_button(self, screenshot: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        OCR 查找确认/进入战斗按钮。

        Returns:
            基准坐标 (x, y) 或 None
        """
        h, w = screenshot.shape[:2]
        x1 = int(w * CONFIRM_BTN_LEFT)
        y1 = int(h * CONFIRM_BTN_TOP)
        x2 = int(w * CONFIRM_BTN_RIGHT)
        y2 = int(h * CONFIRM_BTN_BOTTOM)

        roi = screenshot[y1:y2, x1:x2]
        results = self.rec.ocr_full(roi)

        confirm_words = ["确定", "进入", "开始", "出战", "挑战", "出击"]

        for bbox, text, conf in results:
            for kw in confirm_words:
                if kw in text:
                    cx = x1 + int((bbox[0][0] + bbox[2][0]) / 2)
                    cy = y1 + int((bbox[0][1] + bbox[2][1]) / 2)
                    base_x = int(cx * 1920 / w)
                    base_y = int(cy * 1080 / h)
                    logger.info(f"确认按钮 '{text}': pos=({base_x},{base_y})")
                    return base_x, base_y

        return None

    # ---------- 调试 ----------

    def save_debug(self, screenshot: np.ndarray, name: str):
        """保存调试图。"""
        import os
        os.makedirs("test_output", exist_ok=True)
        path = f"test_output/czn_{name}.png"
        cv2.imwrite(path, screenshot)
        logger.info(f"调试图已保存: {path}")