"""
出击模块单元测试

不依赖 Windows API，mock 识别层数据，测试 OutingPage 逻辑正确性。

用法:
  python -m pytest test/test_outing_unit.py -v
  或直接:
  python test/test_outing_unit.py
"""

import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Mock 识别器 ──
class MockRecognizer:
    """模拟 Recognizer，返回预设的 OCR 结果。"""

    def __init__(self):
        self._ocr_region_result = ""
        self._ocr_full_results = []  # [(bbox, text, conf), ...]
        self._template_results = {}  # {name: (x, y, conf) | None}

    def ocr_region(self, screenshot, x, y, w, h):
        return self._ocr_region_result

    def ocr_full(self, screenshot):
        return self._ocr_full_results

    def match_template(self, screenshot, name, path, threshold=0.8):
        return self._template_results.get(name)

    def find_text(self, screenshot, keyword):
        return []


# ── Mock 截图 ──
def _make_screenshot():
    """生成一个纯灰色 1920x1080 模拟截图。"""
    import numpy as np
    return np.zeros((1080, 1920, 3), dtype=np.uint8) + 128


def _test_read_level():
    """测试等级 OCR 识别。"""
    from src.pages.outing import OutingPage

    rec = MockRecognizer()
    outing = OutingPage(rec, {})
    ss = _make_screenshot()

    # 正常读取
    rec._ocr_region_result = "LV.40"
    level = outing.read_level(ss)
    assert level == 40, f"预期 40, 实际 {level}"

    # 带额外文字
    rec._ocr_region_result = "关卡等级 45/999"
    level = outing.read_level(ss)
    assert level == 45, f"预期 45, 实际 {level}"

    # 无数字
    rec._ocr_region_result = "出击"
    level = outing.read_level(ss)
    assert level is None, f"预期 None, 实际 {level}"

    # 空结果
    rec._ocr_region_result = ""
    level = outing.read_level(ss)
    assert level is None, f"预期 None, 实际 {level}"

    print("  ✅ test_read_level")


def _test_find_enter_button():
    """测试进入按钮 OCR 识别。"""
    from src.pages.outing import OutingPage

    rec = MockRecognizer()
    outing = OutingPage(rec, {})
    ss = _make_screenshot()

    # 找到"进入"按钮
    h, w = ss.shape[:2]
    btn_y1 = int(h * 0.75)
    btn_x1 = int(w * 0.30)
    rec._ocr_full_results = [
        ([[0, 0], [50, 0], [50, 20], [0, 20]], "进入", 0.95),
    ]
    pos = outing.find_enter_button(ss)
    assert pos is not None, "应找到进入按钮"
    # 坐标应缩放到基准分辨率
    cx = btn_x1 + 25  # ROI x + bbox center x
    cy = btn_y1 + 10
    expected_x = int(cx * 1920 / w)
    expected_y = int(cy * 1080 / h)
    assert pos == (expected_x, expected_y), f"预期 ({expected_x},{expected_y}), 实际 {pos}"

    # 无匹配 → 返回兜底坐标
    rec._ocr_full_results = [([[0, 0], [50, 0], [50, 20], [0, 20]], "其他文字", 0.95)]
    pos = outing.find_enter_button(ss)
    assert pos == (960, int(1080 * 0.82)), f"兜底坐标不对: {pos}"

    print("  ✅ test_find_enter_button")


def _test_find_confirm_button():
    """测试确认按钮 OCR 识别。"""
    from src.pages.outing import OutingPage

    rec = MockRecognizer()
    outing = OutingPage(rec, {})
    ss = _make_screenshot()

    # 各种关键词都应识别
    for kw in ("确认", "出击", "开始", "出战"):
        rec._ocr_full_results = [
            ([[0, 0], [60, 0], [60, 25], [0, 25]], kw, 0.92),
        ]
        pos = outing.find_confirm_button(ss)
        assert pos is not None, f"关键词 '{kw}' 应匹配"

    # 无匹配
    rec._ocr_full_results = [([[0, 0], [60, 0], [60, 25], [0, 25]], "取消", 0.95)]
    pos = outing.find_confirm_button(ss)
    assert pos is None, "不应匹配无关文字"

    print("  ✅ test_find_confirm_button")


