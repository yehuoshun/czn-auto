# AGENTS.md — 卡厄思梦境自动化脚本 (v2)

> 写给接手这个项目的 AI Agent。

## 🚨 铁律（必须遵守）

### 1. 不要安装任何依赖

**这台机器不是测试环境。** 这个项目跑在 Windows 上（Win32 API），开发环境是 Linux。

- ❌ **禁止** `pip install`、`npm install`、`apt install` 任何东西
- ❌ **禁止** 尝试运行依赖 numpy/opencv/paddleocr 的测试代码
- ✅ 代码验证只用 `python3 -c "import ast; ast.parse(open(f).read())"` 做语法检查

### 2. 禁止未经授权修改代码

**开发环境和测试环境隔离。** 代码修改必须经过老大确认后才能提交。

- ❌ **禁止** 写完代码直接 push
- ✅ 先向老大展示修改方案，获得批准后再 push
- ✅ 老大在 Windows 上测试通过后，才算完成
- ✅ 本地只做静态分析和语法检查

工作流：写代码 → 展示 diff → 等老大确认 → push

## 项目是什么

一个 **Python + OpenCV + Win32 API** 的游戏自动化脚本。纯视觉识别 + 后台模拟操作。

**v2 核心**：
- **PrintWindow** 后台截图（窗口遮挡/后台也能截）
- **PostMessage** 后台点击（不移动鼠标，`ChildWindowFromPointEx` 解析子窗口）
- **单一职责**：每个文件只做一件事

## 技术栈

| 层 | 技术 |
|----|------|
| 截图 | PrintWindow (GDI) |
| 视觉 | OpenCV 竖线检测、模板匹配 (TM_CCOEFF_NORMED) |
| OCR | PaddleOCR (PP-OCRv6) |
| 点击 | PostMessage (WM_LBUTTONDOWN/UP) |
| 日志 | logging + RotatingFileHandler |

## 架构

```
main.py (CZNAuto 状态机)
  ├── core/screenshot.py    ← PrintWindow 后台截图
  ├── core/recognizer.py    ← PaddleOCR + 模板匹配
  ├── core/clicker.py       ← PostMessage 后台点击
  ├── pages/home.py         ← 主页/子页面识别
  ├── pages/season.py       ← 赛季页面识别
  ├── pages/czn.py          ← CZN 页面识别
  ├── pages/outing.py       ← 出击页面识别
  └── pages/battle.py       ← 战斗结算识别
```

## 关键概念

### 主页判定

```
竖线 ✅ + 返回箭头 ❌ → 主页
竖线 ✅ + 返回箭头 ✅ → 子页面
竖线 ❌                 → 非游戏页面
```

- **竖线检测**：菜单栏 ROI `(88%-99%) × (8%-82%)`，Sobel X 梯度 + 列投影
- **返回箭头**：模板匹配 `src/images/commons/back_arrow.png`，阈值 0.45

### 坐标系统

- **所有坐标基于 1920×1080 基准**，`Clicker` 内部自动缩放到实际窗口
- ROI 用**屏幕比例**（0.0~1.0），不要硬编码像素

### PostMessage 后台点击

```python
clicker.click(x, y)          # 左键单击（自动解析子窗口）
clicker.click_ratio(0.5, 0.5) # 按比例点击
clicker.send_key(0x1B)       # ESC 按键
```

- `ChildWindowFromPointEx` 解析 Unity/UE 渲染子窗口
- 先发 `WM_MOUSEMOVE` 更新 hover 状态

### PrintWindow 后台截图

```python
img = screenshot.capture()          # → PIL Image
cv_img = screenshot.to_cv2(img)     # → OpenCV BGR
```

- 使用 `PW_RENDERFULLCONTENT` 兼容 DWM 渲染
- 不依赖窗口焦点/可见性

## 三种模式

### manual（手动模式）
仅识别导航，不自动刷。

### outing（出击刷等级）
```
主页 → 菜单「出击」→ 调整等级(LV.40) → 进入 → 确认上阵
     → 战斗 → 结算 → 再次挑战 → 循环
```

