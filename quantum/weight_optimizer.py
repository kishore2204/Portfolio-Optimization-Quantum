"""
Weight Optimizer Module - SLSQP Sharpe Ratio Maximization
==========================================================

Implements classical weight optimization using Sequential Least Squares Programming (SLSQP).
This replaces equal-weight allocation
with optimized allocations.

Key Features:
- Sharpe ratio maximization
- Long-only constraints (no short-selling)
- Sum-to-one constraint (100% capital allocation)
- Handles edge cases (singular matrices, optimization failures)
- Dynamic risk-free rate support

Author: Enhanced Quantum Portfolio Team
Date: March 12, 2026
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


def get_dynamic_risk_free_rate(date: pd.Timestamp = None) -> float:
    """
    Get dynamic risk-free rate based on date (RBI repo rate proxy).
    
    Args:
        date: Date to get rate for. If None, uses latest (6%)
        
    Returns:
        Annual risk-free rate (e.g., 0.06 for 6%)
        
    Historical Indian RBI repo rates:
    - 2020-2021: 4.0% (COVID stimulus)
    - 2022-2023: 6.5% (inflation fighting)
    - 2024-2026: 6.0% (normalized)
    """
    if date is None:
        return 0.06  # Default 6%
    
    year = date.year
    
    if year <= 2020:
        return 0.06  # Pre-COVID
    elif year <= 2021:
        return 0.04  # COVID stimulus
    elif year <= 2023:
        return 0.065  # Inflation fighting
    else:
        return 0.06  # Normalized
        

def optimize_sharpe_slsqp(
    selected_stocks: List,
    mean_returns: np.ndarray,
    cov_matrix: np.ndarray,
    risk_free_rate: float = None,
    max_weight: float = 0.40,
    min_weight: float = 0.0,
    verbose: bool = False
) -> Tuple[np.ndarray, dict]:
    """
    Optimize portfolio weights using SLSQP to maximize Sharpe ratio.
    
    This is the core continuous allocation step.
    Instead of equal weights (1/K), we optimize weights to maximize
    risk-adjusted returns.
    
    Args:
        selected_stocks: List of selected stock indices
        mean_returns: Annual mean returns for all stocks (N,)
        cov_matrix: Annual covariance matrix (N, N)
        risk_free_rate: Annual risk-free rate (default: 6%)
        max_weight: Maximum weight per stock (default: 40%)
        min_weight: Minimum weight per stock (default: 0%)
        verbose: Print optimization details
        
    Returns:
        Tuple of (weights, info_dict):
        - weights: Optimized weight vector (n_selected,)
        - info_dict: Optimization details (Sharpe, return, volatility, etc.)
        
    Example:
        > selected = [0, 5, 12]  # INFY, TCS, HDFCBANK
        > weights, info = optimize_sharpe_slsqp(selected, mean_returns, cov_matrix)
        > # weights might be [0.35, 0.42, 0.23] instead of [0.33, 0.33, 0.33]
    """
    if risk_free_rate is None:
        risk_free_rate = get_dynamic_risk_free_rate()
    
    n_selected = len(selected_stocks)
    
    # Extract sub-matrices for selected stocks only
    mean_returns_selected = mean_returns[selected_stocks]
    cov_matrix_selected = cov_matrix[np.ix_(selected_stocks, selected_stocks)]
    
    # Add regularization to prevent singular matrix issues
    epsilon = 1e-8
    cov_matrix_selected = cov_matrix_selected + epsilon * np.eye(n_selected)
    
    # Objective function: Minimize negative Sharpe ratio (= Maximize Sharpe)
    def neg_sharpe_ratio(weights: np.ndarray) -> float:
        """Calculate negative Sharpe ratio (for minimization)"""
        portfolio_return = np.dot(weights, mean_returns_selected)
        portfolio_volatility = np.sqrt(
            np.dot(weights, np.dot(cov_matrix_selected, weights))
        )
        
        # Avoid division by zero
        if portfolio_volatility < 1e-10:
            return 1e10  # Very high penalty
        
        sharpe = (portfolio_return - risk_free_rate) / portfolio_volatility
        return -sharpe  # Negative because we minimize
    
    # Constraints
    constraints = [
        {
            'type': 'eq',
            'fun': lambda w: np.sum(w) - 1.0  # Sum to 100%
        }
    ]
    
    # Bounds: Each weight between min_weight and max_weight
    bounds = [(min_weight, max_weight) for _ in range(n_selected)]
    
    # Initial guess: Equal weights
    w0 = np.array([1.0 / n_selected] * n_selected)
    
    # Optimize using SLSQP
    try:
        result = minimize(
            neg_sharpe_ratio,
            w0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={
                'ftol': 1e-9,
                'maxiter': 1000,
                'disp': verbose
            }
        )
        
        if not result.success:
            logger.warning(f"SLSQP optimization warning: {result.message}")
            logger.warning("Falling back to equal weights")
            weights = w0
        else:
            weights = result.x
            
    except Exception as e:
        logger.error(f"SLSQP optimization failed: {e}")
        logger.error("Using equal weights as fallback")
        weights = w0
    
    # Normalize to ensure sum = 1.0 (numerical precision)
    weights = weights / np.sum(weights)
    
    # Calculate final portfolio statistics
    portfolio_return = np.dot(weights, mean_returns_selected)
    portfolio_volatility = np.sqrt(
        np.dot(weights, np.dot(cov_matrix_selected, weights))
    )
    sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_volatility
    
    # Build info dictionary
    info = {
        'sharpe_ratio': sharpe_ratio,
        'portfolio_return': portfolio_return,
        'portfolio_volatility': portfolio_volatility,
        'risk_free_rate': risk_free_rate,
        'n_stocks': n_selected,
        'max_weight': np.max(weights),
        'min_weight': np.min(weights),
        'optimization_success': result.success if 'result' in locals() else False
    }
    
    if verbose:
        print("\n" + "="*60)
        print("SLSQP WEIGHT OPTIMIZATION RESULTS")
        print("="*60)
        print(f"Portfolio Return:     {portfolio_return:.2%}")
        print(f"Portfolio Volatility: {portfolio_volatility:.2%}")
        print(f"Sharpe Ratio:         {sharpe_ratio:.3f}")
        print(f"Risk-Free Rate:       {risk_free_rate:.2%}")
        print(f"\nWeight Distribution:")
        print(f"  Max Weight:         {np.max(weights):.2%}")
        print(f"  Min Weight:         {np.min(weights):.2%}")
        print(f"  Std Dev:            {np.std(weights):.2%}")
        print("="*60 + "\n")
    
    return weights, info


def create_full_weight_vector(
    selected_stocks: List,
    optimized_weights: np.ndarray,
    n_total_stocks: int
) -> np.ndarray:
    """
    Create full weight vector with zeros for non-selected stocks.
    
    Args:
        selected_stocks: List of selected stock indices
        optimized_weights: Optimized weights for selected stocks
        n_total_stocks: Total number of stocks in universe
        
    Returns:
        Full weight vector (n_total_stocks,) with non-selected = 0
        
    Example:
        > selected = [2, 5, 8]
        > weights_opt = [0.40, 0.35, 0.25]
        > full_weights = create_full_weight_vector(selected, weights_opt, 50)
        > # full_weights[2]=0.40, full_weights[5]=0.35, full_weights[8]=0.25
        > # all others = 0.0
    """
    full_weights = np.zeros(n_total_stocks)
    full_weights[selected_stocks] = optimized_weights
    return full_weights


def optimize_portfolio_weights(
    selected_stocks: List,
    train_data: pd.DataFrame,
    risk_free_rate: float = None,
    verbose: bool = False
) -> Tuple[np.ndarray, dict]:
    """
    End-to-end weight optimization from training data.
    
    This is a convenience wrapper that:
    1. Calculates returns, mean, covariance from train_data
    2. Runs SLSQP optimization
    3. Returns full weight vector
    
    Args:
        selected_stocks: List of selected stock indices or names
        train_data: Training price data (DataFrame with stock columns)
        risk_free_rate: Risk-free rate (default: dynamic based on date)
        verbose: Print optimization details
        
    Returns:
        Tuple of (full_weights, info_dict)
    """
    # Calculate returns
    returns = np.log(train_data / train_data.shift(1)).dropna()
    
    # Annualize statistics
    mean_returns = returns.mean().values * 252
    cov_matrix = returns.cov().values * 252
    
    # Get stock indices if names were provided
    if isinstance(selected_stocks[0], str):
        stock_names = list(train_data.columns)
        selected_indices = [stock_names.index(stock) for stock in selected_stocks]
    else:
        selected_indices = selected_stocks
    
    # Optimize weights
    optimized_weights, info = optimize_sharpe_slsqp(
        selected_indices,
        mean_returns,
        cov_matrix,
        risk_free_rate=risk_free_rate,
        verbose=verbose
    )
    
    # Create full weight vector
    n_total = len(train_data.columns)
    full_weights = create_full_weight_vector(
        selected_indices,
        optimized_weights,
        n_total
    )
    
    return full_weights, info


if __name__ == "__main__":
    """
    Test the weight optimizer with sample data.
    """
    print("Testing SLSQP Weight Optimizer...")
    print("="*60)
    
    # Create synthetic test data
    np.random.seed(42)
    n_stocks = 50
    n_days = 1000
    
    # Simulate returns (some stocks better than others)
    returns = np.random.randn(n_days, n_stocks) * 0.02
    returns[:, :10] += 0.001  # Top 10 stocks have higher drift
    
    # Calculate statistics
    mean_returns = returns.mean(axis=0) * 252
    cov_matrix = np.cov(returns, rowvar=False) * 252
    
    # Select top 7 stocks by mean return
    selected_stocks = np.argsort(mean_returns)[-7:]
    
    print(f"Selected stocks: {selected_stocks}")
    print(f"Their mean returns: {mean_returns[selected_stocks]}")
    print()
    
    # Test 1: Optimize weights
    print("Test 1: SLSQP Optimization")
    weights_opt, info = optimize_sharpe_slsqp(
        selected_stocks,
        mean_returns,
        cov_matrix,
        verbose=True
    )
    
    print(f"\nOptimized weights: {weights_opt}")
    print(f"Sum of weights: {np.sum(weights_opt):.6f}")
    
    # Test 2: Compare with equal weights
    print("\n" + "="*60)
    print("Test 2: Comparison with Equal Weights")
    print("="*60)
    
    weights_equal = np.array([1.0/7] * 7)
    
    mean_ret_selected = mean_returns[selected_stocks]
    cov_selected = cov_matrix[np.ix_(selected_stocks, selected_stocks)]
    
    return_equal = np.dot(weights_equal, mean_ret_selected)
    vol_equal = np.sqrt(np.dot(weights_equal, np.dot(cov_selected, weights_equal)))
    sharpe_equal = (return_equal - 0.06) / vol_equal
    
    return_opt = np.dot(weights_opt, mean_ret_selected)
    vol_opt = np.sqrt(np.dot(weights_opt, np.dot(cov_selected, weights_opt)))
    sharpe_opt = (return_opt - 0.06) / vol_opt
    
    print(f"\nEqual Weights:")
    print(f"  Return: {return_equal:.2%}")
    print(f"  Volatility: {vol_equal:.2%}")
    print(f"  Sharpe: {sharpe_equal:.3f}")
    
    print(f"\nOptimized Weights:")
    print(f"  Return: {return_opt:.2%}")
    print(f"  Volatility: {vol_opt:.2%}")
    print(f"  Sharpe: {sharpe_opt:.3f}")
    
    print(f"\nImprovement:")
    print(f"  Return: +{(return_opt - return_equal)*100:.2f}pp")
    print(f"  Sharpe: +{(sharpe_opt - sharpe_equal):.3f}")
    print(f"  Improvement: {((sharpe_opt/sharpe_equal - 1)*100):.1f}%")
    
    print("\nWeight optimizer test completed successfully!")

