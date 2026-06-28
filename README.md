# 卡厄思梦境自动化脚本

基于 **Python + OpenCV + Win32 API** 的游戏自动化框架。

> 不碰内存、不注入、不改包。纯视觉识别 + 模拟点击。

## 核心能力

| 模块 | 能力 | 技术方案 |
|------|------|----------|
| **截图** | 游戏窗口截图 | ImageGrab（主） → PrintWindow（回退） |
| **识别** | 主页/子页面判定 | 竖线检测 + 返回箭头模板匹配 |
| **OCR** | 菜单按钮文字识别 | PaddleOCR（PP-OCRv6） |
| **点击** | 模拟真实鼠标点击 | SetCursorPos + mouse_event（管理员权限） |
| **导航** | 主页↔子页面切换 | OCR 定位菜单按钮 + 返回箭头模板匹配 |

## 项目结构

```
czn-auto/
├── main.py                    # 主入口，状态机主循环
├── src/
│   ├── config.json            # 配置文件
│   ├── core/                  # 底层能力
│   │   ├── screenshot.py      # 截图：ImageGrab + PrintWindow
│   │   ├── recognizer.py      # 识别：模板匹配 + PaddleOCR
│   │   ├── clicker.py         # 点击：SetCursorPos / SendInput
│   │   ├── config.py          # 配置：JSON 加载，自动缩放
│   │   └── logger.py          # 日志：文件+控制台双输出，终端文件一致
│   ├── modules/               # 识别层（纯视觉，不点击）
│   │   ├── home.py            # 主页检测 / 页面判定 / 赛季入口
│   │   ├── season.py          # 赛季页面识别 / 卡厄思按钮
│   │   └── czn.py             # 常驻卡厄思页面识别 / 关卡/难度/确认按钮
│   ├── actions/               # 操作层（封装点击）
│   │   ├── home_actions.py    # 导航 / 返回主页 / 关闭弹窗
│   │   ├── season_actions.py  # 赛季页面操作 / 进入卡厄思
│   │   └── czn_actions.py     # 常驻卡厄思操作 / 关卡选择 / 难度 / 进入战斗
│   ├── data/                  # 游戏数据
│   │   ├── card_loader.py     # 卡牌数据加载器
│   │   └── cards/             # 角色卡牌图鉴（JSON）
│   │       ├── 海德玛丽.json   # 已更新：7张卡牌 + 神光一闪
│   │       ├── 米卡.json
│   │       └── ...            # 36+ 角色卡牌数据
│   ├── images/
│   │   ├── commons/           # 公共模板（跨赛季复用）
│   │   │   └── back_arrow.png
│   │   └── s3/                # 赛季3「回荡在银河中的歌声」
│   │       ├── banner.png     # 主页赛季入口横幅
│   │       └── czn.png        # 赛季页面「卡厄思」按钮
│   └── logs/                  # 日志输出
└── .github/workflows/         # CI：钉钉通知
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
  "click": { "delay_ms": 100, "post_click_wait_ms": 500, "humanize": true },
  "loop": { "interval_ms": 1000, "max_iterations": 0 },
  "log": { "level": "DEBUG", "file": "src/logs/czn-auto.log", "max_size_mb": 50, "backup_count": 5 }
}
```

### 2. 运行

```bash
python main.py
```

**必须以管理员权限运行**（ACE 反作弊拦截非管理员进程）。

## 架构

```
main.py (CZNAuto)
  ├── Screenshot    ← 截图
  ├── Recognizer    ← 识别
  ├── Clicker       ← 点击
  ├── HomePage      ← 识别层: is_home / detect_page / find_season_banner
  ├── SeasonPage    ← 识别层: find_czn_button
  ├── CznPage       ← 识别层: is_czn / find_stages / find_difficulty / find_confirm_button
  ├── HomeActions   ← 操作层: navigate_to / go_home / close_popup
  ├── SeasonActions ← 操作层: enter_czn
  └── CznActions    ← 操作层: select_stage / select_difficulty / enter_battle / scan_page
```

**分层规则**：
- `core/` — 底层能力，不依赖业务
- `modules/` — 纯识别，不操作鼠标键盘
- `actions/` — 纯操作，调 modules 拿坐标后执行点击
- 新增页面 → `modules/` 加识别类 + `actions/` 加操作类

## 主页判定逻辑

```
竖线 ✅ + 返回箭头 ❌ → 主页大厅
竖线 ✅ + 返回箭头 ✅ → 子页面（出击/模拟/卡厄思…）
竖线 ❌                 → 非游戏页面
```