### czn（卡厄思刷取）
```
主页 → 赛季横幅 → 赛季页面 → 卡厄思按钮
     → 幻象剧场 → 选关卡 → 选难度 → 进入战斗
     → 战斗 → 结算 → 再次挑战 → 循环
```

## 配置

```json
{
  "mode": { "type": "manual" },
  "outing": { "target_level": 40, "max_repeats": 0 },
  "czn": { "stage_keyword": "幻象", "difficulty": "困难", "max_repeats": 0 }
}
```

## 开发规范

- **单一职责**：一个文件一个类，一个方法一件事
- **阿里巴巴开发守则**：命名清晰、异常处理、完整注释
- **新增页面**：在 `src/pages/` 加识别类，在 `main.py` 加分支
- **改代码** → 同步更新 AGENTS.md 和 README.md

## 异常恢复机制

`main.py` 内置了多层异常恢复：

### 卡页检测
- `_check_recovery()` 每步检查是否卡在同一页面
- `max_page_stuck`（默认 30）轮后触发恢复
- 连续 5 轮 `unknown` 立即触发恢复

### 恢复模式
- 触发后进入 `_recovery_mode`，每次 step 强制 ESC 回主页
- 最多尝试 10 次，超过则暂停自动操作（mode=manual）

### 弹窗处理
- `_click_popup_close()` 优先 OCR 查找「关闭/取消/确定」按钮
- 兜底 ESC 按键

### 配置
```json
{
  "recovery": {
    "max_page_stuck": 30,
    "max_unknown": 5,
    "max_recovery_attempts": 10
  }
}
```

## 项目状态

- ✅ PrintWindow 后台截图
- ✅ PostMessage 后台点击（含子窗口解析）
- ✅ 主页检测（竖线+返回箭头）
- ✅ 子页面检测（OCR 标题：season/czn/outing）
- ✅ outing 模式（刷等级 → 进入 → 结算 → 循环）
- ✅ czn 模式（选关卡 → 选难度 → 进入 → 结算 → 循环）
- ✅ 弹窗关闭 + ESC 回主页
- ✅ ROI 校准脚本 scripts/calibrate_czn_roi.py
- ✅ 卡牌数据系统（36 角色 + 神光一闪选择引擎）
- ✅ 代码审查清理（删未用 import、补 typing、删死代码、补 __init__.py）
- ✅ 出击流程实机测试脚本 test/test_outing_flow.py
- ✅ 出击模块单元测试 test/test_outing_unit.py
- 🚧 CZN 页面 ROI 需实际截图微调（Windows 实测）
- 🚧 PostMessage 兼容性需 Windows 实测
- ✅ 等级调整支持双向箭头（左减右增）
- ✅ 异常恢复机制：
  - 卡页检测（同一页面连续 N 轮 → 触发恢复）
  - 未知页面超时（连续 5 轮 unknown → 触发恢复）
  - 恢复模式（强制 ESC 回主页，最多 10 次尝试）
  - 弹窗关闭增强版（优先 OCR 找关闭按钮，兜底 ESC）
- ✅ PaddleOCR v3 接口兼容性修复（统一 OCRResult/dict 解析）
- ✅ HomePage 增加 find_season_banner()（模板匹配赛季横幅）

## 测试脚本

```bash
# 实机流程测试（Windows，需要游戏窗口）
python test/test_outing_flow.py

# 单元测试（不依赖 Windows API）
python test/test_outing_unit.py
```

### 单元测试覆盖
- `test_read_level` — 等级 OCR 数字提取
- `test_find_enter_button` — 进入按钮识别
- `test_find_confirm_button` — 确认按钮识别
- `test_is_page` — 页面判定
- `test_get_arrow_pos` — 左右箭头坐标（新增右箭头）
- `test_level_adjustment_logic` — 双向调整方向逻辑
- `test_level_adjustment_max_clicks` — 最大点击次数限制
- `test_find_back_arrow` — 返回箭头模板匹配

## 参考数据

- `references/flash_keywords.json` — 灵光/神光一闪词条表，作为数据参考未被代码直接引用
