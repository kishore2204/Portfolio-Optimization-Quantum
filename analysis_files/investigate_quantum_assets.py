"""
INVESTIGATION: Why does Quantum portfolio have 13 assets instead of 14?
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

root = Path("c:\\Users\\kisho\\Downloads\\Portfolio-Optimization-Quantum")
data_dir = root / "data"
sys.path.insert(0, str(root))

print("=" * 90)
print(" " * 20 + "🔍 INVESTIGATION: QUANTUM ASSET COUNT DISCREPANCY")
print("=" * 90)

# Load weights
weights = pd.read_csv(data_dir / "07_portfolio_weights.csv", index_col=0)

print("\n[STEP 1] Detailed Weight Analysis")
print("-" * 90)

# Classical
class_weights = weights[weights['Classical'] > 0.0001].copy()
class_weights = class_weights.sort_values('Classical', ascending=False)

print(f"\nCLASSICAL PORTFOLIO ({len(class_weights)} assets, sum={class_weights['Classical'].sum():.6f}):")
print(f"{'Asset':20} {'Weight':12} {'Cumulative':12}")
print("-" * 45)
cumsum = 0
for asset, weight in zip(class_weights.index, class_weights['Classical']):
    cumsum += weight
    print(f"{asset:20} {weight:12.6f} {cumsum:12.6f}")

# Quantum
quant_weights = weights[weights['Quantum'] > 0.0001].copy()
quant_weights = quant_weights.sort_values('Quantum', ascending=False)

print(f"\nQUANTUM PORTFOLIO ({len(quant_weights)} assets, sum={quant_weights['Quantum'].sum():.6f}):")
print(f"{'Asset':20} {'Weight':12} {'Cumulative':12}")
print("-" * 45)
cumsum = 0
for asset, weight in zip(quant_weights.index, quant_weights['Quantum']):
    cumsum += weight
    print(f"{asset:20} {weight:12.6f} {cumsum:12.6f}")

# Compare
print(f"\n[STEP 2] Asset Selection Comparison")
print("-" * 90)

class_assets = set(class_weights.index)
quant_assets = set(quant_weights.index)

only_classical = class_assets - quant_assets
only_quantum = quant_assets - class_assets
common = class_assets & quant_assets

print(f"\nAssets only in Classical: {only_classical}")
print(f"Assets only in Quantum: {only_quantum}")
print(f"Common assets: {len(common)} (overlap)")

print(f"\n[STEP 3] Check for Near-Zero Weights")
print("-" * 90)

# Check all weights, not just > 0.0001
zero_threshold = 1e-10

class_all = weights[(weights['Classical'] > zero_threshold) & (weights['Classical'] <= 0.0001)]
quant_all = weights[(weights['Quantum'] > zero_threshold) & (weights['Quantum'] <= 0.0001)]

print(f"\nClassical weights (0 < w <= 0.0001): {len(class_all)}")
if len(class_all) > 0:
    print(class_all['Classical'])

print(f"\nQuantum weights (0 < w <= 0.0001): {len(quant_all)}")
if len(quant_all) > 0:
    print(quant_all['Quantum'])

print(f"\n[STEP 4] Check Annealing Configuration")
print("-" * 90)

from config_constants import K_RATIO

universe_size = 680
k_computed = max(10, int(K_RATIO * universe_size))

print(f"\nK Configuration:")
print(f"  K_RATIO: {K_RATIO}")
print(f"  Universe size: {universe_size}")
print(f"  K_computed: {k_computed}")
print(f"  Classical selected: {len(class_weights)}")
print(f"  Quantum selected: {len(quant_weights)}")

if len(quant_weights) == k_computed - 1:
    print(f"\n⚠️ Quantum has K-1 assets (off by 1)")
    print(f"   This suggests annealing may have selected one less asset")
else:
    print(f"\n⚠️ Difference: {k_computed - len(quant_weights)} assets")

print(f"\n[STEP 5] Check Recent QUBO Inputs")
print("-" * 90)

# Read the expected returns and downside to check if annealing had right data
expected_ret = pd.read_csv(data_dir / "04_expected_returns_and_downside.csv", index_col=0)
print(f"\nExpected returns & downside data:")
print(f"  Assets in file: {len(expected_ret)}")
print(f"  Columns: {list(expected_ret.columns)}")

# Check if quantum selected assets are in the expected returns
for asset in quant_weights.index:
    if asset not in expected_ret.index:
        print(f"  ❌ {asset} not in expected returns!")

# Check QUBO inputs
try:
    qubo_corr = pd.read_csv(data_dir / "QUBO_inputs_correlation_matrix.csv", index_col=0)
    print(f"\nQUBO correlation matrix: {qubo_corr.shape}")
    
    qubo_exp_ret = pd.read_csv(data_dir / "QUBO_inputs_expected_returns.csv", index_col=0)
    print(f"QUBO expected returns: {len(qubo_exp_ret)} assets")
    print(f"  Sample: {list(qubo_exp_ret.index[:5])}")
except:
    print("Could not read QUBO input files")

print("\n" + "=" * 90)
print("[CONCLUSION]")
print("=" * 90)
print(f"""
The quantum portfolio has 13 assets while classical has 14.
This is likely due to ONE of:

1. ** Annealing constraint**: The annealing algorithm selected exactly 13 assets
   instead of 14 due to the constraint optimization.
   
2. **Sharpe filtering**: The post-annealing Sharpe filter may have removed one asset
   that had poor individual performance.
   
3. **K value mismatch**: If K=14 is set, but annealing is configured for K=13,
   this would explain the discrepancy.

VERIFICATION NEEDED:
- Check annealing output in hybrid_optimizer.py
- Verify K is correctly passed to annealing function
- Check if Sharpe filter is removing assets with low risk-adjusted returns

ACTION: Review hybrid_optimizer.py line where annealing returns assets.
""")
