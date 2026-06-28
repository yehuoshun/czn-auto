"""
战斗结算模块 - 结算画面识别 + 等待战斗结束
纯识别，不包含点击操作
"""

import logging

logger = logging.getLogger("czn-auto.battle")

# 结算文字区域
RESULT_LEFT = 0.25
RESULT_RIGHT = 0.75
RESULT_TOP = 0.25
RESULT_BOTTOM = 0.75

# 再次挑战按钮
REPEAT_LEFT = 0.55
REPEAT_RIGHT = 0.80
REPEAT_TOP = 0.70
REPEAT_BOTTOM = 0.90


class BattlePage:
    """战斗/结算画面识别"""

    def __init__(self, recognizer, config: dict = None):
        self.rec = recognizer
        self.config = config or {}

    def is_result(self, screenshot) -> bool:
        """检测是否在战斗结算画面"""
        h, w = screenshot.shape[:2]
        x1 = int(w * RESULT_LEFT)
        y1 = int(h * RESULT_TOP)
        x2 = int(w * RESULT_RIGHT)
        y2 = int(h * RESULT_BOTTOM)

        text = self.rec.ocr_region(screenshot, x1, y1, x2 - x1, y2 - y1)
        if not text:
            return False
        return any(kw in text for kw in ("胜利", "失败", "结算", "通关"))

    def find_repeat_button(self, screenshot) -> tuple | None:
        """查找「再次挑战」按钮，返回 1920×1080 坐标"""
        h, w = screenshot.shape[:2]
        x1 = int(w * REPEAT_LEFT)
        y1 = int(h * REPEAT_TOP)
        x2 = int(w * REPEAT_RIGHT)
        y2 = int(h * REPEAT_BOTTOM)

        roi = screenshot[y1:y2, x1:x2]
        raw = self.rec.ocr_full(roi)

        for bbox, text, conf in raw:
            for kw in ("再次挑战", "重复", "再来", "继续", "再次"):
                if kw in text:
                    cx = x1 + int((bbox[0][0] + bbox[2][0]) / 2)
                    cy = y1 + int((bbox[0][1] + bbox[2][1]) / 2)
                    return int(cx * 1920 / w), int(cy * 1080 / h)
        return None

    def wait_end(self, screenshot, clicker, timeout: int = 180) -> bool:
        """
        等待战斗结束：每2秒检测竖线是否恢复
        返回 True=结束
        """
        import time
        import cv2
        import numpy as np

        start = time.time()
        while time.time() - start < timeout:
            time.sleep(2.0)

            h, w = screenshot.shape[:2]
            x1, y1 = int(w * 0.88), int(h * 0.08)
            x2, y2 = int(w * 0.99), int(h * 0.82)
            if x2 <= x1 or y2 <= y1:
                continue

            roi = screenshot[y1:y2, x1:x2]
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
            sobel = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            sobel = np.clip(np.abs(sobel), 0, 255).astype(np.uint8)
            _, edges = cv2.threshold(sobel, 60, 255, cv2.THRESH_BINARY)
            col_sums = np.sum(edges, axis=0)

            if len(np.where(col_sums > (y2 - y1) * 0.7)[0]) > 0:
                elapsed = int(time.time() - start)
                logger.info(f"战斗结束 ({elapsed}s)")
                return True

            elapsed = int(time.time() - start)
            if elapsed > 15:
                logger.debug(f"战斗中... ({elapsed}s)")

        logger.warning(f"战斗等待超时 ({timeout}s)")
        return False
