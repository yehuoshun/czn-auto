"""
常驻卡厄思页面模块 - 卡厄思子页面识别
主页菜单点击「卡厄思」进入，包含关卡选择、难度、进入战斗等
纯识别，不包含点击操作
"""

import cv2
import logging

logger = logging.getLogger("czn-auto.czn")

# ==================== ROI 定义 (屏幕比例) ====================

# 页面标题区域（左上角），用于验证是否在卡厄思页面
TITLE_LEFT = 0.05
TITLE_RIGHT = 0.35
TITLE_TOP = 0.02
TITLE_BOTTOM = 0.08

# 返回箭头模板（复用 commons）
BACK_ARROW_TEMPLATE = "src/images/commons/back_arrow.png"
BACK_ARROW_THRESHOLD = 0.45

# 关卡列表区域（TODO: 截图后精确调整）
STAGE_AREA_LEFT = 0.10
STAGE_AREA_RIGHT = 0.85
STAGE_AREA_TOP = 0.15
STAGE_AREA_BOTTOM = 0.90

# 确定/进入战斗按钮区域（TODO: 截图后精确调整）
CONFIRM_BTN_LEFT = 0.35
CONFIRM_BTN_RIGHT = 0.65
CONFIRM_BTN_TOP = 0.85
CONFIRM_BTN_BOTTOM = 0.95

# 难度选择按钮区域（TODO: 截图后精确调整）
DIFFICULTY_AREA_LEFT = 0.10
DIFFICULTY_AREA_RIGHT = 0.90
DIFFICULTY_AREA_TOP = 0.80
DIFFICULTY_AREA_BOTTOM = 0.95

# 难度关键词（OCR 匹配用）
DIFFICULTY_KEYWORDS = ["简单", "普通", "困难", "噩梦", "地狱"]


