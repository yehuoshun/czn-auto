"""
主入口 - 卡厄思梦境自动化脚本

主循环：截图 → 识别 → 决策 → 操作 → 循环

架构：
  - core/     底层能力（截图、点击、OCR、配置、日志）
  - pages/    页面识别层（纯视觉，不点击）
  - main.py   状态机编排（识别→决策→操作）

单一职责：main.py 只做流程编排，不涉及具体识别或点击逻辑。
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
from src.pages import HomePage, SeasonPage, CznPage, OutingPage, BattlePage

logger = logging.getLogger("czn-auto.main")

# ---------- 模式常量 ----------
MODE_MANUAL = "manual"    # 手动模式，仅辅助识别
MODE_OUTING = "outing"    # 出击刷等级
MODE_CZN = "czn"          # 卡厄思刷取


class CZNAuto:
    """
    自动化主控制器。

    职责：
      1. 初始化底层模块
      2. 主循环：截图 → 识别 → 决策 → 操作
      3. 各模式的状态流转
    """

    def __init__(self, config_path: str = "src/config.json"):
        """初始化配置、日志、底层模块。"""
        self.config = Config(config_path)
        setup_logging(
            level=self.config.get("log", "level", default="INFO"),
            log_file=self.config.get("log", "file", default="logs/czn-auto.log"),
            max_size_mb=self.config.get("log", "max_size_mb", default=10),
            backup_count=self.config.get("log", "backup_count", default=3),
            compact=self.config.get("log", "compact", default=False),
        )
        print_startup_banner(logger, self.config.data)

        # 模式配置
        self.mode = self.config.get("mode", "type", default=MODE_MANUAL)
        self.outing_cfg = self.config.get("outing", default={
            "target_level": 45, "max_repeats": 0,
        })
        self.czn_cfg = self.config.get("czn", default={
            "stage_keyword": "幻象", "difficulty": "困难", "max_repeats": 0,
        })
        self.battle_count = 0

        self._init_modules()

    def _init_modules(self):
        """初始化截图、识别、点击、页面模块。"""
        # 截图
        self.screenshot = Screenshot(
            window_title=self.config.window_title,
            window_class=self.config.window_class,
        )
        if not self.screenshot.find_window():
            logger.error(f"未找到窗口: {self.config.window_title}")
            sys.exit(1)

        # 识别
        self.recognizer = Recognizer()

        # 点击
        self.clicker = Clicker(
            hwnd=self.screenshot.hwnd,
            post_click_wait_ms=self.config.post_click_wait_ms,
        )

        # 页面识别
        cfg = self.config.data
        self.home = HomePage(self.recognizer, cfg)
        self.season = SeasonPage(self.recognizer, cfg)
        self.czn = CznPage(self.recognizer, cfg)
        self.outing = OutingPage(self.recognizer, cfg)
        self.battle = BattlePage(self.recognizer, cfg)

        logger.info(f"初始化完成 (mode={self.mode})")

    # ---------- 截图辅助 ----------

    def _capture(self):
        """截图并转为 OpenCV BGR。"""
        img = self.screenshot.capture()
        if img is None:
            return None
        return self.screenshot.to_cv2(img)

    # ---------- 主循环 ----------

    def step(self):
        """
        单步执行：截图 → 识别 → 决策 → 操作。

        页面判定流程：
          1. HomePage.detect_page() 返回页面标识
          2. 根据标识分发到对应的 handler
          3. 未知页面检测战斗结算
        """
        cv_img = self._capture()
        if cv_img is None:
            return

        page = self.home.detect_page(cv_img)

        # 未知页面优先检测战斗结算
        if page == "unknown" and self.mode != MODE_MANUAL:
            if self.battle.is_page(cv_img):
                self._handle_battle_result(cv_img)
                return
            return  # 可能页面切换中，等下一轮

        # 页面分发
        match page:
            case "home":    self._handle_home(cv_img)
            case "outing":  self._handle_outing(cv_img)
            case "season":  self._handle_season(cv_img)
            case "czn":     self._handle_czn(cv_img)
            case "popup":   self.clicker.send_key(0x1B)  # ESC 关闭弹窗
            case _:         self._go_home()

    # ---------- 页面处理器 ----------

    def _handle_home(self, screenshot):
        """
        主页处理。

        - outing 模式：导航到出击页面
        - czn 模式：优先走赛季入口，兜底直接菜单
        - 其他模式：不做自动操作
        """
        logger.info("📍 主页")
        if self.mode == MODE_OUTING:
            self._navigate_to("出击", screenshot)
            return
        if self.mode == MODE_CZN:
            pos = self.home.find_season_banner(screenshot)
            if pos:
                self.clicker.click(*pos)
                time.sleep(3.0)
                return
            self._navigate_to("卡厄思", screenshot)

    def _handle_outing(self, screenshot):
        """出击页面：设置等级 → 进入战斗 → 确认上阵。"""
        logger.info("📍 出击页面")
        if self.mode != MODE_OUTING:
            return

        # 设置目标等级
        target = self.outing_cfg.get("target_level", 45)
        current = self.outing.read_level(screenshot)
        if current is not None and current != target:
            arrow = self.outing.get_arrow_left_pos(screenshot)
            for _ in range(10):
                self.clicker.click(*arrow)
                time.sleep(0.8)
                current = self.outing.read_level(screenshot)
                if current == target:
                    break

        # 进入战斗
        pos = self.outing.find_enter_button(screenshot)
        if pos:
            self.clicker.click(*pos)
            time.sleep(2.0)

        # 确认上阵
        pos = self.outing.find_confirm_button(screenshot)
        if pos:
            self.clicker.click(*pos)
            time.sleep(2.0)

    def _handle_season(self, screenshot):
        """赛季页面：查找并点击卡厄思入口。"""
        for attempt in range(5):
            pos = self.season.find_czn_button(screenshot)
            if pos:
                self.clicker.click(*pos)
                time.sleep(1.5)
                return
            logger.debug(f"卡厄思按钮未出现 ({attempt+1}/5)")
            time.sleep(1.0)
            cv_img = self._capture()
            if cv_img:
                screenshot = cv_img

    def _handle_czn(self, screenshot):
        """
        卡厄思页面：选关卡 → 选难度 → 进入战斗。

        流程：
          1. OCR 查找关卡，点击选中
          2. OCR 查找难度按钮，点击
          3. OCR 查找确认按钮，点击进入
        """
        if self.mode != MODE_CZN:
            return

        logger.info("📍 卡厄思页面")

        # 选关卡
        stage_kw = self.czn_cfg.get("stage_keyword", "幻象")
        pos = self.czn.find_stage_by_name(screenshot, stage_kw)
        if pos:
            self.clicker.click(*pos)
            time.sleep(0.5)
            cv_img = self._capture()
            if cv_img:
                screenshot = cv_img

        # 选难度
        difficulty = self.czn_cfg.get("difficulty", "困难")
        pos = self.czn.find_difficulty_button(screenshot, difficulty)
        if pos:
            self.clicker.click(*pos)
            time.sleep(0.3)

        # 进入战斗
        pos = self.czn.find_confirm_button(screenshot)
        if pos:
            self.clicker.click(*pos)
            logger.info("已进入战斗")

    def _handle_battle_result(self, screenshot):
        """
        战斗结算处理。

        流程：
          1. 增加战斗计数
          2. 检查是否达到最大次数
          3. 点击「再次挑战」或停止
        """
        logger.info("📍 战斗结算")
        self.battle_count += 1

        max_r = self.czn_cfg.get("max_repeats", 0) if self.mode == MODE_CZN \
                else self.outing_cfg.get("max_repeats", 0)
        if max_r > 0 and self.battle_count >= max_r:
            logger.info(f"已达最大次数 {max_r}")
            self.mode = MODE_MANUAL
            return

        # 点击再次挑战
        pos = self.battle.find_repeat_button(screenshot)
        if pos:
            self.clicker.click(*pos)
        else:
            self.clicker.click(960, 540)  # 兜底点画面中心

        logger.info(f"再战 (第{self.battle_count}次)")

    # ---------- 辅助方法 ----------

    def _navigate_to(self, target: str, screenshot):
        """导航到目标页面。"""
        pos = self.home.find_button(screenshot, target)
        if pos:
            self.clicker.click(*pos)
        else:
            # 固定坐标兜底
            from src.pages.home import BUTTON_NAMES, BUTTON_Y_RATIOS
            idx = BUTTON_NAMES.index(target)
            x = int(1920 * 0.90)
            y = int(1080 * BUTTON_Y_RATIOS[idx])
            self.clicker.click(x, y)
        time.sleep(1.5)

    def _go_home(self):
        """通过 ESC 返回主页。"""
        for _ in range(5):
            self.clicker.send_key(0x1B)
            time.sleep(0.3)

    # ---------- 启动 ----------

    def run(self):
        """
        启动主循环。

        每秒执行一次 step()，直到达到最大迭代次数或用户中断。
        """
        iteration = 0
        max_iter = self.config.max_iterations
        interval = self.config.loop_interval_ms / 1000.0

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
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("用户中断")
        finally:
            logger.info("结束")


def main():
    """入口函数。"""
    config_path = "src/config.json"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    CZNAuto(config_path).run()


if __name__ == "__main__":
    main()
