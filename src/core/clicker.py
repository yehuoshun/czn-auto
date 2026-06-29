"""
点击模块 - PostMessage 后台点击

通过 PostMessage 异步投递鼠标/键盘消息到目标窗口的消息队列。
完全不移动真实鼠标，适合挂机时继续使用电脑。

实现要点（参考 czn_auto 开源方案）：
  1. ChildWindowFromPointEx 解析坐标命中的渲染子窗口。
     Unity/UE 游戏实际接收输入的是子窗口，直接发顶层窗口可能被忽略。
  2. 先发 WM_MOUSEMOVE 帮助依赖 hover 状态的界面更新。
  3. 坐标自动从 1920×1080 基准缩放到实际窗口尺寸。

单一职责：仅处理 PostMessage 消息投递，不涉及截图或识别。
"""

import ctypes
import ctypes.wintypes
import logging
import time
from typing import Tuple, Optional

logger = logging.getLogger("czn-auto.clicker")

# ---------- Win32 消息常量 ----------
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MOUSEMOVE = 0x0200
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
MK_LBUTTON = 0x0001

# ChildWindowFromPointEx 标志
CWP_SKIPINVISIBLE = 0x0001
CWP_SKIPDISABLED = 0x0002
CWP_SKIPTRANSPARENT = 0x0004

# 基准分辨率
BASE_WIDTH = 1920
BASE_HEIGHT = 1080

# ---------- ctypes 签名（防止 64 位句柄截断） ----------
user32 = ctypes.windll.user32
user32.PostMessageW.argtypes = [
    ctypes.wintypes.HWND, ctypes.wintypes.UINT,
    ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM,
]
user32.PostMessageW.restype = ctypes.wintypes.BOOL
user32.ChildWindowFromPointEx.argtypes = [
    ctypes.wintypes.HWND, ctypes.wintypes.POINT, ctypes.wintypes.UINT,
]
user32.ChildWindowFromPointEx.restype = ctypes.wintypes.HWND
user32.ScreenToClient.argtypes = [ctypes.wintypes.HWND, ctypes.POINTER(ctypes.wintypes.POINT)]
user32.ScreenToClient.restype = ctypes.wintypes.BOOL
user32.ClientToScreen.argtypes = [ctypes.wintypes.HWND, ctypes.POINTER(ctypes.wintypes.POINT)]
user32.ClientToScreen.restype = ctypes.wintypes.BOOL
user32.GetClientRect.argtypes = [ctypes.wintypes.HWND, ctypes.POINTER(ctypes.wintypes.RECT)]
user32.GetClientRect.restype = ctypes.wintypes.BOOL


def _make_lparam(x: int, y: int) -> int:
    """打包坐标 → LPARAM（低 16 位 x，高 16 位 y）。"""
    return ((y & 0xFFFF) << 16) | (x & 0xFFFF)


class Clicker:
    """
    PostMessage 后台点击器。

    通过 PostMessage 向窗口消息队列投递鼠标/键盘事件。
    不移动真实鼠标，不依赖窗口焦点。
    """

    def __init__(self, hwnd: int, post_click_wait_ms: int = 500):
        """
        Args:
            hwnd: 目标窗口句柄
            post_click_wait_ms: 点击后等待毫秒数
        """
        self._hwnd = hwnd
        self.post_click_wait_ms = post_click_wait_ms

    def _get_client_size(self) -> Tuple[int, int]:
        """获取窗口客户区尺寸 (width, height)。"""
        rect = ctypes.wintypes.RECT()
        user32.GetClientRect(self._hwnd, ctypes.byref(rect))
        return rect.right - rect.left, rect.bottom - rect.top

    def _scale(self, x: int, y: int) -> Tuple[int, int]:
        """
        基准分辨率坐标 → 实际客户区坐标。
        """
        cw, ch = self._get_client_size()
        if cw == BASE_WIDTH and ch == BASE_HEIGHT:
            return x, y
        return int(x * cw / BASE_WIDTH), int(y * ch / BASE_HEIGHT)

    def _resolve_child(self, x: int, y: int) -> Tuple[int, int, int]:
        """
        解析 (x, y) 命中的子窗口。

        通过 ChildWindowFromPointEx 找到实际接收输入的渲染子窗口，
        避免消息被顶层窗口忽略。

        Returns:
            (target_hwnd, client_x, client_y)
        """
        # 基准坐标 → 客户区像素
        cw, ch = self._get_client_size()
        sx = x * cw // BASE_WIDTH
        sy = y * ch // BASE_HEIGHT

        # 客户区坐标 → 屏幕坐标
        pt = ctypes.wintypes.POINT(sx, sy)
        user32.ClientToScreen(self._hwnd, ctypes.byref(pt))
        screen_x, screen_y = pt.x, pt.y

        # 解析子窗口
        flags = CWP_SKIPINVISIBLE | CWP_SKIPDISABLED | CWP_SKIPTRANSPARENT
        pt = ctypes.wintypes.POINT(screen_x, screen_y)
        child = user32.ChildWindowFromPointEx(self._hwnd, pt, flags)

        if child and child != self._hwnd:
            # 坐标转为子窗口客户区坐标
            cpt = ctypes.wintypes.POINT(screen_x, screen_y)
            user32.ScreenToClient(child, ctypes.byref(cpt))
            return child, cpt.x, cpt.y

        return self._hwnd, sx, sy

    # ---------- 公开接口 ----------

    def click(self, x: int, y: int) -> bool:
        """
        后台左键单击。

        流程：
          1. 解析子窗口
          2. 发送 WM_MOUSEMOVE（帮助 hover 状态更新）
          3. 发送 WM_LBUTTONDOWN + WM_LBUTTONUP

        Args:
            x: 基准分辨率 x（1920×1080）
            y: 基准分辨率 y
        """
        target, cx, cy = self._resolve_child(x, y)
        lparam = _make_lparam(cx, cy)

        user32.PostMessageW(target, WM_MOUSEMOVE, 0, lparam)
        time.sleep(0.02)
        user32.PostMessageW(target, WM_LBUTTONDOWN, MK_LBUTTON, lparam)
        time.sleep(0.05)
        user32.PostMessageW(target, WM_LBUTTONUP, 0, lparam)

        logger.debug(f"PostMessage 点击: hwnd={target:#x} ({cx},{cy}) 基准({x},{y})")
        time.sleep(self.post_click_wait_ms / 1000.0)
        return True

    def click_ratio(self, rx: float, ry: float) -> bool:
        """
        按比例点击。

        Args:
            rx: 水平比例（0.0~1.0）
            ry: 垂直比例（0.0~1.0）
        """
        x = int(BASE_WIDTH * rx)
        y = int(BASE_HEIGHT * ry)
        return self.click(x, y)

    def send_key(self, vk_code: int) -> bool:
        """
        后台按键。

        Args:
            vk_code: 虚拟键码（如 0x1B = ESC）
        """
        user32.PostMessageW(self._hwnd, WM_KEYDOWN, vk_code, 0)
        time.sleep(0.05)
        user32.PostMessageW(self._hwnd, WM_KEYUP, vk_code, 0)
        logger.debug(f"PostMessage 按键: VK=0x{vk_code:02X}")
        return True
