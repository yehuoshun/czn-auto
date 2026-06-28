"""
截图模块 - 获取游戏窗口画面
方案1: PrintWindow API (Win32)
方案2: PIL ImageGrab (回退)
"""

import ctypes
import ctypes.wintypes
from ctypes import wintypes
import numpy as np
from PIL import Image, ImageGrab
import logging
import time

logger = logging.getLogger("czn-auto.screenshot")


class Screenshot:
    """游戏窗口截图器"""

    def __init__(self, window_title: str, window_class: str | None = None):
        self.window_title = window_title
        self.window_class = window_class
        self.hwnd: int | None = None
        self._user32 = ctypes.windll.user32
        self._gdi32 = ctypes.windll.gdi32

    def find_window(self) -> bool:
        """查找游戏窗口句柄"""
        if self.window_class:
            self.hwnd = self._user32.FindWindowW(self.window_class, self.window_title)
        else:
            self.hwnd = self._user32.FindWindowW(None, self.window_title)

        if self.hwnd == 0:
            logger.warning(f"未找到窗口: {self.window_title}")
            self.hwnd = None
            return False

        logger.info(f"找到窗口: {self.window_title} (hwnd={self.hwnd:#x})")
        return True

    def focus_window(self) -> bool:
        """将游戏窗口置顶并聚焦"""
        if not self.hwnd:
            if not self.find_window():
                return False

        # 如果窗口最小化了，先恢复
        SW_RESTORE = 9
        if self._user32.IsIconic(self.hwnd):
            self._user32.ShowWindow(self.hwnd, SW_RESTORE)

        # 设为前台窗口
        self._user32.SetForegroundWindow(self.hwnd)

        logger.debug(f"窗口已聚焦: {self.window_title}")
        return True

    def get_window_rect(self) -> tuple[int, int, int, int] | None:
        """获取窗口位置和大小 (left, top, right, bottom)"""
        if not self.hwnd:
            if not self.find_window():
                return None

        rect = wintypes.RECT()
        self._user32.GetWindowRect(self.hwnd, ctypes.byref(rect))
        return rect.left, rect.top, rect.right, rect.bottom

    def capture_printwindow(self) -> Image.Image | None:
        """方案1: PrintWindow API 截图"""
        if not self.hwnd:
            if not self.find_window():
                return None

        rect = self.get_window_rect()
        if not rect:
            return None

        left, top, right, bottom = rect
        width = right - left
        height = bottom - top

        if width <= 0 or height <= 0:
            logger.warning(f"窗口尺寸异常: {width}x{height}")
            return None

        # 获取窗口 DC
        hwnd_dc = self._user32.GetWindowDC(self.hwnd)
        if not hwnd_dc:
            logger.warning("GetWindowDC 失败")
            return None

        # 创建兼容 DC 和位图
        mem_dc = self._gdi32.CreateCompatibleDC(hwnd_dc)
        bitmap = self._gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
        old_bitmap = self._gdi32.SelectObject(mem_dc, bitmap)

        # PrintWindow 截取
        PW_CLIENTONLY = 0x00000001
        result = self._user32.PrintWindow(self.hwnd, mem_dc, PW_CLIENTONLY)

        if result == 0:
            logger.debug("PrintWindow 失败，尝试无 PW_CLIENTONLY 标志")
            result = self._user32.PrintWindow(self.hwnd, mem_dc, 0)

        image = None
        if result != 0:
            # 从位图创建 PIL Image
            bmp_info = ctypes.create_string_buffer(ctypes.sizeof(wintypes.BITMAPINFOHEADER) + 8)
            bmp_header = ctypes.cast(bmp_info, wintypes.PBITMAPINFOHEADER)
            bmp_header.contents.biSize = ctypes.sizeof(wintypes.BITMAPINFOHEADER)
            bmp_header.contents.biWidth = width
            bmp_header.contents.biHeight = -height  # 负值 = 自上而下
            bmp_header.contents.biPlanes = 1
            bmp_header.contents.biBitCount = 32
            bmp_header.contents.biCompression = 0  # BI_RGB

            buf = ctypes.create_string_buffer(width * height * 4)
            self._gdi32.GetDIBits(mem_dc, bitmap, 0, height, buf, bmp_info, 0)
            image = Image.frombuffer("RGBA", (width, height), buf, "raw", "BGRA", 0, 1)
            image = image.convert("RGB")
            logger.debug(f"PrintWindow 截图成功: {width}x{height}")
        else:
            logger.warning("PrintWindow 截图失败")

        # 清理
        self._gdi32.SelectObject(mem_dc, old_bitmap)
        self._gdi32.DeleteObject(bitmap)
        self._gdi32.DeleteDC(mem_dc)
        self._user32.ReleaseDC(self.hwnd, hwnd_dc)

        return image

    def capture_imagegrab(self) -> Image.Image | None:
        """方案2: PIL ImageGrab 全屏截图后裁剪窗口区域"""
        rect = self.get_window_rect()
        if not rect:
            return None

        left, top, right, bottom = rect
        screenshot = ImageGrab.grab(bbox=(left, top, right, bottom), all_screens=True)
        logger.debug(f"ImageGrab 截图成功: {right - left}x{bottom - top}")
        return screenshot

    def capture(self, clicker=None, wake_ui: bool = False) -> Image.Image | None:
        """
        截图：聚焦窗口 → 截图
        wake_ui: 是否唤醒 UI（点击空白区域防止长时间不操作隐藏 UI）
        需要管理员权限运行（ACE 会拦截非管理员进程的鼠标操作）
        """
        self.focus_window()

        # 只在明确需要时才唤醒 UI，避免在子页面误触按钮
        if clicker and wake_ui:
            import random
            # 点窗口中心附近空白区域（避开 UI 密集区）
            cx = 960 + random.randint(-100, 100)
            cy = 540 + random.randint(-50, 50)
            clicker.post_click(cx, cy)
            time.sleep(0.2)

        image = self.capture_imagegrab()
        if image is not None:
            return image

        logger.info("ImageGrab 失败，回退到 PrintWindow")
        return self.capture_printwindow()

    def to_cv2(self, image: Image.Image) -> np.ndarray:
        """PIL Image 转 OpenCV 格式 (BGR)"""
        return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


# 延迟导入避免循环依赖
import cv2
