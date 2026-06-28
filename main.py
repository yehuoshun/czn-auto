"""
主入口 - 卡厄斯梦境自动化脚本
主循环: 截图 → 识别 → 决策 → 操作 → 循环
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
import traceback
import logging

from src.core.config import Config
from src.core.logger import setup_logging, print_startup_banner
from src.core.screenshot import Screenshot
from src.core.recognizer import Recognizer
from src.core.clicker import Clicker
from src.modules.home import HomePage
from src.modules.season import SeasonPage
from src.modules.czn import CznPage
from src.modules.outing import OutingPage
from src.modules.battle import BattlePage
from src.actions.home_actions import HomeActions
from src.actions.season_actions import SeasonActions
from src.actions.czn_actions import CznActions
from src.actions.outing_actions import OutingActions
from src.actions.battle_actions import BattleActions

logger = logging.getLogger("czn-auto.main")

MODE_MANUAL = "manual"
MODE_OUTING = "outing"
MODE_SEASON = "season"
MODE_CZN = "czn"


class CZNAuto:
    def __init__(self, config_path: str = "src/config.json"):
        self.config = Config(config_path)
        setup_logging(
            level=self.config.get("log", "level", default="INFO"),
            log_file=self.config.get("log", "file", default="logs/czn-auto.log"),
            max_size_mb=self.config.get("log", "max_size_mb", default=10),
            backup_count=self.config.get("log", "backup_count", default=3),
            compact=self.config.get("log", "compact", default=False),
        )
        print_startup_banner(logger, self.config.data)

        self.mode = self.config.get("mode", "type", default=MODE_MANUAL)
        self.outing_cfg = self.config.get("outing", default={
            "target_level": 45, "repeat_battle": False, "max_repeats": 0,
        })
        self.battle_count = 0
        self._init_modules()

    def _init_modules(self):
        self.screenshot = Screenshot(
            window_title=self.config.window_title,
            window_class=self.config.window_class,
        )
        if not self.screenshot.find_window():
            logger.error(f"未找到窗口: {self.config.window_title}")
            sys.exit(1)

        self.recognizer = Recognizer(
            templates_dir=self.config.get("templates", "path", default="templates"),
        )
        self.clicker = Clicker(
            hwnd=self.screenshot.hwnd,
            base_width=self.config.base_width,
            base_height=self.config.base_height,
            delay_ms=self.config.click_delay_ms,
            post_click_wait_ms=self.config.post_click_wait_ms,
            humanize=self.config.get("click", "humanize", default=True),
        )

        self.home = HomePage(self.recognizer, self.config.data)
        self.season = SeasonPage(self.recognizer, self.config.data)
        self.czn = CznPage(self.recognizer, self.config.data)
        self.outing = OutingPage(self.recognizer, self.config.data)
        self.battle = BattlePage(self.recognizer, self.config.data)

        self.actions = HomeActions(self.home, self.clicker)
        self.season_actions = SeasonActions(self.season, self.clicker)
        self.cz  = CznActions(self.czn, self.clicker)
        self.outing_actions = OutingActions(self.outing, self.clicker)
        self.battle_actions = BattleActions(self.battle, self.clicker)

        logger.info(f"已初始化 (mode={self.mode})")

    def step(self) -> None:
        image = self.screenshot.capture(clicker=self.clicker, wake_ui=False)
        if image is None:
            return

        cv_img = self.screenshot.to_cv2(image)
        page = self.home.detect_page(cv_img)

        if page == "unknown":
            image = self.screenshot.capture(clicker=self.clicker, wake_ui=True)
            if image:
                cv_img = self.screenshot.to_cv2(image)
                page = self.home.detect_page(cv_img)

        # 未知页面优先检测战斗结算
        if page == "unknown" and self.mode == MODE_OUTING and self.battle.is_result(cv_img):
            self._handle_battle_result(cv_img)
            return

        match page:
            case "home":    self._handle_home(cv_img)
            case "outing":  self._handle_outing(cv_img)
            case "season":  self._handle_season(cv_img)
            case "czn":     self._handle_czn(cv_img)
            case "popup":   self._handle_popup()
            case "unknown": self._handle_unknown()

    def _handle_home(self, screenshot):
        logger.info("📍 主页")
        if self.mode == MODE_OUTING:
            pos = self.home.find_button(screenshot, "出击")
            if pos:
                self.clicker.post_click(*pos)
                time.sleep(1.5)
            else:
                self.actions.navigate_to("出击", screenshot=screenshot)
            return
        pos = self.home.find_season_banner(screenshot)
        if pos:
            self.clicker.post_click(*pos)
            time.sleep(3.0)

    def _handle_outing(self, screenshot):
        logger.info("📍 出击页面")
        if self.mode != MODE_OUTING:
            return
        self.outing_actions.set_level(screenshot, self.outing_cfg.get("target_level", 45))
        self.outing_actions.enter_battle(screenshot)
        self.outing_actions.confirm_battle(screenshot)

    def _handle_battle_result(self, screenshot):
        logger.info("📍 战斗结算")
        self.battle_count += 1
        max_r = self.outing_cfg.get("max_repeats", 0)
        if max_r > 0 and self.battle_count >= max_r:
            logger.info(f"已达最大次数 {max_r}")
            self.mode = MODE_MANUAL
            return
        self.battle_actions.click_repeat(screenshot)
        logger.info(f"再战 (第{self.battle_count}次)")

    def _handle_popup(self):
        self.actions.close_popup()

    def _handle_season(self, screenshot):
        self.season_actions.enter_czn(screenshot)

    def _handle_czn(self, screenshot):
        info = self.cz.scan_page(screenshot)
        logger.info(f"卡厄思: {info}")

    def _handle_unknown(self):
        self.actions.go_home()

    def run(self) -> None:
        iteration = 0
        max_iter = self.config.max_iterations
        logger.info(f"启动 (间隔={self.config.loop_interval_ms}ms, 上限={max_iter or '无限'})")
        try:
            while True:
                iteration += 1
                if max_iter > 0 and iteration > max_iter:
                    break
                logger.debug(f"--- #{iteration} ---")
                try:
                    self.step()
                except Exception as e:
                    logger.error(f"异常: {e}")
                    logger.debug(traceback.format_exc())
                time.sleep(self.config.loop_interval_ms / 1000.0)
        except KeyboardInterrupt:
            logger.info("用户中断")
        finally:
            logger.info("结束")


def main():
    config_path = "src/config.json"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    CZNAuto(config_path).run()


if __name__ == "__main__":
    main()
