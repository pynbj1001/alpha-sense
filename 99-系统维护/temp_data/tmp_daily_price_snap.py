import os
import time
import ssl
import io
import urllib.request
import pandas as pd
from datetime import datetime

ctx = ssl.create_default_context()
ctx.load_verify_locations(r'C:\Users\pynbj\AppData\Local\Temp\cacert.pem')

tickers = {
    'UBER': 'uber.us',
    'NVDA': 'nvda.us',
    'META': 'meta.us',
    'AMZN': 'amzn.us',
    'GOOGL': 'googl.us',
    'MU': 'mu.us',
    'TSM': 'tsm.us',
    'NET': 'net.us',
}

results = {}
for name, sym in tickers.items():
    url = 'https://stooq.com/q/d/l/?s=' + sym + '&i=d'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, context=ctx, timeout=15)
        df = pd.read_csv(io.BytesIO(resp.read()))
        df.columns = [c.strip() for c in df.columns]
        df = df.dropna(subset=['Close'])
        if len(df) > 0:
            last = df.iloc[-1]
            w52 = df.tail(252)
            lo = w52['Close'].min()
            hi = w52['Close'].max()
            cur = last['Close']
            pct = round((cur - lo) / (hi - lo) * 100, 1) if (hi - lo) > 0 else 'N/A'
            results[name] = {
                'date': str(last['Date']),
                'price': round(cur, 2),
                '52wL': round(lo, 2),
                '52wH': round(hi, 2),
                '52w_pct': pct,
            }
            print(name + ': date=' + str(last['Date']) + ', close=' + str(round(cur, 2)) +
                  ', 52wL=' + str(round(lo, 2)) + ', 52wH=' + str(round(hi, 2)) +
                  ', 52w%=' + str(pct) + '%')
        time.sleep(1)
    except Exception as e:
        results[name] = {'error': str(e)[:100]}
        print(name + ': ERR ' + str(e)[:100])

print('\n数据获取时间: ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
