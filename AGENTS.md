# AGENTS.md — 卡厄思梦境自动化脚本

> 写给接手这个项目的 AI Agent。读完这个文件，你应该能直接开始写代码。

## 项目是什么

一个 **Python + OpenCV + Win32 API** 的游戏自动化脚本。目标是让脚本自动操作 PC 游戏「卡厄思梦境」。

**核心原则**：不碰内存、不注入、不改包。纯视觉识别 + 模拟点击。

## 技术栈

| 层 | 技术 | 用途 |
|----|------|------|
| 截图 | PIL ImageGrab / PrintWindow | 获取游戏窗口画面 |
| 视觉 | OpenCV (cv2) | 竖线检测（Sobel）、模板匹配（TM_CCOEFF_NORMED） |
| OCR | PaddleOCR (PP-OCRv6) | 识别菜单按钮文字 |
| 点击 | Win32 SetCursorPos + mouse_event | 模拟鼠标点击（需管理员权限） |
| 日志 | logging + RotatingFileHandler | 文件+控制台双输出，终端与文件完全一致 |

## 架构

```
main.py (CZNAuto)
  ├── Screenshot    ← 截图 (find_window → focus → capture → to_cv2)
  ├── Recognizer    ← 识别 (OCR / 模板匹配)
  ├── Clicker       ← 点击 (post_click / send_key)
  ├── HomePage      ← 识别层 (modules/home.py)：纯视觉，不点鼠标
  └── HomeActions   ← 操作层 (actions/home_actions.py)：调 HomePage 拿坐标后点击
```

**分层规则**：
- `src/core/` — 底层能力（截图/识别/点击/配置/日志），不依赖业务
- `src/modules/` — **识别层**，纯视觉识别，不操作鼠标键盘。每个模块对应一个游戏页面
- `src/actions/` — **操作层**，封装点击操作。调 modules 拿坐标后用 clicker 执行
- `src/images/commons/` — 公共模板图片
- 新增页面 → `modules/` 加识别类 + `actions/` 加操作类，在 `main.py` 接入

## 关键概念

### 坐标系统

- **所有坐标基于 1920×1080 基准分辨率**
- `Clicker.post_click(x, y)` 接收 1920×1080 坐标，内部自动缩放到实际窗口
- 新代码中的 ROI 都用**屏幕比例**（0.0~1.0），不要硬编码像素
- 模板匹配返回的是截图像素坐标，需要转回 1920×1080 基准再传给 `post_click`

### 主页判定

```
is_home() 判定逻辑:
  竖线 ✅ + 返回箭头 ❌ → 是主页
  竖线 ✅ + 返回箭头 ✅ → 是子页面（出击/模拟/卡厄思…）
  竖线 ❌                 → 非游戏页面
```

- **竖线检测**：菜单栏 ROI `(88%-99%) × (8%-82%)`，Sobel X 梯度 + 列投影
- **返回箭头**：模板匹配 `src/images/commons/back_arrow.png`，阈值 0.45
- 子页面左上角有返回箭头（←），主页没有。模板匹配用 `TM_CCOEFF_NORMED`，对颜色不敏感，黑白返回箭头都能匹配
- **弹窗判定**：竖线存在但无返回箭头 → `popup`（弹窗叠加在主页上）

### 导航流程

```
主页 → actions.navigate_to("出击") → OCR 定位按钮 → 点击 → sleep 1.5s
子页面 → actions.go_home() → 模板匹配找返回箭头 → 点击 → 验证回到主页
弹窗 → actions.close_popup() → ESC
```

**踩坑记录**：
- 之前 `is_home()` 只看竖线，子页面也有竖线导致误判
- 房子图标颜色随背景变化（深色背景白图标、浅色背景黑图标），颜色检测不可靠
- 最终方案：模板匹配返回箭头，不依赖颜色
- `capture()` 之前每次截图都点 2-3 下窗口中心，在子页面会误触按钮，改为默认不唤醒

### 为什么需要管理员权限

ACE 反作弊会拦截非管理员进程的鼠标操作。必须以管理员权限运行。

## 开发规范

### 新增页面

```python
# src/modules/xxx.py — 识别层
class XxxPage:
    def __init__(self, recognizer, config):
        self.rec = recognizer

    def is_xxx(self, screenshot) -> bool:
        """判定当前是否在 xxx 页面"""
        pass

    def find_something(self, screenshot) -> tuple | None:
        """返回坐标，不点击"""
        pass

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

### 截图

```python
image = self.screenshot.capture(clicker=self.clicker, wake_ui=False)  # 默认不唤醒
cv_img = self.screenshot.to_cv2(image)
```

`wake_ui=True` 只在首次截图或长时间无操作时使用，避免子页面误触。

### 日志

```python
import logging
logger = logging.getLogger("czn-auto.模块名")

# 初始化（main.py 中已调用，新模块直接 getLogger 即可）
from src.core.logger import setup_logging, print_startup_banner
setup_logging(level="DEBUG", compact=False)  # compact=True 用紧凑格式
print_startup_banner(logger, config_dict)     # 打印版本/环境/配置摘要
```

- 终端和文件使用同一个 Formatter，输出完全一致
- 文件始终 DEBUG 全量，控制台按 `level` 参数控制
- `compact=True` 去掉模块名/行号/函数名，适合发布版本
- 新增 `print_startup_banner()` 打印版本号、Python 版本、平台、管理员权限、配置摘要
```

