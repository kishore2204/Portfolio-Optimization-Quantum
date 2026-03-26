from __future__ import annotations

from pathlib import Path
from typing import Dict

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from classical_optimizer import optimize_markowitz, optimize_sharpe
from evaluation import value_from_returns
from hybrid_optimizer import HybridConfig, portfolio_returns, run_quantum_hybrid_selection
from preprocessing import annualize_stats, log_returns
from rebalancing import RebalanceConfig, run_quarterly_rebalance


def _build_candidate_pool(returns: pd.DataFrame, k_target: int) -> list[str]:
    mu = returns.mean()
    vol = returns.std().replace(0.0, np.nan)
    sharpe_like = (mu / vol).replace([np.inf, -np.inf], np.nan).dropna()

    pool_n = min(returns.shape[1], max(4 * k_target, 100))
    candidates = list(sharpe_like.sort_values(ascending=False).head(pool_n).index)
    if len(candidates) < k_target:
        candidates = list(returns.columns)
    return candidates


def _normalize_to_one(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return s
    return s / s.iloc[0]


def _save_plot(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=220)
    plt.close()


def create_normal_15y_graphs(
    prices: pd.DataFrame,
    sector_map: Dict[str, str],
    output_dir: str | Path,
    rf: float = 0.05,
    k_ratio: float = 0.06,
    max_weight: float = 0.12,
    risk_aversion: float = 4.0,
) -> list[str]:
    """Generate 15-year normal-dataset graphs requested by user.

    Returns:
        Two output image paths.
    """
    out_dir = Path(output_dir)

    returns = log_returns(prices).dropna(how="all")
    if returns.empty:
        raise RuntimeError("Cannot create 15-year graphs: no returns available.")

    mu, cov, _ = annualize_stats(returns)

    n_assets = len(returns.columns)
    K = max(10, int(k_ratio * n_assets))
    K = min(K, n_assets)

    # Classical weights via top-K shortlist from Markowitz.
    w_mvo_all = optimize_markowitz(mu, cov, risk_aversion=risk_aversion, w_max=max_weight)
    top_assets = list(w_mvo_all.sort_values(ascending=False).head(K).index)
    w_classical = optimize_sharpe(mu.loc[top_assets], cov.loc[top_assets, top_assets], rf=rf, w_max=max_weight)
    classical_value = value_from_returns(portfolio_returns(returns, w_classical))
    classical_value.name = "Classical"

    # Quantum static portfolio on full period.
    hcfg = HybridConfig(K=K, max_weight=max_weight, rf=rf)
    candidate_assets = _build_candidate_pool(returns, K)
    _, q_weights = run_quantum_hybrid_selection(
        returns,
        sector_map,
        hcfg,
        candidate_assets=candidate_assets,
    )
    quantum_value = value_from_returns(portfolio_returns(returns, q_weights))
    quantum_value.name = "Quantum"

    # Rebalanced series over the full span with a short warmup for initialization.
    warmup_days = min(252, max(42, len(returns) // 8))
    train_r = returns.iloc[:warmup_days].copy()
    test_r = returns.iloc[warmup_days:].copy()
    if test_r.empty:
        raise RuntimeError("Cannot create 15-year rebalanced curve: not enough observations.")

    rcfg = RebalanceConfig(K=K, max_weight=max_weight, rf=rf)
    q_rebal_test = run_quarterly_rebalance(train_r, test_r, sector_map, rcfg)

    warmup_curve = quantum_value.loc[train_r.index]
    warmup_last = float(warmup_curve.iloc[-1]) if not warmup_curve.empty else 1.0
    q_rebalanced_full = pd.concat([warmup_curve, q_rebal_test * warmup_last])
    q_rebalanced_full = q_rebalanced_full[~q_rebalanced_full.index.duplicated(keep="last")]
    q_rebalanced_full.name = "Quantum_Rebalanced"

    combined = pd.DataFrame(
        {
            "Classical": _normalize_to_one(classical_value),
            "Quantum": _normalize_to_one(quantum_value),
            "Quantum_Rebalanced": _normalize_to_one(q_rebalanced_full),
        }
    ).dropna(how="all")
    combined = combined.ffill().bfill()

    values_csv = out_dir / "normal_15y_portfolio_values.csv"
    combined.to_csv(values_csv)

    # Graph A: Classical vs Quantum vs Quantum Rebalanced (full period)
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.figure(figsize=(13, 7))
    for name, color in [
        ("Classical", "#2ca02c"),
        ("Quantum", "#1f77b4"),
        ("Quantum_Rebalanced", "#ff7f0e"),
    ]:
        if name in combined.columns:
            plt.plot(combined.index, combined[name], label=name, linewidth=2.2, color=color)
    plt.title("15-Year Normal Dataset: Classical vs Quantum vs Quantum Rebalanced")
    plt.xlabel("Date")
    plt.ylabel("Normalized Portfolio Value")
    plt.legend()
    path_1 = out_dir / "15y_1_classical_vs_quantum_vs_rebalanced.png"
    _save_plot(path_1)

    # Graph B: Quantum vs Quantum Rebalanced (full period)
    plt.figure(figsize=(13, 7))
    for name, color in [
        ("Quantum", "#1f77b4"),
        ("Quantum_Rebalanced", "#ff7f0e"),
    ]:
        if name in combined.columns:
            plt.plot(combined.index, combined[name], label=name, linewidth=2.4, color=color)
    plt.title("15-Year Normal Dataset: Quantum vs Quantum Rebalanced")
    plt.xlabel("Date")
    plt.ylabel("Normalized Portfolio Value")
    plt.legend()
    path_2 = out_dir / "15y_2_quantum_vs_quantum_rebalanced.png"
    _save_plot(path_2)

    return [str(path_1), str(path_2)]
