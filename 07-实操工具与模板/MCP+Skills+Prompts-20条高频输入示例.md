# MCP + Skills + Prompts：20 条高频输入示例（可直接复制）

> 用法：把下面任意一条直接粘贴到 VS Code Chat。
> 建议结构：`任务 + 标的 + 数据源 + 输出格式 + 时间范围`。

---

## A. 路由器 @ 指令（6 条）

1. `@分析 MSFT`
2. `@估值 NVDA`
3. `@护城河 GOOGL`
4. `@打分 META`
5. `@情景 AMZN`
6. `@L6 TSLA`

---

## B. MCP 数据源驱动（7 条）

7. `用 lseg 拉取美债 2Y/10Y/30Y 最新收益率，做牛/基/熊三情景，并输出到 10-研究报告输出。`

8. `用 sp-global 生成 AAPL 的公司 tear sheet：估值、盈利预测、近 8 季关键指标，输出 markdown 表格。`

9. `用 factset 对 MSFT 做可比公司估值（PE/PB/EV-EBITDA），可比对象：AAPL/GOOGL/AMZN/META，附数据日期。`

10. `用 morningstar 拉取 NVDA 过去 5 年财务与估值区间，判断当前估值分位并给出风险提示。`

11. `用 moodys + mtnewswire 汇总美国信用与利差最新变化，给出对成长股估值的影响路径。`

12. `用 pitchbook 视角梳理 AI 应用层赛道近 12 个月融资节奏，输出“赛道热度 + 估值风险”简报。`

13. `用 daloopa 拉取 TSM 的关键财报字段并交叉验证 yfinance 数据，差异超过 10% 的项单独标红。`

---

## C. FSP 工作流模板（7 条）

14. `按 fsp-equity-research-earnings 工作流，做 NVDA 最新季度 earnings update，要求 8-12 页结构和 sources。`

15. `按 fsp-equity-research-earnings-preview 工作流，做 AMD 下季财报前瞻：关键看点、预期差、触发条件。`

16. `按 fsp-financial-analysis-comps 工作流，做 CRM 可比公司分析，输出估值表 + 一句话结论。`

17. `按 fsp-financial-analysis-dcf 工作流，做 ASML DCF，给出核心假设、敏感性和可证伪条件。`

18. `按 fsp-private-equity-unit-economics 工作流，评估 Duolingo 的单位经济学：LTV/CAC、回收周期、风险阈值。`

19. `按 fsp-private-equity-ic-memo 工作流，生成“投资委员会备忘录”模板，标的为 Snowflake。`

20. `按 fsp-wealth-management-portfolio-rebalance 工作流，给出一个中风险美元组合的再平衡方案和执行清单。`

---

## 强化版一句话模板

`用 [数据源/MCP] + [工作流名]，分析 [标的] 在 [时间范围] 的 [问题]，输出为 [markdown表格/备忘录/研报]，并包含 [情景分析/可证伪条件/风险清单]。`
