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
) -> pd.Series:
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
    bounds = [(0.0, w_max) for _ in range(n)]

    res = minimize(neg_sharpe, x0, method="SLSQP", bounds=bounds, constraints=constraints)
    wv = res.x if res.success else x0
    wv = np.clip(wv, 0, w_max)
    if wv.sum() == 0:
        wv = x0
    else:
        wv = wv / wv.sum()

    return pd.Series(wv, index=assets)
