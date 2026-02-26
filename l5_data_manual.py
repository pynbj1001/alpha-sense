# l5_data_manual.py
# Hardcoded data based on recent 10-K/10-Q (Feb 2026 Context)

# Moderna Q4 2025 / Full Year 2025 Approximate Data
# Revenue: ~$4.0B (Covid decline)
# Cash: ~$6.0B
# Shares: ~390M
# Price: ~$45
# Market Cap: ~$17.5B

class MRNA_Data:
    price = 45.00
    shares = 390  # Million
    market_cap = 17.55 # Billion
    cash_balance = 6.2 # Billion (Cash + Investments)
    debt = 0.5 # Leases primarily
    
    # Income Statement 2025 (Est)
    revenue = 4.0 # Billion
    cogs = 1.8 # Billion (High due to write-offs/low volume)
    gross_margin = 0.55 # 55% (Target 75% at scale)
    rd = 4.5 # Billion (Heavy investment)
    sga = 1.2 # Billion
    
    # Asset Values (EPV inputs)
    # LNP Platform Value: $15B
    # Clinical Data Value: $10B
    # Manufacturing: $3B
    
    # Unit Economics (Respiratory)
    # ASP (Blended): $30
    # COGS per dose (scaled): $5
    # Royalty/other: $2
    # Gross Profit per dose: $23
    
    # Unit Economics (Cancer - INT)
    # ASP: $50,000 - $100,000 (Treatment course)
    # COGS: $5,000 (Personalized mfg)
    # Gross Margin: ~90%
