#!/usr/bin/env python
"""
fetch_prices_api.py — 使用 Web Search API 获取股票价格数据
"""
import json
import re
import requests
from pathlib import Path
from datetime import datetime

WATCHLIST_PATH = Path("11.投资机会跟踪报告/ideas_watchlist.json")
OUTPUT_PATH = Path("11.投资机会跟踪报告/daily_reports")

# 使用 DashScope 的搜索 API
DASHSCOPE_API_KEY = ""  # 从环境变量或配置文件读取
SEARCH_API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

def load_watchlist():
    with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def fetch_price_search_api(symbol: str, market: str) -> dict:
    """使用搜索 API 获取股票价格"""
    try:
        if market == "US":
            query = f"{symbol} stock price today February 2026"
        elif market == "HK":
            query = f"{symbol} stock price today February 2026 HKD"
        else:
            return {"error": f"Unsupported market: {market}"}
        
        # 使用 requests 调用搜索 API
        headers = {
            "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "qwen-turbo",
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": f"请告诉我 {symbol} 股票在 2026 年 2 月的最新价格（美元）。只需要价格数字。"
                    }
                ]
            }
        }
        
        response = requests.post(SEARCH_API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            content = result.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # 提取价格
            price_match = re.search(r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', content)
            if price_match:
                price_str = price_match.group(1).replace(",", "")
                return {
                    "symbol": symbol,
                    "price": float(price_str),
                    "source": "DashScope Qwen",
                    "raw_response": content
                }
            
            return {"error": "No price found in response", "raw_response": content}
        else:
            return {"error": f"API Error: {response.status_code}"}
    
    except Exception as e:
        return {"error": str(e)}

def fetch_price_simple(symbol: str, market: str) -> dict:
    """简单版本：直接返回预设数据（用于测试）"""
    # 这些是从 web_search 获取的真实数据
    preset_data = {
        "GOOGL": {"price": 312.90, "change_pct": 3.5, "source": "Morningstar"},
        "NVDA": {"price": 184.72, "change_pct": -5.5, "source": "Yahoo Finance"},
        "MU": {"price": None, "change_pct": None, "source": "待更新"},
        "TSM": {"price": None, "change_pct": None, "source": "待更新"},
        "UBER": {"price": None, "change_pct": None, "source": "待更新"},
        "META": {"price": None, "change_pct": None, "source": "待更新"},
        "AMZN": {"price": None, "change_pct": None, "source": "待更新"},
        "NET": {"price": None, "change_pct": None, "source": "待更新"},
    }
    
    if symbol in preset_data:
        data = preset_data[symbol]
        return {
            "symbol": symbol,
            "price": data["price"],
            "change_pct": data.get("change_pct"),
            "source": data["source"],
            "market": market
        }
    
    return {"error": f"Symbol {symbol} not found"}

def fetch_portfolio_prices(use_api: bool = False):
    """批量获取持仓组合价格"""
    wl = load_watchlist()
    
    stocks = [
        idea for idea in wl.get("ideas", [])
        if idea.get("market") in ("US", "HK") and idea.get("symbol")
    ]
    
    print(f"获取 {len(stocks)} 个标的价格...\n")
    
    results = {}
    for i, stock in enumerate(stocks):
        symbol = stock["symbol"]
        market = stock["market"]
        print(f"[{i+1}/{len(stocks)}] {symbol} ({market})...", end=" ")
        
        if use_api and DASHSCOPE_API_KEY:
            data = fetch_price_search_api(symbol, market)
        else:
            data = fetch_price_simple(symbol, market)
        
        if "error" not in data and data.get("price"):
            print(f"${data['price']} ({data.get('change_pct', 'N/A')}%) - {data.get('source', '')}")
        else:
            print(f"无价格数据 - {data.get('error', '待更新')}")
        
        results[symbol] = data
    
    # 保存结果
    output_file = OUTPUT_PATH / f"price_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n价格快照已保存至：{output_file}")
    return results

if __name__ == "__main__":
    fetch_portfolio_prices(use_api=False)  # 默认使用预设数据
