import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Optional, Union
import argparse
import sys

# 设置中文字体，防止乱码 (根据系统可能需要调整)
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS'] 
plt.rcParams['axes.unicode_minus'] = False

class UnitEconomics:
    """
    L5级 单体经济模型 (Unit Economics) 计算器
    核心哲学：一笔生意赚不赚钱，不看总量，先看单位。
    支持：
    1. LTV/CAC 模型 (SaaS/互联网/订阅制)
    2. 单店模型 (零售/餐饮/连锁)
    """
    def __init__(self, currency: str = "CNY"):
        self.currency = currency

    def calculate_saas_metrics(self, 
                             arpu: float, 
                             gross_margin: float, 
                             churn_rate: float, 
                             cac: float,
                             expansion_rate: float = 0.0,
                             discount_rate: float = 0.08) -> Dict[str, Union[float, str]]:
        """
        LTV/CAC 模型计算 (考虑折现和净留存)
        
        :param arpu: Average Revenue Per User (月度/年度 ARPU)
        :param gross_margin: 毛利率 (0.0 - 1.0)
        :param churn_rate: 流失率 (0.0 - 1.0)
        :param cac: Customer Acquisition Cost (获客成本)
        :param expansion_rate: 增购/膨胀率 (Upsell/Cross-sell)
        :param discount_rate: 资金成本折现率
        """
        # 净流失率 = 流失率 - 增购率
        net_churn = churn_rate - expansion_rate
        
        # 用户生命周期 (Life Time)
        # 如果 net_churn <= 0 (净留存>100%)，理论上 LT 无限，但在模型中需截断 (例如 10年 或 设置最小流失率)
        effective_churn = max(net_churn, 0.05) # 强制设置最小流失率 5% 以防止除零或无穷大
        lifetime = 1 / effective_churn
        
        # 边际贡献 (Contribution Margin per period)
        contribution = arpu * gross_margin
        
        # LTV 计算 (简单的无穷级数求和公式: Margin / (Churn + Discount))
        # LTV = (ARPU * Gross Margin) / (Net Churn + Discount Rate)
        denominator = effective_churn + discount_rate
        ltv = contribution / denominator if denominator > 0 else 0
        
        ratio = ltv / cac if cac > 0 else 0
        payback_period = cac / contribution if contribution > 0 else float('inf')
        
        # 评级逻辑
        rating = "观察"
        if ratio > 5: rating = "卓越 (L5级)"
        elif ratio > 3: rating = "健康"
        elif ratio < 1: rating = "毁灭价值 (Kill-Switch)"

        return {
            "ARPU": arpu,
            "Gross_Margin": f"{gross_margin:.1%}",
            "Churn_Rate": f"{churn_rate:.1%}",
            "Lifetime_Periods": round(lifetime, 1),
            "LTV": round(ltv, 2),
            "CAC": cac,
            "LTV_CAC_Ratio": round(ratio, 2),
            "Payback_Periods": round(payback_period, 1),
            "Rating": rating
        }

    def calculate_retail_ue(self,
                            aov: float,
                            orders_per_year: float,
                            gross_margin: float,
                            fulfillment_cost: float,
                            marketing_cost_per_order: float,
                            fixed_ops_per_order: float) -> Dict[str, float]:
        """
        单单经济模型 (Unit Economics per Order) - 适用于电商/外卖/履约型业务
        """
        revenue = aov
        cogs = aov * (1 - gross_margin)
        gross_profit = revenue - cogs
        
        contribution_margin_1 = gross_profit - fulfillment_cost # 履约后毛利
        contribution_margin_2 = contribution_margin_1 - marketing_cost_per_order # 营销后毛利
        op_profit_per_order = contribution_margin_2 - fixed_ops_per_order
        
        return {
            "AOV (客单价)": aov,
            "Gross_Profit (毛利)": round(gross_profit, 2),
            "CM1 (履约后毛利)": round(contribution_margin_1, 2),
            "CM2 (营销后毛利)": round(contribution_margin_2, 2),
            "OP_Profit (单单经营利润)": round(op_profit_per_order, 2),
            "UE_Margin (%)": round(op_profit_per_order / aov * 100, 2)
        }

