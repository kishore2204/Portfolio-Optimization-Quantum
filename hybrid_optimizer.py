from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd

from classical_optimizer import optimize_sharpe, optimize_sharpe_with_min_weight
from preprocessing import annualize_stats
from qubo import build_qubo
from annealing import select_assets_via_annealing
from config_constants import Q_RISK, BETA_DOWNSIDE, MAX_WEIGHT_PER_ASSET, RISK_FREE_RATE, MAX_ASSETS_PER_SECTOR


@dataclass
class HybridConfig:
    """QUBO Quantum-Classical Hybrid Optimizer Configuration
    
    IMPORTANT: Uses FIXED CONSTANTS from config_constants.py
    No parameter tuning - all values are theoretically justified.
    """
    K: int = 25
    max_weight: float = MAX_WEIGHT_PER_ASSET
    rf: float = RISK_FREE_RATE
    q_risk: float = Q_RISK              # Fixed: 0.5
    beta_downside: float = BETA_DOWNSIDE  # Fixed: 0.3
    lambda_card: float = None            # Computed adaptive
    gamma_sector: float = None           # Computed from lambda
    max_per_sector: int = MAX_ASSETS_PER_SECTOR


def run_quantum_hybrid_selection(
    train_returns: pd.DataFrame,
    sector_map: Dict[str, str],
    config: HybridConfig,
    candidate_assets: list[str] | None = None,
) -> tuple[list[str], pd.Series, Any]:  # Returns: (assets, weights, qubo_model)
    if candidate_assets is not None:
        cols = [c for c in candidate_assets if c in train_returns.columns]
        if len(cols) >= 3:
            use_returns = train_returns[cols]
        else:
            use_returns = train_returns
    else:
        use_returns = train_returns

    mu, cov, downside = annualize_stats(use_returns)

    K = min(config.K, len(mu))
    qubo_model = build_qubo(
        mu=mu,
        cov=cov,
        downside=downside,
        sector_map=sector_map,
        K=K,
        q_risk=config.q_risk,
        beta_downside=config.beta_downside,
        lambda_card=config.lambda_card,
        gamma_sector=config.gamma_sector,
    )

    selected_assets, _ = select_assets_via_annealing(
        Q=qubo_model.Q,
        assets=qubo_model.assets,
        sector_map=sector_map,
        K=K,
        max_per_sector=config.max_per_sector,
    )

    mu_s = mu.loc[selected_assets]
    cov_s = cov.loc[selected_assets, selected_assets]
    w = optimize_sharpe_with_min_weight(mu_s, cov_s, rf=config.rf, w_max=config.max_weight, min_weight=0.02)
    return selected_assets, w, qubo_model  # Now returns the QUBO used for annealing


def portfolio_returns(returns: pd.DataFrame, weights: pd.Series) -> pd.Series:
    cols = [c for c in weights.index if c in returns.columns]
    if not cols:
        return pd.Series(index=returns.index, dtype=float)
    w = weights.loc[cols].values
    r = returns[cols].values @ w
    return pd.Series(r, index=returns.index)
