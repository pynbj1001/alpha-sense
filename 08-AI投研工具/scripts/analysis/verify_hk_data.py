import yfinance as yf
import requests
import json
import logging

logging.basicConfig(level=logging.INFO)

def get_tencent_hk_data(codes):
    # codes formatting: 'hk01816'
    url = f"http://qt.gtimg.cn/q={','.join(codes)}"
    try:
        resp = requests.get(url, timeout=5)
        resp.encoding = 'gbk'
        data = {}
        if resp.status_code == 200:
            lines = resp.text.strip().split('\n')
            for line in lines:
                if not line: continue
                parts = line.split('=')
                code_part = parts[0].split('_')[1] # e.g. hk01816
                vals = parts[1].replace('"', '').replace(';', '').split('~')
                if len(vals) > 40:
                    data[code_part] = {
                        "name": vals[1],
                        "price": float(vals[3]),
                        "pe_ttm": float(vals[39]) if vals[39] else None, # 动态市盈率
                        "pb": float(vals[46]) if vals[46] else None,     # 市净率
                        "market_cap": float(vals[45]) if vals[45] else None # 总市值(亿)
                    }
        return data
    except Exception as e:
        logging.error(f"Tencent API error: {e}")
        return {}

def get_yf_data(ticker):
    try:
        t = yf.Ticker(ticker)
        i = t.info
        return {
            "pe": i.get("trailingPE"),
            "pb": i.get("priceToBook"),
            "roe": i.get("returnOnEquity"),
            "rev_g": i.get("revenueGrowth"),
            "net_g": i.get("earningsGrowth"),
            "ocf": i.get("operatingCashflow"),
            "ni": i.get("netIncomeToCommon"),
            "div": i.get("dividendYield")
        }
    except Exception as e:
        logging.error(f"YK error for {ticker}: {e}")
        return {}

if __name__ == "__main__":
    # Fetch Tencent Data
    tc_data = get_tencent_hk_data(['hk01816', 'hk01072'])
    print("=== TENCENT FINANCE (REAL-TIME QUOTES) ===")
    for k, v in tc_data.items():
        print(f"{k}: Price={v['price']}, PE={v['pe_ttm']}, PB={v['pb']}, MCAP={v['market_cap']}B")
        
    print("\n=== YAHOO FINANCE (FINANCIALS & VALUATION) ===")
    yf_1816 = get_yf_data("1816.HK")
    print("1816.HK:", yf_1816)
    
    yf_1072 = get_yf_data("1072.HK")
    print("1072.HK:", yf_1072)
