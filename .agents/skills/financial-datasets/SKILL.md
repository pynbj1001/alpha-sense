---
name: financial-datasets
description: 通过 Financial Datasets 拉取结构化美股/港股财务数据与文档（利润表/资产负债表/现金流、股价历史、公司新闻、10-K/10-Q/SEC相关信息）。当用户提到“拉取财报/三大报表/财务快照”“按 ticker 获取收入/EPS/现金流”“下载或解析 10-K/10-Q”“用 API 批量取历史价格/指标”“需要结构化财务数据做估值/财务分析”时优先使用；但必须遵守数据瀑布：先尝试 yfinance/akshare，只有免费源不可用或缺字段/频繁报错时才降级调用本接口，并严格控制调用次数与分页。
---
# Financial Datasets API

## 概述
Financial Datasets 是一套为 LLM 和 AI Agents 设计的财务数据接口，提供包括全美股的利润表、资产负债表、现金流量表、股票价格及其他市场数据。在需要进行深度个股财务分析或调取结构化财报时，能极大地简化处理流程。本系统已将其安装支持。

> [!WARNING]
> **数据获取瀑布策略与限制（特级指令）**
> - **优先免费源**：当需要获取行情、股价、基本面等数据时，**必须优先**尝试调用免费开源数据库（如重点优先使用 `yfinance` 获取标的数据、`akshare` 获取宏观或A股数据）。
> - **末位备用**：只有在穷尽 `yfinance` / `akshare` 等免费渠道，且确实找不到所需数据或反复报错时，才允许降级使用 Financial Datasets 这类付费接口。
> - **请求限额控制**：Financial Datasets 属于高价值付费接口，额度极其珍贵。使用时**必须严格控制调用次数和分页大小**（例如：避免在循环中盲目批量请求，尽量只查询所需的具体日期或具体指标）。切记不要无限次调用，避免额度在短时间内被过度消耗。

## 输出质量要求（强制）

- **数据落地**：对外展示/分析时，输出必须包含：
  - **来源**（Financial Datasets / yfinance / akshare）与 **抓取日期**
  - **时间范围**（例如 2020-01-01 ~ 2025-12-31）与 **频率**（annual / quarterly / daily）
  - **字段列表**（用于复现与审计）
- **一致性校验**：若同时使用免费源与 Financial Datasets，至少对 1-2 个关键指标做交叉核对（如 Revenue / Net Income / EPS / Shares）。
- **失败降级**：遇到 401/403/429/5xx 或字段缺失时，优先缩小查询范围、降低 limit、缓存结果；仍失败再切换数据源或改用更粗粒度输出。

## 快速上手
- 环境要求：此项目已经安装了 `financial-datasets` 依赖包。
- API Key 配置：请在系统/终端环境或者代码中配置 `FINANCIAL_DATASETS_API_KEY` （可通过注册 financialdatasets.ai 获取）。

### Python 代码示例 (REST API 直接调取)
调用官方 API 提取财报或股票市场数据（推荐使用 `requests` 发送）：

```python
import os
import requests

# 读取环境变量中的 API key
api_key = os.environ.get("FINANCIAL_DATASETS_API_KEY", "YOUR_API_KEY_HERE")
headers = {"X-API-KEY": api_key}

# 1. 获取利润表 (Income Statements)
url_income = "https://api.financialdatasets.ai/financials/income-statements"
params_income = {
    "ticker": "AAPL",
    "period": "annual",  # 可选: annual, quarterly
    "limit": 5
}
resp = requests.get(url_income, params=params_income, headers=headers)
income_data = resp.json()

# 2. 获取股票行情价格 (Prices)
url_prices = "https://api.financialdatasets.ai/prices/"
params_prices = {
    "ticker": "AAPL",
    "start_date": "2024-01-01",
    "end_date": "2024-03-31"
}
resp_prices = requests.get(url_prices, params=params_prices, headers=headers)
prices_data = resp_prices.json()
```

### Python 代码示例 (生成问答数据集)
如果你需要用 10-K 或者年报去生成财务问答数据集，可以这样使用包自带的方法 (需要 OpenAI 权限)：

```python
from financial_datasets.generator import DatasetGenerator

generator = DatasetGenerator(model="gpt-4o", api_key="your-openai-key")
# 基于 10-K 生成问答集
dataset = generator.generate_from_10K(
    ticker="AAPL",
    year=2023,
    max_questions=10,
    item_names=["Item 1", "Item 7"]
)
```

## 支持的核心功能
| 功能模块 | API Endpoint 示例 | 作用 |
| --- | --- | --- |
| **利润表** | `/financials/income-statements` | 获取公司收入、净利润、EPS等 |
| **资产负债表** | `/financials/balance-sheets` | 获取资产、负债情况 |
| **现金流量表** | `/financials/cash-flow-statements` | 分析运营、投资、筹资现金流 |
| **行情与价格** | `/prices/` | 按日期范围获取个股日级别或分钟级行情 |
| **公司新闻** | `/news/` | 获取与公司 ticker 相关的新闻和事件 |
| **SEC 文档** | (支持通过 DatasetGenerator 解析) | 10-K, 10-Q 信息解析 |
