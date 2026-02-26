# VS Code（非 Claude）99%能力复刻指南

## 目标

在不安装 Claude 插件体系的前提下，用你当前仓库复刻“指令化投研工作流”：

- 指令入口统一：`@分析`、`@估值`、`@护城河`、`@打分`、`@情景`、`@陷阱`、`@L5`、`@L6`、`@宏观`、`@日志`、`@机会`
- 输出落盘统一：全部写入 `10-研究报告输出/`
- VS Code 一键执行：通过 Task 面板触发

---

## 你现在已经有的能力（已落地）

### 1）统一路由器

- 文件：`tools/vscode_investment_router.py`
- 调用方式：
  - `python tools/vscode_investment_router.py --query "@分析 GOOGL"`
  - `python tools/vscode_investment_router.py --query "@估值 MSFT"`
  - `python tools/vscode_investment_router.py --query "@护城河 MSFT"`
  - `python tools/vscode_investment_router.py --query "@打分 MSFT"`
  - `python tools/vscode_investment_router.py --query "@情景 MSFT"`
  - `python tools/vscode_investment_router.py --query "@陷阱 MSFT"`
  - `python tools/vscode_investment_router.py --query "@L5 MSFT"`
  - `python tools/vscode_investment_router.py --query "@L6 MSFT"`
  - `python tools/vscode_investment_router.py --query "@宏观"`
  - `python tools/vscode_investment_router.py --query "@日志"`
  - `python tools/vscode_investment_router.py --query "@机会"`

### 2）VS Code 一键任务

- 文件：`.vscode/tasks.json`
- 使用：`Ctrl+Shift+P` → `Tasks: Run Task` → 选择：
  - `投研路由：输入@指令`
  - `投研路由：@宏观`
  - `投研路由：@日志`
  - `投研路由：@机会`

---

## 指令映射表（非 Claude 模式）

| 指令 | 当前行为 | 输出 |
| --- | --- | --- |
| `@分析 [标的]` | 生成个股研究草案（含预检清单、估值快照、情景表、Kill-Switch） | `10-研究报告输出/[日期]-个股-[标的]-非Claude路由版.md` |
| `@估值 [标的]` | 实时拉取估值字段并计算 `PR` 与 `g*` | `10-研究报告输出/[日期]-估值-[标的]-自动快照.md` |
| `@护城河 [标的]` | 巴菲特五维的量化近似评估 + 可证伪条件 | `10-研究报告输出/[日期]-护城河-[标的]-自动评估.md` |
| `@打分 [标的]` | Q-G-P-R 自动打分与评级 | `10-研究报告输出/[日期]-打分-[标的]-QGPR.md` |
| `@情景 [标的]` | 牛/基/熊/黑天鹅情景 + TSR 分解 | `10-研究报告输出/[日期]-情景-[标的]-TSR分解.md` |
| `@陷阱 [标的]` | 六类负范式陷阱检查（可量化项+待核验项） | `10-研究报告输出/[日期]-陷阱-[标的]-六类检查.md` |
| `@L5 [标的]` | L5 决策备忘录骨架（Key Variable/赔率/仓位） | `10-研究报告输出/[日期]-个股-[标的]-L5决策备忘录-路由版.md` |
| `@L6 [标的]` | L6 沙盘推演骨架（红蓝对抗/末日协议/执行兵法） | `10-研究报告输出/[日期]-个股-[标的]-L6沙盘推演-路由版.md` |
| `@宏观` | 调用 `bond_data.py --all` 生成债券宏观快照 | `10-研究报告输出/[日期]-宏观-债券快照-非Claude路由版.md` |
| `@日志` | 生成日度投资决策日志模板 | `10-研究报告输出/[日期]-投资决策日志.md` |
| `@机会` | 调用 `stock_tracker.py run-daily --news-limit 8` | `11.投资机会跟踪报告/daily_reports/` |

---

## 与 Claude 插件的差异（务实版）

- 已复刻：
  - 指令式入口
  - 多脚本编排
  - 报告模板化落盘
  - VS Code 一键触发

- 仍需你手工补位：
  - 私有数据源 MCP API Key（FactSet、LSEG、S&P 等）
  - 机构内流程模板（投委会格式、品牌模板）
  - 高阶自动化（如多代理并行协同）

---

## 建议的每日工作流（5分钟）

1. 跑 `投研路由：@宏观`，更新市场温度
2. 跑 `投研路由：@机会`，拿到日机会池
3. 对重点标的跑 `@估值` 或 `@分析`
4. 收尾跑 `@日志`，固化当天决策与可证伪条件

---

## 常见问题

### Q1：`@估值` 没有取到完整数据

答：通常是数据源字段缺失，路由器会在报告里写入 `数据告警`。先核对 ticker，再用第二数据源交叉验证。

### Q2：`@宏观` 失败

答：优先单独运行 `python bond_data.py --all` 看报错。常见是依赖没装或网络问题。

### Q3：如何扩展新指令

答：在 `tools/vscode_investment_router.py` 的 `execute_query()` 里新增分支，并把任务加到 `.vscode/tasks.json`。
