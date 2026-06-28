"""
测试脚本 - 验证主页→赛季→卡厄思流程
运行: python test_season_flow.py
会在 test_output/ 下保存每步的截图和调试信息
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
import cv2
import logging

from src.core.config import Config
from src.core.logger import setup_logging
from src.core.screenshot import Screenshot
from src.core.recognizer import Recognizer
from src.core.clicker import Clicker
from src.modules.home import HomePage
from src.modules.season import SeasonPage

# 调试输出目录
OUT_DIR = "test_output"
os.makedirs(OUT_DIR, exist_ok=True)

setup_logging(level="DEBUG", log_file=f"{OUT_DIR}/test.log", max_size_mb=10, backup_count=1)
logger = logging.getLogger("test")


def save_debug(img, name: str, rect=None, point=None, text=""):
    """保存调试截图，可选画框/画点/写字"""
    dbg = img.copy()
    h, w = dbg.shape[:2]
    if rect:
        x1, y1, x2, y2 = rect
        cv2.rectangle(dbg, (x1, y1), (x2, y2), (0, 255, 0), 2)
    if point:
        cv2.circle(dbg, point, 10, (0, 0, 255), 3)
    if text:
        cv2.putText(dbg, text, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3)
    path = f"{OUT_DIR}/{name}.png"
    cv2.imwrite(path, dbg)
    logger.info(f"调试截图已保存: {path}")


def main():
    config = Config("src/config.json")
    sc = Screenshot(window_title=config.window_title, window_class=config.window_class)
    if not sc.find_window():
        print(f"❌ 未找到窗口: {config.window_title}")
        return

    rec = Recognizer(templates_dir=config.get("templates", "path", default="templates"))
    clicker = Clicker(
        hwnd=sc.hwnd, base_width=1920, base_height=1080,
        delay_ms=100, post_click_wait_ms=500, humanize=True,
    )
    home = HomePage(rec, config.data)
    season = SeasonPage(rec, config.data)

    # ========== Step 1: 截图 + 检测主页 ==========
    print("\n📸 Step 1: 截图并检测主页...")
    img = sc.capture(clicker=clicker, wake_ui=True)
    cv_img = sc.to_cv2(img)
    page = home.detect_page(cv_img)
    print(f"   页面判定: {page}")

    save_debug(cv_img, "01_current_page", text=f"page={page}")

    if page != "home":
        print(f"⚠️ 当前不在主页 (page={page})，请手动回到主页后重试")
        return

    # ========== Step 2: 检测赛季入口横幅 ==========
    print("\n📸 Step 2: 检测赛季入口横幅...")
    pos = home.find_season_banner(cv_img)
    if not pos:
        print("❌ 未检测到赛季入口横幅")
        # 画一下搜索区域
        h, w = cv_img.shape[:2]
        from src.modules.home import SEASON_BANNER_LEFT, SEASON_BANNER_RIGHT, SEASON_BANNER_TOP, SEASON_BANNER_BOTTOM
        x1 = int(w * SEASON_BANNER_LEFT)
        y1 = int(h * SEASON_BANNER_TOP)
        x2 = int(w * SEASON_BANNER_RIGHT)
        y2 = int(h * SEASON_BANNER_BOTTOM)
        save_debug(cv_img, "02_season_banner_search", rect=(x1, y1, x2, y2), text="NOT FOUND")
        return

    print(f"   ✅ 赛季入口: ({pos[0]}, {pos[1]})")
    save_debug(cv_img, "02_season_banner_found", point=pos, text=f"banner ({pos[0]},{pos[1]})")

    # ========== Step 3: 点击赛季入口 ==========
    print("\n🖱️ Step 3: 点击赛季入口，等待 3s 动画...")
    clicker.post_click(*pos)
    time.sleep(3.0)

    # ========== Step 4: 截图 + 检测赛季页面 ==========
    print("\n📸 Step 4: 截图并检测赛季页面...")
    img2 = sc.capture(clicker=clicker, wake_ui=False)
    cv_img2 = sc.to_cv2(img2)
    page2 = home.detect_page(cv_img2)
    print(f"   页面判定: {page2}")

    save_debug(cv_img2, "03_after_click", text=f"page={page2}")

    if page2 != "season":
        print(f"⚠️ 未进入赛季页面 (page={page2})，检查 OCR 标题识别")
        return

    # ========== Step 5: 检测卡厄思按钮（重试等动画） ==========
    print("\n📸 Step 5: 检测卡厄思按钮...")
    pos2 = None
    for attempt in range(5):
        pos2 = season.find_czn_button(cv_img2)
        if pos2:
            break
        print(f"   等待动画... ({attempt+1}/5)")
        time.sleep(1.0)
        img2 = sc.capture(clicker=clicker, wake_ui=False)
        cv_img2 = sc.to_cv2(img2)

    if not pos2:
        print("❌ 未检测到卡厄思按钮")
        h, w = cv_img2.shape[:2]
        from src.modules.season import CZN_BUTTON_LEFT, CZN_BUTTON_RIGHT, CZN_BUTTON_TOP, CZN_BUTTON_BOTTOM
        x1 = int(w * CZN_BUTTON_LEFT)
        y1 = int(h * CZN_BUTTON_TOP)
        x2 = int(w * CZN_BUTTON_RIGHT)
        y2 = int(h * CZN_BUTTON_BOTTOM)
        save_debug(cv_img2, "04_czn_button_search", rect=(x1, y1, x2, y2), text="NOT FOUND")
        return

    print(f"   ✅ 卡厄思按钮: ({pos2[0]}, {pos2[1]})")
    save_debug(cv_img2, "04_czn_button_found", point=pos2, text=f"czn ({pos2[0]},{pos2[1]})")

    # ========== Step 6: 点击卡厄思按钮 ==========
    print("\n🖱️ Step 6: 点击卡厄思按钮...")
    clicker.post_click(*pos2)
    time.sleep(1.5)

    # ========== Step 7: 截图看结果 ==========
    print("\n📸 Step 7: 截图看结果...")
    img3 = sc.capture(clicker=clicker, wake_ui=False)
    cv_img3 = sc.to_cv2(img3)
    page3 = home.detect_page(cv_img3)
    print(f"   页面判定: {page3}")
    save_debug(cv_img3, "05_final", text=f"page={page3}")

    print("\n✅ 测试完成！查看 test_output/ 目录下的截图")


if __name__ == "__main__":
    main()
