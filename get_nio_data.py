import yfinance as yf
import pandas as pd
from datetime import datetime

print(f"Current System Date: {datetime.now()}")

try:
    nio = yf.Ticker("NIO")
    
    # 1. Financials
    print("\n--- Quarterly Financials Columns ---")
    if not nio.quarterly_financials.empty:
        print(nio.quarterly_financials.columns.tolist())
        # Try to print latest revenue and net income if available
        try:
            # Note: yfinance financial keys can vary, usually "Total Revenue", "Net Income"
            fin = nio.quarterly_financials
            # Get latest date column
            latest_date = fin.columns[0]
            print(f"\nLatest Data Date: {latest_date}")
            
            # Helper to safely get value
            def get_val(df, key):
                if key in df.index:
                    return df.loc[key, latest_date]
                return "N/A"

            revenue = get_val(fin, "Total Revenue")
            net_income = get_val(fin, "Net Income")
            gross_profit = get_val(fin, "Gross Profit")
            
            print(f"Revenue: {revenue}")
            print(f"Net Income: {net_income}")
            print(f"Gross Profit: {gross_profit}")
            
        except Exception as e:
            print(f"Error parsing financials: {e}")
    else:
        print("No quarterly financials found.")

    # 2. Info
    print("\n--- Market Info ---")
    info = nio.info
    print(f"Current Price: {info.get('currentPrice')}")
    print(f"Market Cap: {info.get('marketCap')}")
    print(f"Forward PE: {info.get('forwardPE')}")
    
    # 3. News
    print("\n--- Latest News ---")
    news = nio.news
    if news:
        for n in news[:5]:
            print(f"Title: {n.get('title')}")
            print(f"Link: {n.get('link')}")
            print(f"Date: {datetime.fromtimestamp(n.get('providerPublishTime', 0))}")
            print("-")
    else:
        print("No news found.")

except Exception as e:
    print(f"Critical Error: {e}")
