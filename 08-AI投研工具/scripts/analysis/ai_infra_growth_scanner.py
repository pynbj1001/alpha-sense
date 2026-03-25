import akshare as ak
import pandas as pd
import time
import os

# Disable proxy for akshare to avoid Eastmoney connection issues
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''

def retry_call(func, *args, retries=5, delay=3, **kwargs):
    for attempt in range(retries):
        try:
            df = func(*args, **kwargs)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            time.sleep(delay)
    return pd.DataFrame()

def main():
    print("Fetching constituents for AI Infrastructure sectors...")
    boards_concept = ["液冷概念", "光通信模块"]
    boards_industry = ["电力行业", "电网设备"]
    
    symbols_info = []
    
    # Fetch Concept Boards
    for board in boards_concept:
        print(f"Fetching {board}...")
        df = retry_call(ak.stock_board_concept_cons_em, symbol=board)
        if not df.empty:
            df['Sector'] = board
            symbols_info.append(df[['代码', '名称', 'Sector']])
        else:
            print(f"Failed to fetch {board}")
            
    # Fetch Industry Boards 
    for board in boards_industry:
        print(f"Fetching {board}...")
        df = retry_call(ak.stock_board_industry_cons_em, symbol=board)
        if not df.empty:
            df['Sector'] = board
            symbols_info.append(df[['代码', '名称', 'Sector']])
        else:
            print(f"Failed to fetch {board}")

    if not symbols_info:
        print("Failed to fetch symbols for any board.")
        return
        
    all_symbols_df = pd.concat(symbols_info).drop_duplicates(subset=['代码'])
    print(f"Total unique symbols identified across sectors: {len(all_symbols_df)}")

    # Fetch spot data for PE and Market Cap
    print("Fetching current spot market data...")
    spot = retry_call(ak.stock_zh_a_spot_em)
    if not spot.empty:
        spot = spot[['代码', '最新价', '市盈率-动态', '总市值']]
        all_symbols_df = pd.merge(all_symbols_df, spot, on='代码', how='left')

    # Fetch latest earnings report (2024Q3)
    print("Fetching earnings report (yjbb) for Growth metrics...")
    earning = retry_call(ak.stock_yjbb_em, date="20240930")
    if earning.empty:
        print("Failed to fetch earnings report.")
        return

    # Merge data
    earning = earning.rename(columns={'股票代码': '代码'})
    df = pd.merge(all_symbols_df, earning[['代码', '营业收入-同比增长', '净利润-同比增长', '净资产收益率', '每股收益']], on='代码', how='inner')
    
    print(f"Merged data has {len(df)} rows. Applying AI Growth Filters...")

    # Data Type Casting
    df['市盈率-动态'] = pd.to_numeric(df['市盈率-动态'], errors='coerce')
    df['总市值'] = pd.to_numeric(df['总市值'], errors='coerce')
    df['营业收入-同比增长'] = pd.to_numeric(df['营业收入-同比增长'], errors='coerce')
    df['净利润-同比增长'] = pd.to_numeric(df['净利润-同比增长'], errors='coerce')
    df['净资产收益率'] = pd.to_numeric(df['净资产收益率'], errors='coerce')
    df['每股收益'] = pd.to_numeric(df['每股收益'], errors='coerce')

    # Absolute Exclusions (Red Flags from AI Growth System)
    df = df[df['净利润-同比增长'].notna() & df['营业收入-同比增长'].notna()]
    df = df[df['净利润-同比增长'] > 0] # Must have positive net profit growth
    df = df[df['每股收益'] > 0] # Must be profitable
    df = df[df['市盈率-动态'] > 0] # Filter out negative PE
    df = df[df['市盈率-动态'] < 120] # Avoid ridiculous valuations (relaxed for high growth tech)
    
    # Calculate Custom AI Growth Accelerations (Approximations)
    # PEG Proxy: PE / Net Profit YoY Growth
    df['PEG_Proxy'] = df['市盈率-动态'] / df['净利润-同比增长'].clip(lower=1)
    
    # Volume/Price Proxy: Net Profit Growth > Revenue Growth (Margin Expansion)
    df['Margin_Expansion'] = df['净利润-同比增长'] - df['营业收入-同比增长']

    def calculate_growth_score(row):
        score = 40 # Base
        
        # 1. Growth Magnitude
        rev_g = row['营业收入-同比增长']
        profit_g = row['净利润-同比增长']
        
        score += min(max(rev_g, 0) * 0.4, 15)
        score += min(max(profit_g, 0) * 0.3, 20)
        
        # 2. Quality of Growth (Margin Expansion)
        margin_exp = row['Margin_Expansion']
        if margin_exp > 0:
            score += min(margin_exp * 0.5, 15) # Up to 15 points for margin expansion (量价齐升 proxy)
        else:
            score -= min(abs(margin_exp) * 0.2, 5) # Penalize margin contraction
            
        # 3. ROE
        roe = row['净资产收益率']
        if pd.notna(roe) and roe > 10:
            score += 15
        elif pd.notna(roe) and roe > 5:
            score += 5
        elif pd.notna(roe) and roe < 3:
            score -= 10
            
        # 4. Valuation Penalty
        peg = row['PEG_Proxy']
        if peg > 3:
            score -= 15
        elif peg < 1:
            score += 10 # Undervalued growth
            
        return min(max(score, 0), 100)
        
    df['AI_Growth_Score'] = df.apply(calculate_growth_score, axis=1)
    
    # Sort and group by sectors
    df = df.sort_values(by=['Sector', 'AI_Growth_Score'], ascending=[True, False])
    
    # Generate the Markdown Report
    timestamp = pd.Timestamp.now()
    report = f"# AI大帝核心配套基建 选股精选池 (AI Infra Growth Screening)\n\n"
    report += f"> **筛选系统:** `AI成长100选股系统_SKILL.md` (定制化精简运行)\n"
    report += f"> **赛道聚焦:** 液冷散热、光通信模块、电力设备与电网\n"
    report += f"> **底层逻辑:** 全球科技巨头资本开支向基础设施集中，寻找配套资源“卖铲人”\n"
    report += f"> **数据截至:** {timestamp.strftime('%Y-%m-%d')} (最新动态行情 & 24Q3业绩)\n"
    report += f"> **评价因子权重:** 营收与利润绝对增速(35%)、利润率扩张/量价齐升Proxy(15%)、ROE质量(15%)、PEG估值容错度(降权/加分项)\n\n"
    
    sectors = df['Sector'].unique()
    
    for sec in sectors:
        # Top 15 per sector based on AI Growth Score
        sec_df = df[df['Sector'] == sec].head(15)
        report += f"## 赛道：{sec} (Top 15 高胜率/赔率标的)\n\n"
        report += "| 评级 | 代码 | 简称 | 营收增速(YOY) | 净利增速(YOY) | 动态PE | PEG代理 | ROE(%) | 【AI成长总分】 |\n"
        report += "|:---:|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|\n"
        
        for idx, row in enumerate(sec_df.itertuples()):
            score = getattr(row, 'AI_Growth_Score', 0)
            if score >= 85: rating = 'S'
            elif score >= 75: rating = 'A'
            elif score >= 60: rating = 'B+'
            else: rating = 'B'
            
            # Format numbers
            rev_g = f"{getattr(row, '营业收入-同比增长', 0):.1f}%"
            prof_g = f"{getattr(row, '净利润-同比增长', 0):.1f}%"
            pe = f"{getattr(row, '市盈率-动态', 0):.1f}"
            peg = f"{getattr(row, 'PEG_Proxy', 0):.2f}"
            roe = f"{getattr(row, '净资产收益率', 0):.1f}%"
            
            # Identify Margin Expansion (利润率红利)
            margin = getattr(row, 'Margin_Expansion', 0)
            star = "🔥" if margin > 15 else ("⭐" if margin > 5 else "")
            
            report += f"| {rating} | {row.代码} | {row.名称} {star} | {rev_g} | {prof_g} | {pe} | {peg} | {roe} | **{score:.1f}** |\n"
        
        report += "\n> 标识说明: 🔥表示利润增速远超营收增速(爆米花效应)；⭐表示利润增速大于营收增速(良性扩张)。\n\n"
        
    report += "---\n"
    report += "### 💡 调仓建言与行动 (CIO Notes)\n"
    report += "- **光通信模块：** 全网算力放量的直接印金机。当前如果动态估值(PE)被高增速迅速消化、PEG处于1.0附近或以下，处于绝佳的“双击”买点。优先配置有海外直供能力的龙头。\n"
    report += "- **液冷散热：** B系列芯片功耗墙倒逼液冷全面渗透。优选🔥标的，这类公司通常已经度过了研发定型期，开始进入利润兑现和良率提升的甜蜜期。\n"
    report += "- **电力行业与电网设备：** 算力的物理尽头是电力。此类标的通常具备公用事业的收息底座，叠加特高压或微电网的新增量。寻找ROE>10%且估值尚未狂热的价值明珠。\n"

    out_path = 'C:/Users/pynbj/OneDrive/1.积累要看的文件/1. 投资框架/10-研究报告输出/AI大帝配套_基建设施选股报告.md'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(report)
        
    print(f"Report successfully written to {out_path}")

if __name__ == "__main__":
    main()
