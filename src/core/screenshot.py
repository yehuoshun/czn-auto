"""
截图模块 - PrintWindow 后台截图

使用 GDI PrintWindow API 后台获取窗口画面，不依赖窗口焦点或可见性。
窗口被遮挡、位于后台时仍可截图。

单一职责：仅处理窗口截图，不涉及点击或识别。
"""

import ctypes
import ctypes.wintypes
import logging
from typing import Optional

import numpy as np
from PIL import Image

logger = logging.getLogger("czn-auto.screenshot")

# ---------- GDI 常量 ----------
PW_RENDERFULLCONTENT = 0x00000002  # 兼容 DWM/DirectComposition 渲染
BI_RGB = 0
DIB_RGB_COLORS = 0


class BITMAPINFOHEADER(ctypes.Structure):
    """位图信息头结构体。"""
    _fields_ = [
        ("biSize", ctypes.wintypes.DWORD),
        ("biWidth", ctypes.wintypes.LONG),
        ("biHeight", ctypes.wintypes.LONG),
        ("biPlanes", ctypes.wintypes.WORD),
        ("biBitCount", ctypes.wintypes.WORD),
        ("biCompression", ctypes.wintypes.DWORD),
        ("biSizeImage", ctypes.wintypes.DWORD),
        ("biXPelsPerMeter", ctypes.wintypes.LONG),
        ("biYPelsPerMeter", ctypes.wintypes.LONG),
        ("biClrUsed", ctypes.wintypes.DWORD),
        ("biClrImportant", ctypes.wintypes.DWORD),
    ]


# ---------- ctypes 签名（防止 64 位句柄截断） ----------
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

user32.GetWindowDC.restype = ctypes.wintypes.HDC
user32.GetWindowDC.argtypes = [ctypes.wintypes.HWND]
user32.ReleaseDC.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.HDC]
user32.PrintWindow.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.HDC, ctypes.wintypes.UINT]
user32.PrintWindow.restype = ctypes.wintypes.BOOL
user32.GetWindowRect.argtypes = [ctypes.wintypes.HWND, ctypes.POINTER(ctypes.wintypes.RECT)]
user32.GetWindowRect.restype = ctypes.wintypes.BOOL

gdi32.CreateCompatibleDC.restype = ctypes.wintypes.HDC
gdi32.CreateCompatibleDC.argtypes = [ctypes.wintypes.HDC]
gdi32.CreateCompatibleBitmap.restype = ctypes.wintypes.HBITMAP
gdi32.CreateCompatibleBitmap.argtypes = [ctypes.wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.SelectObject.restype = ctypes.wintypes.HGDIOBJ
gdi32.SelectObject.argtypes = [ctypes.wintypes.HDC, ctypes.wintypes.HGDIOBJ]
gdi32.DeleteObject.argtypes = [ctypes.wintypes.HGDIOBJ]
gdi32.DeleteDC.argtypes = [ctypes.wintypes.HDC]
gdi32.GetDIBits.argtypes = [
    ctypes.wintypes.HDC, ctypes.wintypes.HBITMAP,
    ctypes.wintypes.UINT, ctypes.wintypes.UINT,
    ctypes.c_void_p, ctypes.c_void_p, ctypes.wintypes.UINT,
]
gdi32.GetDIBits.restype = ctypes.c_int


class Screenshot:
    """
    PrintWindow 后台截图器。

    使用 GDI PrintWindow API，窗口被遮挡/后台时仍可截图。
    """

    def __init__(self, window_title: str, window_class: Optional[str] = None):
        """
        Args:
            window_title: 窗口标题
            window_class: 窗口类名（可选）
        """
        self.window_title = window_title
        self.window_class = window_class
        self.hwnd: Optional[int] = None

    def find_window(self) -> bool:
        """查找游戏窗口句柄。"""
        if self.window_class:
            self.hwnd = user32.FindWindowW(self.window_class, self.window_title)
        else:
            self.hwnd = user32.FindWindowW(None, self.window_title)

        if not self.hwnd:
            logger.warning(f"未找到窗口: {self.window_title}")
            return False

        logger.info(f"找到窗口: {self.window_title} (hwnd={self.hwnd:#x})")
        return True

    def capture(self) -> Optional[Image.Image]:
        """
        PrintWindow 后台截图。

        Returns:
            PIL RGB Image，失败返回 None
        """
        if not self.hwnd and not self.find_window():
            return None

        # 获取窗口尺寸
        rect = ctypes.wintypes.RECT()
        user32.GetWindowRect(self.hwnd, ctypes.byref(rect))
        width = rect.right - rect.left
        height = rect.bottom - rect.top

        if width <= 0 or height <= 0:
            logger.warning(f"窗口尺寸异常: {width}x{height}")
            return None

        # 获取窗口 DC
        hwnd_dc = user32.GetWindowDC(self.hwnd)
        if not hwnd_dc:
            logger.warning("GetWindowDC 失败")
            return None

        try:
            # 创建离屏 DC 和位图
            mem_dc = gdi32.CreateCompatibleDC(hwnd_dc)
            bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
            old_bitmap = gdi32.SelectObject(mem_dc, bitmap)

            # PrintWindow 截图
            ok = user32.PrintWindow(self.hwnd, mem_dc, PW_RENDERFULLCONTENT)
            if not ok:
                logger.debug("PrintWindow 返回 0（部分窗口仍可得到画面）")

            # 读取位图数据
            bmi = BITMAPINFOHEADER()
            bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.biWidth = width
            bmi.biHeight = -height  # 负值 = 自上而下
            bmi.biPlanes = 1
            bmi.biBitCount = 32
            bmi.biCompression = BI_RGB

            buf = (ctypes.c_ubyte * (width * height * 4))()
            scanned = gdi32.GetDIBits(
                mem_dc, bitmap, 0, height,
                ctypes.byref(buf), ctypes.byref(bmi), DIB_RGB_COLORS,
            )

            if not scanned:
                logger.warning("GetDIBits 失败")
                return None

            # BGRA → RGB
            image = Image.frombuffer("RGBA", (width, height), buf, "raw", "BGRA", 0, 1)
            logger.debug(f"PrintWindow 截图: {width}x{height}")
            return image.convert("RGB")

        finally:
            gdi32.SelectObject(mem_dc, old_bitmap)
            gdi32.DeleteObject(bitmap)
            gdi32.DeleteDC(mem_dc)
            user32.ReleaseDC(self.hwnd, hwnd_dc)

    def to_cv2(self, image: Image.Image) -> np.ndarray:
        """PIL Image → OpenCV BGR。"""
        import cv2
        return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    def get_client_size(self):
        """获取客户区尺寸。"""
        rect = ctypes.wintypes.RECT()
        user32.GetClientRect(self.hwnd, ctypes.byref(rect))
        return rect.right - rect.left, rect.bottom - rect.top
