import yfinance as yf
import pandas as pd
import numpy as np

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

print("="*60)
print("🚀 MRNA L5 Data Extraction")
print("="*60)

try:
    ticker = yf.Ticker("MRNA")
    info = ticker.info
    
    # 1. Basic Stats
    price = info.get('currentPrice', 0)
    if price == 0:
        # Fallback to history for price
        hist = ticker.history(period="1d")
        if not hist.empty:
            price = hist['Close'].iloc[-1]
            
    shares = info.get('sharesOutstanding', 0)
    mkt_cap = price * shares / 1e9 if shares > 0 else info.get('marketCap', 0) / 1e9
    
    # Cash & Debt
    # Try looking for balance sheet directly if info fails
    bs = ticker.balance_sheet
    cash = 0
    debt = 0
    
    if not bs.empty:
        # Recent column
        col = bs.columns[0]
        try:
            cash_equiv = bs.loc['Cash And Cash Equivalents', col] if 'Cash And Cash Equivalents' in bs.index else 0
            short_inv = bs.loc['Other Short Term Investments', col] if 'Other Short Term Investments' in bs.index else 0
            cash = (cash_equiv + short_inv) / 1e9
        except:
            pass
            
        try:
            # Long Term Debt usually
            lt_debt = bs.loc['Long Term Debt', col] if 'Long Term Debt' in bs.index else 0
            curr_debt = bs.loc['Current Debt', col] if 'Current Debt' in bs.index else 0
            debt = (lt_debt + curr_debt) / 1e9
        except:
            pass
    
    # Fallback to info
    if cash == 0: cash = info.get('totalCash', 0) / 1e9
    if debt == 0: debt = info.get('totalDebt', 0) / 1e9

    print(f"\n[Basic Snapshot]")
    print(f"Price: ${price:.2f}")
    print(f"Market Cap: ${mkt_cap:.2f} B")
    print(f"Total Cash: ${cash:.2f} B")
    print(f"Total Debt: ${debt:.2f} B")
    print(f"Net Cash: ${cash - debt:.2f} B")
    
    # 2. Income Statement
    inc = ticker.financials
    rev = 0
    cogs = 0
    rd = 0
    sga = 0
    
    if not inc.empty:
        col = inc.columns[0]
        print(f"Using Financials Date: {col}")
        
        rev = inc.loc['Total Revenue', col] if 'Total Revenue' in inc.index else 0
        cogs = inc.loc['Cost Of Revenue', col] if 'Cost Of Revenue' in inc.index else 0
        
        try:
            rd = inc.loc['Research And Development', col]
        except:
            pass
            
        try:
            sga = inc.loc['Selling General And Administration', col]
        except:
            pass
            
    revenue_b = rev / 1e9
    gross_profit = rev - cogs
    gross_margin = (gross_profit / rev) if rev > 0 else 0
    
    print(f"\n[Financials (Latest TTM/Year)]")
    print(f"Revenue: ${revenue_b:.2f} B")
    print(f"Gross Margin: {gross_margin*100:.1f}%")
    print(f"R&D: ${rd/1e9:.2f} B ({(rd/rev)*100:.1f}%)")
    print(f"SG&A: ${sga/1e9:.2f} B ({(sga/rev)*100:.1f}%)")
    
    # 3. L5 Estimates (Hardcoded based on industry logic if not available)
    # Average Selling Price (ASP) for Vaccine Doses
    # Estimated: Covid ~$20-25, RSV ~$180-280 (Premium), Flu ~$50
    # Let's assume blended ASP for simple UE model
    
except Exception as e:
    print(f"Error: {e}")
