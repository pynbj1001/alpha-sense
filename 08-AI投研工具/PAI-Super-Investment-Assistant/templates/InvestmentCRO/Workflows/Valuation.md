# Valuation Workflow

1. Pull current valuation inputs with timestamp and source.
2. Run at least two valuation methods:
   - Greenwald three-layer valuation
   - PR/PEG style cross-check
3. Stress test key assumptions (growth, margin, discount rate).
4. Output valuation range and margin-of-safety band.
5. Save to `10-研究报告输出/`.
