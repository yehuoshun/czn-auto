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

    def _parse_ocr_result(self, raw: list) -> list:
        """
        将 PaddleOCR 原始结果统一解析为 [(bbox, text, confidence), ...]。

        PaddleOCR 3.x predict() 返回的 item 可能是 OCRResult 对象或 dict，
        不同版本格式有差异，这里统一处理。
        """
        results = []
        for item in raw:
            # OCRResult 对象格式 (PP-OCRv6 3.x)
            if hasattr(item, 'rec_texts') and hasattr(item, 'rec_scores'):
                texts = item.rec_texts or []
                scores = item.rec_scores or []
                boxes = item.dt_polys if hasattr(item, 'dt_polys') else []
            # 单结果 OCRResult 对象
            elif hasattr(item, 'rec_text') and hasattr(item, 'rec_score'):
                texts = [item.rec_text] if item.rec_text else []
                scores = [item.rec_score] if hasattr(item, 'rec_score') else [1.0]
                boxes = item.dt_poly if hasattr(item, 'dt_poly') else []
                if boxes:
                    boxes = [boxes]
            # dict 格式
            elif isinstance(item, dict):
                texts = item.get('rec_texts', item.get('rec_text', []))
                if isinstance(texts, str):
                    texts = [texts]
                scores = item.get('rec_scores', item.get('rec_score', [1.0] * len(texts)))
                if isinstance(scores, (int, float)):
                    scores = [scores]
                boxes = item.get('dt_polys', item.get('dt_poly', []))
                if boxes and not isinstance(boxes[0], list):
                    boxes = [boxes]
            else:
                continue

            for i, text in enumerate(texts):
                if not text:
                    continue
                bbox = boxes[i] if i < len(boxes) else [[0, 0], [0, 0], [0, 0], [0, 0]]
                conf = scores[i] if i < len(scores) else 1.0
                results.append((bbox, text, conf))

        return results

    def _ocr_raw(self, image: np.ndarray) -> list:
        """
        调用 PaddleOCR predict 并返回解析后的结果列表。
        """
        ocr = _get_ocr()
        try:
            raw = list(ocr.predict(image))
            return self._parse_ocr_result(raw)
        except Exception as e:
            logger.warning(f"OCR 调用失败: {e}")
            return []

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

        results = self._ocr_raw(region)
        texts = [t for _, t, _ in results]

        text = " ".join(texts).strip()
        logger.debug(f"OCR 区域 ({x},{y},{w},{h}): '{text}'")
        return text

    def ocr_full(self, screenshot: np.ndarray) -> list:
        """
        全屏/区域 OCR
        返回: [(bbox, text, confidence), ...]
        bbox: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        """
        return self._ocr_raw(screenshot)

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