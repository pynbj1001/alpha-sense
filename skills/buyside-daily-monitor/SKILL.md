---
name: buyside-daily-monitor
description: |
  买方机构级日报生成技能。将 stock_tracker.py 产出的新闻情绪原料，升级为CIO级别的每日投资跟踪备忘录。
  整合：市场情绪扫描 + 实时估值快照 + 论点健康度评分 + 宏观/信用看板 + 仓位信号 + 当日行动建议。

  **适用场景：**
  - 每日盘前/盘后投资组合跟踪
  - 论点完整性检验（催化剂 vs 论点支柱是否偏离）
  - 仓位调整信号生成（增/减/观察/止损）
  - 机构级晨会材料准备

  **不适用场景：**
  - 首次覆盖报告（使用 @分析 指令）
  - 估值建模（使用 @估值 指令）
  - 行业格局研究（使用 @行业 指令）

  **触发词：** "日报"、"buyside daily"、"晨报"、"@日报"、"daily monitor"、"投资组合日报"
---

# Buyside Daily Monitor — 买方机构级日报技能 v1.0

## ⚠️ CRITICAL CONSTRAINTS — 首先阅读，全程遵守

**在生成任何日报段落之前，必须遵守以下规则：**

### 数据源优先级（严格按序）

1. **FIRST：stock_tracker.py 原料** — 读取最新的 `11.投资机会跟踪报告/daily_reports/YYYY-MM-DD-investment-idea-tracking-report.md`，这是新闻情绪扫描的基础数据
2. **SECOND：Python 实时价格** — `yfinance`（美股/港股/ETF）获取当日收盘价、52周高/低、PE/PB、EV/EBITDA
3. **THIRD：akshare** — A股双源验证估值数据
4. **LAST RESORT：Web 搜索** — 仅当以上均不可用，必须标注"非机构数据源"

❌ **NEVER 凭记忆引用股价、PE、目标价等任何数字**  
❌ **NEVER 在未获取最新价格的情况下输出"估值偏低/偏高"结论**  
❌ **NEVER 跳过论点健康度评估直接给出仓位信号**  
❌ **NEVER 使用"一定""肯定""必然"等词**  
❌ **NEVER 输出超过 5 页（约 2000 字）的报告正文** — 日报必须可在 5 分钟内读完

### 防止走捷径规则

❌ **NEVER** 写"此部分数据待更新"（必须显示实际获取的数字，或明确标注 N/A + 原因）  
❌ **NEVER** 跳过 Risk Tripwire 检查（每个持仓必须测试止损条件）  
❌ **NEVER** 在论点分数 < 50 的标的上输出"维持"建议（需明确说明维持理由）  
❌ **NEVER** 合并展示两个不同方向的仓位信号（多头/空头信号必须分栏）

### 输出规范

| 深度等级 | 触发条件 | 报告长度 | 核心内容 |
|---|---|---|---|
| **快报（Quick Flash）** | 临时触发、追问 | ≤ 300字 | 仅执行摘要 + TOP3 变化 |
| **标准日报（Standard Daily）** | 每日常规触发 | 800-1500字 | 全规格报告（本技能默认） |
| **周报版（Weekly Digest）** | 每周五触发 | 2000-3000字 | 标准日报 + 7日论点漂移分析 |

---

## 日报工作流

### Step 0：数据准备（硬性前提）

执行以下操作，**确认数据已就绪再开始写报告**：

```python
# 0-A：定位最新日报原料
import glob, os
from pathlib import Path

report_dir = Path("11.投资机会跟踪报告/daily_reports")
reports = sorted(report_dir.glob("*-investment-idea-tracking-report.md"))
latest = reports[-1] if reports else None
# → 读取 latest 文件，提取各标的新闻条数、情绪偏向、热词

# 0-B：用 yfinance 拉取实时快照（批量）
import yfinance as yf

watchlist_tickers = [...]  # 从 ideas_watchlist.json 读取
data = yf.download(watchlist_tickers, period="5d", auto_adjust=True)
# → 记录当日收盘价、5日涨跌幅、52周高/低位置（%ile）

# 0-C：估值指标（PE、PB、EV/EBITDA）
for ticker in watchlist_tickers:
    info = yf.Ticker(ticker).info
    # → pe_ratio, pb_ratio, ev_to_ebitda, target_mean_price
```

