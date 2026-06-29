"""
CZN 页面 ROI 校准工具

在常驻卡厄思页面运行，帮助精确调整关卡/难度/确认按钮的 ROI。

使用方式：
  1. 打开游戏，进入常驻卡厄思（幻象剧场）页面
  2. 运行: python scripts/calibrate_czn_roi.py
  3. 查看 test_output/czn_debug.png 确认 ROI 覆盖是否正确
  4. 根据结果编辑 src/pages/czn.py 中的 ROI 常量
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
from src.pages import HomePage, CznPage

OUT_DIR = "test_output"
os.makedirs(OUT_DIR, exist_ok=True)
setup_logging(level="DEBUG", log_file=f"{OUT_DIR}/calibrate_czn.log", max_size_mb=10, backup_count=1)
logger = logging.getLogger("calibrate")

# 初始化
config = Config("src/config.json")
sc = Screenshot(window_title=config.window_title, window_class=config.window_class)
if not sc.find_window():
    print("❌ 未找到窗口")
    sys.exit(1)

rec = Recognizer()
home = HomePage(rec, config.data)
czn = CznPage(rec, config.data)

# 截图
img = sc.capture()
if img is None:
    print("❌ 截图失败")
    sys.exit(1)
cv_img = sc.to_cv2(img)
h, w = cv_img.shape[:2]

page = home.detect_page(cv_img)
print(f"📄 页面判定: {page}")
print(f"📐 截图尺寸: {w}x{h} (缩放因子: {w/1920:.3f}x{h/1080:.3f})")

# 保存原图
cv2.imwrite(f"{OUT_DIR}/czn_raw.png", cv_img)

# 1. 标题 OCR
tx1, ty1 = int(w * 0.05), int(h * 0.02)
tx2, ty2 = int(w * 0.35), int(h * 0.08)
title_text = rec.ocr_region(cv_img, tx1, ty1, tx2 - tx1, ty2 - ty1)
print(f"\n📌 标题OCR: '{title_text}'")

# 2. 全屏 OCR
print("\n🔍 全屏 OCR 扫描...")
results = rec.ocr_full(cv_img)
print(f"   识别到 {len(results)} 个文字块:")

dbg = cv_img.copy()
for bbox, text, conf in results:
    cx = int((bbox[0][0] + bbox[2][0]) / 2)
    cy = int((bbox[0][1] + bbox[2][1]) / 2)
    base_x = int(cx * 1920 / w)
    base_y = int(cy * 1080 / h)
    print(f"   「{text}」 conf={conf:.2f} 截图({cx},{cy}) → 基准({base_x},{base_y})")
    cv2.putText(dbg, text, (int(bbox[0][0]), int(bbox[0][1]) - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    cv2.rectangle(dbg, (int(bbox[0][0]), int(bbox[0][1])),
                  (int(bbox[2][0]), int(bbox[2][1])), (0, 255, 0), 1)

# 3. 关卡扫描
print(f"\n📋 关卡列表: {len(czn.find_stages(cv_img))} 个")

# 4. 难度 + 确认按钮
print(f"\n🎯 当前难度: {czn.find_difficulty(cv_img)}")
print(f"🟢 确认按钮: {czn.find_confirm_button(cv_img)}")

# 5. 标注 ROI 区域
sx1 = int(w * 0.10)
sy1 = int(h * 0.15)
sx2 = int(w * 0.85)
sy2 = int(h * 0.90)
cv2.rectangle(dbg, (sx1, sy1), (sx2, sy2), (255, 0, 0), 2)
cv2.putText(dbg, "STAGE_AREA", (sx1, sy1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

dx1 = int(w * 0.10)
dy1 = int(h * 0.80)
dx2 = int(w * 0.90)
dy2 = int(h * 0.95)
cv2.rectangle(dbg, (dx1, dy1), (dx2, dy2), (0, 0, 255), 2)
cv2.putText(dbg, "DIFFICULTY_AREA", (dx1, dy1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

cx1 = int(w * 0.35)
cy1 = int(h * 0.85)
cx2 = int(w * 0.65)
cy2 = int(h * 0.95)
cv2.rectangle(dbg, (cx1, cy1), (cx2, cy2), (0, 255, 255), 2)
cv2.putText(dbg, "CONFIRM_BTN", (cx1, cy1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

cv2.putText(dbg, f"page={page}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
cv2.imwrite(f"{OUT_DIR}/czn_debug.png", dbg)

print(f"\n✅ 已保存: {OUT_DIR}/czn_raw.png, {OUT_DIR}/czn_debug.png")
print("💡 查看 czn_debug.png 确认 ROI 覆盖区域，如有偏差请编辑 src/pages/czn.py 中的 ROI 常量")
