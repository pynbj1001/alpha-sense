import json
import yfinance as yf
from pathlib import Path
from datetime import datetime
import requests
import time
import re

ROOT = Path(r"c:\Users\pynbj\OneDrive\1.积累要看的文件\1. 投资框架")
WATCHLIST_PATH = ROOT / "11.投资机会跟踪报告" / "ideas_watchlist.json"
REPORT_DIR = ROOT / "11.投资机会跟踪报告" / "daily_reports"

def load_watchlist():
    with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def to_tencent_code(symbol: str) -> str:
    """Convert standard symbol to Tencent API format"""
    s = symbol.strip().lower()
    if s.endswith(".hk"):
        return f"hk{s[:-3].zfill(5)}"
    elif s.endswith(".sz"):
        return f"sz{s[:-3]}"
    elif s.endswith(".ss") or s.endswith(".sh"):
        return f"sh{s[:-3]}"
    else:
        # Assuming US stock
        return f"us{s.replace('.us', '').upper()}"

def safe_float(val):
    try:
        if not val or val == "N/A": return None
        return float(val)
    except Exception:
        return None

def fetch_tencent_batch(codes: list[str]) -> dict:
    """Fetch quotes in batch using Tencent API (extremely fast and stable)"""
    if not codes:
        return {}
    
    url = f"http://qt.gtimg.cn/q={','.join(codes)}"
    try:
        resp = requests.get(url, timeout=5)
        resp.encoding = 'gbk'
        lines = resp.text.strip().split('\n')
        
        results = {}
        for line in lines:
            if not line: continue
            parts = line.split('=')
            if len(parts) < 2: continue
            
            raw_code = parts[0].split('_')[1] # e.g. hk00700
            vals = parts[1].replace('"', '').replace(';', '').split('~')
            
            if len(vals) > 40:
                results[raw_code] = {
                    "price": safe_float(vals[3]),
                    "pe_ttm": safe_float(vals[39]) if len(vals) > 39 else None,
                    "pb": safe_float(vals[46]) if len(vals) > 46 else None,
                    "market_cap": safe_float(vals[45]) if len(vals) > 45 else None,
                    "name": vals[1]
                }
        return results
    except Exception as e:
        print(f"Tencent API error: {e}")
        return {}

def get_price_snapshot(tickers: list[str]) -> dict:
    result = {}
    
    # 1. First Pass: Fetch all prices and valuation dynamically using pure Tencent API
    tc_codes = [to_tencent_code(t) for t in tickers]
    print(f"--> Pinging Tencent Finance API for {len(tc_codes)} symbols...")
    tc_data = fetch_tencent_batch(tc_codes)
    
    # 2. Second Pass: Enhance with 52-week data using yfinance (bypassing the extremely slow .info hook)
    for t in tickers:
        print(f"  --> Processing {t} ...")
        tc_key = to_tencent_code(t)
        base_data = tc_data.get(tc_key, {})
        
        cur_price = base_data.get("price")
        pe_ttm = base_data.get("pe_ttm")
        pb = base_data.get("pb")
        
        try:
            # Handle HK tickers for yfinance
            if ".hk" in t.lower():
                yf_ticker = t.upper()
                if not yf_ticker.startswith("0") and len(yf_ticker) == 7: # e.g. 1816.HK
                    yf_ticker = "0" + yf_ticker
            else:
                yf_ticker = t.upper()
                
            # Only pull history to avoid .info timeouts
            hist = yf.Ticker(yf_ticker).history(period="52wk")
            
            if hist.empty:
                result[t] = {
                    "price": cur_price,
                    "pct_52w_percentile": "N/A",
                    "pe_ttm": pe_ttm,
                    "pb": pb,
                    "ev_ebitda": "N/A",
                    "target_mean": "N/A",
                    "data_date": datetime.now().strftime("%Y-%m-%d"),
                }
                continue
               
            w52_low = hist["Close"].min()
            w52_high = hist["Close"].max()
            
            # fallback to history latest if Tencent missed
            if cur_price is None:
                cur_price = hist["Close"].iloc[-1]
                
            pct_52w = (cur_price - w52_low) / (w52_high - w52_low) * 100 if cur_price and w52_high > w52_low else None
            
            result[t] = {
                "price": cur_price,
                "pct_52w_percentile": round(pct_52w, 1) if pct_52w else "N/A",
                "pe_ttm": pe_ttm,
                "pb": pb,
                "ev_ebitda": "N/A", # info endpoint is disabled for speed, omitted ev_ebitda
                "target_mean": "N/A",
                "data_date": datetime.now().strftime("%Y-%m-%d"),
            }
        except Exception as e:
            result[t] = {
                "price": cur_price,
                "pe_ttm": pe_ttm,
                "error": str(e),
                "data_date": datetime.now().strftime("%Y-%m-%d")
            }
            
    return result

def locate_latest_tracker_report() -> Path | None:
    reports = sorted(REPORT_DIR.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-investment-idea-tracking-report.md"))
    return reports[-1] if reports else None

if __name__ == "__main__":
    wl = load_watchlist()
    tickers = [
        idea["symbol"] for idea in wl.get("ideas", [])
        if idea.get("symbol") and idea.get("market") in ("US", "HK")
    ]
    print(f"开始执行双网关极速拉取 {len(tickers)} 个核心标的价格与估值快照...")
    
    start_time = time.time()
    snapshot = get_price_snapshot(tickers)
    
    with open(ROOT / "11.投资机会跟踪报告" / "snapshot_dump.json", "w", encoding="utf-8") as f:
         json.dump(snapshot, f, indent=2, ensure_ascii=False)
         
    latest = locate_latest_tracker_report()
    print(f"\n✅ 极速快照拉取完成! 耗时: {time.time() - start_time:.2f} 秒")
    print(f"最新原料文件：{latest}")
    print("Snapshot saved to snapshot_dump.json")
