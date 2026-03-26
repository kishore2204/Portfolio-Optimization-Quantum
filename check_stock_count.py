#!/usr/bin/env python3
import json
import numpy as np
from pathlib import Path

print("=" * 80)
print("STOCK COUNT ANALYSIS FOR QUBO")
print("=" * 80)

# 1. Check dataset
print("\n[1] DATASET SIZE")
import pandas as pd
df = pd.read_csv('Dataset/prices_timeseries_complete.csv')
print(f"    Total stocks in raw dataset: {len(df.columns) - 1}")

# 2. Check config
print("\n[2] CONFIGURATION")
with open('config/config.json', 'r') as f:
    cfg = json.load(f)
    
print(f"    Universe size (config): {cfg['data'].get('universe_size')}")
print(f"    Target portfolio K: {cfg['portfolio'].get('K')}")

# 3. Check NIFTY100 config
print("\n[3] NIFTY 100 CONFIGURATION")
with open('config/nifty100_sectors.json', 'r') as f:
    nifty_cfg = json.load(f)
    
total_nifty = 0
sector_counts = {}
for sector, stocks in nifty_cfg.get('NIFTY_100_STOCKS', {}).items():
    count = len(stocks)
    total_nifty += count
    sector_counts[sector] = count
    
print(f"    Total NIFTY 100 stocks configured: {total_nifty}")
for sector in sorted(sector_counts.keys()):
    print(f"      {sector}: {sector_counts[sector]}")

# 4. Check prepared universe (Phase 01 output)
print("\n[4] PREPARED UNIVERSE (Phase 01 Output)")
try:
    with open('data/universe_metadata.json', 'r') as f:
        meta = json.load(f)
    stocks = meta.get('stocks', [])
    print(f"    Stocks in prepared universe: {len(stocks)}")
    print(f"    Sectors: {len(set(meta.get('stock_to_sector', {}).values()))}")
    print(f"    First 10 stocks: {stocks[:10]}")
except FileNotFoundError:
    print("    ⚠️  universe_metadata.json not found (Phase 01 not run)")

# 5. Check QUBO matrix size
print("\n[5] QUBO MATRIX SIZE (Phase 03 Input)")
try:
    Q = np.load('quantum/qubo_matrix.npy')
    print(f"    QUBO matrix dimensions: {Q.shape[0]} x {Q.shape[1]}")
    print(f"    ✓ This is the number of stocks used in QUBO calculation")
except FileNotFoundError:
    print("    ⚠️  qubo_matrix.npy not found (Phase 03 not run)")

# 6. Check QUBO metadata
print("\n[6] QUBO METADATA")
try:
    with open('quantum/qubo_metadata.json', 'r') as f:
        qubo_meta = json.load(f)
    qubo_stocks = qubo_meta.get('stocks', [])
    print(f"    Stocks in QUBO metadata: {len(qubo_stocks)}")
    print(f"    First 10: {qubo_stocks[:10] if qubo_stocks else 'N/A'}")
except FileNotFoundError:
    print("    ⚠️  qubo_metadata.json not found")

# 7. Summary with filtering logic
print("\n" + "=" * 80)
print("SUMMARY: STOCK FILTERING PIPELINE")
print("=" * 80)
print(f"""
Dataset → Phase 01 → Phase 03 → QUBO
   ↓                   ↓        ↓
{len(df.columns)-1} stocks    N stocks    → {cfg['data'].get('universe_size')} config    QUBO uses
   (raw)      (filtered)                      N actual stocks

Filtering logic in Phase 01:
1. Load all {len(df.columns)-1} stocks from dataset
2. Filter to NIFTY 100 configured (≤ {total_nifty} stocks)
3. Remove stocks with < {cfg['data'].get('min_history_days')} days
4. Remove low-price stocks (< {cfg['data'].get('min_price')})
5. Result = N stocks for QUBO
6. QUBO creates N×N matrix (one variable per stock)
7. Solver selects K = {cfg['portfolio'].get('K')} stocks from N
""")

print("=" * 80)
