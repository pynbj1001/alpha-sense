# -*- coding: utf-8 -*-
"""
债券市场实时数据获取模块（Rolldown计算透明化版）
用于支持可交易级别的债券策略分析

数据来源：akshare（免费开源）
用法：python bond_data.py [--all | --rates | --curve | --macro | --policy]

核心指标：
1. 收益率曲线：中国国债各期限、中美利差
2. 宏观数据：CPI/PPI、LPR、货币供应
3. 政策利率：LPR、MLF

Rolldown计算公式（完全透明）：
1. 使用的曲线期限点：2Y, 5Y, 10Y, 30Y
2. 插值方式：线性插值（假设两点间收益率线性变化）
3. 久期：近似等于债券期限（简化假设，不考虑凸性）
4. 定价公式：Price = FV / (1+y)^n
5. Rolldown = Duration × (y_current - y_after) × HoldingPeriod

静态曲线假设风险：
- 假设持有期间收益率曲线不变
- 实际上曲线可能平移/旋转/蝶形变化
- 因此Rolldown仅为"参考估算"，非精确预测
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
import sys
import io

warnings.filterwarnings("ignore")


class BondMarketData:
    """债券市场数据获取类"""

    def __init__(self):
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.data_cache = {}

    # ==================== Rolldown计算（透明化版） ====================

    def calculate_rolldown_transparent(self, yields_data, holding_months=3):
        """
        透明化计算Rolldown收益

        计算公式披露：
        1. 使用的曲线期限点：2Y, 5Y, 10Y, 30Y
        2. 插值方式：线性插值（假设两点间收益率线性变化）
        3. 久期：近似等于债券期限（简化假设，不考虑凸性）
        4. 定价公式：Price = FV / (1+y)^n
        5. Rolldown = Duration × (y_current - y_after) × (HoldingPeriod / 12)

        Args:
            yields_data: 收益率数据
            holding_months: 持有期（月）

        Returns:
            dict: 包含详细计算步骤的结果
        """
        if yields_data is None:
            return None

        try:
            latest = yields_data["latest"]

            # 步骤1：明确使用的期限点
            tenor_points = [
                ("2Y", 2, latest.get("中国2Y")),
                ("5Y", 5, latest.get("中国5Y")),
                ("10Y", 10, latest.get("中国10Y")),
                ("30Y", 30, latest.get("中国30Y")),
            ]

            results = []

            for i, (name, tenor, yield_current) in enumerate(tenor_points):
                if yield_current is None:
                    continue

                # 步骤2：计算Carry
                carry = yield_current * (holding_months / 12)

                # 步骤3：计算Rolldown
                # 3.1 确定插值目标：滑动到下一个期限点
                rolldown = 0
                calculation_detail = {}

                if i > 0:
                    prev_name, prev_tenor, prev_yield = tenor_points[i - 1]

                    # 3.2 插值方式：线性插值
                    # 假设：经过HoldingPeriod/12年后，收益率从y_current线性变化到y_prev

                    # 时间推移比例
                    time_ratio = (holding_months / 12) / (tenor - prev_tenor)

                    # 插值后的收益率
                    yield_after = (
                        yield_current + (prev_yield - yield_current) * time_ratio
                    )

                    # 3.3 久期：简化假设等于期限（实际应考虑凸性）
                    duration = tenor

                    # 3.4 定价公式推导
                    # Price = FV / (1+y)^n
                    # 对于小变动，dP/P ≈ -D × dy
                    # 因此 Rolldown ≈ Duration × (y_current - y_after)

                    rolldown = (
                        duration
                        * (yield_current - yield_after)
                        / 100
                        * (holding_months / 12)
                        * 100
                    )

                    calculation_detail = {
                        "插值目标": f"{prev_name}({prev_tenor}年)",
                        "插值方式": "线性插值",
                        "时间推移比例": f"{(holding_months / 12):.3f} / {(tenor - prev_tenor)} = {time_ratio:.3f}",
                        "插值后收益率(%)": f"{yield_current:.3f} + ({prev_yield:.3f} - {yield_current:.3f}) × {time_ratio:.3f} = {yield_after:.3f}",
                        "久期假设": f"Duration ≈ {tenor}年（简化，未考虑凸性）",
                        "Rolldown公式": f"Duration × (y_current - y_after) × (HoldingPeriod/12) × 100",
                        "Rolldown计算": f"{tenor} × ({yield_current:.3f} - {yield_after:.3f}) × {holding_months / 12:.3f} × 100 = {rolldown:.3f}%",
                    }
                else:
                    calculation_detail = {
                        "说明": "2Y是曲线最短端，无更短期限可滑动",
                        "Rolldown": "0%（假设曲线不变）",
                    }

                total = carry + rolldown

                results.append(
                    {
                        "期限": name,
                        "当前收益率(%)": round(yield_current, 3),
                        "Carry(%)": round(carry, 3),
                        "Rolldown(%)": round(rolldown, 3),
                        "总收益(%)": round(total, 3),
                        "久期(年)": tenor,
                        "计算详情": calculation_detail,
                    }
                )

            return pd.DataFrame(results), calculation_detail if results else (None, {})

        except Exception as e:
            print(f"计算Carry+Rolldown失败: {e}")
            import traceback

            traceback.print_exc()
            return None, {}

    # ==================== 1. 收益率曲线 ====================

    def get_china_us_yields(self, start_date="20240101"):
        """获取中美国债收益率"""
        try:
            df = ak.bond_zh_us_rate(start_date=start_date)
            if df is not None and len(df) > 0:
                # 重命名列（处理中文编码）
                df.columns = [
                    "日期",
                    "中国2Y",
                    "中国5Y",
                    "中国10Y",
                    "中国30Y",
                    "美国2Y",
                    "美国5Y",
                    "美国10Y",
                    "美国30Y",
                    "中美利差10Y",
                    "中美利差2Y",
                    "美国10Y-2Y",
                    "美国GDP年化",
                ]

                latest = df.iloc[-1]

                # 计算中国曲线利差
                cn_spreads = {
                    "10Y-2Y": float(latest["中国10Y"]) - float(latest["中国2Y"]),
                    "10Y-5Y": float(latest["中国10Y"]) - float(latest["中国5Y"]),
                    "5Y-2Y": float(latest["中国5Y"]) - float(latest["中国2Y"]),
                }

                return {
                    "latest": {
                        "日期": str(latest["日期"]),
                        "中国2Y": float(latest["中国2Y"]),
                        "中国5Y": float(latest["中国5Y"]),
                        "中国10Y": float(latest["中国10Y"]),
                        "中国30Y": float(latest["中国30Y"])
                        if pd.notna(latest["中国30Y"])
                        else None,
                        "美国10Y": float(latest["美国10Y"]),
                        "中美利差10Y": float(latest["中美利差10Y"])
                        if pd.notna(latest["中美利差10Y"])
                        else None,
                    },
                    "cn_spreads": cn_spreads,
                    "history": df.tail(60),
                    "source": "akshare/英为财情",
                    "update_time": self.today,
                }
        except Exception as e:
            print(f"获取中美国债收益率失败: {e}")
        return None

    # ==================== 2. 宏观数据 ====================

    def get_cpi(self, months=24):
        """获取CPI数据"""
        try:
            df = ak.macro_china_cpi_monthly()
            if df is not None and len(df) > 0:
                # 清洗列名
                df.columns = ["品种", "日期", "今值", "预期值", "前值"]
                df = df.tail(months)
                latest = (
                    df[df["今值"].notna()].iloc[-1]
                    if len(df[df["今值"].notna()]) > 0
                    else df.iloc[-1]
                )

                # 计算数据滞后
                latest_date = (
                    pd.to_datetime(latest["日期"]) if pd.notna(latest["日期"]) else None
                )
                today = datetime.now()
                lag_days = (today - latest_date).days if latest_date else None

                return {
                    "latest": {
                        "日期": str(latest["日期"]),
                        "CPI同比(%)": float(latest["今值"])
                        if pd.notna(latest["今值"])
                        else None,
                        "预期": float(latest["预期值"])
                        if pd.notna(latest["预期值"])
                        else None,
                        "前值": float(latest["前值"])
                        if pd.notna(latest["前值"])
                        else None,
                    },
                    "history": df,
                    "数据滞后天数": lag_days,
                    "时效性警告": f"数据滞后{lag_days}天，需结合最新市场动态判断"
                    if lag_days and lag_days > 30
                    else "数据时效性良好",
                    "source": "akshare/英为财情",
                }
        except Exception as e:
            print(f"获取CPI失败: {e}")
        return None

    # ==================== 3. 政策利率 ====================

    def get_lpr(self, months=24):
        """获取LPR"""
        try:
            df = ak.macro_china_lpr()
            if df is not None and len(df) > 0:
                df = df.tail(months)
                latest = df.iloc[-1]
                return {
                    "latest": {
                        "日期": str(latest["TRADE_DATE"]),
                        "LPR_1Y(%)": float(latest["LPR1Y"]),
                        "LPR_5Y(%)": float(latest["LPR5Y"]),
                    },
                    "history": df,
                    "source": "akshare/央行",
                }
        except Exception as e:
            print(f"获取LPR失败: {e}")
        return None

    # ==================== 汇总报告 ====================

    def generate_market_snapshot(self):
        """
        生成债券市场快照报告
        包含Rolldown计算方法透明披露
        """
        lines = []
        lines.append("=" * 60)
        lines.append("📊 债券市场实时数据快照（可交易级别）")
        lines.append(f"⏰ 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)

        # ========== 核心验真指标 ==========
        lines.append("\n" + "🔴" * 20)
        lines.append("【策略验真：3个硬指标】")
        lines.append("🔴" * 20)

        # 1. 收益率曲线
        yields = self.get_china_us_yields()
        if yields:
            lines.append("\n## 1️⃣ 收益率曲线（判断久期策略）")
            lines.append("-" * 40)
            latest = yields["latest"]
            lines.append(f"  📅 日期: {latest['日期']}")
            lines.append(f"  🇨🇳 中国2Y: {latest['中国2Y']:.3f}%")
            lines.append(f"  🇨🇳 中国5Y: {latest['中国5Y']:.3f}%")
            lines.append(f"  🇨🇳 中国10Y: {latest['中国10Y']:.3f}%")
            lines.append(f"  🇨🇳 中国30Y: {latest['中国30Y']:.3f}%")
            lines.append(f"  🇺🇸 美国10Y: {latest['美国10Y']:.3f}%")
            if latest.get("中美利差10Y"):
                lines.append(f"  📉 中美利差10Y: {latest['中美利差10Y']:.0f}bp")

            # 期限利差
            spreads = yields["cn_spreads"]
            lines.append("\n  📊 期限利差（判断曲线形态）:")
            lines.append(f"     10Y-2Y: {spreads['10Y-2Y'] * 100:.1f}bp")
            lines.append(f"     10Y-5Y: {spreads['10Y-5Y'] * 100:.1f}bp")
            lines.append(f"     5Y-2Y:  {spreads['5Y-2Y'] * 100:.1f}bp")

            # Carry + Rolldown（透明化）
            lines.append("\n  📈 Carry+Rolldown（3个月持有期）")
            lines.append("  ============== 计算方法披露 ==============")

            cr_df, calc_detail = self.calculate_rolldown_transparent(yields)
            if cr_df is not None and len(cr_df) > 0:
                # 显示公式
                lines.append("\n  【使用的曲线期限点】: 2Y, 5Y, 10Y, 30Y")
                lines.append("  【插值方式】: 线性插值（假设两点间收益率线性变化）")
                lines.append("  【久期假设】: Duration ≈ 期限（简化，未考虑凸性）")
                lines.append("  【定价公式】: Price = FV / (1+y)^n")
                lines.append(
                    "  【Rolldown公式】: Duration × (y_current - y_after) × (HoldingPeriod/12) × 100"
                )

                lines.append("\n  【静态曲线假设风险】:")
                lines.append("     ⚠️ 假设持有期间收益率曲线不变")
                lines.append("     ⚠️ 实际可能发生曲线平移/旋转/蝶形变化")
                lines.append("     ⚠️ 因此Rolldown为参考估算，非精确预测")

                lines.append("\n  【计算结果（3个月持有）】:")
                for _, row in cr_df.iterrows():
                    lines.append(
                        f"     {row['期限']}: Carry {row['Carry(%)']:.2f}% + Rolldown {row['Rolldown(%)']:.2f}% = 总收益 {row['总收益(%)']:.2f}%"
                    )

                # 显示详细计算示例（以10Y为例）
                if calc_detail:
                    lines.append("\n  【Rolldown计算示例（10Y）】:")
                    for k, v in calc_detail.items():
                        lines.append(f"     {k}: {v}")

        # 2. 通胀数据
        lines.append("\n## 2️⃣ 通胀数据（判断政策空间）")
        lines.append("-" * 40)

        cpi = self.get_cpi()
        if cpi:
            c = cpi["latest"]
            lines.append(f"  📅 CPI日期: {c['日期']}")
            if c.get("CPI同比(%)") is not None:
                lines.append(f"  📊 CPI同比: {c['CPI同比(%)']}%")
            if c.get("前值") is not None:
                lines.append(f"     前值: {c['前值']}%")

            # 时效性警告
            if cpi.get("数据滞后天数"):
                lag = cpi["数据滞后天数"]
                warning = cpi.get("时效性警告", "")
                lines.append(f"\n  ⚠️ 时效性警告: {warning}")

        # 3. 政策利率
        lines.append("\n## 3️⃣ 政策利率（判断货币政策方向）")
        lines.append("-" * 40)

        lpr = self.get_lpr()
        if lpr:
            l = lpr["latest"]
            lines.append(f"  📅 日期: {l['日期']}")
            lines.append(f"  💰 LPR 1年: {l['LPR_1Y(%)']}%")
            lines.append(f"  🏠 LPR 5年: {l['LPR_5Y(%)']}%")

        # ========== 策略含义 ==========
        lines.append("\n" + "=" * 60)
        lines.append("【数据→策略 映射提示】")
        lines.append("=" * 60)

        if yields:
            cn10y = yields["latest"]["中国10Y"]
            spread_10_2 = yields["cn_spreads"]["10Y-2Y"] * 100

            lines.append(f"\n🎯 收益率水平: 10Y国债 {cn10y:.2f}%")
            if cn10y < 2.0:
                lines.append("   → 收益率历史低位，注意估值风险")
            elif cn10y < 2.5:
                lines.append("   → 收益率偏低，牛市可能延续但空间有限")
            elif cn10y < 3.0:
                lines.append("   → 收益率中性，关注边际变化")
            else:
                lines.append("   → 收益率较高，可能存在配置价值")

            lines.append(f"\n🎯 曲线形态: 10Y-2Y利差 {spread_10_2:.0f}bp")
            if spread_10_2 < 30:
                lines.append("   → 曲线平坦，短端性价比可能更优")
            elif spread_10_2 < 60:
                lines.append("   → 曲线正常，可均衡配置")
            else:
                lines.append("   → 曲线陡峭，长端可能有骑乘收益")

        if cpi and cpi["latest"].get("CPI同比(%)") is not None:
            cpi_val = cpi["latest"]["CPI同比(%)"]
            lines.append(f"\n🎯 通胀: CPI {cpi_val}%")
            if cpi_val < 1:
                lines.append("   → 通胀低迷，货币政策有宽松空间")
            elif cpi_val < 3:
                lines.append("   → 通胀温和，政策中性")
            else:
                lines.append("   → 通胀抬头，警惕政策收紧")

        lines.append("\n" + "=" * 60)
        lines.append("数据来源: akshare（英为财情/央行/外汇交易中心）")
        lines.append("⚠️ 以上为参考信息，不构成投资建议")
        lines.append("=" * 60)

        return "\n".join(lines)


def main():
    """命令行入口"""
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    print("正在获取债券市场数据...\n")

    bmd = BondMarketData()

    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg == "--all":
            print(bmd.generate_market_snapshot())
        else:
            print(f"未知参数: {arg}")
            print("可用参数: --all")
    else:
        print(bmd.generate_market_snapshot())


if __name__ == "__main__":
    main()
