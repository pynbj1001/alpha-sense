---
name: morning-note
description: 生成“晨会纪要 / Morning Note / Morning Call”一页纸：复盘隔夜与盘前要点、覆盖标的关键新闻与财报快评、当日重要事件日程、可执行的交易想法。用户提到“晨会/早报/晨报/晨会纪要/晨会材料”“morning note/morning call”“隔夜发生了什么/盘前发生了什么”“今天有哪些关键事件/数据/财报”“给我交易想法/今日 top call”时必须触发；输出需紧凑（2分钟可读）、观点明确、可落地，且对关键事实标注来源与时间戳。
---

# Morning Note

## Workflow

### Step 1: Overnight Developments

Scan for relevant events across coverage universe:

**Earnings & Guidance**
- Any coverage companies reporting overnight or pre-market?
- Earnings surprises (beat/miss on revenue, EPS, key metrics)
- Guidance changes (raised, lowered, maintained)

**News & Events**
- M&A announcements or rumors
- Management changes
- Product launches or regulatory decisions
- Analyst upgrades/downgrades from competitors
- Macro data or policy changes affecting the sector

**Market Context**
- Overnight futures / pre-market moves
- Sector ETF performance
- Relevant commodity or currency moves
- Key economic data releases today

### Step 2: Morning Note Format

Keep it tight — a morning note should be readable in 2 minutes:

---

**[Date] Morning Note — [Analyst Name]**
**[Sector Coverage]**

**Executive Summary (≤3 sentences)**
- 1 sentence: what happened
- 1 sentence: why it matters / so what
- 1 sentence: what we do (positioning / watchlist / action)

**Top Call: [Headline — the one thing PMs need to hear]**
- 2-3 sentences on the key development and why it matters
- Stock impact: price target, rating reiteration/change

**Overnight/Pre-Market Developments**
- [Company A]: One-line summary of earnings/news + our take
- [Company B]: One-line summary + our take
- [Sector/Macro]: Relevant sector-wide development

**Key Events Today**
- [Time]: [Company] earnings call
- [Time]: Economic data release (expectations vs. our view)
- [Time]: Conference or investor day

**Trade Ideas** (if any)
- [Long/Short] [Company]: 1-2 sentence thesis + catalyst
- Risk: What would make this wrong

**Sources & Timestamp**
- Written at: [Local time + timezone]
- Key sources: [source list with links or file paths]

---

### Step 3: Quick Takes on Earnings

If a coverage company reported, provide a quick reaction:

| Metric | Consensus | Actual | Beat/Miss |
|--------|-----------|--------|-----------|
| Revenue | | | |
| EPS | | | |
| [Key metric] | | | |
| Guidance | | | |

**Our Take**: 2-3 sentences — is this good or bad for the stock? Does it change our thesis?

**Action**: Maintain / Upgrade / Downgrade rating? Adjust price target?

### Step 4: Output

- Markdown text for email/Slack distribution
- Word document if formal distribution is needed
- Keep to 1 page max — PMs and traders won't read more

## Important Notes

- Be opinionated — morning notes that just summarize news without a view are useless
- Lead with the most important thing — don't bury the headline
- "No news" is a valid morning note — say "nothing material overnight, maintaining positioning"
- Distinguish between actionable events (earnings, M&A) and noise (minor analyst notes, non-events)
- Time-stamp your takes — if you're writing at 6am, note that pre-market may change by open
- If you're wrong, own it in the next morning note — credibility matters more than being right every time

## ✅ 输出质量要求（强制）

- **事实要可追溯**：任何关键事实（财报数值/政策/并购/监管）都要标注来源与时间戳。
- **观点要可执行**：每条“我们的看法”必须对应到“Action/Watch/Do nothing”之一。
- **篇幅硬约束**：默认 1 页内；超出时只保留 Top Call + 今日事件 + 1-2 个最相关标的。
