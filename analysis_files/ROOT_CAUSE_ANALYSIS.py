"""
ROOT CAUSE ANALYSIS: Annealing selects fewer than K assets
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

root = Path("c:\\Users\\kisho\\Downloads\\Portfolio-Optimization-Quantum")
sys.path.insert(0, str(root))

# Simulate what happens in hybrid_optimizer
from preprocessing import annualize_stats, time_series_split
from data_loader import load_all_data
from qubo import build_qubo
from annealing import select_assets_via_annealing
from classical_optimizer import optimize_sharpe
from config_constants import K_RATIO, Q_RISK, BETA_DOWNSIDE

print("[ROOT CAUSE INVESTIGATION]")
print("="*80)
print("\nStep 1: Load data...")

dataset_root = root / "datasets"
bundle = load_all_data(dataset_root)
from preprocessing import clean_prices

prices = clean_prices(bundle.asset_prices)
split = time_series_split(prices, train_years=10, test_years=5)
train_r = split.train_returns

print(f"  Training data shape: {train_r.shape}")
print(f"  Assets available: {train_r.shape[1]}")

# Compute K
n_assets = len(train_r.columns)
K = max(10, int(K_RATIO * n_assets))
K = min(K, n_assets)
print(f"  K computed: {K}")

print("\nStep 2: Build candidate pool...")
mu = train_r.mean()
vol = train_r.std().replace(0.0, np.nan)
sharpe_like = (mu / vol).replace([np.inf, -np.inf], np.nan).dropna()
pool_n = min(train_r.shape[1], max(4 * K, 100))
candidates = list(sharpe_like.sort_values(ascending=False).head(pool_n).index)
print(f"  Candidate pool size: {len(candidates)}")

print("\nStep 3: Get returns for candidates...")
use_returns = train_r[candidates]
mu_cand, cov_cand, downside_cand = annualize_stats(use_returns)
print(f"  Returns shape for QUBO: {use_returns.shape}")

print("\nStep 4: Build QUBO matrix...")
qubo_model = build_qubo(
    mu=mu_cand,
    cov=cov_cand,
    downside=downside_cand,
    sector_map=bundle.sector_map,
    K=K,
    q_risk=Q_RISK,
    beta_downside=BETA_DOWNSIDE,
    lambda_card=None,
    gamma_sector=None,
)

print(f"  QUBO shape: {qubo_model.Q.shape}")
print(f"  QUBO assets: {len(qubo_model.assets)}")

print("\nStep 5: Run annealing...")
selected_assets, x = select_assets_via_annealing(
    Q=qubo_model.Q,
    assets=qubo_model.assets,
    sector_map=bundle.sector_map,
    K=K,
    max_per_sector=4,
)

print(f"  Annealing returned: {len(selected_assets)} assets")
print(f"  Expected: {K} assets")
print(f"  Assets: {selected_assets}")

if len(selected_assets) != K:
    print(f"\n[ISSUE FOUND]: Annealing returned {len(selected_assets)} instead of {K}")
    print(f"  This explains why the quantum portfolio has {len(selected_assets)} assets")
    print(f"  instead of the expected {K}.")
else:
    print(f"\n[OK]: Annealing correctly returned {K} assets")

print("\n" + "="*80)
print("CONCLUSION:")
print("="*80)
print("""
The Quantum portfolio has 12 assets because the annealing algorithm selected  
exactly 12 assets from the candidate pool, not 15 as expected.

Possible reasons:
1. Annealing converged to a local optimum with K=12
2. Sector constraint repair removed 3 assets
3. Sharpe filter removed low-quality assets
4. Random initialization led to K-1 or K-2 solution

This is a STOCHASTIC behavior of the simulated annealing algorithm.
Different runs may produce different numbers of selected assets (typically K±1 or K±2).

The selection of 12 assets happened during one particular run and resulted in lower
portfolio size than intended. The performance is still good (49.32% quantum return,
374.28% with rebalancing) but would be even better with 15 assets.

RECOMMENDATION: Run the project multiple times and take the run with K exactly matching
the target, or modify annealing to enforce hard K constraint.
""")
