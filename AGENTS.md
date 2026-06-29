# AGENTS.md — 卡厄思梦境自动化脚本 (v2)

> 写给接手这个项目的 AI Agent。读完这个文件，你应该能直接开始写代码。

## 项目是什么

一个 **Python + OpenCV + Win32 API** 的游戏自动化脚本。目标：让脚本自动操作 PC 游戏「卡厄思梦境」。

**核心原则**：不碰内存、不注入、不改包。纯视觉识别 + 模拟点击。

**v2 变更**：
- 截图统一用 **PrintWindow**（后台截图，不依赖窗口焦点）
- 点击统一用 **PostMessage**（后台点击，不依赖鼠标位置）
- 去掉 SetCursorPos/mouse_event/SendInput/ImageGrab 等冗余方案

## 技术栈

| 层 | 技术 | 用途 |
|----|------|------|
| 截图 | PrintWindow API (Win32 GDI) | 后台获取游戏窗口画面 |
| 视觉 | OpenCV (cv2) | 竖线检测（Sobel）、模板匹配（TM_CCOEFF_NORMED） |
| OCR | PaddleOCR (PP-OCRv6) | 识别菜单按钮文字 |
| 点击 | PostMessage (WM_LBUTTONDOWN/UP) | 后台向窗口发送鼠标消息 |
| 日志 | logging + RotatingFileHandler | 文件+控制台双输出 |

## 架构

```
main.py (CZNAuto)
  ├── Screenshot    ← PrintWindow 后台截图
  ├── Recognizer    ← OCR / 模板匹配
  ├── Clicker       ← PostMessage 后台点击
  ├── HomePage      ← 识别层 (modules/home.py)
  └── HomeActions   ← 操作层 (actions/home_actions.py)
```

**分层规则**：
- `src/core/` — 底层能力，不依赖业务
- `src/modules/` — **识别层**，纯视觉识别，不操作鼠标键盘
- `src/actions/` — **操作层**，封装点击操作，调 modules 拿坐标后点击
- `src/images/commons/` — 公共模板图片（仅返回箭头）
- `src/images/s*/` — 赛季模板（每季换目录）

## 关键概念

### PrintWindow 后台截图

```python
# 无需窗口焦点，无需唤醒 UI
image = self.screenshot.capture()
cv_img = self.screenshot.to_cv2(image)
```

- 不依赖窗口是否可见、是否最小化
- 不发送鼠标事件，不会误触按钮
- 唯一截图方案，无回退

### PostMessage 后台点击

```python
# 发送 WM_LBUTTONDOWN + WM_LBUTTONUP 到窗口消息队列
self.clicker.post_click(x, y)   # 1920×1080 基准坐标，自动缩放
self.clicker.send_key(0x1B)     # 发送按键，0x1B = ESC
self.clicker.click_ratio(0.5, 0.5)  # 按比例点击
```

- 不移动鼠标，不依赖窗口焦点
- 坐标自动从 1920×1080 缩放到实际窗口尺寸
- **仅适用于 Windows 消息处理型 UI**（按钮、菜单、弹窗）
- 不适用于 DirectInput/Raw Input 操控

### 坐标系统

- **所有坐标基于 1920×1080 基准分辨率**
- `Clicker.post_click(x, y)` 接收 1920×1080 坐标，内部自动缩放到实际窗口
- ROI 都用**屏幕比例**（0.0~1.0），不要硬编码像素

### 主页判定

```
is_home() 判定逻辑:
  竖线 ✅ + 返回箭头 ❌ → 是主页
  竖线 ✅ + 返回箭头 ✅ → 是子页面（出击/模拟/卡厄思…）
  竖线 ❌                 → 非游戏页面
```

- **竖线检测**：菜单栏 ROI `(88%-99%) × (8%-82%)`，Sobel X 梯度 + 列投影
- **返回箭头**：模板匹配 `src/images/commons/back_arrow.png`，阈值 0.45
- 子页面左上角有返回箭头（←），主页没有
- **弹窗判定**：竖线存在但无返回箭头 → `popup`

## 状态机

```
run():
  loop:
    screenshot = PrintWindow 截图
    page = detect_page(screenshot)
    match page:
      "home"    → navigate based on mode
      "outing"  → set level → enter battle
      "season"  → enter CZN
      "czn"     → select stage → difficulty → enter battle
      "popup"   → ESC
      "unknown" → go_home or detect battle result
```