def _test_is_page():
    """测试页面判定（基于真实 OCR 数据更新）。"""
    from src.pages.outing import OutingPage

    rec = MockRecognizer()
    outing = OutingPage(rec, {})
    ss = _make_screenshot()

    # 标题含"次元奇点"
    rec._ocr_region_result = "次元奇点"
    assert outing.is_page(ss), "标题含次元奇点应识别"

    # 标题含"出击累计"
    rec._ocr_region_result = "出击累计通关"
    assert outing.is_page(ss), "标题含出击累计应识别"

    # 标题不含
    rec._ocr_region_result = "卡厄思梦境"
    assert not outing.is_page(ss), "不应识别"

    # 空标题
    rec._ocr_region_result = ""
    assert not outing.is_page(ss), "空标题不应识别"

    print("  ✅ test_is_page")


def _test_get_arrow_pos():
    """测试箭头坐标（左右）。"""
    from src.pages.outing import OutingPage

    rec = MockRecognizer()
    outing = OutingPage(rec, {})
    ss = _make_screenshot()

    pos = outing.get_arrow_left_pos(ss)
    assert pos == (288, 594), f"左箭头坐标: {pos}"

    pos = outing.get_arrow_right_pos(ss)
    assert pos == (1632, 594), f"右箭头坐标: {pos}"

    print("  ✅ test_get_arrow_pos")


def _test_level_adjustment_logic():
    """测试等级调整方向逻辑（双向箭头）。"""
    def adjust(current, target):
        if current is None:
            return None
        if current == target:
            return 0
        if current > target:
            return -1  # 左箭头（减）
        return 1  # 右箭头（增）

    assert adjust(50, 40) == -1   # 需要减
    assert adjust(30, 40) == 1    # 需要增
    assert adjust(40, 40) == 0    # 已达标
    assert adjust(50, 50) == 0
    assert adjust(10, 100) == 1   # 大幅增加
    assert adjust(None, 40) is None

    print("  ✅ test_level_adjustment_logic")


def _test_level_adjustment_max_clicks():
    """测试等级调整最大点击次数限制。"""
    def max_clicks(current, target):
        if current > target:
            return min(current - target, 20)
        return min(target - current, 20)

    assert max_clicks(50, 40) == 10
    assert max_clicks(30, 40) == 10
    assert max_clicks(100, 40) == 20  # 限制 20 次
    assert max_clicks(40, 100) == 20  # 限制 20 次

    print("  ✅ test_level_adjustment_max_clicks")


def _test_find_back_arrow():
    """测试返回箭头识别。"""
    from src.pages.outing import OutingPage

    rec = MockRecognizer()
    outing = OutingPage(rec, {})
    ss = _make_screenshot()

    # 模板匹配找到
    rec._template_results["back_arrow"] = (100, 200, 0.85)
    pos = outing.find_back_arrow(ss)
    assert pos is not None, "应找到返回箭头"
    # 截图坐标 (100,200) → 基准坐标 (100, 200) （1:1 缩放）
    assert pos == (100, 200), f"坐标: {pos}"

    # 模板匹配未找到
    rec._template_results["back_arrow"] = None
    pos = outing.find_back_arrow(ss)
    assert pos is None, "未匹配时应返回 None"

    print("  ✅ test_find_back_arrow")


# ── 无 import cv2 的 _handle_outing 逻辑测试 ──

def _test_config_defaults():
    """测试配置默认值一致性。"""
    # config.json 的默认值
    import json
    with open("src/config.json") as f:
        cfg = json.load(f)
    assert cfg.get("outing", {}).get("target_level") == 40, "config.json target_level 应为 40"
    print("  ✅ test_config_defaults")


def main():
    print("=" * 50)
    print("  OutingPage 单元测试")
    print("=" * 50)
    print()

    tests = [
        _test_read_level,
        _test_find_enter_button,
        _test_find_confirm_button,
        _test_is_page,
        _test_get_arrow_pos,
        _test_level_adjustment_logic,
        _test_level_adjustment_max_clicks,
        _test_find_back_arrow,
        _test_config_defaults,
    ]

    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"  ❌ {t.__name__}: {e}")
            import traceback
            traceback.print_exc()
        print()

    print(f"结果: {passed}/{len(tests)} 通过")
    return passed == len(tests)


if __name__ == "__main__":
    # 只在 numpy 可用时运行
    try:
        import numpy as np
        success = main()
        sys.exit(0 if success else 1)
    except ImportError as e:
        print(f"❌ 跳过: {e}")
        print("   本测试需要 numpy，在 Windows 上直接运行即可")
        sys.exit(0)
