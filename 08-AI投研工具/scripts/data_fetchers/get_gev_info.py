import yfinance as yf
stock = yf.Ticker('GEV')
info = stock.info
print('Market Cap:', info.get('marketCap'))
print('Forward PE:', info.get('forwardPE'))
print('Revenue:', info.get('totalRevenue'))
print('Sector:', info.get('sector'))
print('Industry:', info.get('industry'))