### 坐标

```python
# ✅ 正确：用比例
x = int(w * 0.88)

# ❌ 错误：硬编码像素
x = 1700
```

## 常见坑

1. **窗口没找到** → 检查 `config.json` 里 `window_title` 是否正确
2. **点击没反应** → 是不是没以管理员权限运行？ACE 会拦截
3. **OCR 识别不准** → 菜单按钮只有部分文字能匹配（如「卡厄思」→「厄思」），`_fuzzy_match()` 做了模糊匹配。PP-OCRv6 精度比 v4 提升 ~5%
4. **返回箭头检测不到** → 模板匹配阈值 0.45，主战员页面黑色箭头 conf≈0.485，主页 conf≈0.379
5. **`is_home()` 误判** → 检查竖线检测和返回箭头模板匹配的日志
6. **子页面误触** → 确认 `capture()` 传了 `wake_ui=False`
7. **UI 隐藏 → 主页检测失败** → 首帧用 `wake_ui=True`，或 `step()` 检测到 unknown 后自动唤醒重试
8. **赛季动画加载慢** → 进入赛季页面后等 3s，卡厄思按钮 OCR 有 5 次重试
9. **PaddleOCR 3.x API 变更** → `ocr.ocr()` 改为 `ocr.predict()`，返回 OCRResult 对象，`recognizer.py` 已做兼容处理

## 文件维护规则

- 改代码 → 改完检查 README.md 和 AGENTS.md
- 新增模块/API/判定逻辑 → 同步更新 README
- 新增架构/规范/踩坑 → 同步更新 AGENTS
- 两个 md 和代码放同一个 commit
- 不确定要不要改 → 改。宁可多写不少写

## 项目状态

- ✅ 截图、点击、OCR 基础能力
- ✅ 主页检测 + 导航 + 返回 + 弹窗关闭
- ✅ 识别层/操作层分离
- ✅ 主页→赛季入口→赛季页面→卡厄思 全流程跑通
- ✅ 常驻卡厄思页面识别 + 操作模块（待测试调 ROI）
- ✅ 测试脚本 test_season_flow.py / test_czn_flow.py
- 🚧 幻象剧场关卡界面（进入战斗、难度选择）
- 🚧 常驻卡厄思业务逻辑（需截图确认 UI 后填充）

## 赛季模式入口

```
主页 → 模板匹配右下角横幅 s3/banner.png → 点击 + 等 3s 动画
     → 赛季页面（OCR 标题「银河系灾害」识别）
     → OCR 找左下角「卡厄思」文字 → 点击（5次重试）
     → 幻象剧场关卡界面
```

赛季模板：`src/images/s3/`，换季新建 `s4/` 目录即可。

## 快速上手

### 状态机怎么跑

```python
# main.py 主循环
step():
    image = screenshot.capture(wake_ui=False)  # 截图
    cv_img = screenshot.to_cv2(image)           # 转 OpenCV
    page = home.detect_page(cv_img)             # 识别当前页面
    match page:
        "home"    → _handle_home()
        "season"  → _handle_season()
        "czn"     → _handle_czn()
        "popup"   → actions.close_popup()
        "unknown" → actions.go_home()
```

`detect_page()` 返回值：
- `"home"` — 竖线有、返回箭头无
- `"season"` — OCR 标题匹配「银河系灾害」等
- `"czn"` — OCR 标题匹配「卡厄思」
- `"popup"` — 竖线有、返回箭头无（弹窗遮盖）
- `"unknown"` — 竖线无（战斗/加载等）

### 我要新增一个页面

1. 在 `src/modules/` 新建识别类，实现 `is_xxx(screenshot) → bool` 和 `find_xxx(screenshot) → tuple`
2. 在 `src/actions/` 新建操作类，构造函数接收 `(page, clicker)`
3. 在 `main.py` 的 `_init_modules()` 初始化，`step()` 的 `detect_page()` 里加分支
4. 同步更新 README.md 和 AGENTS.md

### 我要加一个按钮导航

```python
# home.py 里 BUTTON_NAMES 和 BUTTON_Y_RATIOS 加一项
# 然后直接 actions.navigate_to("新按钮", screenshot=cv_img)
```

### 截图怎么用

```python
# main.py 里（已有 screenshot 实例）
image = self.screenshot.capture(clicker=self.clicker, wake_ui=False)
cv_img = self.screenshot.to_cv2(image)

# actions 里（HomeActions 内部自己截图，不需要传）
# navigate_to 需要外部传 screenshot 做 OCR
# go_home / close_popup 内部调用 _capture() 自己截
```

### 点击怎么用

```python
self.clicker.post_click(x, y)        # 1920×1080 基准坐标，自动缩放
self.clicker.send_key(0x1B)          # 发送按键，0x1B = ESC
```

### OCR 怎么用

