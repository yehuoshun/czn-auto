"""
出击操作 - 切换等级 + 进入战斗
"""

import time
import logging

logger = logging.getLogger("czn-auto.actions.outing")


class OutingActions:
    """出击页面操作"""

    def __init__(self, page, clicker):
        self.page = page
        self.clicker = clicker

    def set_level(self, screenshot, target_level: int, max_clicks: int = 10) -> bool:
        """
        点击←箭头直到目标等级
        """
        current = self.page.read_level(screenshot)
        if current is None:
            logger.warning("无法读取当前等级")
            return False

        if current == target_level:
            logger.info(f"已是目标等级: LV.{target_level}")
            return True

        logger.info(f"当前: LV.{current} → 目标: LV.{target_level}")
        arrow = self.page.get_arrow_left_pos(screenshot)

        for i in range(max_clicks):
            self.clicker.post_click(*arrow)
            time.sleep(0.8)
            current = self.page.read_level(screenshot)
            if current == target_level:
                logger.info(f"已切换到 LV.{target_level} ({i+1}次)")
                return True

        logger.warning(f"切换失败: 目标 LV.{target_level}")
        return False

    def enter_battle(self, screenshot) -> bool:
        """点击「进入」"""
        pos = self.page.find_enter_button(screenshot)
        if pos:
            self.clicker.post_click(*pos)
            time.sleep(2.0)
            return True
        logger.warning("未找到进入按钮")
        return False

    def confirm_battle(self, screenshot) -> bool:
        """确认上阵"""
        pos = self.page.find_confirm_button(screenshot)
        if pos:
            self.clicker.post_click(*pos)
            time.sleep(2.0)
            return True
        logger.info("无确认按钮→跳过")
        return False

    def go_home(self, home_actions, max_try: int = 10) -> bool:
        """退回到主页"""
        for i in range(max_try):
            home_actions.go_home()
            time.sleep(1.0)
            from src.core.screenshot import Screenshot
            sc = Screenshot(window_title="卡厄思梦境")
            if sc.find_window():
                img = sc.capture_imagegrab()
                if img and not home_actions.home.has_back_arrow(sc.to_cv2(img)):
                    return True
        return False
