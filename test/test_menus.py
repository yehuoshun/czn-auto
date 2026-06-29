"""
测试脚本 - 菜单按钮识别测试

在游戏任意页面运行，检测菜单按钮 OCR 识别效果。
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
from src.pages import HomePage

OUT_DIR = "test_output"
os.makedirs(OUT_DIR, exist_ok=True)
setup_logging(level="DEBUG", log_file=f"{OUT_DIR}/test_menus.log", max_size_mb=10, backup_count=1)

config = Config("src/config.json")
sc = Screenshot(window_title=config.window_title, window_class=config.window_class)
if not sc.find_window():
    print("❌ 未找到窗口"); exit(1)

rec = Recognizer()
home = HomePage(rec, config.data)

img = sc.capture()
if img is None:
    print("❌ 截图失败"); exit(1)
cv_img = sc.to_cv2(img)

page = home.detect_page(cv_img)
print(f"📄 页面判定: {page}")

h, w = cv_img.shape[:2]
x1, y1 = int(w * 0.85), int(h * 0.05)
x2, y2 = int(w * 1.00), int(h * 0.95)
roi = cv_img[y1:y2, x1:x2]

print(f"\n🔍 OCR 右侧菜单区域 ({x1},{y1})-({x2},{y2}) ...")
results = rec.ocr_full(roi)
print(f"   识别到 {len(results)} 个文字块:")
for bbox, text, conf in results:
    cx = x1 + int((bbox[0][0] + bbox[2][0]) / 2)
    cy = y1 + int((bbox[0][1] + bbox[2][1]) / 2)
    print(f"   「{text}」 conf={conf:.2f}  @ ({cx},{cy})")

dbg = cv_img.copy()
cv2.rectangle(dbg, (x1, y1), (x2, y2), (0, 255, 0), 2)
for bbox, text, conf in results:
    cx = x1 + int((bbox[0][0] + bbox[2][0]) / 2)
    cy = y1 + int((bbox[0][1] + bbox[2][1]) / 2)
    cv2.putText(dbg, text, (x1 + int(bbox[0][0]), y1 + int(bbox[0][1]) - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    cv2.circle(dbg, (cx, cy), 5, (0, 0, 255), -1)
cv2.imwrite(f"{OUT_DIR}/menus_debug.png", dbg)
cv2.imwrite(f"{OUT_DIR}/menus_raw.png", cv_img)
print(f"\n✅ 已保存: {OUT_DIR}/menus_raw.png, {OUT_DIR}/menus_debug.png")
