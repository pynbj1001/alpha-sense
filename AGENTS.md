# AGENTS.md — AI 代理通用指令 v5.0

> 本文件供所有 AI 编码代理自动读取（GitHub Copilot、Claude Code、Cursor Agent 等）。

---

## 项目概述

**类型**: 混合型投资研究框架（Python + Markdown）  
**核心**: AI 驱动的机构级首席执行官（CEO）系统  
**Python 版本**: 3.10+（使用现代类型注解 `float | None`）

---

## Build / Lint / Test 命令

### 数据与研究工具

```bash
# 投研路由（核心入口）
python tools/vscode_investment_router.py --query "@分析 GOOGL"
python tools/vscode_investment_router.py --query "@估值 MSFT"
python tools/vscode_investment_router.py --query "@宏观"

# 留存收益检验（巴菲特 $1 测试）
python tools/retained_earnings_check.py --ticker AAPL
python tools/retained_earnings_check.py --ticker 600519.SS --years 10 --save

# 债券数据
python bond_data.py --all

# 股票追踪 / 日报
python stock_tracker.py run-daily --news-limit 8
```

### VS Code 任务（Ctrl+Shift+P → Tasks: Run Task）

- `投研路由：输入@指令` — 交互式投研入口
- `投研路由：@宏观` — 宏观周期分析
- `投研路由：@日志` — 决策日志
- `同步FSP复用资产` — 同步金融插件

### 测试

```bash
# 新闻扫描模块测试（pytest）
cd "13.新闻扫描/ai-news-radar" && pytest tests/ -v

# 运行单个测试文件
cd "13.新闻扫描/ai-news-radar" && pytest tests/test_utils.py -v

# 运行单个测试函数
cd "13.新闻扫描/ai-news-radar" && pytest tests/test_utils.py::test_function_name -v
```

### 类型检查

```bash
# Pyright/Pylance 类型检查（已在 .vscode/settings.json 启用）
# 设置: "python.analysis.typeCheckingMode": "standard"
```

---

## 代码风格规范

### Python 导入顺序

```python
# 1. 标准库
import argparse
import json
import os
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Any

# 2. 第三方库
import pandas as pd
import requests

# 3. 本地模块（如有）
from tools.some_module import SomeClass
```

### 类型注解

```python
# 使用 Python 3.10+ 联合类型语法
from __future__ import annotations

def _try_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None

# 使用 dataclass 定义结构化返回类型
@dataclass
class RouteResult:
    ok: bool
    message: str
```

### 命名约定

| 类型 | 风格 | 示例 |
|---|---|---|
| 函数/变量 | snake_case | `fetch_valuation_snapshot`, `avg_roe` |
| 类 | PascalCase | `RouteResult`, `AnalysisEngine` |
| 常量 | UPPER_CASE | `DEFAULT_YEARS`, `REPORT_DIR` |
| 私有函数 | 前缀下划线 | `_try_float`, `_fmt_num` |

### 错误处理

```python
# 可选依赖容错模式
try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False
    print("[警告] yfinance 未安装，自动模式不可用。请运行: pip install yfinance")

# 使用时检查
if not HAS_YF:
    return {"error": "yfinance 不可用"}
```

### 文档字符串

```python
def calculate_rolldown_transparent(self, yields_data, holding_months=3):
    """
    透明化计算 Rolldown 收益
    
    计算公式披露：
    - Rolldown = (Y_n - Y_m) × (m / n)
    
    参数:
        yields_data: 收益率曲线数据
        holding_months: 持有月数
    
    返回:
        Dict[str, float]: 各期限 rolldown 收益
    """
```

---

## 任务操作系统 (Task OS) & 应用程序 (Apps)

**架构定位**：本系统采用 "OS + App" 架构。`planning-with-files` 作为 **任务操作系统 (Kernel)** 负责状态编排、进度跟踪和上下文持久化；其他 `@指令` 对应的 Skill 作为 **应用程序 (Apps)** 运行在系统上完成具体领域任务。

### 1. 任务操作系统 (Kernel)
**核心组件**：`tasks/planning-with-files/`
**启动指令**：`@OS:start` 或 `planning-with-files`
**核心文件**：
- `task_plan.md`: 任务蓝图、阶段追踪
- `findings.md`: 结构化研究发现、元数据
- `progress.md`: 运行日志、错误记录、验证结果

### 2. 应用程序 (Apps)
所有 `@指令` 指向的领域技能均为应用程序。执行任何 App 前，**必须**已经通过 Kernel 建立了任务上下文。

