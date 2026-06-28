"""
主页模块 - 卡厄思梦境大厅识别
策略: 竖线分割线检测 + 菜单按钮 OCR + 返回箭头模板匹配
纯识别，不包含点击操作
"""

import cv2
import numpy as np
import logging

logger = logging.getLogger("czn-auto.home")

# ==================== ROI 定义 (屏幕比例) ====================

MENU_LEFT = 0.88
MENU_RIGHT = 0.99
MENU_TOP = 0.08
MENU_BOTTOM = 0.82

BUTTON_NAMES = ["故事", "出击", "模拟", "卡厄思", "方舟城市", "主战员"]
BUTTON_Y_RATIOS = [0.15, 0.25, 0.35, 0.45, 0.55, 0.65]
BUTTON_X_RATIO = 0.90

BACK_ARROW_TEMPLATE = "src/images/commons/back_arrow.png"
BACK_ARROW_THRESHOLD = 0.45

# 赛季入口横幅（右下角，每季换图）
SEASON_BANNER_TEMPLATE = "src/images/s3/banner.png"
SEASON_BANNER_THRESHOLD = 0.7
SEASON_BANNER_LEFT = 0.40
SEASON_BANNER_RIGHT = 0.98
SEASON_BANNER_TOP = 0.75
SEASON_BANNER_BOTTOM = 0.98

# 子页面标题 OCR + 关键词→页面标识
SUB_PAGE_TITLE_LEFT = 0.05
SUB_PAGE_TITLE_RIGHT = 0.35
SUB_PAGE_TITLE_TOP = 0.02
SUB_PAGE_TITLE_BOTTOM = 0.08
SUB_PAGE_KEYWORDS = {
    "银河系灾害": "season",
    "卡厄思": "czn",
    "出击": "outing",
}


