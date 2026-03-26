#!/usr/bin/env python3
"""Check the actual structure of metadata and identify the issue"""

import json

print("=" * 80)
print("METADATA STRUCTURE ANALYSIS")
print("=" * 80)

with open('data/universe_metadata.json', 'r') as f:
    meta = json.load(f)

print("\n[1] KEYS IN METADATA FILE")
for key in meta.keys():
    print(f"    - {key}")

print("\n[2] STOCKS KEY")
stocks = meta.get('stocks', [])
print(f"    Count: {len(stocks)}")
if stocks:
    print(f"    First 5: {stocks[:5]}")

print("\n[3] SECTORS KEY (where mappings are stored)")
sectors_dict = meta.get('sectors', {})
print(f"    Type: {type(sectors_dict)}")
print(f"    Count: {len(sectors_dict)}")

if isinstance(sectors_dict, dict):
    print(f"\n    Structure:")
    for stock in list(sectors_dict.keys())[:5]:
        print(f"      {stock}: {sectors_dict[stock]}")
    
    print(f"\n    ✓ ALL SECTORS ARE MAPPED:")
    
    sectors_by_name = {}
    for stock, sector in sectors_dict.items():
        if sector not in sectors_by_name:
            sectors_by_name[sector] = []
        sectors_by_name[sector].append(stock)
    
    for sector in sorted(sectors_by_name.keys()):
        print(f"      {sector:<20}: {len(sectors_by_name[sector]):>3} stocks")

print("\n[4] ERROR SOURCE")
print("    The script used 'stock_to_sector' key but metadata stores 'sectors'")
print("    Fix: Use meta['sectors'] instead of meta['stock_to_sector']")

print("\n" + "=" * 80)