| 指令 | Skill | 类型 |
|---|---|
| `@分析 [公司]` | `skills/DeepAnalysis/SKILL.md` |
| `@估值 [公司]` | `skills/Valuation/SKILL.md` |
| `@护城河 [公司]` | `skills/Moat/SKILL.md` |
| `@打分 [公司]` | `skills/Scoring/SKILL.md` |
| `@情景 [公司]` | `skills/Scenario/SKILL.md` |
| `@陷阱 [公司]` | `skills/TrapCheck/SKILL.md` |
| `@宏观` / `@周期` | `skills/MacroCycle/SKILL.md` |
| `@债券` | `skills/BondStrategy/SKILL.md` |
| `@L5 [公司]` | `skills/CIO-Memo/SKILL.md` |
| `@L6 [公司]` | `skills/War-Game/SKILL.md` |
| `@行业 [行业]` | `skills/IndustryAnalysis/SKILL.md` |
| `@日志` / `@反思` | `skills/DecisionLog/SKILL.md` |
| `@留存 [公司]` | `skills/RetainedEarningsCheck/SKILL.md` |
| `@问 / @快评 / @辩论` | `THINK-TANK.md` | App |
| `@财报 [公司]` | `skills/tech-earnings-deepdive/SKILL.md` | App |
| `@流动性` / `@liquidity` | `skills/macro-liquidity/SKILL.md` | App |
| `@情绪` / `@sentiment` | `skills/us-market-sentiment/SKILL.md` | App |
| `@价值 [公司]` / `@value` | `skills/us-value-investing/SKILL.md` | App |
| `@BTC` / `@比特币底部` | `skills/btc-bottom-model/SKILL.md` | App |
| `@乱世` / `@策略` | `skills/chaotic-era-strategy/SKILL.md` | App |

**执行链路**：`任务启动` → `调用 planning-with-files (初始化 OS 层)` → `调用领域 App` → `更新 OS 状态` → `完成`。

---

## 核心铁律

1. **数据先行** — 禁止凭记忆引用财务数据；通过 `yfinance`/`akshare` 实时获取，标注来源与日期。免费渠道找不到时，启用 `tushare` 备用（参见数据瀑布策略）。
2. **概率化表达** — 结论用概率区间，禁用"一定""肯定"。
3. **多框架验证** — 至少 3 个独立框架指向同一方向才构成投资建议。
4. **Kill-Switch** — 7 项红线任一触发 → 立即降为"观察"。
5. **记忆偏好** — 对话开始读 `03-Agents_Config/USER/PREFERENCES.md`。
6. **持续优化** — 错误/纠正追加 `tasks/lessons.md`。
7. **结论优先** — 执行摘要 ≤ 3 句，先结论后数据。
8. **框架自动索引** — 收到投研问题时，先查 `00-核心投研指南/INDEX.md` 索引，自动匹配适用框架，读取框架原文后再回答。优先使用 `tools/data_toolkit.py` 获取数据、`tools/report_templates.py` 生成报告。
9. **FSP 机构级优先** — 生成任何投研报告时，**必须**参考 `skills/financial-services-plugins/` 中对应技能的格式与流程（如 `earnings-analysis` 的 beat/miss 格式、`initiating-coverage` 的 5 阶段流程）。报告标准：数字先行、来源标注、■ 要点格式、新旧估计对比表、敏感性矩阵、估值足球场图。

---

## 用户记忆文件

> **唯一真实路径**：`03-Agents_Config/USER/`

| 文件 | 用途 |
|---|---|
| `03-Agents_Config/USER/PREFERENCES.md` | 报告风格/深度/语言偏好 |
| `03-Agents_Config/USER/GOALS.md` | 当前投资目标与关注标的 |
| `03-Agents_Config/USER/THOUGHTS.md` | 用户洞见与已建仓论点 |
| `03-Agents_Config/USER/EXPERIENCE.md` | 历史对话摘要与经验教训 |

**规则：只增不删，轻量追加，对话结束后隐式更新。**

---

## 数据依赖

### 数据获取瀑布策略（优先级从高到低）

| 优先级 | 库 | 用途 | 备注 |
|--------|----|----|------|
| ① **优先** | `yfinance` | 美股/港股行情、基本面 | 免费，无需 token |
| ① **优先** | `akshare` | A 股数据（双源验证）、宏观 | 免费，数据丰富 |
| ② **备用** | `tushare` | 当免费渠道找不到数据时使用 | token 已配置，每分钟50次，接口文档见 `.agents/skills/tushare/SKILL.md` |
| — | `pandas` | 数据处理 | — |
| — | `requests` | HTTP 请求 | — |

> **调用规范**：`pro = ts.pro_api()`（token 已持久化，无需传参）。只有 yfinance/akshare 均无法满足需求时，才调用 Tushare。

---

## 输出规范

- **报告**: `10-研究报告输出/[YYYY-MM-DD]-[类型]-[标的]-[框架].md`
- **任务**: `tasks/todo.md`
- **教训**: `tasks/lessons.md`

---

*AGENTS.md v5.0 — 完整开发指南 × 投研路由 × 代码风格*