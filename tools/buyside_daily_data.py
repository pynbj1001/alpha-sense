#!/usr/bin/env python
"""
buyside_daily_data.py — 买方日报数据拉取模板
"""
import json
import yfinance as yf
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
WATCHLIST_PATH = ROOT / "11.投资机会跟踪报告" / "ideas_watchlist.json"
REPORT_DIR = ROOT / "11.投资机会跟踪报告" / "daily_reports"

def load_watchlist():
    with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_price_snapshot(tickers: list) -> dict:
    """批量拉取价格快照 — 收盘价、52 周高低、PE、PB"""
    result = {}
    for t in tickers:
        try:
            info = yf.Ticker(t).info
            hist = yf.Ticker(t).history(period="52wk")
            w52_low = hist["Close"].min()
            w52_high = hist["Close"].max()
            cur = info.get("currentPrice") or info.get("regularMarketPrice")
            pct_52w = (cur - w52_low) / (w52_high - w52_low) * 100 if cur else None
            result[t] = {
                "price": cur,
                "pct_52w_percentile": round(pct_52w, 1) if pct_52w else "N/A",
                "pe_ttm": info.get("trailingPE"),
                "pb": info.get("priceToBook"),
                "ev_ebitda": info.get("enterpriseToEbitda"),
                "target_mean": info.get("targetMeanPrice"),
                "data_date": datetime.now().strftime("%Y-%m-%d"),
            }
        except Exception as e:
            result[t] = {"error": str(e)}
    return result

def locate_latest_tracker_report() -> Path:
    """定位最新的 stock_tracker 原料文件"""
    reports = sorted(REPORT_DIR.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-investment-idea-tracking-report.md"))
    return reports[-1] if reports else None

if __name__ == "__main__":
    wl = load_watchlist()
    # 提取所有有 ticker 的标的
    tickers = [
        idea["symbol"] for idea in wl.get("ideas", [])
        if idea.get("symbol") and idea.get("market") in ("US", "HK")
    ]
    print(f"拉取 {len(tickers)} 个标的的价格快照...")
    snapshot = get_price_snapshot(tickers)
    for t, d in snapshot.items():
        print(f"{t}: {d}")

    latest = locate_latest_tracker_report()
    print(f"\n最新原料文件：{latest}")
