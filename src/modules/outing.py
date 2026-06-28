"""
出击模块 - 出击页面识别（次元奇点/精英关卡）
主页点击「出击」进入，中央显示关卡等级，底部「进入」按钮
纯识别，不包含点击操作
"""

import re
import logging

logger = logging.getLogger("czn-auto.outing")

# ==================== ROI 定义 (屏幕比例) ====================

# 页面标题区域（左上角）
TITLE_LEFT = 0.05
TITLE_RIGHT = 0.20
TITLE_TOP = 0.02
TITLE_BOTTOM = 0.08

# 中央关卡等级文字
LEVEL_TEXT_LEFT = 0.35
LEVEL_TEXT_RIGHT = 0.65
LEVEL_TEXT_TOP = 0.25
LEVEL_TEXT_BOTTOM = 0.45

# 左侧箭头按钮位置
ARROW_LEFT_RATIO_X = 0.15
ARROW_RATIO_Y = 0.55

# 底部「进入」按钮
ENTER_BTN_LEFT = 0.30
ENTER_BTN_RIGHT = 0.70
ENTER_BTN_TOP = 0.75
ENTER_BTN_BOTTOM = 0.90

# 选完主战员后的确认按钮
CONFIRM_LEFT = 0.25
CONFIRM_RIGHT = 0.75
CONFIRM_TOP = 0.80
CONFIRM_BOTTOM = 0.95


class OutingPage:
    """出击页面识别"""

    def __init__(self, recognizer, config: dict = None):
        self.rec = recognizer
        self.config = config or {}

    # ==================== 页面判定 ====================

    def is_outing(self, screenshot) -> bool:
        h, w = screenshot.shape[:2]
        x1 = int(w * TITLE_LEFT)
        y1 = int(h * TITLE_TOP)
        x2 = int(w * TITLE_RIGHT)
        y2 = int(h * TITLE_BOTTOM)
        text = self.rec.ocr_region(screenshot, x1, y1, x2 - x1, y2 - y1)
        return bool(text and "出击" in text)

    # ==================== 关卡等级 ====================

    def read_level(self, screenshot) -> int | None:
        """OCR 中央区域读取关卡等级，返回数字或 None"""
        h, w = screenshot.shape[:2]
        x1 = int(w * LEVEL_TEXT_LEFT)
        y1 = int(h * LEVEL_TEXT_TOP)
        x2 = int(w * LEVEL_TEXT_RIGHT)
        y2 = int(h * LEVEL_TEXT_BOTTOM)

        text = self.rec.ocr_region(screenshot, x1, y1, x2 - x1, y2 - y1)
        if not text:
            return None

        logger.debug(f"等级区域OCR: '{text}'")
        nums = re.findall(r'\d+', text)
        if nums:
            level = int(nums[0])
            logger.info(f"检测到关卡等级: LV.{level}")
            return level
        return None

    # ==================== 进入按钮 ====================

    def find_enter_button(self, screenshot) -> tuple | None:
        """OCR 查找底部「进入」按钮，返回 1920×1080 基准坐标"""
        h, w = screenshot.shape[:2]
        x1 = int(w * ENTER_BTN_LEFT)
        y1 = int(h * ENTER_BTN_TOP)
        x2 = int(w * ENTER_BTN_RIGHT)
        y2 = int(h * ENTER_BTN_BOTTOM)

        roi = screenshot[y1:y2, x1:x2]
        raw = self.rec.ocr_full(roi)

        for bbox, text, conf in raw:
            if "进入" in text:
                cx = x1 + int((bbox[0][0] + bbox[2][0]) / 2)
                cy = y1 + int((bbox[0][1] + bbox[2][1]) / 2)
                return int(cx * 1920 / w), int(cy * 1080 / h)

        # 兜底
        return 960, int(1080 * 0.82)

    # ==================== 确认上阵 ====================

    def find_confirm_button(self, screenshot) -> tuple | None:
        """确认上阵/出击按钮（选完阵容后）"""
        h, w = screenshot.shape[:2]
        x1 = int(w * CONFIRM_LEFT)
        y1 = int(h * CONFIRM_TOP)
        x2 = int(w * CONFIRM_RIGHT)
        y2 = int(h * CONFIRM_BOTTOM)

        roi = screenshot[y1:y2, x1:x2]
        raw = self.rec.ocr_full(roi)

        for bbox, text, conf in raw:
            for kw in ("确认", "出击", "开始", "出战"):
                if kw in text:
                    cx = x1 + int((bbox[0][0] + bbox[2][0]) / 2)
                    cy = y1 + int((bbox[0][1] + bbox[2][1]) / 2)
                    return int(cx * 1920 / w), int(cy * 1080 / h)
        return None

    # ==================== 切换箭头 ====================

    def get_arrow_left_pos(self, screenshot) -> tuple:
        """左侧切换箭头固定坐标"""
        return 288, 594

    # ==================== 返回箭头 ====================

    def find_back_arrow(self, screenshot) -> tuple | None:
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
