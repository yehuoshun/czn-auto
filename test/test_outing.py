"""
测试脚本 - 出击页面识别测试
在出击页面运行，检测等级读取和进入按钮
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import logging

from src.core.config import Config
from src.core.logger import setup_logging
from src.core.screenshot import Screenshot
from src.core.recognizer import Recognizer
from src.core.clicker import Clicker
from src.modules.home import HomePage
from src.modules.outing import OutingPage

OUT_DIR = "test_output"
os.makedirs(OUT_DIR, exist_ok=True)
setup_logging(level="DEBUG", log_file=f"{OUT_DIR}/test_outing.log", max_size_mb=10, backup_count=1)
logger = logging.getLogger("test")

config = Config("src/config.json")
sc = Screenshot(window_title=config.window_title, window_class=config.window_class)
if not sc.find_window():
    print("❌ 未找到窗口"); exit(1)

rec = Recognizer()
clicker = Clicker(hwnd=sc.hwnd, base_width=1920, base_height=1080)
home = HomePage(rec, config.data)
outing = OutingPage(rec, config.data)

img = sc.capture(clicker=clicker, wake_ui=True)
cv_img = sc.to_cv2(img)

page = home.detect_page(cv_img)
print(f"📄 页面判定: {page}")

# 保存原图
cv2.imwrite(f"{OUT_DIR}/outing_raw.png", cv_img)

# 1. 检测标题
h, w = cv_img.shape[:2]
tx1, ty1 = int(w * 0.05), int(h * 0.02)
tx2, ty2 = int(w * 0.20), int(h * 0.08)
text = rec.ocr_region(cv_img, tx1, ty1, tx2 - tx1, ty2 - ty1)
print(f"\n📌 标题OCR: '{text}'")

# 2. 检测等级
level = outing.read_level(cv_img)
print(f"📊 关卡等级: LV.{level if level else '读取失败'}")

# 3. 检测等级区域文字
lx1, ly1 = int(w * 0.35), int(h * 0.25)
lx2, ly2 = int(w * 0.65), int(h * 0.45)
level_text = rec.ocr_region(cv_img, lx1, ly1, lx2 - lx1, ly2 - ly1)
print(f"📊 等级区域全OCR: '{level_text}'")

# 4. 检测进入按钮
enter = outing.find_enter_button(cv_img)
print(f"🟢 进入按钮: {enter}")

# 5. 检测确认上阵按钮
confirm = outing.find_confirm_button(cv_img)
print(f"🟡 确认按钮: {confirm}")

# 6. 返回箭头
back = outing.find_back_arrow(cv_img)
print(f"🔙 返回箭头: {back}")

# 标注截图
dbg = cv_img.copy()
# 标题区域
cv2.rectangle(dbg, (tx1, ty1), (tx2, ty2), (0, 255, 0), 2)
# 等级区域
cv2.rectangle(dbg, (lx1, ly1), (lx2, ly2), (255, 0, 0), 2)
# 进入按钮区域
ex1, ey1 = int(w * 0.30), int(h * 0.75)
ex2, ey2 = int(w * 0.70), int(h * 0.90)
cv2.rectangle(dbg, (ex1, ey1), (ex2, ey2), (0, 0, 255), 2)
if enter:
    cv2.circle(dbg, (int(enter[0] * w / 1920), int(enter[1] * h / 1080)), 8, (0, 255, 255), -1)
if back:
    cv2.circle(dbg, (int(back[0] * w / 1920), int(back[1] * h / 1080)), 8, (0, 255, 0), -1)
cv2.putText(dbg, f"page={page} level={level}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
cv2.imwrite(f"{OUT_DIR}/outing_debug.png", dbg)

print(f"\n✅ 截图: {OUT_DIR}/outing_raw.png, {OUT_DIR}/outing_debug.png")
