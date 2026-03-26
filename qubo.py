from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd


@dataclass
class QuboModel:
    Q: np.ndarray
    assets: List[str]


def build_qubo(
    mu: pd.Series,
    cov: pd.DataFrame,
    downside: pd.Series,
    sector_map: Dict[str, str],
    K: int,
    q_risk: float = 1.0,
    beta_downside: float = 0.5,
    lambda_card: float = 4.0,
    gamma_sector: float = 0.3,
) -> QuboModel:
    assets = list(mu.index)
    n = len(assets)

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

    return QuboModel(Q=Q, assets=assets)


def qubo_energy(x: np.ndarray, Q: np.ndarray) -> float:
    return float(x.T @ Q @ x)