class CznPage:
    """常驻卡厄思页面识别"""

    def __init__(self, recognizer, config: dict = None):
        self.rec = recognizer
        self.config = config or {}

    # ==================== 页面判定 ====================

    def is_czn(self, screenshot) -> bool:
        """判定当前是否在常驻卡厄思页面"""
        h, w = screenshot.shape[:2]
        x1 = int(w * TITLE_LEFT)
        y1 = int(h * TITLE_TOP)
        x2 = int(w * TITLE_RIGHT)
        y2 = int(h * TITLE_BOTTOM)

        text = self.rec.ocr_region(screenshot, x1, y1, x2 - x1, y2 - y1)
        if not text:
            return False

        if "卡厄思" in text:
            logger.debug(f"卡厄思页面标题: '{text}'")
            return True

        return False

    # ==================== 关卡识别 ====================

    def find_stages(self, screenshot) -> list[dict]:
        """
        OCR 识别关卡列表区域
        返回: [{ "text": "关卡名", "center": (x, y), "bbox": [[x1,y1],...], "conf": float }, ...]
        """
        h, w = screenshot.shape[:2]
        x1 = int(w * STAGE_AREA_LEFT)
        y1 = int(h * STAGE_AREA_TOP)
        x2 = int(w * STAGE_AREA_RIGHT)
        y2 = int(h * STAGE_AREA_BOTTOM)

        roi = screenshot[y1:y2, x1:x2]
        raw = self.rec.ocr_full(roi)

        stages = []
        for bbox, text, conf in raw:
            cx = x1 + int((bbox[0][0] + bbox[2][0]) / 2)
            cy = y1 + int((bbox[0][1] + bbox[2][1]) / 2)
            base_x = int(cx * 1920 / w)
            base_y = int(cy * 1080 / h)
            stages.append({
                "text": text,
                "center": (base_x, base_y),
                "bbox": bbox,
                "conf": conf,
            })
            logger.debug(f"关卡: '{text}' conf={conf:.2f} pos=({base_x},{base_y})")

        return stages

    def find_stage_by_name(self, screenshot, keyword: str) -> tuple | None:
        """
        按名称查找关卡，返回 1920×1080 基准坐标
        keyword: 关卡名称关键词（模糊匹配）
        """
        stages = self.find_stages(screenshot)
        for s in stages:
            if keyword in s["text"] or s["text"] in keyword:
                logger.info(f"找到关卡: '{s['text']}' pos=({s['center'][0]},{s['center'][1]})")
                return s["center"]
        return None

    # ==================== 难度选择 ====================

    def find_difficulty(self, screenshot) -> dict | None:
        """
        OCR 识别当前选中的难度
        返回: { "text": "困难", "center": (x, y), "conf": float } 或 None
        """
        h, w = screenshot.shape[:2]
        x1 = int(w * DIFFICULTY_AREA_LEFT)
        y1 = int(h * DIFFICULTY_AREA_TOP)
        x2 = int(w * DIFFICULTY_AREA_RIGHT)
        y2 = int(h * DIFFICULTY_AREA_BOTTOM)

        roi = screenshot[y1:y2, x1:x2]
        raw = self.rec.ocr_full(roi)

        for bbox, text, conf in raw:
            for kw in DIFFICULTY_KEYWORDS:
                if kw in text:
                    cx = x1 + int((bbox[0][0] + bbox[2][0]) / 2)
                    cy = y1 + int((bbox[0][1] + bbox[2][1]) / 2)
                    base_x = int(cx * 1920 / w)
                    base_y = int(cy * 1080 / h)
                    logger.info(f"当前难度: '{text}' pos=({base_x},{base_y})")
                    return {"text": text, "center": (base_x, base_y), "conf": conf}

        return None

    def find_difficulty_button(self, screenshot, target: str) -> tuple | None:
        """
        查找指定难度按钮，返回 1920×1080 基准坐标
        target: "简单" / "普通" / "困难" 等
        """
        h, w = screenshot.shape[:2]
        x1 = int(w * DIFFICULTY_AREA_LEFT)
        y1 = int(h * DIFFICULTY_AREA_TOP)
        x2 = int(w * DIFFICULTY_AREA_RIGHT)
        y2 = int(h * DIFFICULTY_AREA_BOTTOM)

        roi = screenshot[y1:y2, x1:x2]
        raw = self.rec.ocr_full(roi)

        for bbox, text, conf in raw:
            if target in text:
                cx = x1 + int((bbox[0][0] + bbox[2][0]) / 2)
                cy = y1 + int((bbox[0][1] + bbox[2][1]) / 2)
                base_x = int(cx * 1920 / w)
                base_y = int(cy * 1080 / h)
                logger.info(f"难度按钮: '{text}' pos=({base_x},{base_y})")
                return base_x, base_y

        return None

    # ==================== 确认/进入战斗 ====================

    def find_confirm_button(self, screenshot) -> tuple | None:
        """
        OCR 查找「确定」/「进入」/「开始」等确认按钮
        返回 1920×1080 基准坐标
        """
        h, w = screenshot.shape[:2]
        x1 = int(w * CONFIRM_BTN_LEFT)
        y1 = int(h * CONFIRM_BTN_TOP)
        x2 = int(w * CONFIRM_BTN_RIGHT)
        y2 = int(h * CONFIRM_BTN_BOTTOM)

        roi = screenshot[y1:y2, x1:x2]
        raw = self.rec.ocr_full(roi)
        confirm_words = ["确定", "进入", "开始", "出战", "挑战", "出击"]

        for bbox, text, conf in raw:
            for kw in confirm_words:
                if kw in text:
                    cx = x1 + int((bbox[0][0] + bbox[2][0]) / 2)
                    cy = y1 + int((bbox[0][1] + bbox[2][1]) / 2)
                    base_x = int(cx * 1920 / w)
                    base_y = int(cy * 1080 / h)
                    logger.info(f"确认按钮: '{text}' pos=({base_x},{base_y})")
                    return base_x, base_y

        return None

    # ==================== 调试 ====================

    def save_debug(self, screenshot, name: str):
        """保存调试图（用于远程调试）"""
        import os
        os.makedirs("test_output", exist_ok=True)
        path = f"test_output/czn_{name}.png"
        cv2.imwrite(path, screenshot)
        logger.info(f"调试图已保存: {path}")