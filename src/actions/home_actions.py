"""
主页操作 - 导航、返回、关闭弹窗
依赖 home 模块的识别能力，封装点击操作
"""

import time
import logging

logger = logging.getLogger("czn-auto.actions")


class HomeActions:
    """主页/子页面操作"""

    def __init__(self, home, clicker, screenshot_mod=None):
        self.home = home
        self.clicker = clicker
        self._screenshot_mod = screenshot_mod

    def _get_screenshot(self):
        if self._screenshot_mod is None:
            from src.core.screenshot import Screenshot
            self._screenshot_mod = Screenshot
        return self._screenshot_mod

    def _capture(self) -> "np.ndarray | None":
        """截图并返回 OpenCV 格式"""
        sc = self._get_screenshot()(window_title="卡厄思梦境")
        if not sc.find_window():
            return None
        sc.focus_window()
        time.sleep(0.2)
        img = sc.capture_imagegrab()
        return sc.to_cv2(img) if img else None

    # ==================== 导航 ====================

    def navigate_to(self, target: str, screenshot=None) -> bool:
        """导航到目标页面（出击/模拟/卡厄思/方舟城市/主战员）"""
        if screenshot is not None:
            pos = self.home.find_button(screenshot, target)
            if pos:
                self.clicker.post_click(*pos)
                logger.info(f"导航到: {target} (OCR)")
                time.sleep(1.5)
                return True

        # 兜底: 固定坐标
        from src.modules.home import BUTTON_NAMES, BUTTON_X_RATIO, BUTTON_Y_RATIOS
        idx = BUTTON_NAMES.index(target)
        x, y = int(1920 * BUTTON_X_RATIO), int(1080 * BUTTON_Y_RATIOS[idx])
        self.clicker.post_click(x, y)
        logger.info(f"导航到: {target} (固定坐标 {x},{y})")
        time.sleep(1.5)
        return True

    # ==================== 返回主页 ====================

    def go_home(self) -> bool:
        """点击返回箭头回到主页，ESC 兜底"""
        cv_img = self._capture()
        if cv_img is not None:
            pos = self.home.find_back_arrow(cv_img)
            if pos:
                self.clicker.post_click(*pos)
                logger.info(f"已点击返回箭头 ({pos[0]},{pos[1]})")
                time.sleep(1.5)
                if self._verify_home():
                    return True
                logger.debug("点击返回箭头后未回到主页，尝试 ESC")

        for _ in range(5):
            self.clicker.send_key(0x1B)
            time.sleep(0.3)
        return True

    def _verify_home(self) -> bool:
        cv_img = self._capture()
        return cv_img is not None and not self.home.has_back_arrow(cv_img)

    # ==================== 弹窗 ====================

    def close_popup(self) -> bool:
        self.clicker.send_key(0x1B)
        time.sleep(0.3)
        return True