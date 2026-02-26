# Agent OS — 完整系统文档
> 认知守护操作系统 v2.0
> 设计哲学：**模型即数据源，对话即操作界面**

---

## 一、系统概述

### 为什么存在

每一个基金经理都有这样的经历：
- 早上想好了计划，盘中就被情绪带走
- 止损线画好了，到了位置却犹豫不决
- 赚钱的时候忘记记录为什么赚，亏钱的时候只想逃避

Agent OS 不解决这些问题。它**逼你面对**这些问题。

### 核心架构

```
┌─────────────────────────────────────────────────┐
│                   用户（基金经理）                  │
│             在 VS Code 对话框中交互                │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│              AI 模型（Claude / GPT）              │
│                                                  │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌───────┐ │
│  │盘前研判│  │判断管理│  │盘中监控│  │决策引擎│ │
│  └────────┘  └────────┘  └────────┘  └───────┘ │
│  ┌────────┐  ┌────────┐                         │
│  │风控守护│  │盘后复盘│                         │
│  └────────┘  └────────┘                         │
│                                                  │
│  数据来源：模型自身的训练知识（宏观/行业/市场）     │
│  推理引擎：模型的深度推理能力                      │
│  状态持久化：state/ 目录的 JSON 文件              │
│  历史归档：vault/ 目录                            │
└─────────────────────────────────────────────────┘
```

### 与传统方案的区别

| 传统方案 | Agent OS |
|---------|----------|
| 写 Python 爬虫抓新闻 | AI 模型本身就有市场知识 |
| 调 API 拿行情数据 | 用户在对话中告知当前行情 |
| 搭建后端服务器运行 | 打开 VS Code 文件夹即可 |
| 需要 API Key 和网络 | 只需 VS Code 内置 AI |
| 复杂的部署和维护 | 零部署，文件夹即系统 |

---

## 二、数据来源策略

### 模型知识（自动）
AI 模型自身提供：
- 宏观经济框架分析（货币政策、财政政策、经济周期）
- 行业逻辑和产业链关系
- 历史相似情境的参考
- 交易心理学和行为金融学知识
- 风险管理理论框架

### 用户输入（主动）
用户在对话中提供：
- 当日具体行情数据（看盘软件截图或数据）
- 突发新闻事件
- 自己的持仓信息
- 交易想法和判断
- 市场情绪感受

### 状态文件（持久化）
系统通过 JSON 文件记住：
- 所有未过期的判断 → `state/judgments.json`
- 今日的决策记录 → `state/decisions.json`
- 今日的交易记录 → `state/trades.json`
- 当前持仓 → `state/portfolio.json`
- 今日边界条件 → `state/daily_boundary.json`

---

## 三、一天的完整生命周期

### 08:00 — 盘前研判
```
用户说: "开盘"
系统做:
  1. 读取 state/judgments.json 中的存量判断
  2. 读取 vault/ 中最近的复盘记录
  3. 基于模型知识分析当前市场环境
  4. 逐一检查每个判断是否仍然成立
  5. 生成今日边界条件（什么情况下不动手）
  6. 输出晨间研判简报
  7. 更新 state/daily_boundary.json
```

### 09:30-15:00 — 盘中运作
```
用户说: "看看 XX" / "想买 XX" / "更新"
系统做:
  - 建立/审查判断 → 要求证伪条件
  - 生成 Decision Brief → 风控审查
  - 监控判断是否被市场破坏
  - 检测行为是否偏离计划
  - 更新 state/ 目录下的对应文件
```

### 15:00 后 — 盘后复盘
```
用户说: "收盘"
系统做:
  1. 汇总全天的判断、决策、交易、告警
  2. 四维评分打分
  3. 提炼教训
  4. 归档到 vault/YYYY/MM/YYYY-MM-DD.json
  5. 重置 state/ 中的当日临时文件
```

---

## 四、核心概念

### 判断（Judgment）
判断是认知的最小单元。每个判断必须包含：
- **标的**：看什么
- **方向**：做多/做空/中性
- **核心逻辑**：为什么这么判断
- **关键变量**：支撑判断的要素
- **证伪条件**：什么情况下承认自己错了（必填！）
- **置信度**：0-100%
- **时间框架**：日内/短期/中期

