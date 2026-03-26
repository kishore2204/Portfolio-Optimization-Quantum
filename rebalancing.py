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
class RebalanceConfig:
    K: int = 25
    max_weight: float = 0.12
    rf: float = 0.05
    q_risk: float = 1.0
    beta_downside: float = 0.5
    lambda_card: float = 5.0
    gamma_sector: float = 0.5
    max_per_sector: int = 4
    rebalance_days: int = 63
    lookback_days: int = 252
    replace_frac: float = 0.2
    transaction_cost: float = 0.001


def _underperformers(selected: List[str], lookback: pd.DataFrame, frac: float) -> List[str]:
    k = max(1, int(len(selected) * frac))
    perf = lookback[selected].mean().sort_values(ascending=True)
    return list(perf.head(k).index)


def _replace_same_sector(
    selected: List[str],
    to_replace: List[str],
    universe: List[str],
    sector_map: Dict[str, str],
    lookback: pd.DataFrame,
) -> List[str]:
    selected_set = set(selected)
    mu = lookback.mean()

    for old in to_replace:
        old_sector = sector_map.get(old, "UNKNOWN")
        candidates = [
            s
            for s in universe
            if s not in selected_set and sector_map.get(s, "UNKNOWN") == old_sector
        ]
        if not candidates:
            candidates = [s for s in universe if s not in selected_set]
        if not candidates:
            continue

        new_s = max(candidates, key=lambda s: float(mu.get(s, -np.inf)))
        selected_set.discard(old)
        selected_set.add(new_s)

    return list(selected_set)


def run_quarterly_rebalance(
    train_returns: pd.DataFrame,
    test_returns: pd.DataFrame,
    sector_map: Dict[str, str],
    config: RebalanceConfig,
) -> pd.Series:
    all_hist = train_returns.copy()
    dates = list(test_returns.index)
    value = 1.0

    K = min(config.K, len(train_returns.columns))
    selected = list(train_returns.columns[:K])
    weights = pd.Series(np.full(len(selected), 1.0 / len(selected)), index=selected)

    values = []

    for i, dt in enumerate(dates):
        # Rebalance at quarter-like cadence.
        if i % config.rebalance_days == 0:
            lookback = all_hist.tail(config.lookback_days)
            if lookback.shape[0] > 20:
                valid_universe = [c for c in lookback.columns if lookback[c].notna().mean() > 0.9]
                selected = [s for s in selected if s in valid_universe]
                if len(selected) < max(3, K // 2):
                    selected = valid_universe[:K]

                to_drop = _underperformers(selected, lookback, config.replace_frac)
                seeded = _replace_same_sector(
                    selected=selected,
                    to_replace=to_drop,
                    universe=valid_universe,
                    sector_map=sector_map,
                    lookback=lookback,
                )

                # Re-run QUBO on a dynamic candidate pool (paper-style hybrid refresh).
                look_mu = lookback[valid_universe].mean()
                look_vol = lookback[valid_universe].std().replace(0.0, np.nan)
                score = (look_mu / look_vol).replace([np.inf, -np.inf], np.nan).dropna()

                pool_n = min(len(valid_universe), max(4 * K, 100))
                candidate_universe = list(score.sort_values(ascending=False).head(pool_n).index)
                if len(candidate_universe) < min(K, len(valid_universe)):
                    candidate_universe = valid_universe

                mu, cov, downside = annualize_stats(lookback[candidate_universe])
                qubo_model = build_qubo(
                    mu=mu,
                    cov=cov,
                    downside=downside,
                    sector_map=sector_map,
                    K=min(K, len(candidate_universe)),
                    q_risk=config.q_risk,
                    beta_downside=config.beta_downside,
                    lambda_card=config.lambda_card,
                    gamma_sector=config.gamma_sector,
                )
                new_selected, _ = select_assets_via_annealing(
                    Q=qubo_model.Q,
                    assets=qubo_model.assets,
                    sector_map=sector_map,
                    K=min(K, len(candidate_universe)),
                    max_per_sector=config.max_per_sector,
                )

                # Keep seeded replacements if QUBO misses them and capacity exists.
                seeded_set = set(seeded)
                merged = list(dict.fromkeys(new_selected + list(seeded_set)))
                merged = merged[: min(K, len(merged))]

                mu_s = mu.loc[merged]
                cov_s = cov.loc[merged, merged]
                new_w = optimize_sharpe(mu_s, cov_s, rf=config.rf, w_max=config.max_weight)

                prev_w = weights.reindex(new_w.index).fillna(0.0)
                turnover = float(np.abs(new_w - prev_w).sum())
                value *= (1.0 - config.transaction_cost * turnover)

                selected = merged
                weights = new_w

        day_r = test_returns.loc[dt, weights.index].fillna(0.0).values @ weights.values
        value *= float(np.exp(day_r))
        values.append(value)

        all_hist.loc[dt, test_returns.columns] = test_returns.loc[dt]

    return pd.Series(values, index=test_returns.index, name="Quantum_Rebalanced")
