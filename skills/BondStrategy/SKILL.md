---
name: BondStrategy
description: |
  债券策略工作流。处理 @债券 指令。
  执行收益率曲线分析 + Carry/Rolldown计算 + 宏观数据驱动的久期策略判断。
  强制实时拉取数据（bond_data.py），不得用记忆数据。
  输出：久期策略建议（具体年限）+ 最优配置区间 + 止损阈值。
---

# BondStrategy Workflow — 债券策略工作流 v5.0

适用：`@债券`

---

## ⚠️ CRITICAL CONSTRAINTS

❌ **NEVER** 用记忆中的历史利率数字（必须运行 bond_data.py 实时拉取）  
❌ **NEVER** 给出"久期适当降低"这类模糊建议（必须给出具体目标久期年限）  
❌ **NEVER** 省略止损阈值（每个策略必须有具体的利率变动反向确认信号）

**最低交付标准：**
- ✅ 实时利率数据快照（10Y国债 + 期限利差，含日期）
- ✅ Carry + Rolldown 最优久期区间
- ✅ 三情景利率预判（概率之和=100%）
- ✅ 具体久期建议（X年 ± Y年）
- ✅ 止损/反转信号（具体数字阈值）

```
文件命名：10-研究报告输出/[YYYY-MM-DD]-债券策略.md
```

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

   **search_web 央行动态搜索（硬性步骤）：**
   - `search_web("央行 公开市场操作 最新 [month] [year]")` — 央行最新净投放/回笼
   - `search_web("中国利率 债券策略 [month] [year]")` — 市场策略观点
   - → 提取：央行操作方向、市场利率预期变化

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