判断有生命周期：`活跃 → 松动 → 失效/过期`

### Decision Brief（决策简报）
每一次想交易之前，必须先生成一份 Decision Brief：
- 不是交易指令，而是判断说明
- 强制交易者把想法写清楚
- 系统会审查逻辑、评估风险、提出质疑
- 只有通过风控审查，才能进入执行

### 边界条件
每天开盘前设定的"不出手"规则：
- 在什么市场条件下，今天不交易
- 在什么情绪状态下，今天不交易
- 这是"防冲动"的第一道防线

---

## 五、状态文件格式

### state/judgments.json
```json
{
  "last_updated": "2026-02-08T08:30:00",
  "judgments": [
    {
      "id": "j001",
      "created_at": "2026-02-07T09:00:00",
      "symbol": "600519",
      "symbol_name": "贵州茅台",
      "direction": "long",
      "thesis": "白酒消费复苏，春节数据超预期",
      "confidence": 0.7,
      "time_horizon": "短期（1-2周）",
      "key_variables": ["春节消费数据", "渠道库存", "北向资金流向"],
      "invalidation_conditions": [
        "股价跌破1600元",
        "渠道库存数据显著恶化",
        "北向资金持续大幅流出白酒板块"
      ],
      "status": "active",
      "status_reason": "",
      "ai_assessment": "",
      "ai_risk_notes": ""
    }
  ]
}
```

### state/decisions.json
```json
{
  "date": "2026-02-08",
  "decisions": [
    {
      "id": "d001",
      "created_at": "2026-02-08T10:30:00",
      "judgment_id": "j001",
      "symbol": "600519",
      "direction": "long",
      "confidence": 0.7,
      "rationale": "判断春节消费复苏逻辑成立，回调到支撑位",
      "entry_price": 1650,
      "stop_loss": 1600,
      "take_profit": 1800,
      "position_size_pct": 0.05,
      "status": "pending",
      "risk_check_passed": false,
      "risk_check_result": ""
    }
  ]
}
```

### state/portfolio.json
```json
{
  "last_updated": "2026-02-08T15:00:00",
  "total_value": 1000000,
  "cash": 850000,
  "positions": [
    {
      "symbol": "600519",
      "symbol_name": "贵州茅台",
      "direction": "long",
      "entry_price": 1650,
      "current_price": 1680,
      "quantity": 100,
      "position_value": 168000,
      "position_pct": 0.168,
      "unrealized_pnl": 3000,
      "stop_loss": 1600,
      "take_profit": 1800,
      "judgment_id": "j001",
      "decision_id": "d001"
    }
  ],
  "daily_pnl": 3000,
  "daily_pnl_pct": 0.003
}
```

### state/daily_boundary.json
```json
{
  "date": "2026-02-08",
  "boundaries": [
    "如果大盘跳空低开超过2%，今日不新开仓",
    "如果早盘30分钟成交量低于昨日同期50%，保持观望",
    "如果已有2笔亏损交易，停止今日所有新交易"
  ],
  "sentiment": "谨慎",
  "max_new_positions_today": 2
}
```

### state/trades.json
```json
{
  "date": "2026-02-08",
  "trades": [],
  "daily_pnl": 0,
  "trade_count": 0
}
```

---

## 六、文件夹结构总览

```
agent_os/
├── .github/
│   └── copilot-instructions.md     ← VS Code Copilot 自动读取
├── AGENT_OS.md                      ← 你正在看的完整文档
├── README.md                        ← 使用指南
├── workflow/                        ← 工作流详细定义
│   ├── 01_盘前研判.md
│   ├── 02_判断管理.md
│   ├── 03_盘中监控.md
│   ├── 04_决策执行.md
│   ├── 05_风控审查.md
│   └── 06_盘后复盘.md
├── state/                           ← 运行状态（AI 读写）
│   ├── judgments.json
│   ├── decisions.json
│   ├── trades.json
│   ├── portfolio.json
│   └── daily_boundary.json
├── rules/                           ← 风控规则
│   └── risk_config.json
├── vault/                           ← 历史归档
│   └── (YYYY/MM/YYYY-MM-DD.json)
└── config.json                      ← 基础配置
```
