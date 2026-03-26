#!/usr/bin/env python3
"""Check if all stocks are properly mapped to sectors"""

import json

print("=" * 80)
print("SECTOR MAPPING COMPLETENESS CHECK")
print("=" * 80)

# Load metadata from Phase 01
try:
    with open('data/universe_metadata.json', 'r') as f:
        meta = json.load(f)
    
    stocks = meta.get('stocks', [])
    stock_to_sector = meta.get('stock_to_sector', {})
    
    print(f"\n[1] UNIVERSE STOCKS")
    print(f"    Total stocks in universe: {len(stocks)}")
    print(f"    Stocks with mappings: {len(stock_to_sector)}")
    
    # Check unmapped
    unmapped = [s for s in stocks if s not in stock_to_sector]
    print(f"    Unmapped stocks: {len(unmapped)}")
    
    if unmapped:
        print(f"\n    ⚠️  UNMAPPED STOCKS (No sector assigned):")
        for stock in sorted(unmapped):
            print(f"       - {stock}")
    else:
        print(f"    ✓ All stocks mapped to sectors")
    
    # Sector distribution in metadata
    sectors_in_meta = {}
    for stock, sector in stock_to_sector.items():
        sectors_in_meta[sector] = sectors_in_meta.get(sector, 0) + 1
    
    print(f"\n[2] SECTORS IN METADATA ({len(sectors_in_meta)} unique)")
    for sector in sorted(sectors_in_meta.keys()):
        print(f"    {sector:<20}: {sectors_in_meta[sector]:>3} stocks")
    
except FileNotFoundError as e:
    print(f"\n⚠️  Error: {e}")
    print("   Phase 01 (data preparation) needs to be run first")

# Load config
print(f"\n[3] SECTORS IN CONFIG (nifty100_sectors.json)")
with open('config/nifty100_sectors.json', 'r') as f:
    cfg = json.load(f)

config_sectors = cfg.get('NIFTY_100_STOCKS', {})
config_stocks_list = []

for sector, stocks_list in config_sectors.items():
    config_stocks_list.extend(stocks_list)
    print(f"    {sector:<20}: {len(stocks_list):>3} configured")

print(f"\n[4] COMPARISON")
print(f"    Config total stocks: {len(config_stocks_list)}")
print(f"    Unique config stocks: {len(set(config_stocks_list))}")
print(f"    Universe stocks: {len(stocks)}")

# Find duplicates in config
from collections import Counter
duplicates = [s for s, count in Counter(config_stocks_list).items() if count > 1]
if duplicates:
    print(f"\n    ⚠️  DUPLICATE STOCKS IN CONFIG:")
    for stock in duplicates:
        print(f"       - {stock}")

# Check mapping completeness
try:
    config_in_universe = [s for s in config_stocks_list if s in stocks]
    config_not_in_universe = [s for s in config_stocks_list if s not in stocks]
    
    print(f"\n[5] MAPPING STATUS")
    print(f"    Config stocks in universe: {len(config_in_universe)}/{len(set(config_stocks_list))}")
    
    if config_not_in_universe:
        print(f"    ⚠️  Config stocks NOT in universe ({len(set(config_not_in_universe))}):")
        for stock in sorted(set(config_not_in_universe)):
            print(f"       - {stock}")
    
    universe_not_in_config = [s for s in stocks if s not in config_stocks_list]
    if universe_not_in_config:
        print(f"\n    ⚠️  Universe stocks NOT in config ({len(universe_not_in_config)}):")
        for stock in sorted(universe_not_in_config):
            print(f"       - {stock}")
    
except NameError:
    print("    (Skipped - Phase 01 data not available)")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

try:
    if len(unmapped) == 0 and len(stocks) == len(stock_to_sector):
        print("✓ ALL STOCKS ARE PROPERLY MAPPED TO SECTORS")
    else:
        print(f"⚠️  INCOMPLETE MAPPING: {len(unmapped)} stocks without sectors")
except NameError:
    print("⚠️  Cannot verify - run Phase 01 first")

print("=" * 80)
