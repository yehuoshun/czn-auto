"""
出击流程实机测试脚本

在 Windows 上运行，逐步骤验证出击模式完整流程：
  主页 → 菜单「出击」→ 调整等级 → 进入 → 确认上阵

每步输出 ✅/❌，保存调试图到 test_output/。

用法:
  python test/test_outing_flow.py
"""

import sys
import os
import time

# 项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUT_DIR = "test_output"
os.makedirs(OUT_DIR, exist_ok=True)

# ── 延迟 import：避免 Linux 上直接炸 ──
def _import():
    global Config, Screenshot, Recognizer, Clicker
    global HomePage, OutingPage, BattlePage
    global setup_logging, logger, cv2, np

    import cv2
    import numpy as np
    import logging

    from src.core.config import Config
    from src.core.logger import setup_logging
    from src.core.screenshot import Screenshot
    from src.core.recognizer import Recognizer
    from src.core.clicker import Clicker
    from src.pages import HomePage, OutingPage, BattlePage

    return (Config, Screenshot, Recognizer, Clicker,
            HomePage, OutingPage, BattlePage,
            setup_logging, logging, cv2, np)


def _step(step_num: int, label: str, ok: bool, detail: str = ""):
    """格式化输出步骤结果。"""
    icon = "✅" if ok else "❌"
    detail_str = f" — {detail}" if detail else ""
    print(f"  {icon} [{step_num}] {label}{detail_str}")


def test_outing_flow():
    """出击流程逐步骤测试。"""
    print("=" * 60)
    print("  出击流程测试 v2")
    print("=" * 60)
    print()

    # ── 1. 初始化 ──
    print("🔧 [初始化]")
    Config, Screenshot, Recognizer, Clicker, \
        HomePage, OutingPage, BattlePage, \
        setup_logging, logging, cv2, np = _import()

    setup_logging(level="INFO", log_file=f"{OUT_DIR}/test_outing_flow.log",
                  max_size_mb=10, backup_count=1)
    logger = logging.getLogger("test.outing_flow")

    config = Config("src/config.json")
    sc = Screenshot(window_title=config.window_title, window_class=config.window_class)
    rec = Recognizer()
    home = HomePage(rec, config.data)
    outing = OutingPage(rec, config.data)
    battle = BattlePage(rec, config.data)

    if not sc.find_window():
        print("  ❌ 未找到游戏窗口 — 请先打开卡厄思梦境")
        return False
    print(f"  ✅ 窗口已找到: {config.window_title}")
    print()

    steps_passed = 0
    steps_total = 6

    # ── 2. 截图 ──
    print("📸 [步骤 1/6] 截图")
    img = sc.capture()
    if img is None:
        _step(1, "截图", False, "capture() 返回 None")
        return False
    cv_img = sc.to_cv2(img)
    cv2.imwrite(f"{OUT_DIR}/flow_01_raw.png", cv_img)
    _step(1, "截图", True, f"{cv_img.shape[1]}x{cv_img.shape[0]}")
    steps_passed += 1

    # ── 3. 页面判定 ──
    print(f"\n🔍 [步骤 2/6] 页面判定")
    page = home.detect_page(cv_img)
    ok = page in ("home", "outing", "season", "czn", "popup")
    _step(2, f"页面识别 = {page}", ok)
    if not ok:
        _step(2, f"页面识别 = {page}", False, "未知页面")
        return False
    steps_passed += 1

    # ── 4. 菜单按钮识别 ──
    print(f"\n📋 [步骤 3/6] 菜单按钮识别")
    if page == "home":
        pos = home.find_button(cv_img, "出击")
        ok = pos is not None
        _step(3, "找到「出击」按钮", ok, str(pos) if pos else "未找到")
    else:
        # 非主页：测试返回箭头识别
        pos = home.find_back_arrow(cv_img)
        ok = pos is not None
        _step(3, "找到返回箭头", ok, str(pos) if pos else "未找到")
        # 如果能返回主页，执行返回
        if ok:
            from src.core.clicker import Clicker
            clicker = Clicker(hwnd=sc.hwnd)
            clicker.click(*pos)
            time.sleep(2.0)
            cv_img2 = sc.to_cv2(sc.capture())
            cv2.imwrite(f"{OUT_DIR}/flow_03_after_back.png", cv_img2)
            page2 = home.detect_page(cv_img2)
            _step(3, "返回后页面", page2 == "home", f"page={page2}")
    steps_passed += 1

    # ── 5. 出击页面识别 ──
    print(f"\n📄 [步骤 4/6] 出击页面识别")
    if page != "outing":
        # 导航到出击页面
        clicker = Clicker(hwnd=sc.hwnd)
        pos = home.find_button(cv_img, "出击")
        if pos:
            clicker.click(*pos)
            time.sleep(2.0)
            cv_img = sc.to_cv2(sc.capture())
            cv2.imwrite(f"{OUT_DIR}/flow_04_outing_page.png", cv_img)

    is_outing = outing.is_page(cv_img)
    _step(4, "在出击页面", is_outing)
    if not is_outing:
        _step(4, "出击页面", False, "OCR 未识别到「出击」标题")
        # 保存全屏 OCR 调试
        results = rec.ocr_full(cv_img)
        texts = [f"'{t}'({c:.2f})" for _, t, c in results]
        print(f"   全屏 OCR: {', '.join(texts[:20])}")
    else:
        steps_passed += 1

        # ── 6. 等级读取 ──
        print(f"\n📊 [步骤 5/6] 等级读取")
        level = outing.read_level(cv_img)
        ok = level is not None
        _step(5, f"当前等级 = LV.{level}", ok)
        if ok:
            steps_passed += 1

            # ── 7. 按钮识别 ──
            print(f"\n🎯 [步骤 6/6] 按钮识别")
            enter = outing.find_enter_button(cv_img)
            confirm = outing.find_confirm_button(cv_img)
            arrow_left = outing.get_arrow_left_pos(cv_img)

            _step(6, "进入按钮", enter is not None, str(enter) if enter else "未找到")
            _step(6, "确认上阵按钮", confirm is not None, str(confirm) if confirm else "未找到")
            _step(6, "左箭头坐标", True, str(arrow_left))

            if enter:
                steps_passed += 1

                # ── 标注截图 ──
                dbg = cv_img.copy()
                h, w = cv_img.shape[:2]
                if enter:
                    ex, ey = int(enter[0] * w / 1920), int(enter[1] * h / 1080)
                    cv2.circle(dbg, (ex, ey), 8, (0, 255, 0), -1)
                    cv2.putText(dbg, "ENTER", (ex + 10, ey),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                if confirm:
                    cx, cy = int(confirm[0] * w / 1920), int(confirm[1] * h / 1080)
                    cv2.circle(dbg, (cx, cy), 8, (0, 255, 255), -1)
                    cv2.putText(dbg, "CONFIRM", (cx + 10, cy),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.putText(dbg, f"LV.{level}", (30, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                cv2.imwrite(f"{OUT_DIR}/flow_06_annotated.png", dbg)
                print(f"\n   📝 标注截图: {OUT_DIR}/flow_06_annotated.png")

    # ── 总结 ──
    print()
    print("=" * 60)
    print(f"  结果: {steps_passed}/{steps_total} 步骤通过")
    print(f"  调试图: {OUT_DIR}/flow_*.png")
    print("=" * 60)
    return steps_passed == steps_total


if __name__ == "__main__":
    success = test_outing_flow()
    sys.exit(0 if success else 1)
