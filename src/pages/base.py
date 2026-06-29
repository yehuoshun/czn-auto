"""
页面抽象基类

定义游戏页面的统一识别接口。所有具体页面（主页、赛季、CZN 等）继承此类。

单一职责：仅处理页面识别，不涉及点击操作。
"""

from abc import ABC, abstractmethod

import numpy as np


class BasePage(ABC):
    """
    游戏页面抽象基类。

    所有页面类必须实现：
      - is_page(screenshot): 判断当前是否在该页面
      - detect_page(screenshot): 返回页面标识

    属性:
        name: 页面标识名
    """

    name: str = "base"

    def __init__(self, recognizer, config: dict):
        """
        Args:
            recognizer: Recognizer 实例（OCR + 模板匹配）
            config: 配置字典
        """
        self.rec = recognizer
        self.config = config

    @abstractmethod
    def is_page(self, screenshot: np.ndarray) -> bool:
        """
        判断当前是否在该页面。

        Args:
            screenshot: OpenCV BGR 图像

        Returns:
            是否在该页面
        """
        raise NotImplementedError

    def detect_page(self, screenshot: np.ndarray) -> str:
        """
        返回页面标识。

        Args:
            screenshot: OpenCV BGR 图像

        Returns:
            页面标识字符串（如 "home", "season", "czn", "unknown"）
        """
        if self.is_page(screenshot):
            return self.name
        return "unknown"