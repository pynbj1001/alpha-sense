#!/usr/bin/env python
import json
import yfinance as yf
from pathlib import Path
from datetime import datetime

ROOT = Path(r"c:\Users\pynbj\OneDrive\1.积累要看的文件\1. 投资框架")
WATCHLIST_PATH = ROOT / "11.投资机会跟踪报告" / "ideas_watchlist.json"

def load_watchlist():
    with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_price_snapshot(tickers):
    result = {}
    for t in tickers:
        try:
            ticker_obj = yf.Ticker(t)
            info = ticker_obj.info
            hist = ticker_obj.history(period="52wk")
            if hist.empty:
                result[t] = {"error": "No data"}
                continue
            w52_low = hist["Close"].min()
            w52_high = hist["Close"].max()
            cur = info.get("currentPrice") or info.get("regularMarketPrice") or hist["Close"].iloc[-1]
            pct_52w = (cur - w52_low) / (w52_high - w52_low) * 100 if cur and w52_high != w52_low else None
            
            result[t] = {
                "price": cur,
                "pct_52w_percentile": round(pct_52w, 1) if pct_52w is not None else "N/A",
                "pe_ttm": info.get("trailingPE", "N/A"),
                "pb": info.get("priceToBook", "N/A"),
                "ev_ebitda": info.get("enterpriseToEbitda", "N/A"),
                "target_mean": info.get("targetMeanPrice", "N/A"),
            }
        except Exception as e:
            result[t] = {"error": str(e)}
    return result

if __name__ == "__main__":
    wl = load_watchlist()
    tickers = [
        idea["symbol"] for idea in wl.get("ideas", [])
        if idea.get("symbol") and idea.get("market") in ("US", "HK", "JP")
    ]
    # To avoid long running time, maybe just top ones or what PM owns
    # Print the json to stdout
    snapshot = get_price_snapshot(tickers)
    print(json.dumps(snapshot, indent=2))
