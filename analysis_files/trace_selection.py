"""
TRACE INITIAL QUANTUM SELECTION
Determine where the 13 assets come from in the first annealing call
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

root = Path("c:\\Users\\kisho\\Downloads\\Portfolio-Optimization-Quantum")
sys.path.insert(0, str(root))

from preprocessing import time_series_split, annualize_stats
from data_loader import load_all_data
from hybrid_optimizer import HybridConfig, run_quantum_hybrid_selection
from config_constants import K_RATIO

print("=" * 90)
print(" " * 15 + "🔍 TRACING INITIAL QUANTUM SELECTION")
print("=" * 90)

# Replicate the main.py workflow
root_path = Path(__file__).resolve().parent
dataset_root = root_path / "datasets"

bundle = load_all_data(dataset_root)
prices = bundle.asset_prices

split = time_series_split(prices, train_years=10, test_years=5)

train_r = split.train_returns
test_r = split.test_returns

print(f"\nStep 1: Data Loaded")
print(f"  Train returns shape: {train_r.shape}")
print(f"  Test returns shape: {test_r.shape}")
print(f"  Train dates: {train_r.index[0]} to {train_r.index[-1]}")
print(f"  Test dates: {test_r.index[0]} to {test_r.index[-1]}")

# Compute K
n_assets = len(train_r.columns)
K = max(10, int(K_RATIO * n_assets))
K = min(K, n_assets)

print(f"\nStep 2: K Calculation")
print(f"  n_assets: {n_assets}")
print(f"  K_RATIO: {K_RATIO}")
print(f"  K computed: max(10, int({K_RATIO} × {n_assets})) = {K}")
print(f"  K final: {K}")

# Build candidate pool
mu = train_r.mean()
vol = train_r.std().replace(0.0, np.nan)
sharpe_like = (mu / vol).replace([np.inf, -np.inf], np.nan).dropna()

pool_n = min(train_r.shape[1], max(4 * K, 100))
candidates = list(sharpe_like.sort_values(ascending=False).head(pool_n).index)
if len(candidates) < K:
    candidates = list(train_r.columns)

print(f"\nStep 3: Candidate Pool")
print(f"  pool_n: min({train_r.shape[1]}, max({4*K}, 100)) = {pool_n}")
print(f"  Candidates selected: {len(candidates)}")
print(f"  Sample: {candidates[:5]}")

# Run hybrid selection
hcfg = HybridConfig(K=K)

print(f"\nStep 4: HybridConfig")
print(f"  K: {hcfg.K}")
print(f"  max_weight: {hcfg.max_weight}")
print(f"  rf: {hcfg.rf}")
print(f"  q_risk: {hcfg.q_risk}")
print(f"  beta_downside: {hcfg.beta_downside}")

print(f"\nStep 5: Running Quantum Selection...")
q_assets, q_weights, qubo_model = run_quantum_hybrid_selection(
    train_r,
    bundle.sector_map,
    hcfg,
    candidate_assets=candidates,
)

print(f"  Result: {len(q_assets)} assets selected")
print(f"  Assets: {q_assets}")
print(f"  Weights sum: {q_weights.sum():.6f}")

print(f"\n" + "="*90)
print("FINDING: Initial annealing selects FEWER than K assets")
if len(q_assets) < K:
    print(f"  Expected K: {K}")
    print(f"  Actually selected: {len(q_assets)}")
    print(f"  Shortfall: {K - len(q_assets)} assets")
    
if len(q_assets) == 13:
    print(f"\n✅ CONFIRMED: Annealing is returning 13 assets when K=14 is requested")
    print(f"\nPOSSIBLE CAUSES:")
    print(f"  1. Annealing stochastic behavior - may select 13-14 depending on initialization")
    print(f"  2. Sector constraint repair logic reducing assets below K")
    print(f"  3. QUBO formula causing annealing to favor fewer assets")
    
print("="*90)
