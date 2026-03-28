from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd

from classical_optimizer import optimize_sharpe, optimize_sharpe_with_min_weight
from preprocessing import annualize_stats
from qubo import build_qubo
from annealing import select_assets_via_annealing
from real_world_execution import discrete_allocation, effective_portfolio_returns
from config_constants import (
    Q_RISK, BETA_DOWNSIDE, MAX_WEIGHT_PER_ASSET, RISK_FREE_RATE,
    MAX_ASSETS_PER_SECTOR, REBALANCE_CADENCE, LOOKBACK_WINDOW,
    TRANSACTION_COST
)


@dataclass
class RebalanceConfig:
    """Quarterly Rebalancing Configuration
    
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
    rebalance_days: int = REBALANCE_CADENCE
    lookback_days: int = LOOKBACK_WINDOW
    replace_frac: float = 0.2
    transaction_cost: float = TRANSACTION_COST


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
                new_w = optimize_sharpe_with_min_weight(mu_s, cov_s, rf=config.rf, w_max=config.max_weight, min_weight=0.02)

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


def run_quarterly_rebalance_with_discrete(
    train_returns: pd.DataFrame,
    test_returns: pd.DataFrame,
    test_prices: pd.DataFrame,
    sector_map: Dict[str, str],
    config: RebalanceConfig,
    initial_budget: float = 1_000_000,
) -> pd.Series:
    """
    Quarterly rebalancing with discrete share allocation at each rebalance point.
    
    Combines quarterly rebalancing logic with real-world discrete allocation:
    1. At each rebalance date (quarterly), apply discrete allocation
    2. Between rebalances, use effective weights (with cash contribution)
    3. Cash earns risk-free rate between rebalances
    4. Transaction costs applied at each rebalance
    
    Args:
    - train_returns: Training returns for lookback
    - test_returns: Test period returns
    - test_prices: Test period prices for discrete allocation
    - sector_map: Asset to sector mapping
    - config: RebalanceConfig with K, transaction_cost, etc.
    - initial_budget: Starting capital
    
    Returns:
    - Portfolio value series with discrete allocations
    """
    from evaluation import compute_metrics
    
    all_hist = train_returns.copy()
    dates = list(test_returns.index)
    portfolio_value = initial_budget
    
    K = min(config.K, len(train_returns.columns))
    selected = list(train_returns.columns[:K])
    weights = pd.Series(np.full(len(selected), 1.0 / len(selected)), index=selected)
    
    values = []
    current_allocation = None
    current_shares = {}
    current_cash = initial_budget
    rebalance_dates = []
    
    for i, dt in enumerate(dates):
        # Rebalance at quarter-like cadence
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

                # Re-run QUBO
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

                seeded_set = set(seeded)
                merged = list(dict.fromkeys(new_selected + list(seeded_set)))
                merged = merged[: min(K, len(merged))]

                mu_s = mu.loc[merged]
                cov_s = cov.loc[merged, merged]
                new_w = optimize_sharpe_with_min_weight(mu_s, cov_s, rf=config.rf, w_max=config.max_weight, min_weight=0.02)

                # Apply transaction costs
                prev_w = weights.reindex(new_w.index).fillna(0.0)
                turnover = float(np.abs(new_w - prev_w).sum())
                portfolio_value *= (1.0 - config.transaction_cost * turnover)

                selected = merged
                weights = new_w
                rebalance_dates.append(dt)
                
                # Apply discrete allocation at rebalance point
                current_prices = test_prices.loc[dt, weights.index].fillna(weights.loc[weights.index[0]])
                current_allocation = discrete_allocation(
                    target_weights=weights,
                    prices=current_prices,
                    budget=portfolio_value
                )
                current_shares = current_allocation.shares.to_dict()
                current_cash = current_allocation.cash
        
        # Compute return for this day with discrete allocation
        if current_allocation is not None:
            # Get today's returns for allocated assets
            day_returns = test_returns.loc[dt, list(current_shares.keys())].fillna(0.0)
            
            # Compute return from shares (dollar amounts change)
            share_return = sum(
                current_shares.get(asset, 0) * 
                test_prices.loc[dt, asset] * 
                (1 + day_returns[asset]) - 
                current_shares.get(asset, 0) * 
                test_prices.loc[dt, asset]
                for asset in day_returns.index
                if asset in current_shares
            )
            
            # Cash contribution: earning risk-free rate daily
            rf_daily = (1 + config.rf) ** (1/252) - 1
            cash_return = current_cash * rf_daily
            
            # Update portfolio value
            day_total_return = share_return + cash_return
            portfolio_value += day_total_return
            
            # Update prices for next iteration
            for asset in current_shares:
                if asset in test_prices.index:
                    current_prices[asset] = test_prices.loc[dt, asset] * (1 + day_returns.get(asset, 0))
        
        values.append(portfolio_value)
    
    # Normalize to unit (1.0 = initial value)
    normalized_values = [v / initial_budget for v in values]
    
    return pd.Series(normalized_values, index=test_returns.index, name="Quantum_Rebalanced_Discrete")

