import os
os.environ["YF_SESSION_BACKEND"] = "requests"

import yfinance as yf
import pandas as pd

stock = yf.Ticker('NET')

# Basic info
info = stock.info
keys_of_interest = [
    'shortName','sector','industry','fullTimeEmployees','marketCap','enterpriseValue',
    'currentPrice','previousClose','fiftyTwoWeekHigh','fiftyTwoWeekLow',
    'trailingPE','forwardPE','priceToBook','priceToSalesTrailing12Months',
    'enterpriseToRevenue','enterpriseToEbitda',
    'totalRevenue','revenueGrowth','grossMargins','operatingMargins','profitMargins',
    'ebitdaMargins','returnOnEquity','returnOnAssets',
    'totalCash','totalDebt','debtToEquity',
    'freeCashflow','operatingCashflow',
    'trailingEps','forwardEps',
    'sharesOutstanding','floatShares',
    'dividendYield','payoutRatio',
    'beta','trailingPegRatio'
]

print("=" * 60)
print("Cloudflare (NET) - 基础数据")
print("=" * 60)
for k in keys_of_interest:
    v = info.get(k, 'N/A')
    print(f'{k}: {v}')

# Financial statements
print("\n" + "=" * 60)
print("利润表 (年度)")
print("=" * 60)
fin = stock.financials
if fin is not None and not fin.empty:
    print(fin.to_string())

print("\n" + "=" * 60)
print("资产负债表 (年度)")
print("=" * 60)
bs = stock.balance_sheet
if bs is not None and not bs.empty:
    print(bs.to_string())

print("\n" + "=" * 60)
print("现金流量表 (年度)")
print("=" * 60)
cf = stock.cashflow
if cf is not None and not cf.empty:
    print(cf.to_string())

# Revenue growth history
print("\n" + "=" * 60)
print("季度收入 (最近)")
print("=" * 60)
qfin = stock.quarterly_financials
if qfin is not None and not qfin.empty:
    if 'Total Revenue' in qfin.index:
        rev = qfin.loc['Total Revenue']
        print(rev.to_string())

# Key ratios over time
print("\n" + "=" * 60)
print("历史股价数据 (近5年月度)")
print("=" * 60)
hist = stock.history(period="5y", interval="1mo")
if hist is not None and not hist.empty:
    print(hist[['Close']].tail(24).to_string())

# Analyst recommendations
print("\n" + "=" * 60)
print("分析师评级")
print("=" * 60)
try:
    rec = stock.recommendations
    if rec is not None and not rec.empty:
        print(rec.tail(10).to_string())
except:
    print("无法获取")

# Institutional holders
print("\n" + "=" * 60)
print("主要股东")
print("=" * 60)
try:
    holders = stock.institutional_holders
    if holders is not None and not holders.empty:
        print(holders.head(10).to_string())
except:
    print("无法获取")
