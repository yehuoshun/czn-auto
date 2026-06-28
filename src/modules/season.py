"""
赛季页面模块 - 赛季卡厄思页面识别
识别「卡厄思」入口按钮等 UI 元素
纯识别，不包含点击操作
"""

import logging

logger = logging.getLogger("czn-auto.season")

# 搜索区域：左下角
CZN_BUTTON_LEFT = 0.0
CZN_BUTTON_RIGHT = 0.50
CZN_BUTTON_TOP = 0.50
CZN_BUTTON_BOTTOM = 0.95


class SeasonPage:
    """赛季页面识别"""

    def __init__(self, recognizer, config: dict = None):
        self.rec = recognizer
        self.config = config or {}

    def find_czn_button(self, screenshot) -> tuple | None:
        """OCR 查找左下角「卡厄思」文字，返回 1920×1080 基准坐标"""
        h, w = screenshot.shape[:2]
        x1 = int(w * CZN_BUTTON_LEFT)
        y1 = int(h * CZN_BUTTON_TOP)
        x2 = int(w * CZN_BUTTON_RIGHT)
        y2 = int(h * CZN_BUTTON_BOTTOM)

        roi = screenshot[y1:y2, x1:x2]
        all_texts = []
        for bbox, text, conf in self.rec.ocr_full(roi):
            all_texts.append(f"'{text}'")
            if "卡厄思" in text:
                cx = x1 + int((bbox[0][0] + bbox[2][0]) / 2)
                cy = y1 + int((bbox[0][1] + bbox[2][1]) / 2)
                base_x = int(cx * 1920 / w)
                base_y = int(cy * 1080 / h)
                logger.info(f"卡厄思按钮(OCR): '{text}' 基准({base_x},{base_y})")
                return base_x, base_y
        logger.debug(f"卡厄思 OCR 结果: {', '.join(all_texts) if all_texts else '(空)'}")
        # 保存调试图
        import cv2, os
        os.makedirs("test_output", exist_ok=True)
        cv2.imwrite("test_output/czn_roi.png", roi)
        return None