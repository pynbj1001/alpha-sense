#!/usr/bin/env python
"""
fetch_prices_stooq.py — 使用 Stooq 获取价格数据（无限流）
"""
import json
import requests
from pathlib import Path

WATCHLIST_PATH = Path("11.投资机会跟踪报告/ideas_watchlist.json")

def load_watchlist():
    with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def fetch_stooq(symbol: str, market: str) -> dict:
    """从 Stooq 获取价格数据"""
    try:
        if market == "US":
            url = f"https://stooq.com/q/l/?s={symbol.lower()}.us&f=sd2t2ohlcvn&e=csv"
        elif market == "HK":
            url = f"https://stooq.com/q/l/?s={symbol.lower()}.hk&f=sd2t2ohlcvn&e=csv"
        else:
            return {"error": f"Unsupported market: {market}"}
        
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        text = r.text.strip()
        
        if not text or "No data" in text:
            return {"error": "No data"}
        
        lines = text.split('\n')
        if len(lines) < 2:
            return {"error": "Invalid response"}
        
        row = lines[1].split(',')
        if len(row) < 9:
            return {"error": f"Invalid row: {row}"}
        
        price = float(row[6]) if row[6] and row[6] != '0' else None
        volume = float(row[7]) if row[7] else None
        name = row[8]
        date = row[1]
        time_val = row[2]
        
        # 获取 52 周高低
        hist_url = f"https://stooq.com/q/d/l/?s={symbol.lower()}.us&i=d" if market == "US" else f"https://stooq.com/q/d/l/?s={symbol.lower()}.hk&i=d"
        try:
            hist_r = requests.get(hist_url, timeout=10)
            hist_df_text = hist_r.text.strip()
            if hist_df_text and "No data" not in hist_df_text:
                import pandas as pd
                from io import StringIO
                df = pd.read_csv(StringIO(hist_df_text))
                if not df.empty and "Close" in df.columns:
                    w52_high = df["High"].max()
                    w52_low = df["Low"].min()
                    pct_52w = (price - w52_low) / (w52_high - w52_low) * 100 if price else None
                else:
                    w52_high, w52_low, pct_52w = None, None, "N/A"
            else:
                w52_high, w52_low, pct_52w = None, None, "N/A"
        except:
            w52_high, w52_low, pct_52w = None, None, "N/A"
        
        return {
            "price": price,
            "pct_52w": round(pct_52w, 1) if pct_52w else "N/A",
            "name": name,
            "date": date,
            "time": time_val,
            "volume": volume,
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    wl = load_watchlist()
    
    us_stocks = [
        idea for idea in wl.get("ideas", [])
        if idea.get("market") in ("US", "HK") and idea.get("symbol")
    ]
    
    print(f"从 Stooq 获取 {len(us_stocks)} 个标的价格...\n")
    
    results = {}
    for stock in us_stocks:
        symbol = stock["symbol"]
        market = stock["market"]
        print(f"{symbol} ({market})...", end=" ")
        data = fetch_stooq(symbol, market)
        print(data.get("price", data.get("error")))
        results[symbol] = data
    
    print("\n=== 价格汇总 ===")
    for sym, data in results.items():
        if "error" not in data:
            print(f"{sym}: ${data['price']} (52 周：{data['pct_52w']}%ile) - {data['date']}")
        else:
            print(f"{sym}: 错误 - {data['error']}")
