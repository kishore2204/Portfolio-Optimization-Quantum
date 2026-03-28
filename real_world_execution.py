"""
Real-World Execution Layer for Portfolio Optimization

Converts theoretical QUBO/Sharpe optimization results into practical
discrete share allocations with cash management.

### STEP 7: REAL-WORLD ADJUSTMENT LAYER ###

This module implements the bridge between mathematical optimization
(which uses continuous fractional weights) and actual trading execution
(which requires discrete shares, cash, and transaction costs).

## Pipeline:

1. DISCRETE SHARE ALLOCATION
   - shares_i = floor(allocation_i / price_i)

2. CASH HANDLING
   - cash = budget - sum(invested_i)

3. EFFECTIVE WEIGHTS
   - w_i_actual = (shares_i × price_i) / budget
   - w_cash = cash / budget

4. PORTFOLIO RETURN
   - R = sum(w_i_actual × r_i) + w_cash × r_f

5. TRANSACTION COST
   - cost = turnover × transaction_cost_rate

References:
- Mathematical formulation: Technical Prompt, Step 7
- Implementation: See discrete_allocation() and effective_portfolio_returns()
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
import pandas as pd


@dataclass
class AllocationResult:
    """Result of real-world share allocation"""
    shares: pd.Series  # Number of whole shares per asset
    invested: pd.Series  # Dollar amount invested in each asset
    cash: float  # Remaining cash after allocation
    effective_weights: pd.Series  # Actual portfolio weights w_i^actual
    cash_weight: float  # Weight in risk-free asset w_cash
    budget: float  # Initial budget


def discrete_allocation(
    target_weights: pd.Series,
    prices: pd.Series,
    budget: float,
) -> AllocationResult:
    """
    Convert theoretical weights to discrete shares with cash.

    ### STEP 7.1: DISCRETE SHARE ALLOCATION ###

    Input:
    - target_weights: w_i (fractional, 0-1, may not sum to 1)
    - prices: P_i (current asset prices)
    - budget: B (initial capital)

    Process:
    1. allocation_i = w_i × B
    2. shares_i = floor(allocation_i / P_i)
    3. invested_i = shares_i × P_i
    4. cash = B - sum(invested_i)

    Output:
    - AllocationResult with shares, invested, cash
    """
    # Normalize weights to sum to 1 (in case SLSQP didn't perfectly)
    if target_weights.sum() > 0:
        w_norm = target_weights / target_weights.sum()
    else:
        # Fallback: equal weight
        w_norm = pd.Series(1.0 / len(target_weights), index=target_weights.index)

    # Align prices and weights
    common = [a for a in w_norm.index if a in prices.index]
    w_norm = w_norm.loc[common]
    p = prices.loc[common]

    # Allocate budget
    allocations = w_norm * budget  # Dollar amount per asset

    # Convert to shares (floor)
    shares = (allocations / p).astype(int)

    # Calculate actual invested amount
    invested = shares * p
    invested_dict = pd.Series(invested.values, index=shares.index)

    # Remaining cash
    cash = float(budget - invested.sum())
    if cash < 0:
        cash = 0.0

    # Effective weights (Step 7.3)
    total_value = invested.sum() + cash
    if total_value > 0:
        effective_weights = invested / total_value
        cash_weight = cash / total_value
    else:
        effective_weights = pd.Series(0.0, index=shares.index)
        cash_weight = 1.0

    return AllocationResult(
        shares=shares,
        invested=invested_dict,
        cash=cash,
        effective_weights=effective_weights,
        cash_weight=cash_weight,
        budget=budget,
    )


def effective_portfolio_returns(
    returns: pd.DataFrame,
    allocation: AllocationResult,
    risk_free_rate: float = 0.05,
) -> pd.Series:
    """
    Compute portfolio returns incorporating cash as risk-free asset.

    ### STEP 7.4: PORTFOLIO RETURN ###

    R_t = sum(w_i^actual × r_{t,i}) + w_cash × r_f

    Where:
    - w_i^actual: actual weight in asset i
    - r_{t,i}: asset i return at time t
    - w_cash: cash weight
    - r_f: risk-free rate (annualized, convert to daily)

    Args:
    - returns: DataFrame, daily returns (T × N)
    - allocation: AllocationResult with effective weights
    - risk_free_rate: annual rate (e.g., 0.05 = 5%)

    Returns:
    - pd.Series: daily portfolio returns
    """
    daily_rf = risk_free_rate / 252.0  # Annualized to daily

    # Align returns with allocation
    common = [a for a in allocation.effective_weights.index if a in returns.columns]
    w_actual = allocation.effective_weights.loc[common]
    r = returns[common]

    # Weighted asset returns
    asset_contribution = (r.values @ w_actual.values)  # Shape: (T,)

    # Cash contribution
    cash_contribution = allocation.cash_weight * daily_rf

    # Total portfolio return
    portfolio_r = asset_contribution + cash_contribution

    return pd.Series(portfolio_r, index=returns.index)


def apply_transaction_cost(
    portfolio_returns: pd.Series,
    prev_allocation: AllocationResult,
    current_allocation: AllocationResult,
    transaction_cost_rate: float = 0.002,
) -> pd.Series:
    """
    Apply transaction costs based on portfolio turnover.

    ### STEP 7.5: TRANSACTION COST ###

    When rebalancing:
    1. Turnover = sum(|w_i^new - w_i^old|) / 2
    2. Cost = turnover × transaction_cost_rate
    3. Apply on first day only (impulsive cost)

    Args:
    - portfolio_returns: daily returns before costs
    - prev_allocation: previous portfolio allocation
    - current_allocation: new portfolio allocation
    - transaction_cost_rate: e.g., 0.002 = 0.2% per turnover unit

    Returns:
    - pd.Series: returns with transaction costs applied on day 1
    """
    # Compute turnover
    common_assets = [
        a for a in prev_allocation.effective_weights.index
        if a in current_allocation.effective_weights.index
    ]

    if not common_assets:
        # No overlap, 100% turnover
        turnover = 1.0
    else:
        prev_w = prev_allocation.effective_weights.loc[common_assets]
        curr_w = current_allocation.effective_weights.loc[common_assets]
        turnover = float(np.abs(curr_w - prev_w).sum()) / 2.0

    # Apply cost on first day
    costs = np.zeros(len(portfolio_returns))
    costs[0] = -turnover * transaction_cost_rate

    return portfolio_returns + costs


def rebalance_allocation(
    current_prices: pd.Series,
    new_weights: pd.Series,
    current_allocation: AllocationResult,
) -> Tuple[AllocationResult, float]:
    """
    Rebalance portfolio to new weights.

    When rebalancing:
    1. Liquidate current holdings
    2. Allocate based on new weights
    3. Calculate turnover cost

    Args:
    - current_prices: current asset prices
    - new_weights: target weights from optimization
    - current_allocation: current portfolio state

    Returns:
    - (new_allocation, turnover_cost)
    """
    # Total portfolio value
    total_value = current_allocation.invested.sum() + current_allocation.cash

    # New allocation at current prices
    new_alloc = discrete_allocation(new_weights, current_prices, total_value)

    # Turnover cost
    common = [a for a in current_allocation.effective_weights.index
              if a in new_alloc.effective_weights.index]

    if common:
        prev_w = current_allocation.effective_weights.loc[common]
        new_w = new_alloc.effective_weights.loc[common]
        turnover = float(np.abs(new_w - prev_w).sum()) / 2.0
    else:
        turnover = 1.0

    turnover_cost = turnover * 0.002  # 0.2% per unit turnover

    return new_alloc, turnover_cost


# ============================================================================
# VALIDATION & DIAGNOSTICS
# ============================================================================

def validate_allocation(alloc: AllocationResult, prices: pd.Series) -> dict:
    """
    Validate allocation for consistency.

    Returns dict with checks:
    - budget_respected: budget ≤ initial
    - weights_sum_to_one: effective weights sum to 1.0
    - cash_non_negative: cash ≥ 0
    - shares_non_negative: all shares ≥ 0
    """
    total_invested = alloc.invested.sum() + alloc.cash
    budget_ok = total_invested <= alloc.budget * 1.01  # 1% tolerance for rounding

    weights_ok = abs(alloc.effective_weights.sum() + alloc.cash_weight - 1.0) < 0.01
    cash_ok = alloc.cash >= -0.01  # Allow tiny rounding errors
    shares_ok = (alloc.shares >= 0).all()

    return {
        "budget_respected": budget_ok,
        "weights_sum_to_one": weights_ok,
        "cash_non_negative": cash_ok,
        "shares_non_negative": shares_ok,
        "all_valid": budget_ok and weights_ok and cash_ok and shares_ok,
        "total_invested": float(total_invested),
        "cash_remaining": float(alloc.cash),
    }


def allocation_summary(alloc: AllocationResult) -> pd.DataFrame:
    """
    Pretty-print allocation summary.

    Returns DataFrame with columns:
    - Asset
    - Shares
    - Price (reconstructed from invested/shares)
    - Invested
    - Weight
    """
    shares = alloc.shares
    invested = alloc.invested
    weights = alloc.effective_weights

    # Reconstruct prices where possible
    prices_reconstructed = invested / shares.replace(0, 1)

    df = pd.DataFrame({
        "Asset": invested.index,
        "Shares": shares.values,
        "Invested_Value": invested.values,
        "Weight_%": (weights.values * 100).round(2),
    })

    # Add cash row
    cash_row = pd.DataFrame({
        "Asset": ["CASH"],
        "Shares": [1.0],
        "Invested_Value": [alloc.cash],
        "Weight_%": [alloc.cash_weight * 100],
    })

    return pd.concat([df, cash_row], ignore_index=True)
