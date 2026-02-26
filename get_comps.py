import yfinance as yf
import pandas as pd

tickers = ["NIO", "XPEV", "LI"]
print("--- Comparables ---")
for t in tickers:
    tick = yf.Ticker(t)
    info = tick.info
    print(f"[{t}] Price: {info.get('currentPrice')} | Mkt Cap: {info.get('marketCap')} | fwdPE: {info.get('forwardPE')}")
    # Get latest quarterly rev
    try:
        qf = tick.quarterly_financials
        if not qf.empty:
            rev = qf.iloc[0, 0] # Total Revenue, most recent
            print(f"   Latest Q Rev: {rev}")
            last_date = qf.columns[0]
            print(f"   Date: {last_date}")
    except:
        pass
