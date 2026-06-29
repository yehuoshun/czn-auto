# AGENTS.md — 卡厄思梦境自动化脚本 (v2)

> 写给接手这个项目的 AI Agent。

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
- 🚧 CZN 页面 ROI 需实际截图微调
- 🚧 PostMessage 兼容性需 Windows 实测
- 🚧 异常恢复（翻车检测、超时重试）
- 🚧 等级调整需增加右箭头（当前只有左箭头减等级）

## 测试脚本

```bash
# 实机流程测试（Windows，需要游戏窗口）
python test/test_outing_flow.py

# 单元测试（不依赖 Windows API）
python test/test_outing_unit.py
```

## 参考数据

- `references/flash_keywords.json` — 灵光/神光一闪词条表，作为数据参考未被代码直接引用
