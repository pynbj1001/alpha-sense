#!/usr/bin/env python
"""
fetch_prices.py — 获取持仓价格数据
"""
import json
import time
import yfinance as yf
from pathlib import Path

WATCHLIST_PATH = Path("11.投资机会跟踪报告/ideas_watchlist.json")

def load_watchlist():
    with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def fetch_with_retry(ticker_str, max_retries=3):
    """带重试的价格获取"""
    for i in range(max_retries):
        try:
            ticker = yf.Ticker(ticker_str)
            info = ticker.info
            hist = ticker.history(period="1y")
            
            if not hist.empty:
                w52_low = hist["Close"].min()
                w52_high = hist["Close"].max()
            else:
                w52_low, w52_high = None, None
            
            cur = info.get("regularMarketPrice") or info.get("currentPrice")
            pct_52w = (cur - w52_low) / (w52_high - w52_low) * 100 if cur and w52_low and w52_high else None
            
            return {
                "price": cur,
                "pct_52w": round(pct_52w, 1) if pct_52w else "N/A",
                "pe_ttm": info.get("trailingPE"),
                "pb": info.get("priceToBook"),
                "target_mean": info.get("targetMeanPrice"),
            }
        except Exception as e:
            if i < max_retries - 1:
                print(f"  {ticker_str}: 重试 {i+1}/{max_retries} - {e}")
                time.sleep(3)
            else:
                return {"error": str(e)}
    return {"error": "Max retries"}

if __name__ == "__main__":
    wl = load_watchlist()
    
    us_stocks = [
        idea for idea in wl.get("ideas", [])
        if idea.get("market") == "US" and idea.get("symbol")
    ]
    
    print(f"获取 {len(us_stocks)} 个美股标的价格...\n")
    
    results = {}
    for i, stock in enumerate(us_stocks):
        symbol = stock["symbol"]
        print(f"[{i+1}/{len(us_stocks)}] {symbol}...", end=" ")
        data = fetch_with_retry(symbol)
        print(data)
        results[symbol] = data
        time.sleep(2)  # 避免限流
    
    print("\n=== 汇总 ===")
    for sym, data in results.items():
        if "error" not in data:
            print(f"{sym}: ${data['price']} | PE: {data['pe_ttm']} | PB: {data['pb']} | 52 周：{data['pct_52w']}%ile")
        else:
            print(f"{sym}: 错误 - {data['error']}")
