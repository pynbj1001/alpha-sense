import yfinance as yf
import pandas as pd
import json

def analyze_mrna():
    ticker = yf.Ticker("MRNA")
    
    # helper for safe getting
    def get_info(key, default="N/A"):
        return ticker.info.get(key, default)

    info = ticker.info
    
    print("# MRNA 数据快照")
    print(f"**当前价格:** {get_info('currentPrice')}")
    print(f"**市值:** {get_info('marketCap')}")
    print(f"**PE (Trailing):** {get_info('trailingPE')}")
    print(f"**PE (Forward):** {get_info('forwardPE')}")
    print(f"**PB:** {get_info('priceToBook')}")
    print(f"**PS (Trailing):** {get_info('priceToSalesTrailing12Months')}")
    print(f"**EV/EBITDA:** {get_info('enterpriseToEbitda')}")
    
    print("\n## 质量指标")
    print(f"**ROE:** {get_info('returnOnEquity')}")
    print(f"**毛利率:** {get_info('grossMargins')}")
    print(f"**净利率:** {get_info('profitMargins')}")
    print(f"**Operating Margins:** {get_info('operatingMargins')}")
    print(f"**FCF:** {get_info('freeCashflow')}")
    
    print("\n## 资本结构")
    print(f"**总现金:** {get_info('totalCash')}")
    print(f"**总债务:** {get_info('totalDebt')}")
    if get_info('totalDebt') != "N/A" and get_info('totalCash') != "N/A":
        print(f"**净现金:** {get_info('totalCash') - get_info('totalDebt')}")
    print(f"**债务/权益比:** {get_info('debtToEquity')}")
    print(f"**每股现金:** {get_info('totalCashPerShare')}")
    
    print("\n## 成长指标")
    print(f"**营收增长 (yoy):** {get_info('revenueGrowth')}")
    print(f"**盈利增长 (yoy):** {get_info('earningsGrowth')}")
    
    # Financials
    fin = ticker.financials
    bs = ticker.balance_sheet
    cf = ticker.cashflow

    print("\n## 最近3年营收 (Revenue)")
    try:
        if 'Total Revenue' in fin.index:
            print(fin.loc['Total Revenue'].head(3))
        else:
             print("Key 'Total Revenue' not found in financials index")
    except Exception as e:
        print(f"Error accessing financials: {e}")

    print("\n## 最近3年净利润 (Net Income)")
    try:
        if 'Net Income' in fin.index:
            print(fin.loc['Net Income'].head(3))
        elif 'Net Income Common Stock' in fin.index:
             print(fin.loc['Net Income Common Stock'].head(3))
        else:
             print("Key 'Net Income' not found")
    except Exception as e:
        print(f"Error accessing financials: {e}")

    print("\n## 关键资产负债表数据")
    try:
        if 'Total Assets' in bs.index:
            print("Total Assets:", bs.loc['Total Assets'].head(3))
        if 'Stockholders Equity' in bs.index:
            print("Stockholders Equity:", bs.loc['Stockholders Equity'].head(3))
    except Exception as e:
        print(f"Error accessing balance sheet: {e}")

if __name__ == "__main__":
    analyze_mrna()
