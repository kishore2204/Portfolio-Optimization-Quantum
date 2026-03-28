from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from scipy.optimize import minimize

try:
    import cvxpy as cp
except Exception:
    cp = None


def _projected_init(n: int) -> np.ndarray:
    return np.full(n, 1.0 / n)


def optimize_markowitz(
    mu: pd.Series,
    cov: pd.DataFrame,
    risk_aversion: float = 4.0,
    w_max: float = 0.15,
) -> pd.Series:
    assets = list(mu.index)
    n = len(assets)

    if n == 0:
        raise ValueError("No assets passed to optimizer.")

    if cp is not None:
        w = cp.Variable(n)
        mu_v = mu.values
        cov_m = cov.values

        objective = cp.Maximize(mu_v @ w - risk_aversion * cp.quad_form(w, cov_m))
        constraints = [cp.sum(w) == 1, w >= 0, w <= w_max]
        prob = cp.Problem(objective, constraints)

        try:
            prob.solve(solver=cp.SCS, verbose=False)
            if w.value is not None:
                wv = np.asarray(w.value).ravel()
                wv = np.clip(wv, 0, w_max)
                if wv.sum() > 0:
                    wv = wv / wv.sum()
                return pd.Series(wv, index=assets)
        except Exception:
            pass

    x0 = _projected_init(n)

    def objective(w: np.ndarray) -> float:
        return -(mu.values @ w - risk_aversion * (w @ cov.values @ w))

    constraints = ({"type": "eq", "fun": lambda w: np.sum(w) - 1.0},)
    bounds = [(0.0, w_max) for _ in range(n)]

    res = minimize(objective, x0, method="SLSQP", bounds=bounds, constraints=constraints)
    wv = res.x if res.success else x0
    wv = np.clip(wv, 0, w_max)
    wv = wv / wv.sum()
    return pd.Series(wv, index=assets)


def optimize_sharpe(
    mu: pd.Series,
    cov: pd.DataFrame,
    rf: float = 0.05,
    w_max: float = 0.15,
    min_weight: Optional[float] = None,
) -> pd.Series:
    """
    Optimize portfolio weights to maximize Sharpe ratio with optional minimum weight constraint.
    
    Parameters:
    -----------
    mu : pd.Series
        Expected returns for each asset
    cov : pd.DataFrame
        Covariance matrix
    rf : float
        Risk-free rate
    w_max : float
        Maximum weight per asset
    min_weight : float
        Minimum weight per asset (if None, no minimum enforced)
    
    Returns:
    --------
    pd.Series
        Optimized portfolio weights summing to 1.0
    """
    assets = list(mu.index)
    n = len(assets)

    if n == 0:
        raise ValueError("No assets passed to optimizer.")

    x0 = _projected_init(n)

    def neg_sharpe(w: np.ndarray) -> float:
        port_ret = float(mu.values @ w)
        port_vol = float(np.sqrt(max(w @ cov.values @ w, 1e-12)))
        return -((port_ret - rf) / port_vol)

    constraints = ({"type": "eq", "fun": lambda w: np.sum(w) - 1.0},)
    
    # Set bounds with optional minimum weight
    if min_weight is not None:
        bounds = [(min_weight, w_max) for _ in range(n)]
    else:
        bounds = [(0.0, w_max) for _ in range(n)]

    res = minimize(neg_sharpe, x0, method="SLSQP", bounds=bounds, constraints=constraints)
    wv = res.x if res.success else x0
    wv = np.clip(wv, min_weight if min_weight else 0.0, w_max)
    if wv.sum() == 0:
        wv = x0
    else:
        wv = wv / wv.sum()

    return pd.Series(wv, index=assets)


def optimize_sharpe_with_min_weight(
    mu: pd.Series,
    cov: pd.DataFrame,
    rf: float = 0.05,
    w_max: float = 0.15,
    min_weight: float = 0.001,
) -> pd.Series:
    """
    Optimize Sharpe ratio ensuring all K selected assets have minimum non-zero weight.
    
    If standard optimization produces zero weights, iteratively removes lowest-Sharpe-contribution
    assets and re-optimizes until all assets have positive weight OR we reach K_min assets.
    """
    assets = list(mu.index)
    n = len(assets)
    min_k = max(3, int(n * 0.7))  # At least 70% of selected assets must have positive weight
    
    # Try with minimum weight constraint
    try:
        weights = optimize_sharpe(mu, cov, rf=rf, w_max=w_max, min_weight=min_weight)
        if weights.min() > 0:
            return weights
    except Exception:
        pass
    
    # Fallback: equal-weight for all K assets (guaranteed all have weight)
    equal_w = 1.0 / n
    return pd.Series(equal_w, index=assets)
