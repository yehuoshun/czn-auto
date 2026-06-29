"""
主页识别模块

识别卡厄思梦境游戏主页大厅。

判定逻辑：
  竖线存在 + 返回箭头不存在 → 主页
  竖线存在 + 返回箭头存在   → 子页面
  竖线不存在               → 非游戏页面

单一职责：仅处理主页识别，不涉及点击。
"""

from typing import Optional, Tuple

import cv2
import numpy as np
import logging

from .base import BasePage
from ..core.recognizer import Recognizer

logger = logging.getLogger("czn-auto.pages.home")

# ---------- ROI 定义（屏幕比例 0.0~1.0） ----------
# 竖线检测区域（右侧菜单栏分割线）
MENU_LEFT = 0.88
MENU_RIGHT = 0.99
MENU_TOP = 0.08
MENU_BOTTOM = 0.82

# 返回箭头模板路径和阈值
BACK_ARROW_TEMPLATE = "src/images/commons/back_arrow.png"
BACK_ARROW_THRESHOLD = 0.45

# 菜单按钮名称（OCR 匹配）
BUTTON_NAMES = ["故事", "出击", "模拟", "卡厄思", "方舟城市", "主战员"]
BUTTON_Y_RATIOS = [0.15, 0.25, 0.35, 0.45, 0.55, 0.65]
BUTTON_X_RATIO = 0.90

# 子页面标题区域
SUB_PAGE_TITLE_LEFT = 0.05
SUB_PAGE_TITLE_RIGHT = 0.35
SUB_PAGE_TITLE_TOP = 0.02
SUB_PAGE_TITLE_BOTTOM = 0.08

# 子页面关键词 → 页面标识映射
SUB_PAGE_KEYWORDS = {
    "银河系灾害": "season",
    "卡厄思": "czn",
    "次元奇点": "outing",
}


