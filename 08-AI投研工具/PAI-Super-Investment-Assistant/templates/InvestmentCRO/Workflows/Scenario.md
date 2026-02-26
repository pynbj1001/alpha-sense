# Scenario Workflow

1. Pull latest valuation, growth, and macro inputs with source/date.
2. Build bull/base/bear/black-swan scenarios with explicit probabilities (sum = 100%).
3. For each scenario, define assumptions, TSR decomposition (`g + d + ΔPE`), and trigger signals.
4. Compute expected value and break-even growth (`g*`) with sensitivity checks.
5. Save to `10-研究报告输出/`.
