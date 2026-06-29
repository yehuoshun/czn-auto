# 卡厄思梦境自动化脚本 (v2)

基于 **Python + OpenCV + Win32 API** 的游戏自动化框架。

> 不碰内存、不注入、不改包。纯视觉识别 + 后台模拟点击。

**v2 核心变更**：
- **PrintWindow** 后台截图（不依赖窗口焦点）
- **PostMessage** 后台点击（不依赖鼠标位置）
- 一套方案走到底，无冗余回退

## 核心能力

| 能力 | 方案 | 特点 |
|------|------|------|
| **截图** | PrintWindow API | 后台截图，窗口隐藏/最小化也能截 |
| **识别** | 竖线检测 + 模板匹配 + PaddleOCR | 页面判定 + 文字识别 |
| **点击** | PostMessage (WM_LBUTTONDOWN/UP) | 后台发送消息，不移动鼠标 |
| **导航** | OCR 定位菜单按钮 + 模板匹配返回箭头 | 主页↔子页面切换 |

## 项目结构

```
czn-auto/
├── main.py                    # 主入口，状态机主循环 + 异常恢复
├── src/
│   ├── config.json            # 配置文件（含 recovery 段）
│   ├── core/                  # 底层能力
│   │   ├── __init__.py
│   │   ├── screenshot.py      # PrintWindow 后台截图
│   │   ├── recognizer.py      # 模板匹配 + PaddleOCR（兼容 v3）
│   │   ├── clicker.py         # PostMessage 后台点击
│   │   ├── config.py          # JSON 配置加载，自动缩放
│   │   └── logger.py          # 日志双输出
│   ├── pages/                 # 页面识别层（纯视觉，不点击）
│   │   ├── __init__.py
│   │   ├── base.py            # 页面抽象基类
│   │   ├── home.py            # 主页检测 / 页面判定 / 菜单按钮 / 赛季横幅
│   │   ├── season.py          # 赛季页面 / 卡厄思入口
│   │   ├── czn.py             # 卡厄思页面 / 关卡/难度/确认按钮
│   │   ├── outing.py          # 出击页面 / 等级/进入/确认/双向箭头
│   │   └── battle.py          # 战斗结算 / 再次挑战
│   ├── data/                  # 游戏数据
│   │   ├── __init__.py
│   │   ├── card_loader.py     # 卡牌数据加载器
│   │   ├── flash_scorer.py    # 神光一闪选择引擎
│   │   ├── preset_loader.py   # 预设存档加载
│   │   ├── cards/             # 角色卡牌图鉴 (JSON)
│   │   └── presets/           # 预设存档 (JSON)
│   └── images/
│       └── commons/
│           └── back_arrow.png # 返回箭头模板
├── references/
│   └── flash_keywords.json    # 灵光/神光一闪词条参考
├── scripts/
│   ├── calibrate_czn_roi.py   # ROI 校准工具
│   └── fetch_bwiki.py         # GameKee 数据抓取
├── test/
│   ├── test_outing_flow.py    # 出击流程实机测试（Windows）
│   ├── test_outing_unit.py    # 出击模块单元测试（8 项）
│   ├── test_outing.py         # 旧版出击识别测试
│   └── test_menus.py          # 菜单按钮识别测试
├── README.md
└── AGENTS.md
```

## 依赖

```bash
pip install opencv-python pillow numpy "paddlepaddle>=3" "paddleocr>=3"
```

## 快速开始

### 1. 配置

编辑 `src/config.json`：

```json
{
  "game": { "window_title": "卡厄思梦境" },
  "click": { "post_click_wait_ms": 500 },
  "loop": { "interval_ms": 1000, "max_iterations": 0 },
  "mode": { "type": "manual" },
  "outing": { "target_level": 40, "max_repeats": 0 },
  "czn": { "stage_keyword": "幻象", "difficulty": "困难", "max_repeats": 0 }
}
```

**mode.type** 可选值：
- `"manual"` — 手动模式，仅导航不自动刷
- `"outing"` — 出击刷等级
- `"czn"` — 卡厄思自动刷取

### 2. 运行

```bash
python main.py
```

v2 不需要管理员权限（PostMessage + PrintWindow 不触发 ACE 反作弊拦截）。

### 3. 模式说明

#### Outing 模式（出击刷等级）

```
主页 → 点击「出击」→ 设置等级（双向箭头） → 点击「进入」→ 确认上阵 → 进入战斗
战斗结束 → 检测结算 → 点击「再次挑战」→ 循环
```

等级调整支持**双向**：左箭头降低等级，右箭头升高等级。

#### CZN 模式（卡厄思刷取）

```
主页 → 赛季横幅 → 赛季页面 → 点击「卡厄思」按钮 → 幻象剧场
→ 选关卡 → 选难度 → 进入战斗
战斗结束 → 检测结算 → 点击「再次挑战」→ 循环
```

## 主页判定逻辑

```
竖线 ✅ + 返回箭头 ❌ → 主页大厅
竖线 ✅ + 返回箭头 ✅ → 子页面（出击/模拟/卡厄思…）
竖线 ❌                 → 非游戏页面
```

- **竖线检测**：菜单栏 ROI `(88%-99%) × (8%-82%)`，Sobel 梯度 + 列投影
- **返回箭头**：模板匹配 `src/images/commons/back_arrow.png`，阈值 0.45

## 异常恢复

系统内置自动恢复机制，防止卡住或翻车：

| 策略 | 触发条件 | 行为 |
|------|---------|------|
| 卡页检测 | 同一页面停留 ≥30 轮 | ESC 回主页重新导航 |
| 未知页面 | 连续 5 轮 `unknown` | 触发恢复模式 |
| 弹窗关闭 | `popup` 页面 | OCR 找关闭按钮，兜底 ESC |
| 恢复失败 | 恢复模式尝试 ≥10 次 | 暂停自动操作（切 manual） |

配置 `config.json` 的 `recovery` 段可调整阈值。

## 卡牌数据系统

`src/data/cards/*.json` — 角色卡牌图鉴，数据来源 GameKee。

### CardLoader

```python
from src.data.card_loader import load_all_cards, get_by_character
cards = load_all_cards()
hmd_cards = get_by_character(cards, "海德玛丽")
```

### 神光一闪评分

```python
from src.data.card_loader import load_all_cards
from src.data.preset_loader import load_preset
from src.data.flash_scorer import FlashScorer

cards = load_all_cards()
preset = load_preset("heidemarie", "aurora_sword")
scorer = FlashScorer(cards, preset)
best = scorer.pick_best(ocr_texts, card_name)
```

## ROI 校准

在游戏中进入对应页面后运行：

```bash
python scripts/calibrate_czn_roi.py
```

会在 `test_output/` 生成标注截图，根据截图微调 `src/pages/czn.py` 中的 ROI 常量。

## 测试

```bash
# 出击流程实机测试（Windows，需要游戏窗口）
python test/test_outing_flow.py

# 出击模块单元测试（不依赖 Windows API）
python test/test_outing_unit.py
```

## 注意事项

- v2 **不需要管理员权限**（PostMessage + PrintWindow 不触发 ACE 拦截）
- 所有坐标基于 1920×1080 基准，`Clicker` 自动缩放
- 截图不唤醒 UI（PrintWindow 后台操作，无需焦点）
- 赛季模板：`src/images/s*/` 目录，换季新建目录即可