class HomePage(BasePage):
    """
    主页大厅识别。

    通过竖线检测 + 返回箭头模板匹配判断是否在主页。
    """

    name = "home"

    def __init__(self, recognizer: Recognizer, config: dict):
        super().__init__(recognizer, config)
        # 加载返回箭头模板（首次使用时）
        self._back_arrow_template = None

    def _load_back_arrow(self) -> np.ndarray:
        """加载返回箭头模板图片。"""
        if self._back_arrow_template is None:
            self._back_arrow_template = cv2.imread(BACK_ARROW_TEMPLATE, cv2.IMREAD_COLOR)
            if self._back_arrow_template is None:
                logger.warning(f"返回箭头模板加载失败: {BACK_ARROW_TEMPLATE}")
        return self._back_arrow_template

    # ---------- 竖线检测 ----------

    def _has_vline(self, screenshot: np.ndarray) -> bool:
        """
        检测右侧菜单栏竖线是否存在。

        使用 Sobel X 梯度 + 列投影检测垂直分割线。
        """
        h, w = screenshot.shape[:2]
        x1 = int(w * MENU_LEFT)
        y1 = int(h * MENU_TOP)
        x2 = int(w * MENU_RIGHT)
        y2 = int(h * MENU_BOTTOM)

        if x2 <= x1 or y2 <= y1:
            return False

        roi = screenshot[y1:y2, x1:x2]

        # Sobel X 梯度
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
        sobel = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel = np.clip(np.abs(sobel), 0, 255).astype(np.uint8)

        # 二值化 + 列投影
        _, edges = cv2.threshold(sobel, 60, 255, cv2.THRESH_BINARY)
        col_sums = np.sum(edges, axis=0)

        # 存在足够强的竖线列
        roi_h = y2 - y1
        return len(np.where(col_sums > roi_h * 0.7)[0]) > 0

    # ---------- 返回箭头检测 ----------

    def _has_back_arrow(self, screenshot: np.ndarray) -> bool:
        """
        模板匹配检测返回箭头是否存在。
        """
        template = self._load_back_arrow()
        if template is None:
            return False

        result = self.rec.match_template(
            screenshot, "back_arrow",
            BACK_ARROW_TEMPLATE,
            threshold=BACK_ARROW_THRESHOLD,
        )
        return result is not None

    def find_back_arrow(self, screenshot: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        查找返回箭头位置。

        Returns:
            基准坐标 (x, y) 或 None
        """
        result = self.rec.match_template(
            screenshot, "back_arrow",
            BACK_ARROW_TEMPLATE,
            threshold=BACK_ARROW_THRESHOLD,
        )
        if result:
            x, y, conf = result
            h, w = screenshot.shape[:2]
            # 截图像素 → 1920×1080 基准
            base_x = int(x * 1920 / w)
            base_y = int(y * 1080 / h)
            logger.debug(f"返回箭头: 截图({x},{y}) → 基准({base_x},{base_y}) conf={conf:.3f}")
            return base_x, base_y
        return None

    # ---------- 页面判定 ----------

    def is_page(self, screenshot: np.ndarray) -> bool:
        """
        判断是否在主页。

        主页：竖线存在 + 返回箭头不存在
        """
        has_vline = self._has_vline(screenshot)
        has_back = self._has_back_arrow(screenshot)

        is_home = has_vline and not has_back
        logger.debug(
            f"主页判定: 竖线={'✅' if has_vline else '❌'} "
            f"返回={'✅' if has_back else '❌'} → {'主页' if is_home else '非主页'}"
        )
        return is_home

    def detect_page(self, screenshot: np.ndarray) -> str:
        """
        综合页面检测。

        Returns:
            "home" | "season" | "czn" | "outing" | "popup" | "unknown"
        """
        # 主页
        if self.is_page(screenshot):
            return "home"

        # 弹窗：竖线存在但无返回箭头
        if self._has_vline(screenshot) and not self._has_back_arrow(screenshot):
            return "popup"

        # 子页面识别（OCR 标题）
        sub = self._detect_sub_page(screenshot)
        if sub:
            return sub

        return "unknown"

    def _detect_sub_page(self, screenshot: np.ndarray) -> Optional[str]:
        """
        OCR 左上角标题区域识别子页面。
        """
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

    # ---------- 菜单按钮 ----------

    def find_button(self, screenshot: np.ndarray, target: str) -> Optional[Tuple[int, int]]:
        """
        查找菜单按钮位置。

        优先 OCR 匹配，失败时用固定坐标兜底。

        Args:
            target: 按钮名称（如 "出击", "卡厄思"）

        Returns:
            基准坐标 (x, y) 或 None
        """
        if target not in BUTTON_NAMES:
            return None

        # OCR 匹配
        h, w = screenshot.shape[:2]
        x1 = int(w * MENU_LEFT)
        y1 = int(h * MENU_TOP)
        x2 = int(w * MENU_RIGHT)
        y2 = int(h * MENU_BOTTOM)

        for bbox, text, conf in self.rec.ocr_full(screenshot[y1:y2, x1:x2]):
            if _fuzzy_match(target, text):
                # OCR 返回 ROI 内坐标 → 截图全局坐标 → 基准 1920×1080 坐标
                cx = x1 + int((bbox[0][0] + bbox[2][0]) / 2)
                cy = y1 + int((bbox[0][1] + bbox[2][1]) / 2)
                base_x = int(cx * 1920 / w)
                base_y = int(cy * 1080 / h)
                logger.debug(f"菜单按钮 '{target}': 截图({cx},{cy}) → 基准({base_x},{base_y})")
                return base_x, base_y

        # 固定坐标兜底（1920×1080）
        idx = BUTTON_NAMES.index(target)
        if idx < len(BUTTON_Y_RATIOS):
            base_x = int(1920 * BUTTON_X_RATIO)
            base_y = int(1080 * BUTTON_Y_RATIOS[idx])
            logger.info(f"固定坐标 {target}: ({base_x},{base_y})")
            return base_x, base_y

        return None


    # ---------- 赛季横幅 ----------

    def find_season_banner(self, screenshot: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        查找赛季横幅入口（如 S3 银河系灾害横幅）。

        模板匹配 `src/images/s3/banner.png`，找到后点击进入赛季页面。

        Returns:
            基准坐标 (x, y) 或 None
        """
        result = self.rec.match_template(
            screenshot, "season_banner",
            "src/images/s3/banner.png",
            threshold=0.40,
        )
        if result:
            x, y, conf = result
            h, w = screenshot.shape[:2]
            base_x = int(x * 1920 / w)
            base_y = int(y * 1080 / h)
            logger.info(f"赛季横幅: ({base_x},{base_y}) conf={conf:.3f}")
            return base_x, base_y
        return None


def _fuzzy_match(target: str, ocr_text: str) -> bool:
    """
    模糊匹配：互相包含或单字重叠≥2。
    """
    return (
        target in ocr_text
        or ocr_text in target
        or sum(1 for ch in target if ch in ocr_text) >= 2
    )