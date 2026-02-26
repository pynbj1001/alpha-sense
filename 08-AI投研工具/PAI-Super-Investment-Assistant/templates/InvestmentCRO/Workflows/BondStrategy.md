# BondStrategy Workflow

1. Run data pull first:
   - `python bond_data.py --all`
2. Validate three hard indicators:
   - Yield curve and 10Y-2Y spread
   - Inflation (CPI/core CPI)
   - Policy rates (LPR, liquidity spread)
3. Compute carry/rolldown by tenor where available.
4. Map to duration strategy and risk limits.
5. Save to `10-研究报告输出/`.