**前置验证 Checklist（每次生成日报必做）：**
```
✅ [ ] 最新日报原料文件已定位并读取
✅ [ ] yfinance 价格快照已获取（或标注 N/A 原因）
✅ [ ] ideas_watchlist.json 持仓标记已读取（区分"重仓/标配/观察/空仓"）
✅ [ ] 上一份日报的仓位信号已读取（用于对比变化）
✅ [ ] 宏观信用看板数据（HY OAS、Z1 期限）已从原料文件提取

IF 任一未通过 → 明确告知缺失项，要求用户确认后方可出具分析结论
```

---

### Step 1：执行摘要（Executive Summary）

**格式规范：必须是报告第一段，3-5 句话，含明确行动建议**

```
【日报】YYYY-MM-DD | [买方日报 / 晨报 / 盘后版]
报告人：[CIO / Portfolio Manager]
覆盖范围：XX 个标的 | 今日事件：N 条催化剂 | 宏观信号：[绿色/黄色/红色]

TOP CALL：[最值得关注的一件事，1句话]
→ 影响标的：[Ticker] | 建议动作：[增持/观察/止损] | 时限：[当日/本周/中线]

今日市场情绪：[偏正面/偏负面/中性]
信用风险信号：[OFF / 黄色预警 / 红色警报]
```

**撰写原则：**
- 执行摘要必须有观点，不是纯信息汇编
- TOP CALL 必须是可在晨会上拍板决策的事项
- 如果"无值得关注之事"，明确说"今日无 TOP CALL，全仓维持，下一重要事件为 [日期+事件]"

---

### Step 2：宏观与信用看板

直接提取 stock_tracker.py 原料中的三因子信号，格式化输出：

```markdown
## 宏观与信用看板

| 信号 | 最新值 | 6M变动 | 状态 | 解读 |
|---|---|---|---|---|
| HY OAS | X.XX% | ±0.XXpct | 🟢未恶化 / 🟡关注 / 🔴警报 | [一句话] |
| Z1 期限/流动性 | 短债占比 XX% | ±Xpct | 🟢/🟡/🔴 | [一句话] |
| 利息负担缺口 | dE-dEBITDA X.Xpct | 连续X季度 | 🟢/🟡/🔴 | [一句话] |
| **综合信号** | | | **OFF / ON** | [风险判断一句话] |

> 宏观信号颜色规则：绿=三因子均未恶化；黄=1-2因子预警；红=三因子同时恶化（Kill-Switch 触发）
```

**⚠️ 若综合信号为"RED / ON"，则：**
- 所有持仓标的自动降一级（增持→维持，维持→关注）
- 报告顶部加红色警示横幅
- 明确写明：哪个因子触发、历史上同样信号后的市场表现参考

---

### Step 3：持仓组合快照

对 `ideas_watchlist.json` 中标记为 **持仓**（position = "重仓" / "标配"）的标的，逐一输出：

```markdown
## 持仓组合快照

### [公司名] ([TICKER]) — [持仓级别：重仓/标配]

| 指标 | 当前值 | 建仓参考价 | 变化 |
|---|---|---|---|
| 最新收盘价 | $XX.XX | $XX.XX | [+XX% / -XX%] |
| 52周位置 | XX%ile | — | — |
| P/E (TTM) | XX.Xx | [建仓时PE] | [+X / -X] |
| EV/EBITDA | XX.Xx | — | — |
| 分析师目标价均值 | $XX.XX | — | 隐含 [+/-]XX% |

**论点健康度评分：[XX/100]**

| 论点支柱 | 原始期望 | 当前状态 | 分 |
|---|---|---|---|
| [支柱1，如：AI算力需求持续] | [预期增长XX%] | ✅强化/⚠️动摇/❌破坏 | XX |
| [支柱2] | ... | ... | XX |
| [支柱3] | ... | ... | XX |

**今日新闻信号：** [X条正面 / X条负面 / X条中性]
**热词变化：** [今日热词 vs 昨日热词，是否有新议题]

**当日仓位信号：**
- 🟢 **维持 / 加仓** — [理由，1-2句]
- 🟡 **观察** — [需要确认的条件，1句]
- 🔴 **减仓/止损** — [触发条件，1句]

> Risk Tripwire：如果 [具体条件，如"Q4 GPU出货增速低于20%"]，则立即触发止损
```

**论点健康度评分规则（0-100）：**
- 每个支柱满分 25 分（最多 4 个支柱，总分 100）
- ✅强化：+25；⚠️动摇：+10；❌破坏：0；📊中性：+15
- 评分 < 50：必须有明确说明为何维持持仓，或降级信号
- 评分 70-100：正常，可维持或加仓
- 评分 50-70：黄色，建议观察，不宜加仓

