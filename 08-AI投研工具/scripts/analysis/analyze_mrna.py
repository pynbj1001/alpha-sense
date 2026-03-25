import yfinance as yf
import pandas as pd
import json

def get_mrna_analysis():
    ticker = yf.Ticker("MRNA")
    
    # helper for safe getting
    def get_info(key, default="N/A"):
        return ticker.info.get(key, default)

    info = ticker.info
    
    print("--- 基础数据快照 ---")
    print(f"当前价格: {get_info('currentPrice')}")
    print(f"市值: {get_info('marketCap')}")
    print(f"PE (Trailing): {get_info('trailingPE')}")
    print(f"PE (Forward): {get_info('forwardPE')}")
    print(f"PB: {get_info('priceToBook')}")
    print(f"PS (Trailing): {get_info('priceToSalesTrailing12Months')}")
    print(f"EV/EBITDA: {get_info('enterpriseToEbitda')}")
    
    print("\n--- 质量指标 ---")
    print(f"ROE: {get_info('returnOnEquity')}")
    print(f"ROASH: {get_info('returnOnAssets')}")
    print(f"毛利率: {get_info('grossMargins')}")
    print(f"净利率: {get_info('profitMargins')}")
    print(f"自由现金流 (FCF): {get_info('freeCashflow')}")
    
    print("\n--- 资本结构 ---")
    print(f"总现金: {get_info('totalCash')}")
    print(f"总债务: {get_info('totalDebt')}")
    print(f"债务/权益比: {get_info('debtToEquity')}")
    print(f"每股现金: {get_info('totalCashPerShare')}")
    
    print("\n--- 成长指标 ---")
    print(f"营收增长 (yoy): {get_info('revenueGrowth')}")
    print(f"盈利增长 (yoy): {get_info('earningsGrowth')}")
    
    financials = ticker.financials
    balance_sheet = ticker.balance_sheet
    cashflow = ticker.cashflow

    print("\n--- 财务报表摘要 (最近3年) ---")
    if not financials.empty:
        print("营收:\n", financials.loc['Total Revenue'].head(3))
        try:
             print("净利润:\n", financials.loc['Net Income'].head(3))
        except:
             print("净利润(Net Income Common Stock):\n", financials.loc['Net Income Common Stock'].head(3))

    if not balance_sheet.empty:
        print("总资产:\n", balance_sheet.loc['Total Assets'].head(3))
        print("股东权益:\n", balance_sheet.loc['Stockholders Equity'].head(3))
    
    print("\n--- 分析师预期 ---")
    print(f"目标价平均: {get_info('targetMeanPrice')}")
    print(f"评级: {get_info('recommendationKey')}")

if __name__ == "__main__":
    get_mrna_analysis()
