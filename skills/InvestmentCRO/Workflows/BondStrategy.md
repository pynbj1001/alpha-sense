# BondStrategy Workflow — 债券策略工作流

适用：`@债券`

---

## 步骤（数据必须先于结论）

1. **获取实时数据**
   ```bash
   python bond_data.py --all
   python bond_data.py --curve   # 收益率曲线 + Carry/Rolldown
   python bond_data.py --macro   # CPI/PPI/货币供应
   python bond_data.py --policy  # LPR政策利率
   ```

2. **三项硬指标验证**
   - 收益率曲线：10Y国债、期限利差（10Y-2Y）
   - 通胀数据：CPI同比、核心CPI、PPI
   - 政策利率：LPR 1Y/5Y、M2-M1剪刀差

3. **Carry + Rolldown 计算**
   - 各期限"单位DV01收益"
   - 识别最优配置久期区间

4. **久期策略判断**
   - 利率下行预期 → 加长久期
   - 利率上行预期 → 缩短久期或转向浮动
   - 曲线陡峭化 → 做陡（空短端/多长端）

5. **风控边界**
   - DV01（每个基点价值）
   - VaR（99%置信区间最大亏损）
   - 久期上限

6. **存入 `10-研究报告输出/`**