class SensitivityAnalysis:
    """
    L5级 敏感性分析 (Sensitivity Analysis)
    核心哲学：不要告诉我目标价是多少，告诉我当关键假设变动 1% 时，目标价动多少。
    """
    def __init__(self):
        pass

    def run_one_variable_test(self, 
                              base_value: float, 
                              variable_name: str, 
                              model_func, 
                              variation_range: float = 0.2, 
                              steps: int = 10,
                              **kwargs) -> pd.DataFrame:
        """
        单变量敏感性测试 (Spider Plot 数据源)
        :param base_value: 基准值
        :param variation_range: 变动范围 (+/- 20%)
        :param steps: 步长
        :param model_func: 估值/计算函数，接受变量作为输入
        """
        lower_bound = base_value * (1 - variation_range)
        upper_bound = base_value * (1 + variation_range)
        values = np.linspace(lower_bound, upper_bound, steps)
        
        results = []
        for v in values:
            # 复制参数并更新当前变量
            params = kwargs.copy()
            params[variable_name] = v
            output = model_func(**params)
            
            # 假设 model_func 返回 float 或 dict (取 'value' 键)
            target_val = output if isinstance(output, (int, float)) else output.get('Target_Price', 0)
            
            change_pct = (v - base_value) / base_value
            results.append({
                "Variable": variable_name,
                "Input_Value": v,
                "Change_Pct": change_pct,
                "Output_Value": target_val
            })
            
        return pd.DataFrame(results)

    def run_two_variable_matrix(self,
                                var1_name: str, var1_base: float, var1_range: float,
                                var2_name: str, var2_base: float, var2_range: float,
                                model_func,
                                **kwargs) -> pd.DataFrame:
        """
        双变量敏感性矩阵 (Heatmap 数据源)
        """
        steps = 5
        var1_vals = np.linspace(var1_base * (1 - var1_range), var1_base * (1 + var1_range), steps)
        var2_vals = np.linspace(var2_base * (1 - var2_range), var2_base * (1 + var2_range), steps)
        
        matrix = []
        for v1 in var1_vals:
            row = []
            for v2 in var2_vals:
                params = kwargs.copy()
                params[var1_name] = v1
                params[var2_name] = v2
                output = model_func(**params)
                val = output if isinstance(output, (int, float)) else output.get('Target_Price', 0)
                row.append(val)
            matrix.append(row)
            
        df = pd.DataFrame(matrix, index=[round(x, 2) for x in var1_vals], columns=[round(x, 2) for x in var2_vals])
        return df

def dcf_valuation_simplified(fcf_base: float, g_stage1: float, g_stage2: float, wacc: float, terminal_g: float) -> float:
    """
    简易两阶段 DCF 模型用于演示敏感性分析
    """
    # Stage 1: 5 Years
    fcf_sum = 0
    current_fcf = fcf_base
    for i in range(1, 6):
        current_fcf *= (1 + g_stage1)
        fcf_sum += current_fcf / ((1 + wacc) ** i)
        
    # Stage 2: Years 6-10 (Transition)
    for i in range(6, 11):
        current_fcf *= (1 + g_stage2)
        fcf_sum += current_fcf / ((1 + wacc) ** i)
        
    # Terminal Value
    terminal_val = (current_fcf * (1 + terminal_g)) / (wacc - terminal_g)
    terminal_val_discounted = terminal_val / ((1 + wacc) ** 10)
    
    total_value = fcf_sum + terminal_val_discounted
    return total_value # Equity Value (assume no debt for simplicity demo)

def run_demo():
    print("="*60)
    print("🚀 L5 级高价值数据分析演示 (CIO Office Demo)")
    print("="*60)
    
    ue = UnitEconomics()
    sens = SensitivityAnalysis()
    
    # 1. SaaS UE 分析
    print("\n[1] Unit Economics: SaaS Model (LTV/CAC)")
    print("-" * 40)
    # 假设：某企业 ARPU=1000, 毛利=80%, 流失=15%, CAC=3000
    metrics = ue.calculate_saas_metrics(arpu=1000, gross_margin=0.8, churn_rate=0.15, cac=3000)
    for k, v in metrics.items():
        print(f"{k:<20}: {v}")
        
    # 2. 敏感性分析：WACC vs 永续增长率 (g) 对 DCF 估值的影响
    print("\n[2] Sensitivity Matrix: WACC vs Terminal Growth (g)")
    print("-" * 40)
    matrix = sens.run_two_variable_matrix(
        var1_name="wacc", var1_base=0.10, var1_range=0.2,  # WACC 8% - 12%
        var2_name="terminal_g", var2_base=0.03, var2_range=0.5, # g 1.5% - 4.5%
        model_func=dcf_valuation_simplified,
        fcf_base=100, g_stage1=0.15, g_stage2=0.08 # 固定参数
    )
    
    # 打印矩阵
    print("   Row: WACC | Col: Terminal g")
    print(matrix.round(1))
    
    # 热力图可视化提示
    print("\n[Visual Insight]")
    print("矩阵右下角 (Low WACC, High g) 代表乐观情景")
    print("矩阵左上角 (High WACC, Low g) 代表悲观情景")
    print("L5 洞察：若当前股价隐含 wacc=11%, g=4%，则安全边际不足。")

if __name__ == "__main__":
    run_demo()