```python
# 区域 OCR → 返回字符串
text = self.recognizer.ocr_region(cv_img, x, y, w, h)

# 全屏 OCR → 返回列表 [(bbox, text, conf), ...]
# bbox = [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]  四个角点
results = self.recognizer.ocr_full(cv_img)
for bbox, text, conf in results:
    cx = int((bbox[0][0] + bbox[2][0]) / 2)  # 中心点 x
    cy = int((bbox[0][1] + bbox[2][1]) / 2)  # 中心点 y
```

### 模板匹配怎么用

```python
# 模板图放 src/images/commons/
# 返回 (x, y, conf) 或 None
# x, y 是截图像素坐标，不是 1920×1080 基准！需要转换
result = self.recognizer.match_template(cv_img, "name", "src/images/commons/xxx.png", threshold=0.8)
if result:
    x, y, conf = result
    h, w = cv_img.shape[:2]
    base_x = int(x * 1920 / w)   # 转 1920×1080 基准
    base_y = int(y * 1080 / h)
    self.clicker.post_click(base_x, base_y)
```

### 识别层怎么调操作层

**不调。** 识别层只返回坐标/布尔值，操作层拿到坐标后自己点。

```python
# ✅ 正确：actions 调 modules
pos = self.home.find_button(cv_img, "出击")
if pos:
    self.clicker.post_click(*pos)

# ❌ 错误：modules 里调 clicker
```

### 我遇到问题

1. 先看日志 `src/logs/czn-auto.log`
2. 检查 `config.json` 窗口标题是否正确
3. 确认以管理员权限运行
4. 看常见坑列表

### 卡牌数据

```python
from src.data.card_loader import load_all_cards, get_by_character
cards = load_all_cards()
hmd_cards = get_by_character(cards, "海德玛丽")
```

### 神光一闪评分

`src/data/flash_scorer.py` — 存档刷取时 OCR 出 3 个选项后自动选最优。

```python
from src.data.card_loader import load_all_cards
from src.data.preset_loader import load_preset
from src.data.flash_scorer import FlashScorer

cards = load_all_cards()
preset = load_preset("heidemarie", "aurora_sword")
scorer = FlashScorer(cards, preset)
best = scorer.pick_best(ocr_texts, card_name)  # → (index, branch, score)
```

预设 JSON 只含 `闪选评分`：`keywords`（全局标签权重）+ `per_card`（按卡牌覆盖 effects）。
新增角色：`presets/{英文名}/` 下建 JSON，配好权重即可。

### 从 GameKee 抓取角色数据到 JSON

> ⚠️ **必须用国服数据**：GameKee API 返回两套字段——`desc`（国际服/台服繁中）和 `desc_cn`（国服简中）。**全部用 `_cn` 后缀字段**。

**完整流程**：

```
1. 拿到 GameKee 角色页面 URL → 提取 content_id
   例: https://www.gamekee.com/czn/tj/703467.html → 703467

2. 调 API 拿元数据（需 header: game-alias: czn）
   GET https://www.gamekee.com/v1/content/detail/{content_id}
   → 拿到 title, cdn_url, entry_id 等

3. 调 CDN 拿页面内容（⚠️ 必须用 cdnimg-v2 域名，api-cdn 有 567 反爬）
   GET https://cdnimg-v2.gamekee.com/wiki2.0/pro/50388/content/{content_id}.json
   → 拿到 baseData（角色属性、技能、能力值、潜力、语音等）

4. 从 baseData 提取卡牌 ID 列表
   例: 封面卡牌id 列 → 972, 974, 973, 977
   再从可生成卡牌/起始卡牌区域补充 → 971, 976, 975

5. 调卡牌 API 拿卡牌详情
   POST https://www.gamekee.com/v1/entryCard/query-list
   Header: game-alias: czn, Content-Type: application/json
   Body: {"game_id": 50388, "ids": [972, 974, 973, ...]}
   → 每张卡牌有 entry 数组，type=1 是基础版，type=4 是神光一闪

6. 组装 JSON，写入 src/data/cards/角色名.json
   - 卡牌名用 name_cn（国服名），不是 name（国际服名）
   - 卡牌描述用 desc_cn，不是 desc
   - 术语对照：连接←连结、迅捷←快速、消耗←消灭、墓地←坟墓、终结←终极
```

**术语对照表（国服 ← 国际服）**：

| 国服 | 国际服 | 出现位置 |
|------|--------|----------|
| 连接 | 连结 | 卡牌标签/效果 |
| 迅捷 | 快速 | 卡牌标签 |
| 消耗 | 消灭 | 卡牌标签 |
| 墓地 | 坟墓 | 效果描述 |
| 终结 | 终极 | 卡牌标签 |

**踩坑记录**：
- 2026-06-22：第一版用了国际服 desc 字段，术语全错（连结/快速/消灭/坟墓），老板指出后改为 desc_cn
- 2026-06-22：api-cdn.gamekee.com 返回 567（腾讯 EdgeOne 反爬），改用 cdnimg-v2.gamekee.com
- 2026-06-22：卡牌名不要盲从 GameKee——name_cn 是「万人英雄」，但老板说旧名「万众英雄」是对的，以老板为准