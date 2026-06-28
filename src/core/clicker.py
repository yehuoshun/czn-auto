"""
点击模块 - SendInput 模拟真实鼠标/键盘点击
支持坐标自动缩放 (基于 1920x1080)
"""

import ctypes
from ctypes import wintypes
import time
import logging
import random

logger = logging.getLogger("czn-auto.clicker")


# ==================== SendInput 结构体定义 ====================

# 鼠标输入结构体
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


# 键盘输入结构体
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


# 硬件输入结构体
class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


# 输入联合体
class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


# 输入事件结构体
class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]


# SendInput 函数原型
# UINT SendInput(UINT cInputs, LPINPUT pInputs, int cbSize)
_send_input = ctypes.windll.user32.SendInput
_send_input.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
_send_input.restype = wintypes.UINT


# 输入类型常量
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

# 鼠标事件标志
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_WHEEL = 0x0800

# 键盘事件标志
KEYEVENTF_KEYDOWN = 0x0000
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

# 屏幕尺寸常量 (绝对坐标模式)
SM_CXSCREEN = 0
SM_CYSCREEN = 1


class Clicker:
    """模拟真实点击器 (SendInput)"""

    def __init__(
        self,
        hwnd: int,
        base_width: int = 1920,
        base_height: int = 1080,
        delay_ms: int = 100,
        post_click_wait_ms: int = 500,
        humanize: bool = True,
    ):
        """
        hwnd: 游戏窗口句柄 (用于获取窗口位置)
        base_width/height: 基准分辨率，所有坐标输入都基于此分辨率
        """
        self.hwnd = hwnd
        self.base_width = base_width
        self.base_height = base_height
        self.delay_ms = delay_ms
        self.post_click_wait_ms = post_click_wait_ms
        self.humanize = humanize
        self._user32 = ctypes.windll.user32

    def _get_window_rect(self) -> tuple[int, int, int, int]:
        """获取窗口屏幕位置 (left, top, right, bottom)"""
        rect = wintypes.RECT()
        self._user32.GetWindowRect(self.hwnd, ctypes.byref(rect))
        return rect.left, rect.top, rect.right, rect.bottom

    def _scale_coord(self, x: int, y: int) -> tuple[int, int]:
        """坐标缩放：基准分辨率 → 实际窗口尺寸（自动检测后通常为 1:1）"""
        left, top, right, bottom = self._get_window_rect()
        actual_w = right - left
        actual_h = bottom - top

        if actual_w == self.base_width and actual_h == self.base_height:
            return x, y

        scaled_x = int(x * actual_w / self.base_width)
        scaled_y = int(y * actual_h / self.base_height)
        logger.debug(f"坐标缩放: ({x},{y}) → ({scaled_x},{scaled_y}) [{actual_w}x{actual_h}]")
        return scaled_x, scaled_y

    def _window_to_screen(self, x: int, y: int) -> tuple[int, int]:
        """窗口内坐标 → 屏幕绝对坐标"""
        left, top, _, _ = self._get_window_rect()
        return left + x, top + y

    def _screen_to_absolute(self, screen_x: int, screen_y: int) -> tuple[int, int]:
        """
        屏幕像素坐标 → SendInput 绝对坐标 (0~65535)
        """
        abs_x = int(screen_x * 65535 / self._screen_w)
        abs_y = int(screen_y * 65535 / self._screen_h)
        return abs_x, abs_y

    def _human_delay(self, base_ms: float, jitter_ms: float = 30):
        """加入随机抖动，模拟人类操作"""
        if self.humanize:
            delay = base_ms + random.uniform(-jitter_ms, jitter_ms)
            delay = max(delay, 0.001)  # 不能为负
            time.sleep(delay / 1000.0)
        else:
            time.sleep(base_ms / 1000.0)

    def _send_mouse_input(self, flags: int, dx: int = 0, dy: int = 0, data: int = 0) -> bool:
        """发送单个鼠标输入事件"""
        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.union.mi.dx = dx
        inp.union.mi.dy = dy
        inp.union.mi.mouseData = data
        inp.union.mi.dwFlags = flags
        inp.union.mi.time = 0
        inp.union.mi.dwExtraInfo = None

        result = _send_input(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        return result == 1

    def _send_mouse_inputs(self, *events: tuple[int, int, int, int]) -> int:
        """
        批量发送鼠标输入事件 (合并到一次 SendInput 调用)
        每个 event: (flags, dx, dy, data)
        返回成功发送的事件数
        """
        count = len(events)
        if count == 0:
            return 0
        inputs = (INPUT * count)()
        for i, (flags, dx, dy, data) in enumerate(events):
            inputs[i].type = INPUT_MOUSE
            inputs[i].union.mi.dx = dx
            inputs[i].union.mi.dy = dy
            inputs[i].union.mi.mouseData = data
            inputs[i].union.mi.dwFlags = flags
            inputs[i].union.mi.time = 0
            inputs[i].union.mi.dwExtraInfo = None
        return _send_input(count, inputs, ctypes.sizeof(INPUT))

    def _move_to(self, window_x: int, window_y: int):
        """移动鼠标到窗口内指定坐标 (模拟真实移动)"""
        scaled_x, scaled_y = self._scale_coord(window_x, window_y)
        screen_x, screen_y = self._window_to_screen(scaled_x, scaled_y)
        abs_x, abs_y = self._screen_to_absolute(screen_x, screen_y)

        # 带微量随机偏移 (不是每个人都能点到精确像素)
        if self.humanize:
            abs_x += random.randint(-3, 3)
            abs_y += random.randint(-3, 3)

        self._send_mouse_input(
            MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE,
            abs_x, abs_y,
        )

    def click(self, x: int, y: int, right_button: bool = False) -> bool:
        """
        模拟真实鼠标点击
        x, y: 基于 1920x1080 的窗口内坐标，自动缩放
        流程: 移动鼠标 → 按下 → 抬起
        """
        # 移动到目标位置
        self._move_to(x, y)
        self._human_delay(30)  # 移动后短暂停顿

        # 按下
        if right_button:
            self._send_mouse_input(MOUSEEVENTF_RIGHTDOWN)
        else:
            self._send_mouse_input(MOUSEEVENTF_LEFTDOWN)

        self._human_delay(self.delay_ms)

        # 抬起
        if right_button:
            self._send_mouse_input(MOUSEEVENTF_RIGHTUP)
        else:
            self._send_mouse_input(MOUSEEVENTF_LEFTUP)

        logger.debug(f"点击: ({x},{y}) {'右键' if right_button else '左键'}")
        self._human_delay(self.post_click_wait_ms)
        return True

    def post_click(self, x: int, y: int, right_button: bool = False) -> bool:
        """
        模拟鼠标点击: SetCursorPos + mouse_event
        需要管理员权限运行（ACE 反作弊会拦截非管理员进程）
        x, y: 基于 1920x1080 的客户区坐标
        """
        left, top, right, bottom = self._get_window_rect()
        win_w = right - left
        win_h = bottom - top
        cx = int(x * win_w / 1920)
        cy = int(y * win_h / 1080)
        sx = left + cx
        sy = top + cy

        logger.info(f"点击: 基准({x},{y}) → 屏幕({sx},{sy})")

        ctypes.windll.user32.SetCursorPos(sx, sy)
        time.sleep(0.03)
        ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
        time.sleep(self.delay_ms / 1000.0)
        ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
        time.sleep(self.post_click_wait_ms / 1000.0)
        return True

    def click_point(self, point_name: str, points_config: dict) -> bool:
        """
        根据配置名称点击
        points_config: { name: { "x": int, "y": int } }
        """
        if point_name not in points_config:
            logger.error(f"未找到点击配置: {point_name}")
            return False

        point = points_config[point_name]
        return self.click(point["x"], point["y"])

    def drag(
        self,
        x1: int, y1: int,
        x2: int, y2: int,
        speed_px_per_ms: float = 2.0,
    ) -> bool:
        """
        模拟真实拖拽
        坐标基于 1920x1080
        speed_px_per_ms: 拖拽速度 (像素/毫秒)
        """
        scaled_x1, scaled_y1 = self._scale_coord(x1, y1)
        scaled_x2, scaled_y2 = self._scale_coord(x2, y2)

        # 移动到起点
        self._move_to(x1, y1)
        self._human_delay(50)

        # 按下
        self._send_mouse_input(MOUSEEVENTF_LEFTDOWN)
        self._human_delay(30)

        # 逐像素移动 (模拟真实拖拽)
        import math
        dx = scaled_x2 - scaled_x1
        dy = scaled_y2 - scaled_y1
        dist = math.sqrt(dx * dx + dy * dy)
        steps = max(1, int(dist / speed_px_per_ms))

        for i in range(1, steps + 1):
            t = i / steps
            cx = scaled_x1 + int(dx * t)
            cy = scaled_y1 + int(dy * t)
            screen_x, screen_y = self._window_to_screen(cx, cy)
            abs_x, abs_y = self._screen_to_absolute(screen_x, screen_y)
            self._send_mouse_input(
                MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE,
                abs_x, abs_y,
            )
            self._human_delay(1)

        # 抬起
        self._send_mouse_input(MOUSEEVENTF_LEFTUP)

        logger.debug(f"拖拽: ({scaled_x1},{scaled_y1}) → ({scaled_x2},{scaled_y2})")
        self._human_delay(self.post_click_wait_ms)
        return True

    def scroll(self, x: int, y: int, delta: int, steps: int = 3) -> bool:
        """
        模拟滚轮滚动
        x, y: 鼠标位置 (先移动到此)
        delta: 滚动量 (正=向上, 负=向下, 120 = 一格)
        steps: 分几次滚动 (模拟人类渐进滚动)
        """
        self._move_to(x, y)
        self._human_delay(50)

        delta_per_step = delta // steps
        for _ in range(steps):
            self._send_mouse_input(
                MOUSEEVENTF_WHEEL,
                dx=0, dy=0, data=delta_per_step,
            )
            self._human_delay(20)

        logger.debug(f"滚动: ({x},{y}) delta={delta}")
        return True

    def send_key(self, vk_code: int) -> bool:
        """模拟键盘按键"""
        inp_down = INPUT()
        inp_down.type = INPUT_KEYBOARD
        inp_down.union.ki.wVk = vk_code
        inp_down.union.ki.dwFlags = KEYEVENTF_KEYDOWN

        inp_up = INPUT()
        inp_up.type = INPUT_KEYBOARD
        inp_up.union.ki.wVk = vk_code
        inp_up.union.ki.dwFlags = KEYEVENTF_KEYUP

        _send_input(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))
        self._human_delay(self.delay_ms)
        _send_input(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))

        logger.debug(f"按键: VK={vk_code}")
        return True

    def send_text(self, text: str) -> bool:
        """模拟键盘输入文本 (逐字符)"""
        for ch in text:
            vk = ctypes.windll.user32.VkKeyScanW(ord(ch)) & 0xFF
            self.send_key(vk)
            self._human_delay(50)
        return True

    def get_current_pos(self) -> tuple[int, int]:
        """获取当前鼠标屏幕坐标"""
        point = wintypes.POINT()
        self._user32.GetCursorPos(ctypes.byref(point))
        return point.x, point.y