class HomePage:
    """主页大厅识别"""

    def __init__(self, recognizer, config: dict):
        self.rec = recognizer
        self.config = config
        self._last_roi_offset: tuple = (0, 0)

    # ==================== 主页检测 ====================

    def is_home(self, screenshot) -> bool:
        has_menu, _, roi_offset = self._detect_menu_panel(screenshot)
        if has_menu:
            self._last_roi_offset = roi_offset
        return has_menu

    def _detect_menu_panel(self, screenshot) -> tuple[bool, list, tuple]:
        """检测菜单栏竖线 + 返回箭头，判定是否主页"""
        h, w = screenshot.shape[:2]
        x1, y1 = int(w * MENU_LEFT), int(h * MENU_TOP)
        x2, y2 = int(w * MENU_RIGHT), int(h * MENU_BOTTOM)

        if x2 <= x1 or y2 <= y1:
            return False, [], (0, 0)

        # 竖线检测
        roi = screenshot[y1:y2, x1:x2]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
        sobel = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel = np.clip(np.abs(sobel), 0, 255).astype(np.uint8)
        _, edges = cv2.threshold(sobel, 60, 255, cv2.THRESH_BINARY)
        col_sums = np.sum(edges, axis=0)
        roi_h = y2 - y1
        has_vline = len(np.where(col_sums > roi_h * 0.7)[0]) > 0

        # 返回箭头检测
        has_back = self._detect_back_arrow(screenshot)

        is_home = has_vline and not has_back
        logger.debug(f"  主页判定: 竖线={'✅' if has_vline else '❌'} 返回={'✅' if has_back else '❌'} → {'主页' if is_home else '非主页'}")
        return is_home, [], (x1, y1)

    # ==================== 返回箭头 ====================

    def _detect_back_arrow(self, screenshot) -> bool:
        result = self.rec.match_template(screenshot, "back_arrow", BACK_ARROW_TEMPLATE, threshold=BACK_ARROW_THRESHOLD)
        return result is not None

    def has_back_arrow(self, screenshot) -> bool:
        return self._detect_back_arrow(screenshot)

    # ==================== 页面检测 ====================

    def detect_page(self, screenshot) -> str:
        if self.is_home(screenshot):
            return "home"
        if self._has_vline_without_back(screenshot):
            return "popup"
        sub = self._detect_sub_page(screenshot)
        if sub:
            return sub
        return "unknown"

    # ==================== 子页面检测 ====================

    def _detect_sub_page(self, screenshot) -> str | None:
        """OCR 左上角标题区域，识别当前子页面"""
        h, w = screenshot.shape[:2]
        x1 = int(w * SUB_PAGE_TITLE_LEFT)
        y1 = int(h * SUB_PAGE_TITLE_TOP)
        x2 = int(w * SUB_PAGE_TITLE_RIGHT)
        y2 = int(h * SUB_PAGE_TITLE_BOTTOM)
        if x2 <= x1 or y2 <= y1:
            return None
        text = self.rec.ocr_region(screenshot, x1, y1, x2 - x1, y2 - y1)
        if not text:
            return None
        for keyword, page_id in SUB_PAGE_KEYWORDS.items():
            if _fuzzy_match(keyword, text):
                logger.debug(f"子页面识别: '{text}' → {page_id}")
                return page_id
        return None

    def _has_vline_without_back(self, screenshot) -> bool:
        h, w = screenshot.shape[:2]
        x1, y1 = int(w * MENU_LEFT), int(h * MENU_TOP)
        x2, y2 = int(w * MENU_RIGHT), int(h * MENU_BOTTOM)
        if x2 <= x1 or y2 <= y1:
            return False
        roi = screenshot[y1:y2, x1:x2]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
        sobel = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel = np.clip(np.abs(sobel), 0, 255).astype(np.uint8)
        _, edges = cv2.threshold(sobel, 60, 255, cv2.THRESH_BINARY)
        col_sums = np.sum(edges, axis=0)
        has_vline = len(np.where(col_sums > (y2 - y1) * 0.7)[0]) > 0
        return has_vline and not self._detect_back_arrow(screenshot)

    # ==================== 菜单按钮 OCR ====================

    def find_button(self, screenshot, target: str) -> tuple | None:
        """OCR 查找菜单按钮，返回 (screen_x, screen_y) 或 None"""
        if target not in BUTTON_NAMES:
            return None
        h, w = screenshot.shape[:2]
        x1, y1 = int(w * MENU_LEFT), int(h * MENU_TOP)
        x2, y2 = int(w * MENU_RIGHT), int(h * MENU_BOTTOM)
        for bbox, text, conf in self.rec.ocr_full(screenshot[y1:y2, x1:x2]):
            if _fuzzy_match(target, text):
                cx = int((bbox[0][0] + bbox[2][0]) / 2)
                cy = int((bbox[0][1] + bbox[2][1]) / 2)
                return x1 + cx, y1 + cy
        return None

    def find_back_arrow(self, screenshot) -> tuple | None:
        """模板匹配找返回箭头，返回 1920×1080 基准坐标"""
        result = self.rec.match_template(screenshot, "back_arrow", BACK_ARROW_TEMPLATE, threshold=BACK_ARROW_THRESHOLD)
        if result:
            x, y, conf = result
            h, w = screenshot.shape[:2]
            base_x, base_y = int(x * 1920 / w), int(y * 1080 / h)
            logger.debug(f"返回箭头: 截图({x},{y}) → 基准({base_x},{base_y}) conf={conf:.3f}")
            return base_x, base_y
        return None

    # ==================== 赛季入口检测 ====================

    def find_season_banner(self, screenshot) -> tuple | None:
        """模板匹配右下角赛季入口横幅，返回 1920×1080 基准坐标"""
        h, w = screenshot.shape[:2]
        x1 = int(w * SEASON_BANNER_LEFT)
        y1 = int(h * SEASON_BANNER_TOP)
        x2 = int(w * SEASON_BANNER_RIGHT)
        y2 = int(h * SEASON_BANNER_BOTTOM)
        roi = screenshot[y1:y2, x1:x2]
        result = self.rec.match_template(
            roi, "season_banner", SEASON_BANNER_TEMPLATE,
            threshold=SEASON_BANNER_THRESHOLD,
        )
        if result:
            rx, ry, conf = result
            sx, sy = x1 + rx, y1 + ry
            base_x = int(sx * 1920 / w)
            base_y = int(sy * 1080 / h)
            logger.info(f"赛季入口: 基准({base_x},{base_y}) conf={conf:.3f}")
            return base_x, base_y
        return None

    # ==================== 调试 ====================

    def get_layout_debug(self, screenshot) -> dict:
        h, w = screenshot.shape[:2]
        x1, y1 = int(w * MENU_LEFT), int(h * MENU_TOP)
        x2, y2 = int(w * MENU_RIGHT), int(h * MENU_BOTTOM)
        roi = screenshot[y1:y2, x1:x2]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
        sobel = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel = np.clip(np.abs(sobel), 0, 255).astype(np.uint8)
        _, edges = cv2.threshold(sobel, 60, 255, cv2.THRESH_BINARY)
        col_sums = np.sum(edges, axis=0)
        vline_cols = np.where(col_sums > (y2 - y1) * 0.7)[0]
        text = self.rec.ocr_region(screenshot, x1, y1, roi.shape[1], roi.shape[0])
        return {
            "roi": roi, "sobel_x": sobel, "edge_binary": edges,
            "vertical_line_cols": vline_cols.tolist(),
            "has_vertical_line": len(vline_cols) > 0,
            "ocr_text": text,
            "ocr_matched": [kw for kw in BUTTON_NAMES if _fuzzy_match(kw, text)],
            "is_home": len(vline_cols) > 0 and not self._detect_back_arrow(screenshot),
        }


def _fuzzy_match(target: str, ocr_text: str) -> bool:
    """模糊匹配：互相包含 或 单字重叠≥2"""
    return target in ocr_text or ocr_text in target or sum(1 for ch in target if ch in ocr_text) >= 2