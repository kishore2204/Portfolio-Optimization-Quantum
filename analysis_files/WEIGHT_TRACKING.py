"""
INVESTIGATION: Track weights through the optimization pipeline
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

root = Path("c:\\Users\\kisho\\Downloads\\Portfolio-Optimization-Quantum")
sys.path.insert(0, str(root))

from preprocessing import annualize_stats, time_series_split
from data_loader import load_all_data
from qubo import build_qubo
from annealing import select_assets_via_annealing
from classical_optimizer import optimize_sharpe
from config_constants import K_RATIO, Q_RISK, BETA_DOWNSIDE
from preprocessing import clean_prices

print("[WEIGHT TRACKING ANALYSIS]")
print("="*80)

dataset_root = root / "datasets"
bundle = load_all_data(dataset_root)
prices = clean_prices(bundle.asset_prices)
split = time_series_split(prices, train_years=10, test_years=5)
train_r = split.train_returns

# Compute K
n_assets = len(train_r.columns)
K = max(10, int(K_RATIO * n_assets))

# Build candidate pool
mu = train_r.mean()
vol = train_r.std().replace(0.0, np.nan)
sharpe_like = (mu / vol).replace([np.inf, -np.inf], np.nan).dropna()
pool_n = min(train_r.shape[1], max(4 * K, 100))
candidates = list(sharpe_like.sort_values(ascending=False).head(pool_n).index)

# Get returns
use_returns = train_r[candidates]
mu_cand, cov_cand, downside_cand = annualize_stats(use_returns)

# Build QUBO
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

# Run annealing
selected_assets, x = select_assets_via_annealing(
    Q=qubo_model.Q,
    assets=qubo_model.assets,
    sector_map=bundle.sector_map,
    K=K,
    max_per_sector=4,
)

print(f"\n[ANNEALING OUTPUT]")
print(f"  Selected {len(selected_assets)} assets: {selected_assets}")

# Now optimize Sharpe with these selected assets
print(f"\n[OPTIMIZE SHARPE]")
mu_s = mu_cand.loc[selected_assets]
cov_s = cov_cand.loc[selected_assets, selected_assets]

print(f"  Input: {len(mu_s)} assets")
print(f"  Input: {cov_s.shape}")

w = optimize_sharpe(mu_s, cov_s, rf=0.05, w_max=0.12)

print(f"  Output weights: {len(w)} weights")
print(f"  Non-zero weights (> 0.0001): {(w > 0.0001).sum()}")
print(f"  Sum of weights: {w.sum():.6f}")

print(f"\n[WEIGHT DETAILS]")
nonzero = w[w > 0.0001].sort_values(ascending=False)
print(f"  Assets with non-zero weights: {len(nonzero)}")
for asset, weight in nonzero.items():
    print(f"    {asset:15} {weight:8.6f}")

print(f"\n[CONCLUSION]")
if len(nonzero) == 15:
    print(f"  optimize_sharpe returned 15 non-zero weights [OK]")
elif len(nonzero) == 12:
    print(f"  optimize_sharpe returned only 12 non-zero weights [ISSUE]")
    print(f"  The 15 selected assets were optimized but 3 got zero weight")
else:
    print(f"  optimize_sharpe returned {len(nonzero)} non-zero weights")

print("\nAssets used in Sharpe optimization:")
print(f"  {mu_s.index.tolist()}")
