"""
页面模块

导出所有页面识别类。
"""

from .base import BasePage
from .home import HomePage
from .season import SeasonPage
from .czn import CznPage
from .outing import OutingPage
from .battle import BattlePage

__all__ = [
    "BasePage",
    "HomePage",
    "SeasonPage",
    "CznPage",
    "OutingPage",
    "BattlePage",
]