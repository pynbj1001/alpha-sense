#!/usr/bin/env python
"""
buyside_daily_full.py — 生成买方日报完整数据
"""
import json
import requests
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
WATCHLIST_PATH = ROOT / "11.投资机会跟踪报告" / "ideas_watchlist.json"

def fetch_stooq_price(symbol: str) -> dict:
    """从 Stooq 获取价格数据"""
    try:
        url = f"https://stooq.com/q/l/?s={symbol.lower()}.us&f=sd2t2ohlcvn&e=csv"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        text = r.text.strip()
        if not text or "No data" in text:
            return None
        row = text.split('\n')[1].split(',')
        if len(row) < 9:
            return None
        price = float(row[6]) if row[6] else None
        return {
            "price": price,
            "name": row[8],
            "date": row[1],
        }
    except Exception as e:
        return {"error": str(e)}

def load_watchlist():
    with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

if __name__ == "__main__":
    wl = load_watchlist()
    
    # 获取美股标的
    us_stocks = [
        idea for idea in wl.get("ideas", [])
        if idea.get("market") == "US" and idea.get("symbol")
    ]
    
    print("获取 Stooq 价格数据...")
    for stock in us_stocks:
        symbol = stock["symbol"]
        stooq_sym = f"{symbol.lower()}"
        data = fetch_stooq_price(stooq_sym)
        if data:
            print(f"{symbol}: {data}")
        else:
            print(f"{symbol}: 数据获取失败")