**仓位信号判定矩阵：**
```
论点分 ≥ 70 + 估值未透支 + 宏观信号绿 → 维持 / 加仓
论点分 50-70 + 任一估值警戒 → 观察 / 不加仓
论点分 < 50 + 负面催化剂 → 减仓候选
论点分 < 50 + Risk Tripwire 触发 → 止损执行
宏观 RED 信号 + 任一持仓论点分 < 60 → 立即减仓
```

---

### Step 4：观察池动态（Watchlist Alerts）

对 `ideas_watchlist.json` 中标记为 **观察**（position = "观察" / "空仓"）的标的：

**只有满足以下条件之一才值得汇报：**
1. 过去24h 新闻条数 ≥ 3 条（异常关注度）
2. 情绪出现明显偏向（正面/负面，非中性）
3. 价格变动 ≥ 3%（当日）
4. 出现投资论点中定义的催化剂关键词

```markdown
## 观察池动态

### 有信号标的

**[公司名] ([TICKER])** — [触发原因，1句话]
- 新闻信号：[X条，情绪偏向]
- 价格：$XX.XX（+X.X%）｜ 52周位置 XX%ile
- 当前 PE：XX.X（vs 历史中位 XX.X，偏[贵/便宜] XX%）
- 论点进展：[催化剂是否出现 / 关键数据是否披露]
- **行动建议：** [建立观察仓 / 等待回调至$XX建仓 / 无行动]

### 无信号标的（简表）

| 标的 | 今日情绪 | 价格(%变化) | 状态 |
|---|---|---|---|
| [TICKER] | 中性 | $XX(+/-X%) | 无变化 |
```

---

### Step 5：催化剂日历（未来 2 周）

汇总所有观察标的的已知催化剂事件，用 Tripwire 逻辑标注：

```markdown
## 催化剂日历 — 未来 14 天

| 日期 | 标的 | 事件类型 | 预期影响 | 论点影响 | 行动预案 |
|---|---|---|---|---|---|
| MM/DD | [TICKER] | 财报 Q4 | +中性 | 支柱1检验 | 超预期→加仓；低于预期→减仓 |
| MM/DD | [TICKER] | 产品发布 | +偏正面 | 支柱2催化 | 发布→维持；取消→止损 |
| MM/DD | 宏观 | FOMC 会议 | 不确定 | 宏观框架 | 降息→增配成长；暂停→无操作 |

> 催化剂评级：🔑 = 论点关键（不符合则止损）｜ ⭐ = 重要（但非决定性）｜ 📝 = 关注（信息收集）
```

---

### Step 6：当日行动清单

日报核心输出，必须可以直接拍板执行：

```markdown
## ✅ 当日行动清单

> 行动优先级：🔴 立即执行 → 🟡 今日确认 → 🟢 本周追踪

| 优先级 | 标的 | 行动 | 数量/比例 | 价格条件 | 触发依据 |
|---|---|---|---|---|---|
| 🔴 | [TICKER] | 止损卖出 | 全仓 | 市价 | Risk Tripwire 触发：[条件] |
| 🟡 | [TICKER] | 观察加仓 | +X% 仓位 | 回调至 $XX | 论点分 XX，等待价格确认 |
| 🟢 | [TICKER] | 建立跟踪 | 观察仓 5% | — | 催化剂出现：[描述] |
| — | 全组合 | 无操作 | — | — | 宏观绿色，持仓论点健康 |

**今日无行动理由（如适用）：**
[若今日无操作，1-2句说明原因，避免无缘由的"维持不变"]
```

---

### Step 7：输出与存档

**输出格式与文件命名：**
```
文件路径：11.投资机会跟踪报告/daily_reports/
文件名：YYYY-MM-DD-buyside-daily-[HHmm].md
示例：2026-02-26-buyside-daily-0900.md
```

**与 stock_tracker.py 原料的关系：**
- 本报告是原料的**升级版**，不替代原料文件
- 原料文件已含新闻爬取详情（保留原文链接供回溯）
- 本报告提炼决策层信息，引用原料文件的关键线索时注明 "↗ 原料文件第 N 行"

**报告节信号图例（每份日报末尾必须附）：**
```
图例：
🟢 正常/维持   🟡 关注/黄色预警   🔴 警报/减仓/止损
✅ 论点强化    ⚠️ 论点动摇       ❌ 论点破坏
🔑 关键催化剂  ⭐ 重要事件       📝 信息跟踪
```

