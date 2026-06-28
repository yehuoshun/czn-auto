"""
识别模块 - OpenCV 模板匹配 + PaddleOCR 文字识别 (PP-OCRv6)
"""

import cv2
import numpy as np
import logging
from pathlib import Path

logger = logging.getLogger("czn-auto.recognizer")

# PaddleOCR 延迟加载 (首次调用时初始化)
_ocr_engine = None


def _get_ocr():
    """获取 PaddleOCR 引擎 (单例)"""
    global _ocr_engine
    if _ocr_engine is None:
        from paddleocr import PaddleOCR
        _ocr_engine = PaddleOCR(lang='ch')
        logger.info("PaddleOCR 引擎初始化完成 (PP-OCRv6)")
    return _ocr_engine


class Recognizer:
    """图像识别器"""

    def __init__(self, templates_dir: str = "src/templates"):
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self._template_cache: dict[str, np.ndarray] = {}

    # ==================== 模板匹配 ====================

    def load_template(self, name: str, path: str) -> np.ndarray:
        """加载模板图片并缓存"""
        if name not in self._template_cache:
            full_path = Path(path)
            if not full_path.exists():
                raise FileNotFoundError(f"模板文件不存在: {full_path}")

            template = cv2.imread(str(full_path), cv2.IMREAD_COLOR)
            if template is None:
                raise ValueError(f"无法读取模板: {full_path}")

            self._template_cache[name] = template
            logger.debug(f"加载模板: {name} ({full_path})")

        return self._template_cache[name]

    def match_template(
        self,
        screenshot: np.ndarray,
        template_name: str,
        template_path: str,
        threshold: float = 0.8,
    ) -> tuple[int, int, float] | None:
        """
        模板匹配
        返回 (center_x, center_y, confidence) 或 None
        """
        template = self.load_template(template_name, template_path)
        h, w = template.shape[:2]

        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            logger.debug(
                f"模板匹配成功: {template_name} 置信度={max_val:.3f} 位置=({center_x}, {center_y})"
            )
            return center_x, center_y, max_val

        logger.debug(f"模板匹配失败: {template_name} 置信度={max_val:.3f} < {threshold}")
        return None

    def match_all(
        self,
        screenshot: np.ndarray,
        templates: dict[str, dict],
    ) -> dict[str, tuple[int, int, float] | None]:
        """
        批量模板匹配
        templates: { name: { "path": str, "threshold": float } }
        返回: { name: (x, y, confidence) | None }
        """
        results = {}
        for name, cfg in templates.items():
            results[name] = self.match_template(
                screenshot,
                name,
                cfg["path"],
                cfg.get("threshold", 0.8),
            )
        return results

    # ==================== PaddleOCR 文字识别 (PP-OCRv6) ====================

    def _ocr_raw(self, image: np.ndarray) -> list:
        """
        调用 PaddleOCR predict 并返回统一格式
        predict 返回: list of dict 或 list of OCRResult
        """
        ocr = _get_ocr()
        result = list(ocr.predict(image))
        if not result:
            return []
        return result

    def ocr_region(
        self,
        screenshot: np.ndarray,
        x: int, y: int, w: int, h: int,
    ) -> str:
        """
        对指定区域做 OCR 文字识别
        返回识别到的文字 (多行用空格连接)
        """
        region = screenshot[y:y + h, x:x + w]

        raw = self._ocr_raw(region)
        if not raw:
            return ""

        # PaddleOCR 3.x predict 返回 OCRResult 对象列表
        texts = []
        for item in raw:
            if hasattr(item, 'rec_texts'):
                texts.extend(item.rec_texts)
            elif hasattr(item, 'rec_text'):
                texts.append(item.rec_text)

        text = " ".join(texts).strip()
        logger.debug(f"OCR 区域 ({x},{y},{w},{h}): '{text}'")
        return text

    def ocr_full(self, screenshot: np.ndarray) -> list:
        """
        全屏/区域 OCR
        返回: [(bbox, text, confidence), ...]
        bbox: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        """
        raw = self._ocr_raw(screenshot)
        if not raw:
            return []

        results = []
        for item in raw:
            # 兼容 OCRResult 对象和 dict 格式
            if hasattr(item, 'rec_texts'):
                texts = item.rec_texts
                scores = item.rec_scores if hasattr(item, 'rec_scores') else [1.0] * len(texts)
                boxes = item.dt_polys if hasattr(item, 'dt_polys') else []
            else:
                # dict 格式
                texts = item.get('rec_texts', [])
                scores = item.get('rec_scores', [1.0] * len(texts))
                boxes = item.get('dt_polys', [])

            for i, text in enumerate(texts):
                bbox = boxes[i] if i < len(boxes) else [[0, 0], [0, 0], [0, 0], [0, 0]]
                conf = scores[i] if i < len(scores) else 1.0
                results.append((bbox, text, conf))

        return results

    def find_text(self, screenshot: np.ndarray, keyword: str) -> list[tuple]:
        """
        搜索包含关键词的文字区域
        返回: [(x1, y1, x2, y2, text, confidence), ...]
        """
        results = self.ocr_full(screenshot)
        found = []
        for bbox, text, conf in results:
            if keyword in text:
                x1, y1 = bbox[0]
                x2, y2 = bbox[2]
                found.append((x1, y1, x2, y2, text, conf))
                logger.debug(f"找到文字: '{text}' 置信度={conf:.2f}")
        return found