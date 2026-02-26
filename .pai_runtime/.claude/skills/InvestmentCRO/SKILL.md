---
name: InvestmentCRO
description: Institutional-grade investment research router for this repository. Use for commands like @分析, @估值, @护城河, @行业, @宏观, @十倍, @拐点, @周期, @日志.
---

# InvestmentCRO Skill

This skill is a local PAI overlay for the investment framework repository.

## Non-negotiable Rules

1. Data first. Do not cite financial metrics from memory.
2. Use Python for market data (`yfinance`, `akshare`) and mark source/date.
3. Cross-check key metrics with at least two sources when possible.
4. Express conclusions in probabilities, not absolutes.
5. Every major conclusion requires a pre-mortem check.
6. Save reports in `10-研究报告输出/`.

## Routing

- `@分析 [company]` -> `Workflows/DeepAnalysis.md`
- `@估值 [company]` -> `Workflows/Valuation.md`
- `@护城河 [company]` -> `Workflows/Moat.md`
- `@宏观` or `@周期` -> `Workflows/MacroCycle.md`
- `@债券` -> `Workflows/BondStrategy.md`
- `@日志` -> `Workflows/DecisionLog.md`

## Data Commands

```bash
python stock_tracker.py run-daily --news-limit 8
python bond_data.py --all
python bond_data.py --curve
python bond_data.py --macro
python bond_data.py --policy
```

## Output Standard

- Path: `10-研究报告输出/`
- Filename: `[YYYY-MM-DD]-[类型]-[标的]-[框架].md`
- Include:
  - Executive summary
  - Multi-framework matrix
  - Key assumptions and risks
  - Position/action suggestions
  - Follow-up checklist

## Continuous Memory Files

Updated automatically after each dialogue turn by `InvestmentMemoryUpdate.hook.ts`:

- `skills/InvestmentCRO/USER/GOALS.md`
- `skills/InvestmentCRO/USER/THOUGHTS.md`
- `skills/InvestmentCRO/USER/PREFERENCES.md`
- `skills/InvestmentCRO/USER/EXPERIENCE.md`
