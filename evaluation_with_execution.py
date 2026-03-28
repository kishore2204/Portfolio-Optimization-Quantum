"""
Enhanced Evaluation with Real-World Execution Layer

Extends evaluation.py to incorporate:
1. Discrete share allocation
2. Cash management
3. Transaction costs
4. Effective portfolio returns (asset + cash contributions)

This bridges the gap between theoretical optimization and practical trading.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

from evaluation import max_drawdown, compute_metrics
from real_world_execution import (
    discrete_allocation,
    effective_portfolio_returns,
    apply_transaction_cost,
    rebalance_allocation,
    AllocationResult,
)


def portfolio_value_with_execution(
    prices_df: pd.DataFrame,
    returns_df: pd.DataFrame,
    target_weights: pd.Series,
    initial_budget: float = 1_000_000,
    risk_free_rate: float = 0.05,
    rebalance_dates: Optional[list] = None,
    transaction_cost_rate: float = 0.002,
) -> Tuple[pd.Series, Dict]:
    """
    Compute portfolio value with real-world execution constraints.

    Applies discrete share allocation, cash management, and transaction costs
    throughout the backtesting period.

    Args:
    - prices_df: DataFrame with daily prices (rows=dates, cols=assets)
    - returns_df: DataFrame with daily returns (rows=dates, cols=assets)
    - target_weights: Series with target weights (from SLSQP)
    - initial_budget: Starting capital (e.g., $1M)
    - risk_free_rate: Annual rate for cash (e.g., 0.05 = 5%)
    - rebalance_dates: List of dates when to rebalance (None = no rebalancing)
    - transaction_cost_rate: Cost per unit turnover (e.g., 0.002 = 0.2%)

    Returns:
    - (portfolio_values, execution_stats)
      * portfolio_values: pd.Series of portfolio value over time
      * execution_stats: Dict with allocation, cash, effective weights, etc.
    """
    # Align dates
    dates = returns_df.index
    budget = initial_budget

    # Initial allocation
    prices_t0 = prices_df.loc[dates[0]]
    alloc = discrete_allocation(target_weights, prices_t0, budget)

    portfolio_values = []
    allocations = []
    effective_weights_history = []
    cash_history = []
    turnover_costs = []

    # Forward-simulate
    daily_rf = risk_free_rate / 252.0

    for i, dt in enumerate(dates):
        # Rebalance if scheduled
        if rebalance_dates and dt in rebalance_dates:
            prices_rebal = prices_df.loc[dt]
            new_alloc, rebal_cost = rebalance_allocation(
                prices_rebal, target_weights, alloc
            )
            alloc = new_alloc
            turnover_costs.append(rebal_cost)
        else:
            turnover_costs.append(0.0)

        # Compute portfolio value
        daily_returns = returns_df.loc[dt]
        port_return = effective_portfolio_returns(
            returns_df.iloc[[i]], alloc, risk_free_rate
        )
        r_today = float(port_return.iloc[0])

        # Apply transaction cost on rebalance day
        r_today -= turnover_costs[i]

        # Update budget
        budget = budget * (1 + r_today)

        portfolio_values.append(budget)
        allocations.append(alloc)
        effective_weights_history.append(alloc.effective_weights.copy())
        cash_history.append(alloc.cash)

    # Convert to Series
    portfolio_series = pd.Series(portfolio_values, index=dates)
    portfolio_series.name = "Real_World_Execution"

    # Compute stats
    final_value = portfolio_values[-1]
    total_return = (final_value / initial_budget) - 1.0
    total_turnover_cost = sum(turnover_costs)

    stats = {
        "initial_budget": initial_budget,
        "final_value": final_value,
        "total_return_percent": total_return * 100,
        "total_turnover_cost_percent": total_turnover_cost * 100,
        "average_cash_weight": np.mean([a.cash_weight for a in allocations]),
        "number_of_rebalances": len([c for c in turnover_costs if c > 0.001]),
    }

    return portfolio_series, stats


def compare_theoretical_vs_realistic(
    prices_df: pd.DataFrame,
    returns_df: pd.DataFrame,
    target_weights: pd.Series,
    initial_budget: float = 1_000_000,
    risk_free_rate: float = 0.05,
) -> pd.DataFrame:
    """
    Compare theoretical (fractional weights) vs realistic (discrete shares) execution.

    Shows the impact of:
    1. Discrete share rounding
    2. Cash drag
    3. Transaction costs

    Returns:
    - DataFrame comparing metrics side-by-side
    """
    # Theoretical: use fractional weights directly (current approach)
    if target_weights.sum() > 0:
        w_norm = target_weights / target_weights.sum()
    else:
        w_norm = pd.Series(1.0 / len(target_weights), index=target_weights.index)

    common = [a for a in w_norm.index if a in returns_df.columns]
    w_norm = w_norm.loc[common]

    theoretical_returns = returns_df[common] @ w_norm.values
    theoretical_value = initial_budget * np.exp(theoretical_returns.cumsum())

    # Realistic: use discrete allocation
    realistic_value, stats = portfolio_value_with_execution(
        prices_df, returns_df, target_weights, initial_budget, risk_free_rate
    )

    # Compare
    comparison = pd.DataFrame({
        "Theoretical": theoretical_value,
        "Realistic": realistic_value,
    })
    comparison["Difference_$"] = realistic_value - theoretical_value
    comparison["Difference_%"] = (realistic_value / theoretical_value - 1.0) * 100

    return comparison


def enhanced_metrics_table(
    portfolio_values: Dict[str, pd.Series],
    prices_df: Optional[pd.DataFrame] = None,
    returns_df: Optional[pd.DataFrame] = None,
    target_weights: Optional[pd.Series] = None,
    rf: float = 0.05,
    initial_budget: float = 1_000_000,
) -> pd.DataFrame:
    """
    Extended metrics table including real-world execution impact.

    If execution parameters provided, computes:
    - Theoretical metrics (fractional weights)
    - Realistic metrics (discrete shares)
    - Impact of execution layer

    Args:
    - portfolio_values: Dict[name → pd.Series]
    - prices_df, returns_df, target_weights: for execution analysis
    - rf: risk-free rate
    - initial_budget: starting capital

    Returns:
    - pd.DataFrame with comprehensive metrics
    """
    # Standard metrics
    data = {}
    for name, v in portfolio_values.items():
        data[name] = compute_metrics(v, rf=rf)

    df = pd.DataFrame(data).T

    # Add execution analysis if provided
    if (prices_df is not None and returns_df is not None and
            target_weights is not None):
        comparison = compare_theoretical_vs_realistic(
            prices_df, returns_df, target_weights, initial_budget, rf
        )

        # Add execution metrics
        df["Theoretical_Return_%"] = (
            (comparison["Theoretical"].iloc[-1] / initial_budget - 1.0) * 100
        )
        df["Realistic_Return_%"] = (
            (comparison["Realistic"].iloc[-1] / initial_budget - 1.0) * 100
        )
        df["Execution_Impact_%"] = (
            df["Realistic_Return_%"] - df["Theoretical_Return_%"]
        )

    return df
