# l5_analysis_mrna.py
import numpy as np
import pandas as pd
from l5_analysis_tool import UnitEconomics, SensitivityAnalysis
from l5_data_manual import MRNA_Data

def mrna_analysis():
    print("="*60)
    print(f"🚀 L5-Grade Analysis: Moderna (MRNA) | ${MRNA_Data.price} | $ {MRNA_Data.market_cap}B Cap")
    print("="*60)
    
    ue = UnitEconomics(currency="USD")
    sens = SensitivityAnalysis()
    
    # ---------------------------------------------------------
    # 1. Unit Economics: The "Cancer Vaccine" (INT) Revolution
    # ---------------------------------------------------------
    # Hypothesis: INT is not a pill, it's a personalized service.
    # LTV per Patient Model
    print("\n[1] UE Model: Individualized Neoantigen Therapy (INT)")
    print("-" * 50)
    print("Assumption: Adjuvant Melanoma / Lung Cancer Setting")
    
    # Key Inputs (Conservative L5 Estimates)
    asp_int = 60000       # Price per course (Competitor Keytruda is ~$150k/yr)
    cogs_int = 4000       # Manufacturing cost (decreasing with AI/Automation)
    gross_margin_int = (asp_int - cogs_int) / asp_int
    
    # "CAC" in Biotech = S&M + R&D Amortization per patient?
    # For simplicity, let's use Sales & Marketing per new patient acquired.
    # High touch sales force needed initially.
    cac_int_initial = 5000 
    
    # Churn? For Adjuvant treatment, it's a fixed duration (e.g. 9 doses / 1 year).
    # So LTV is basically just the One-off Purchase (unless recurrence).
    # But let's look at "Net Margin per Patient".
    
    print(f"  ASP per Patient: ${asp_int:,}")
    print(f"  COGS (Personalized Mfg): ${cogs_int:,}")
    print(f"  Gross Margin: {gross_margin_int:.1%}")
    print(f"  Est. CAC (Sales/Support): ${cac_int_initial:,}")
    print(f"  Contribution per Patient: ${asp_int - cogs_int - cac_int_initial:,}")
    
    # ---------------------------------------------------------
    # 2. Sensitivity Analysis: Peak Sales & Stock Price
    # ---------------------------------------------------------
    # Valuation Model: RISK-ADJUSTED NPV of Pipeline
    print("\n[2] High-Value Sensitivity: Peak Sales vs Probability of Success (PoS)")
    print("-" * 50)
    
    def biotech_pipeline_value(peak_sales_int, pos_int, peak_sales_resp, pos_resp, cash, shares, multiple=3.5):
        # Simple Sum-of-Parts Valuation
        # Value = Cash + (Peak_INT * PoS * Multiple) + (Peak_Resp * PoS * Multiple) - Debt
        # Multiple: Biotech reliable revenue usually trades 3-5x Peak Sales
        val_int = peak_sales_int * pos_int * multiple
        val_resp = peak_sales_resp * pos_resp * multiple 
        total_ev = val_int + val_resp
        equity_val = total_ev + cash - MRNA_Data.debt
        price_per_share = equity_val / shares * 1000 # items in Billions, shares in Millions -> *1000
        return price_per_share

    # Base Case Assumptions (Billions)
    base_int_sales = 5.0      # Conservative INT Peak
    base_pos_int = 0.40       # 40% PoS (Phase 3 risk)
    base_resp_sales = 4.0     # Endemic Covid + Flu + RSV
    base_pos_resp = 0.90      # Approved/High confidence
    
    matrix = sens.run_two_variable_matrix(
        var1_name="peak_sales_int", var1_base=5.0, var1_range=0.5, # $2.5B - $7.5B
        var2_name="pos_int", var2_base=0.40, var2_range=0.5,       # 20% - 60% PoS
        model_func=biotech_pipeline_value,
        # Fixed
        peak_sales_resp=base_resp_sales,
        pos_resp=base_pos_resp,
        cash=MRNA_Data.cash_balance,
        shares=MRNA_Data.shares
    )
    
    print("   Row: INT Peak Sales ($B) | Col: Probability of Success (PoS)")
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    print(matrix.round(1))
    
    # ---------------------------------------------------------
    # 3. Kill-Switch Check
    # ---------------------------------------------------------
    print("\n[3] Kill-Switch Protocol (L5 Risk Check)")
    print("-" * 50)
    
    # 1. Cash Burn vs Runway
    burn_rate_annual = abs(MRNA_Data.revenue - MRNA_Data.rd - MRNA_Data.sga - MRNA_Data.cogs) 
    # Approx Op Loss
    runway_years = MRNA_Data.cash_balance / burn_rate_annual if burn_rate_annual > 0 else 99
    
    print(f"  Cash Balance: ${MRNA_Data.cash_balance:.2f} B")
    print(f"  Est. Annual Burn: ${burn_rate_annual:.2f} B")
    print(f"  Runway: {runway_years:.1f} Years")
    
    if runway_years < 1.5:
        print("  [ALERT] Runway < 1.5 Years -> HIGH RISK (Potential Dilution)")
    else:
        print("  [PASS] Runway > 1.5 Years -> SAFE")
        
    # 2. Valuation Floor (Cash per Share)
    cash_per_share = (MRNA_Data.cash_balance * 1000) / MRNA_Data.shares
    print(f"  Cash per Share: ${cash_per_share:.2f}")
    if MRNA_Data.price < cash_per_share:
        print("  [OPPORTUNITY] Trading BELOW Cash!")
    else:
        premium = (MRNA_Data.price - cash_per_share) / MRNA_Data.price
        print(f"  Pipeline Premium: {premium*100:.1f}%")

if __name__ == "__main__":
    mrna_analysis()