- **竖线检测**：菜单栏 ROI `(88%-99%) × (8%-82%)`，Sobel 梯度 + 列投影
- **返回箭头**：模板匹配 `src/images/commons/back_arrow.png`，阈值 0.45
- 子页面左上角有返回箭头（←），主页没有，模板匹配不依赖颜色

## 模块 API

### HomePage — 识别层 (`src/modules/home.py`)

| 方法 | 说明 |
|------|------|
| `is_home(screenshot) → bool` | 判定是否在主页 |
| `detect_page(screenshot) → str` | 返回页面标识（"home" / "season" / "czn" / "popup" / "unknown"） |
| `has_back_arrow(screenshot) → bool` | 检测返回箭头是否存在 |
| `find_button(screenshot, target) → tuple | None` | OCR 查找菜单按钮坐标 |
| `find_back_arrow(screenshot) → tuple | None` | 模板匹配找返回箭头坐标（1920×1080 基准） |
| `find_season_banner(screenshot) → tuple | None` | 模板匹配找赛季入口横幅坐标 |
| `get_layout_debug(screenshot) → dict` | 导出调试图数据 |

### HomeActions — 操作层 (`src/actions/home_actions.py`)

| 方法 | 说明 |
|------|------|
| `navigate_to(target, screenshot) → bool` | 导航到目标页面 |
| `go_home() → bool` | 点击返回箭头回到主页，ESC 兜底 |
| `close_popup() → bool` | 关闭弹窗（ESC） |

### CznPage — 识别层 (`src/modules/czn.py`)

| 方法 | 说明 |
|------|------|
| `is_czn(screenshot) → bool` | 判定是否在常驻卡厄思页面 |
| `find_stages(screenshot) → list[dict]` | OCR 识别关卡列表 |
| `find_stage_by_name(screenshot, keyword) → tuple | None` | 按名称查找关卡坐标 |
| `find_difficulty(screenshot) → dict | None` | 识别当前选中难度 |
| `find_difficulty_button(screenshot, target) → tuple | None` | 查找指定难度按钮 |
| `find_confirm_button(screenshot) → tuple | None` | 查找确定/进入战斗按钮 |

### CznActions — 操作层 (`src/actions/czn_actions.py`)

| 方法 | 说明 |
|------|------|
| `select_stage(screenshot, keyword) → bool` | 选择关卡 |
| `select_difficulty(screenshot, target) → bool` | 选择难度 |
| `enter_battle(screenshot) → bool` | 点击确认进入战斗 |
| `quick_start(screenshot, difficulty) → bool` | 一键选难度+进入战斗 |
| `scan_page(screenshot) → dict` | 扫描页面所有可操作元素 |

## 卡牌数据系统

`src/data/cards/*.json` — 角色卡牌图鉴，数据来源 GameKee。

### CardLoader API

| 方法 | 说明 |
|------|------|
| `load_all_cards() → dict` | 加载所有卡牌，返回 `{卡名: {...}}` |
| `get_by_character(cards, char_name) → dict` | 返回指定角色的所有卡牌 |
| `get_by_type(cards, card_type) → dict` | 返回指定类型（攻击/技能）的所有卡牌 |

### 卡牌 JSON 格式

```json
{
  "角色": "海德玛丽",
  "属性": "热情", "职业": "游侠", "稀有度": "五星",
  "卡牌": {
    "卡牌名": {
      "id": 972,
      "type": "攻击",
      "cost": 1,
      "effect": "...",
      "kind": "独特卡牌",
      "rarity": "稀有",
      "灵光一闪": true,
      "神光一闪": [{"cost": 1, "effect": "...", "recommend": true}]
    }
  },
  "自我意识技能": { "名称": "剑之乐园", "EP": 5, "效果": "..." },
  "来源": "GameKee URL"
}
```

### 已更新角色

| 角色 | 卡牌数 | 灵光一闪 | 最后更新 |
|------|--------|----------|----------|
| 海德玛丽 | 8 张（2 基本 + 4 独特 + 2 可生成） | ✅ | 2026-06-22 |

## 注意事项

- **必须管理员权限**：ACE 反作弊拦截非管理员进程
- **必须窗口化**：PrintWindow 对全屏独占模式可能失效
- 所有坐标基于 1920×1080 基准，`Clicker` 自动缩放
- 截图默认不唤醒 UI（`capture(wake_ui=False)`），避免子页面误触按钮
- 日志文件始终 DEBUG 全量记录，终端与文件格式内容完全一致
- **赛季入口**：模板匹配右下角横幅 `s3/banner.png`，每季换图即可复用
- **赛季模板**：`src/images/s3/` 目录，换季新建 `s4/` 目录即可
- **测试脚本**：`python test_season_flow.py` 验证赛季流程，`python test_czn_flow.py` 验证常驻卡厄思流程