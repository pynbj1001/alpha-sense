import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

print("="*60)
print("🚀 MRNA High-Value Data Extraction (L5 Mode)")
print("="*60)

try:
    ticker = yf.Ticker("MRNA")
    info = ticker.info
    
    # 1. Basic Stats for Context
    price = info.get('currentPrice', 0)
    mkt_cap = info.get('marketCap', 0) / 1e9
    cash = info.get('totalCash', 0) / 1e9
    debt = info.get('totalDebt', 0) / 1e9
    shares = info.get('sharesOutstanding', 0) / 1e6
    
    print(f"\n[Basic Snapshot]")
    print(f"Price: ${price:.2f}")
    print(f"Market Cap: ${mkt_cap:.2f} B")
    print(f"Total Cash: ${cash:.2f} B  (Cash/Share: ${cash/shares:.2f})")
    print(f"Net Cash: ${cash - debt:.2f} B")
    
    # 2. Financials for UE Calculation
    # Get last full year or TTM
    financials = ticker.financials
    if financials.empty:
        print("Warning: Could not fetch financials directly. Using info if available.")
        rev = info.get('totalRevenue', 0)
        gp = info.get('grossProfits', 0)
        # Fallback if specific line items missing in info
        cogs = rev - gp if gp else 0
    else:
        # Use TTM or Last Year
        # TTM is often better for current run-rate
        col = financials.columns[0] # Most recent
        rev = financials.loc['Total Revenue', col] if 'Total Revenue' in financials.index else 0
        cogs = financials.loc['Cost Of Revenue', col] if 'Cost Of Revenue' in financials.index else 0
        gross_profit = rev - cogs
        
        # Expenses
        try:
            r_d = financials.loc['Research And Development', col]
        except:
            r_d = 0
            
        try:
            sga = financials.loc['Selling General And Administration', col]
        except:
            sga = 0
            
    print(f"\n[Financials TTM/Last Report]")
    print(f"Revenue: ${rev/1e9:.2f} B")
    print(f"Gross Margin: {(gross_profit/rev)*100:.1f}%")
    print(f"R&D Intensity: {(r_d/rev)*100:.1f}%")
    print(f"SG&A Intensity: {(sga/rev)*100:.1f}%")

    # 3. Key Variables for Sensitivity Analysis (Estimated)
    # L5 needs "Non-consensus" inputs, we will structure them for the tool
    # INT (Cancer Vaccine) estimates often vary
    # Base Case: 
    #   - Peak Sales: $5B (Conservative) to $10B (Optimistic)
    #   - PoS (Probability of Success): 30% (Phase 2->3 avg) to 60% (Merck partnership confidence)
    
    print("\n[Data for L5 Tool]")
    print(f"Current_WACC_Proxy: {0.10} (Biotech Standard)")
    print(f"Current_Shares: {shares:.2f} M")
    
except Exception as e:
    print(f"Error extracting data: {e}")
