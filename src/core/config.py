"""
配置模块 - JSON 配置文件加载，坐标自动缩放
"""

import json
from pathlib import Path
from typing import Any
import logging

logger = logging.getLogger("czn-auto.config")


class Config:
    """配置管理器"""

    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.data: dict[str, Any] = {}
        self._base_width = 1920
        self._base_height = 1080
        self.load()

    def load(self) -> None:
        """加载 JSON 配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        self._base_width = self.data.get("game", {}).get("screen_width", 1920)
        self._base_height = self.data.get("game", {}).get("screen_height", 1080)
        logger.info(f"配置加载成功: {self.config_path} (基准分辨率 {self._base_width}x{self._base_height})")

    def save(self) -> None:
        """保存配置回 JSON 文件"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        logger.info(f"配置已保存: {self.config_path}")

    def get(self, *keys: str, default: Any = None) -> Any:
        """
        获取嵌套配置值
        例: config.get("game", "window_title") → "卡厄斯梦境"
        """
        value = self.data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
            if value is None:
                return default
        return value

    def set(self, *keys: str, value: Any) -> None:
        """
        设置嵌套配置值
        例: config.set("click", "delay_ms", value=200)
        """
        data = self.data
        for key in keys[:-1]:
            if key not in data:
                data[key] = {}
            data = data[key]
        data[keys[-1]] = value

    @property
    def window_title(self) -> str:
        """游戏窗口标题。"""
        return self.get("game", "window_title", default="")

    @property
    def window_class(self) -> str | None:
        """游戏窗口类名（可选）。"""
        return self.get("game", "window_class")

    @property
    def base_width(self) -> int:
        """基准屏幕宽度（1920）。"""
        return self._base_width

    @property
    def base_height(self) -> int:
        """基准屏幕高度（1080）。"""
        return self._base_height

    @property
    def click_points(self) -> dict:
        """预设点击坐标配置。"""
        return self.get("click_points", default={})

    @property
    def templates(self) -> dict:
        """模板图片路径配置。"""
        return self.get("templates", default={})

    @property
    def click_delay_ms(self) -> int:
        """点击间隔毫秒数。"""
        return self.get("click", "delay_ms", default=100)

    @property
    def post_click_wait_ms(self) -> int:
        """点击后等待毫秒数。"""
        return self.get("click", "post_click_wait_ms", default=500)

    @property
    def loop_interval_ms(self) -> int:
        """主循环间隔毫秒数。"""
        return self.get("loop", "interval_ms", default=1000)

    @property
    def max_iterations(self) -> int:
        """最大迭代次数（0=无限）。"""
        return self.get("loop", "max_iterations", default=0)

    def scale_point(self, x: int, y: int, actual_w: int, actual_h: int) -> tuple[int, int]:
        """将配置坐标缩放到实际分辨率"""
        return (
            int(x * actual_w / self._base_width),
            int(y * actual_h / self._base_height),
        )