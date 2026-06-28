"""
战斗操作 - 等待战斗结束 + 再次挑战
"""

import time
import logging

logger = logging.getLogger("czn-auto.actions.battle")


class BattleActions:
    """战斗结算操作"""

    def __init__(self, page, clicker):
        self.page = page
        self.clicker = clicker

    def wait_end(self, screenshot, timeout: int = 180) -> bool:
        """等待战斗结束，内部每轮重新截图检测"""
        from src.core.screenshot import Screenshot
        sc = Screenshot(window_title="卡厄思梦境")
        start = time.time()

        while time.time() - start < timeout:
            time.sleep(2.0)
            if not sc.find_window():
                continue
            img = sc.capture_imagegrab()
            if img is None:
                continue
            cv_img = sc.to_cv2(img)
            # 检查是否是结算画面
            if self.page.is_result(cv_img):
                return True
            # 检查竖线恢复（回到有界面的状态）
            if self._has_vline(cv_img):
                elapsed = int(time.time() - start)
                logger.info(f"战斗结束 ({elapsed}s)")
                return True
            elapsed = int(time.time() - start)
            if elapsed > 15:
                logger.debug(f"战斗中... ({elapsed}s)")

        logger.warning(f"战斗等待超时 ({timeout}s)")
        return False

    def _has_vline(self, screenshot) -> bool:
        """检查竖线菜单栏是否存在"""
        import cv2
        import numpy as np
        h, w = screenshot.shape[:2]
        x1, y1 = int(w * 0.88), int(h * 0.08)
        x2, y2 = int(w * 0.99), int(h * 0.82)
        if x2 <= x1 or y2 <= y1:
            return False
        roi = screenshot[y1:y2, x1:x2]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
        sobel = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel = np.clip(np.abs(sobel), 0, 255).astype(np.uint8)
        _, edges = cv2.threshold(sobel, 60, 255, cv2.THRESH_BINARY)
        col_sums = np.sum(edges, axis=0)
        return len(np.where(col_sums > (y2 - y1) * 0.7)[0]) > 0

    def click_repeat(self, screenshot) -> bool:
        """点击再次挑战"""
        pos = self.page.find_repeat_button(screenshot)
        if pos:
            self.clicker.post_click(*pos)
            time.sleep(2.0)
            return True
        # 兜底：点画面中间跳过动画
        self.clicker.post_click(960, 540)
        time.sleep(1.0)
        return False
