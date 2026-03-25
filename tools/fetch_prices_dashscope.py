#!/usr/bin/env python
"""
fetch_prices_dashscope.py — 使用 DashScope Web Search 获取股票价格数据
"""
import json
import re
from pathlib import Path
from datetime import datetime

try:
    from dashscope import WebSearch
except ImportError:
    print("错误：请先安装 dashscope: pip install dashscope")
    exit(1)

WATCHLIST_PATH = Path("11.投资机会跟踪报告/ideas_watchlist.json")
OUTPUT_PATH = Path("11.投资机会跟踪报告/daily_reports")

def load_watchlist():
    with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def fetch_price_dashscope(symbol: str, market: str) -> dict:
    """使用 DashScope Web Search 获取股票价格"""
    try:
        if market == "US":
            query = f"{symbol} stock price today February 2026 closing price"
        elif market == "HK":
            query = f"{symbol} stock price today February 2026 closing price HKD"
        else:
            return {"error": f"Unsupported market: {market}"}
        
        response = WebSearch.call(query=query, search_resolution="high")
        
        if response.status_code == 200 and response.output:
            results = response.output.get("results", [])
            
            # 解析搜索结果，提取价格信息
            price_data = {
                "symbol": symbol,
                "market": market,
                "search_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "raw_results": []
            }
            
            for result in results[:5]:  # 取前 5 个结果
                title = result.get("title", "")
                snippet = result.get("snippet", "")
                url = result.get("url", "")
                
                # 尝试从 snippet 中提取价格
                price_match = re.search(r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', snippet)
                change_match = re.search(r'([+-]?\d*\.?\d+)%?', snippet)
                
                if price_match:
                    price_str = price_match.group(1).replace(",", "")
                    try:
                        price = float(price_str)
                        price_data["price"] = price
                        price_data["change_pct"] = float(change_match.group(1)) if change_match else None
                        price_data["source"] = title
                        price_data["url"] = url
                        break
                    except ValueError:
                        pass
                
                price_data["raw_results"].append({"title": title, "snippet": snippet, "url": url})
            
            if "price" not in price_data:
                price_data["error"] = "No price found in search results"
            
            return price_data
        else:
            return {"error": f"API Error: {response.status_code}"}
    
    except Exception as e:
        return {"error": str(e)}

def fetch_portfolio_prices():
    """批量获取持仓组合价格"""
    wl = load_watchlist()
    
    stocks = [
        idea for idea in wl.get("ideas", [])
        if idea.get("market") in ("US", "HK") and idea.get("symbol")
    ]
    
    print(f"从 DashScope 获取 {len(stocks)} 个标的价格...\n")
    
    results = {}
    for i, stock in enumerate(stocks):
        symbol = stock["symbol"]
        market = stock["market"]
        print(f"[{i+1}/{len(stocks)}] {symbol} ({market})...", end=" ")
        
        data = fetch_price_dashscope(symbol, market)
        
        if "error" not in data and "price" in data:
            print(f"${data['price']} ({data.get('change_pct', 'N/A')}%)")
        else:
            print(f"错误 - {data.get('error', 'Unknown')}")
        
        results[symbol] = data
    
    # 保存结果
    output_file = OUTPUT_PATH / f"price_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n价格快照已保存至：{output_file}")
    return results

if __name__ == "__main__":
    fetch_portfolio_prices()
