"""
赛季页面操作 - 进入卡厄思、导航等
依赖 season 模块的识别能力，封装点击操作
"""

import time
import logging

logger = logging.getLogger("czn-auto.actions.season")


class SeasonActions:
    """赛季页面操作"""

    def __init__(self, page, clicker):
        self.page = page
        self.clicker = clicker

    def enter_czn(self, screenshot) -> bool:
        """点击卡厄思按钮进入赛季卡厄思，动画可能较慢，重试"""
        for attempt in range(5):
            pos = self.page.find_czn_button(screenshot)
            if pos:
                self.clicker.post_click(*pos)
                logger.info(f"已点击卡厄思按钮 (第{attempt+1}次)")
                time.sleep(1.5)
                return True
            logger.debug(f"卡厄思按钮未出现，等待动画... ({attempt+1}/5)")
            time.sleep(1.0)
            # 重新截图
            from src.core.screenshot import Screenshot
            sc = Screenshot(window_title="卡厄思梦境")
            if sc.find_window():
                sc.focus_window()
                img = sc.capture_imagegrab()
                if img:
                    screenshot = sc.to_cv2(img)
        logger.warning("未找到卡厄思按钮（5次重试）")
        return False