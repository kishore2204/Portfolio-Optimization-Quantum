from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from config_constants import Q_RISK, BETA_DOWNSIDE, compute_lambda_card, compute_gamma_sector


@dataclass
class QuboModel:
    Q: np.ndarray
    assets: List[str]
    lambda_card: float
    gamma_sector: float


def build_qubo(
    mu: pd.Series,
    cov: pd.DataFrame,
    downside: pd.Series,
    sector_map: Dict[str, str],
    K: int,
    q_risk: Optional[float] = None,
    beta_downside: Optional[float] = None,
    lambda_card: Optional[float] = None,
    gamma_sector: Optional[float] = None,
) -> QuboModel:
    assets = list(mu.index)
    n = len(assets)

    # Use fixed constants from config, or compute adaptive values if not provided
    if q_risk is None:
        q_risk = Q_RISK
    if beta_downside is None:
        beta_downside = BETA_DOWNSIDE
    if lambda_card is None:
        lambda_card = compute_lambda_card(mu, cov, K)
    if gamma_sector is None:
        gamma_sector = compute_gamma_sector(lambda_card)

    mu_v = mu.values
    cov_m = cov.loc[assets, assets].values
    down_v = downside.loc[assets].values

    Q = q_risk * cov_m.copy()

    # Linear terms on diagonal.
    for i in range(n):
        Q[i, i] += -mu_v[i] + beta_downside * down_v[i]

    # Cardinality penalty: lambda * (sum x - K)^2.
    for i in range(n):
        Q[i, i] += lambda_card * (1.0 - 2.0 * K)
    for i in range(n):
        for j in range(i + 1, n):
            Q[i, j] += lambda_card
            Q[j, i] += lambda_card

    # Sector concentration penalty (pairwise same-sector).
    for i in range(n):
        si = sector_map.get(assets[i], "UNKNOWN")
        for j in range(i + 1, n):
            sj = sector_map.get(assets[j], "UNKNOWN")
            if si == sj:
                Q[i, j] += gamma_sector
                Q[j, i] += gamma_sector

    return QuboModel(Q=Q, assets=assets, lambda_card=lambda_card, gamma_sector=gamma_sector)


def qubo_energy(x: np.ndarray, Q: np.ndarray) -> float:
    return float(x.T @ Q @ x)
