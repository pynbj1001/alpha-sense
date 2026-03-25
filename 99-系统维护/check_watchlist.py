#!/usr/bin/env python
import json
from pathlib import Path

wl_path = Path(r'c:\Users\pynbj\OneDrive\1.积累要看的文件\1. 投资框架\11.投资机会跟踪报告\ideas_watchlist.json')
wl = json.loads(wl_path.read_text(encoding='utf-8'))

jp_stocks = [i for i in wl['ideas'] if i.get('market') == 'JP']
all_tradeable = [i for i in wl['ideas'] if i.get('symbol') and i.get('market') in ('US','HK','JP')]

print("=== watchlist overview ===")
print(f"Total ideas: {len(wl['ideas'])}")
print(f"JP stocks: {len(jp_stocks)}")
print(f"US+HK+JP with symbol: {len(all_tradeable)}")
print()
print("=== Japan AI Chain ===")
for k, s in enumerate(jp_stocks, 1):
    sym = s.get('symbol','')
    title = s.get('title','')
    note = s.get('note','')[:55]
    print(f"{k:2}. {sym:10} {title:35} {note}")
print()
print("=== All tradeable (US+HK+JP) ===")
for s in all_tradeable:
    print(f"  {s.get('symbol',''):12} [{s.get('market','')}] {s.get('title','')}")
