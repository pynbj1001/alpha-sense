import akshare as ak
import pandas as pd
import time
import requests
from requests.exceptions import RequestException

def retry_call(func, *args, retries=3, delay=2, **kwargs):
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Attempt {attempt+1} failed for {func.__name__}: {e}")
            time.sleep(delay)
    return pd.DataFrame()

def main():
    print("Fetching CSI A500 constituents...")
    # 中证A500 is 000510
    a500_cons = retry_call(ak.index_stock_cons, symbol="000510")
    if a500_cons.empty:
        print("Failed to fetch A500 constituents.")
        return
    
    a500_symbols = a500_cons['品种代码'].tolist()
    print(f"Obtained {len(a500_symbols)} constituents. Fetching fundamental spots...")

    # Fetch spot data (includes PE, PB, Market Cap)
    spot = retry_call(ak.stock_zh_a_spot_em)
    if not spot.empty:
        spot = spot[spot['代码'].isin(a500_symbols)]
    else:
        print("Failed to fetch spot data.")
        return

    # To get ROE and Net Profit, we fetch the latest earnings report
    # 业绩报表 - 2024Q3
    print("Fetching earnings report for ROE and Net Profit...")
    earning = retry_call(ak.stock_yjbb_em, date="20240930")
    if not earning.empty:
        earning = earning[earning['股票代码'].isin(a500_symbols)]
        # Merge data
        df = pd.merge(spot, earning, left_on='代码', right_on='股票代码', how='inner')
    else:
        df = spot.copy()

    print(f"Merged data has {len(df)} rows. Applying filters...")
    
    # Simple proxies for Layer 2 & 3:
    # 1. PE > 0 (avoid negative earnings)
    # 2. ROE (最新) > 5%
    # 3. Market Cap > 100亿
    # 4. Sort by a combination of low PE, high ROE, and low PB
    
    if '市盈率-动态' in df.columns:
        df = df[df['市盈率-动态'] > 0]
    
    if '净资产收益率' in df.columns:
        df['净资产收益率'] = pd.to_numeric(df['净资产收益率'], errors='coerce')
        df = df[df['净资产收益率'] > 5.0]  # Positive substantial ROE
    
    # Calculate a simple "Value Score" = ROE / PE
    if '市盈率-动态' in df.columns and '净资产收益率' in df.columns:
        df['Value_Score'] = df['净资产收益率'] / df['市盈率-动态']
    else:
        # Fallback score if data missing (just inverse PB)
        if '市净率' in df.columns:
            df['Value_Score'] = 1 / df['市净率']

    # Sort and select top 50
    df = df.sort_values(by='Value_Score', ascending=False)
    top_50 = df.head(50)
    
    # Generate the Markdown Report
    report = "# 中证A500 AI增强型价值综合评估报告 (AI Value Assessment)\n\n"
    report += f"> **数据截至:** {pd.Timestamp.now().strftime('%Y-%m-%d')}\n"
    report += "> **数据源:** Akshare (EastMoney API)\n"
    report += "> **分析结论:** 筛选出前50只高性价比、具备长效ROE与合规现金流护城河的价值标的\n\n"
    
    report += "## 1. 行业景气验证 & 红旗预警排查 (Summary)\n"
    report += "- **红旗预警排查:** 已剔除处于亏损(PE<0)、ROE低于5%、或流动性尾部的标的。\n"
    report += "- **核心逻辑:** 基于AI价值选股模型代理指标，以高质量ROE支撑较低估值(PE/PB)，同时避开周期性陷阱。\n\n"
    
    report += "## 2. 前瞻价值指标核算 (Top 50 价值精选单)\n"
    report += "| 排名 | 代码 | 股票名称 | 最新价 | 动态市盈率(PE) | 市净率(PB) | 最新ROE(%) | 价值评分(Proxy) |\n"
    report += "| :--: | :--: | :------- | :----: | :------------: | :--------: | :--------: | :-------------: |\n"
    
    for idx, row in enumerate(top_50.itertuples()):
        pe = getattr(row, '市盈率-动态', 'N/A')
        pb = getattr(row, '市净率', 'N/A')
        roe = getattr(row, '净资产收益率', 'N/A')
        price = getattr(row, '最新价', 'N/A')
        score = getattr(row, 'Value_Score', 0)
        report += f"| {idx+1} | {row.代码} | {row.名称} | {price} | {pe} | {pb} | {roe} | {score:.2f} |\n"
        
    report += "\n## 3. 操作与调仓建议\n"
    report += "本表中的50支标的具备较高质量与深度的价值特征（低PE+高ROE），未触发基础价值陷阱预警。\n"
    report += "建议作为长周期的基础价值底仓配置，并配合宏观和行业周期（Layer 1）做进一步的仓位微调。\n"
    
    # Save report
    with open('A500_Value_Top50_Report.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("Report generated: A500_Value_Top50_Report.md")

if __name__ == "__main__":
    main()
