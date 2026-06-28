"""
常驻卡厄思页面操作 - 关卡选择、难度切换、进入战斗
依赖 czn 模块的识别能力，封装点击操作
"""

import time
import logging

logger = logging.getLogger("czn-auto.actions.czn")


class CznActions:
    """常驻卡厄思页面操作"""

    def __init__(self, page, clicker):
        self.page = page
        self.clicker = clicker

    def select_stage(self, screenshot, keyword: str) -> bool:
        """
        选择关卡
        keyword: 关卡名称关键词（模糊匹配）
        """
        pos = self.page.find_stage_by_name(screenshot, keyword)
        if pos:
            self.clicker.post_click(*pos)
            logger.info(f"已选择关卡: {keyword} ({pos[0]},{pos[1]})")
            time.sleep(0.5)
            return True
        logger.warning(f"未找到关卡: {keyword}")
        return False

    def select_difficulty(self, screenshot, target: str) -> bool:
        """
        选择难度
        target: "简单" / "普通" / "困难" 等
        """
        pos = self.page.find_difficulty_button(screenshot, target)
        if pos:
            self.clicker.post_click(*pos)
            logger.info(f"已选择难度: {target} ({pos[0]},{pos[1]})")
            time.sleep(0.5)
            return True
        logger.warning(f"未找到难度按钮: {target}")
        return False

    def enter_battle(self, screenshot) -> bool:
        """
        点击确认/进入战斗按钮
        """
        pos = self.page.find_confirm_button(screenshot)
        if pos:
            self.clicker.post_click(*pos)
            logger.info(f"已点击进入战斗 ({pos[0]},{pos[1]})")
            time.sleep(1.0)
            return True
        logger.warning("未找到确认/进入战斗按钮")
        return False

    def quick_start(self, screenshot, difficulty: str = "困难") -> bool:
        """
        一键启动：选择难度 → 进入战斗
        如果关卡列表有默认选中则跳过关卡选择
        """
        if not self.select_difficulty(screenshot, difficulty):
            return False
        time.sleep(0.3)
        return self.enter_battle(screenshot)

    def scan_page(self, screenshot) -> dict:
        """
        扫描当前页面所有可操作元素，返回结构化信息
        用于调试和了解页面布局
        """
        info = {
            "is_czn": self.page.is_czn(screenshot),
            "stages": self.page.find_stages(screenshot),
            "difficulty": self.page.find_difficulty(screenshot),
            "confirm_btn": self.page.find_confirm_button(screenshot),
        }
        logger.info(f"页面扫描: czn={info['is_czn']}, "
                     f"关卡数={len(info['stages'])}, "
                     f"难度={info['difficulty']}, "
                     f"确认按钮={'有' if info['confirm_btn'] else '无'}")
        return info