---

## 重要说明（Important Notes）

### 买方与卖方日报的核心差异

| 维度 | 卖方晨报 | **本技能（买方日报）** |
|---|---|---|
| 读者 | PM / 交易员 | **自己就是 PM** |
| 内容重心 | 行情解读 + trade idea | **持仓论点跟踪 + 止损/加仓决策** |
| 估值 | 相对估值 / 共识 PT | **绝对估值 + 论点对应的隐含价值** |
| 时效 | 盘前快速发布 | **随时可生成，聚焦近期催化剂窗口** |
| 行动 | 建议（给客户） | **直接执行指令（自己的仓位）** |

### 使用原则

1. **论点先于价格** — 仓位信号的依据是论点健康度，不是单日涨跌幅
2. **Tripwire 优先** — Risk Tripwire 触发必须立即执行，不允许"再观察一天"
3. **无新闻非理由** — "今日无新闻"不等于"无需操作"；需主动检查催化剂进度
4. **宏观框架统领** — 宏观信号 RED 时，个股论点的权重降低，系统性风险控制优先
5. **日报即备忘录** — 每份日报必须可以独立阅读，不依赖上一份日报的上下文
6. **诚实面对不确定性** — 不确定的数据必须标 N/A，不允许用估计值填充实际数字位置
7. **简洁胜于全面** — 日报不是研报，不需要覆盖所有内容；只覆盖**今天有变化的内容**

### 与其他技能的协作

- 发现新的高评分标的 → 触发 `@分析` 深度研究
- 需要重新测估值 → 触发 `@估值` 三重估值工作流
- 论点发生重大变化 → 触发 `@打分` 更新 Q-G-P-R 分数
- 整周持仓无变化但宏观发出预警 → 触发 `@宏观` 周期定位
- 标的触发 Kill-Switch → 触发 `@陷阱` 全面检查

---

## 附录：Python 数据拉取模板

以下代码块可直接在工作区 Python 环境中执行：

```python
#!/usr/bin/env python
"""
buyside_daily_data.py — 买方日报数据拉取模板
"""
import json
import yfinance as yf
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
WATCHLIST_PATH = ROOT / "11.投资机会跟踪报告" / "ideas_watchlist.json"
REPORT_DIR = ROOT / "11.投资机会跟踪报告" / "daily_reports"

def load_watchlist():
    with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_price_snapshot(tickers: list[str]) -> dict:
    """批量拉取价格快照 — 收盘价、52周高低、PE、PB"""
    result = {}
    for t in tickers:
        try:
            info = yf.Ticker(t).info
            hist = yf.Ticker(t).history(period="52wk")
            w52_low = hist["Close"].min()
            w52_high = hist["Close"].max()
            cur = info.get("currentPrice") or info.get("regularMarketPrice")
            pct_52w = (cur - w52_low) / (w52_high - w52_low) * 100 if cur else None
            result[t] = {
                "price": cur,
                "pct_52w_percentile": round(pct_52w, 1) if pct_52w else "N/A",
                "pe_ttm": info.get("trailingPE"),
                "pb": info.get("priceToBook"),
                "ev_ebitda": info.get("enterpriseToEbitda"),
                "target_mean": info.get("targetMeanPrice"),
                "data_date": datetime.now().strftime("%Y-%m-%d"),
            }
        except Exception as e:
            result[t] = {"error": str(e)}
    return result

def locate_latest_tracker_report() -> Path | None:
    """定位最新的 stock_tracker 原料文件"""
    reports = sorted(REPORT_DIR.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-investment-idea-tracking-report.md"))
    return reports[-1] if reports else None

if __name__ == "__main__":
    wl = load_watchlist()
    # 提取所有有 ticker 的标的
    tickers = [
        idea["ticker"] for idea in wl.get("ideas", [])
        if idea.get("ticker") and idea.get("market") in ("US", "HK")
    ]
    print(f"拉取 {len(tickers)} 个标的的价格快照...")
    snapshot = get_price_snapshot(tickers)
    for t, d in snapshot.items():
        print(f"{t}: {d}")

    latest = locate_latest_tracker_report()
    print(f"\n最新原料文件：{latest}")
```

---

*Buyside Daily Monitor Skill v1.0 — 买方日报 × 论点健康度 × Risk Tripwire × 机构标准*