`detect_page()` 返回值：
- `"home"` — 竖线有、返回箭头无
- `"season"` — OCR 标题匹配「银河系灾害」等
- `"czn"` — OCR 标题匹配「卡厄思」
- `"outing"` — OCR 标题匹配「出击」
- `"popup"` — 竖线有、返回箭头无（弹窗遮盖）
- `"unknown"` — 竖线无（战斗/加载等）

## 模式

### manual（手动模式）
仅导航，不自动刷。用于手动操作时辅助识别。

### outing（出击刷等级）
```
主页 → 点击「出击」→ 设置等级 → 点击「进入」→ 确认上阵 → 进入战斗
战斗结束 → 检测结算 → 点击「再次挑战」→ 循环
```

### czn（卡厄思刷取）
```
主页 → 赛季横幅（或菜单「卡厄思」）→ 赛季页面 → 点击「卡厄思」按钮
→ 幻象剧场 → 选关卡 → 选难度 → 进入战斗
战斗结束 → 检测结算 → 点击「再次挑战」→ 循环
```

## 开发规范

### 新增页面

```python
# src/modules/xxx.py — 识别层
class XxxPage:
    def __init__(self, recognizer, config):
        self.rec = recognizer
    def is_xxx(self, screenshot) -> bool: ...
    def find_something(self, screenshot) -> tuple | None: ...

# src/actions/xxx_actions.py — 操作层
class XxxActions:
    def __init__(self, page, clicker):
        self.page = page
        self.clicker = clicker
    def do_something(self) -> bool:
        pos = self.page.find_something(screenshot)
        if pos:
            self.clicker.post_click(*pos)
```

然后在 `main.py` 的 `detect_page()` / `step()` 里接入。

### OCR 使用

```python
# 区域 OCR
text = self.rec.ocr_region(cv_img, x, y, w, h)

# 全屏 OCR
results = self.rec.ocr_full(cv_img)
for bbox, text, conf in results:
    cx = int((bbox[0][0] + bbox[2][0]) / 2)
    cy = int((bbox[0][1] + bbox[2][1]) / 2)
```

### 模板匹配

```python
result = self.rec.match_template(cv_img, "name", "path/to/template.png", threshold=0.8)
if result:
    x, y, conf = result  # 截图像素坐标
```

### 日志

```python
import logging
logger = logging.getLogger("czn-auto.模块名")
```

## 常见坑

1. **窗口没找到** → 检查 `config.json` 里 `window_title` 是否正确
2. **点击没反应** → PostMessage 可能被游戏忽略（使用 DirectInput 的游戏），需要确认
3. **OCR 识别不准** → PaddleOCR 对游戏字体识别有限，考虑细化 ROI 缩小搜索范围
4. **PrintWindow 截空白** → 某些游戏用 DXGI/DirectX 渲染，PrintWindow 可能抓不到画面
5. **返回箭头检测不到** → 模板匹配阈值 0.45，不同 UI 版本可能需要调
6. **is_home() 误判** → 检查竖线检测和返回箭头模板匹配的日志
7. **赛季动画加载慢** → 进入赛季页面后等 3s，卡厄思按钮 OCR 有 5 次重试
8. **PaddleOCR 3.x API 变更** → `ocr.ocr()` 改为 `ocr.predict()`，`recognizer.py` 已做兼容处理

## 项目状态

- ✅ PrintWindow 后台截图（v2 唯一方案）
- ✅ PostMessage 后台点击（v2 唯一方案）
- ✅ 主页检测 + 导航 + 返回 + 弹窗关闭
- ✅ 识别层/操作层分离
- ✅ 主页→赛季入口→赛季页面→卡厄思 全流程
- ✅ 出击模式（刷等级）+ 战斗结算 + 再战循环
- ✅ CZN 模式：选关卡→选难度→进入战斗→循环
- ✅ ROI 校准脚本: scripts/calibrate_czn_roi.py
- 🚧 CZN 页面 ROI 需在游戏运行时用校准脚本截图微调
- 🚧 PostMessage 兼容性验证（需在真实游戏环境测试）
- 🚧 异常恢复机制（翻车检测、超时重试）

## 文件维护规则

- 改代码 → 改完检查 README.md 和 AGENTS.md
- 新增模块/API/判定逻辑 → 同步更新 README
- 两个 md 和代码放同一个 commit
