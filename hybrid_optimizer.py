from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd

from classical_optimizer import optimize_sharpe
from preprocessing import annualize_stats
from qubo import build_qubo
from annealing import select_assets_via_annealing


@dataclass
class HybridConfig:
    K: int = 25
    max_weight: float = 0.12
    rf: float = 0.05
    q_risk: float = 1.0
    beta_downside: float = 0.5
    lambda_card: float = 5.0
    gamma_sector: float = 0.5
    max_per_sector: int = 4


def run_quantum_hybrid_selection(
    train_returns: pd.DataFrame,
    sector_map: Dict[str, str],
    config: HybridConfig,
    candidate_assets: list[str] | None = None,
) -> tuple[list[str], pd.Series]:
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
    w = optimize_sharpe(mu_s, cov_s, rf=config.rf, w_max=config.max_weight)
    return selected_assets, w


def portfolio_returns(returns: pd.DataFrame, weights: pd.Series) -> pd.Series:
    cols = [c for c in weights.index if c in returns.columns]
    if not cols:
        return pd.Series(index=returns.index, dtype=float)
    w = weights.loc[cols].values
    r = returns[cols].values @ w
    return pd.Series(r, index=returns.index)
