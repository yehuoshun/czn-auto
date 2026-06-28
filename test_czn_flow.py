"""
测试脚本 - 验证主页→常驻卡厄思流程
运行: python test_czn_flow.py
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

# 调试输出目录
OUT_DIR = "test_output"
os.makedirs(OUT_DIR, exist_ok=True)

setup_logging(level="DEBUG", log_file=f"{OUT_DIR}/test_czn.log", max_size_mb=10, backup_count=1)
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

    # ========== Step 2: OCR 查找「卡厄思」按钮 ==========
    print("\n📸 Step 2: OCR 查找「卡厄思」按钮...")
    pos = home.find_button(cv_img, "卡厄思")
    if not pos:
        print("❌ 未找到「卡厄思」按钮")
        # 画一下搜索区域
        h, w = cv_img.shape[:2]
        from src.modules.home import MENU_LEFT, MENU_RIGHT, MENU_TOP, MENU_BOTTOM
        x1 = int(w * MENU_LEFT)
        y1 = int(h * MENU_TOP)
        x2 = int(w * MENU_RIGHT)
        y2 = int(h * MENU_BOTTOM)
        save_debug(cv_img, "02_czn_button_search", rect=(x1, y1, x2, y2), text="NOT FOUND")
        return

    print(f"   ✅ 卡厄思按钮: ({pos[0]}, {pos[1]})")
    save_debug(cv_img, "02_czn_button_found", point=pos, text=f"czn ({pos[0]},{pos[1]})")

    # ========== Step 3: 点击「卡厄思」按钮 ==========
    print("\n🖱️ Step 3: 点击「卡厄思」按钮，等待 1.5s...")
    clicker.post_click(*pos)
    time.sleep(1.5)

    # ========== Step 4: 截图 + 检测卡厄思页面 ==========
    print("\n📸 Step 4: 截图并检测卡厄思页面...")
    img2 = sc.capture(clicker=clicker, wake_ui=False)
    cv_img2 = sc.to_cv2(img2)
    page2 = home.detect_page(cv_img2)
    print(f"   页面判定: {page2}")

    save_debug(cv_img2, "03_after_click", text=f"page={page2}")

    if page2 == "czn":
        print("\n✅ 成功进入常驻卡厄思页面！")
    elif page2 == "unknown":
        print(f"\n⚠️ 页面判定为 unknown（可能进入了卡厄思但 OCR 标题没匹配到）")
        print("   检查 test_output/03_after_click.png 确认实际页面")
    else:
        print(f"\n⚠️ 页面判定: {page2}，检查 test_output/03_after_click.png")

    print("\n✅ 测试完成！查看 test_output/ 目录下的截图")


if __name__ == "__main__":
    main()
