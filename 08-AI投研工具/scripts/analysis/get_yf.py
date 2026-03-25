import yfinance as yf
for sym in ['1816.HK', '1072.HK']:
    a = yf.Ticker(sym)
    print(f'{sym}:')
    print(f"  PE: {a.info.get('trailingPE')}")
    print(f"  ROE: {a.info.get('returnOnEquity')}")
    print(f"  RevG: {a.info.get('revenueGrowth')}")
    print(f"  NetG: {a.info.get('earningsGrowth')}")
    print(f"  Div: {a.info.get('dividendYield')}")
    print(f"  PB: {a.info.get('priceToBook')}")
    print(f"  CF: {a.info.get('operatingCashflow')}")
    print(f"  NI: {a.info.get('netIncomeToCommon')}")
