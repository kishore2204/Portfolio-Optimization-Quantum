"""
Two-Step Cardinality Determination (Paper's Methodology)
========================================================
Step 1: Solve convex Sharpe ratio maximization to derive optimal K
Step 2: Use derived K as cardinality constraint in QUBO

Reference: Morapakula et al. (2025) - Equation (7)

Author: Enhanced Portfolio System
Date: March 2026
"""

import numpy as np
import cvxpy as cp
import json
from pathlib import Path

def determine_optimal_cardinality(mean_returns, cov_matrix, rf_rate=0.06, verbose=True):
    """
    Determine optimal cardinality K using convex Sharpe ratio optimization
    
    Paper's formulation (Equation 7):
        min y'Σy
        s.t. (μ - r)'y = 1
             y ≥ 0
    
    Then compute K = Σ y_i* (sum of optimal weights)
    
    Args:
        mean_returns: Expected returns vector (annualized)
        cov_matrix: Covariance matrix (annualized)
        rf_rate: Risk-free rate (default 0.06)
        verbose: Print optimization details
    
    Returns:
        K_optimal: Derived cardinality (number of assets)
        y_optimal: Optimal continuous weights
    """
    
    if verbose:
        print(f"\n{'='*80}")
        print("STEP 1: CONVEX SHARPE RATIO OPTIMIZATION")
        print(f"{'='*80}")
        print(f"Objective: Derive optimal cardinality K from continuous optimization")
    
    n = len(mean_returns)
    
    # Decision variables
    y = cp.Variable(n)
    
    # Convex Sharpe ratio formulation
    objective = cp.Minimize(cp.quad_form(y, cov_matrix))
    
    constraints = [
        (mean_returns - rf_rate) @ y == 1,  # Normalized excess return
        y >= 0                               # No short selling
    ]
    
    # Solve problem
    problem = cp.Problem(objective, constraints)
    
    try:
        # Try with cvxopt first (newly installed)
        problem.solve(solver=cp.CVXOPT, verbose=False)
        
        if problem.status not in ['optimal', 'optimal_inaccurate']:
            # Fallback to other solvers
            problem.solve(solver=cp.ECOS, verbose=False)
        
        if problem.status not in ['optimal', 'optimal_inaccurate']:
            # Last resort: SCS solver
            problem.solve(solver=cp.SCS, verbose=False)
            
    except Exception as e:
        if verbose:
            print(f"  [WARNING] Primary solver failed: {e}")
            print(f"  [INFO] Attempting fallback solvers...")
        
        try:
            problem.solve(verbose=False)
        except:
            if verbose:
                print(f"  [ERROR] All solvers failed. Using K=15 as default.")
            return 15, None
    
    if problem.status in ['optimal', 'optimal_inaccurate']:
        y_optimal = y.value
        
        # Compute optimal K from sum of weights
        # Paper maps: w_i* = y_i* / Σ y_j*
        # So K ≈ number of non-zero weights
        K_sum = np.sum(y_optimal)
        
        # Count non-negligible weights (> 1% threshold)
        threshold = 0.01 * np.max(y_optimal)
        K_nonzero = np.sum(y_optimal > threshold)
        
        # Paper uses the sum approach
        K_optimal = int(np.round(K_sum))
        
        # Ensure K is reasonable (between 8 and 20)
        K_optimal = max(8, min(20, K_optimal))
        
        if verbose:
            print(f"\n  OK Optimization successful: {problem.status}")
            print(f"  Portfolio variance: {problem.value:.6f}")
            print(f"  Sum of optimal weights: {K_sum:.2f}")
            print(f"  Non-zero weights: {K_nonzero}")
            print(f"  Derived optimal K: {K_optimal}")
            
            # Show top weights
            w_optimal = y_optimal / np.sum(y_optimal)
            top_5 = np.argsort(w_optimal)[-5:][::-1]
            print(f"\n  Top 5 weights:")
            for i, idx in enumerate(top_5, 1):
                print(f"    {i}. Asset {idx}: {w_optimal[idx]*100:.2f}%")
        
        return K_optimal, y_optimal
        
    else:
        if verbose:
            print(f"  [ERROR] Optimization failed: {problem.status}")
            print(f"  Using default K=15")
        return 15, None


def compute_portfolio_metrics_from_y(y_optimal, mean_returns, cov_matrix, rf_rate=0.06):
    """
    Compute portfolio metrics from optimal y weights
    
    Args:
        y_optimal: Optimal weights from convex optimization
        mean_returns: Expected returns
        cov_matrix: Covariance matrix
        rf_rate: Risk-free rate
    
    Returns:
        dict: Portfolio metrics (return, risk, Sharpe ratio)
    """
    
    # Normalize to portfolio weights
    w = y_optimal / np.sum(y_optimal)
    
    # Portfolio return
    portfolio_return = np.dot(w, mean_returns)
    
    # Portfolio risk
    portfolio_variance = np.dot(w, np.dot(cov_matrix, w))
    portfolio_risk = np.sqrt(portfolio_variance)
    
    # Sharpe ratio
    sharpe_ratio = (portfolio_return - rf_rate) / portfolio_risk
    
    return {
        'return': portfolio_return,
        'risk': portfolio_risk,
        'sharpe_ratio': sharpe_ratio,
        'weights': w
    }


def save_cardinality_analysis(K_optimal, y_optimal, mean_returns, cov_matrix, config):
    """Save cardinality analysis results"""
    
    output_dir = Path('portfolios')
    output_dir.mkdir(exist_ok=True)
    
    # Compute metrics
    metrics = compute_portfolio_metrics_from_y(
        y_optimal, mean_returns, cov_matrix, 
        config['data']['risk_free_rate']
    )
    
    # Save analysis
    analysis = {
        'K_optimal': int(K_optimal),
        'method': 'convex_sharpe_maximization',
        'reference': 'Morapakula et al. (2025) - Equation 7',
        'portfolio_metrics': {
            'annual_return': float(metrics['return']),
            'annual_risk': float(metrics['risk']),
            'sharpe_ratio': float(metrics['sharpe_ratio'])
        },
        'optimization_details': {
            'sum_of_weights': float(np.sum(y_optimal)) if y_optimal is not None else None,
            'max_weight': float(np.max(y_optimal)) if y_optimal is not None else None,
            'non_zero_threshold': 0.01
        }
    }
    
    with open('portfolios/cardinality_analysis.json', 'w') as f:
        json.dump(analysis, f, indent=2)
    
    print(f"\n  OK Saved cardinality analysis to portfolios/cardinality_analysis.json")
    
    return analysis


if __name__ == "__main__":
    # Load config
    with open('config/config.json', 'r') as f:
        config = json.load(f)
    
    # Load prepared data
    mean_returns = np.load('data/mean_returns.npy')
    cov_matrix = np.load('data/covariance_matrix.npy')
    
    print(f"Loaded {len(mean_returns)} assets from universe")
    
    # Determine optimal K
    K_optimal, y_optimal = determine_optimal_cardinality(
        mean_returns, cov_matrix, 
        rf_rate=config['data']['risk_free_rate'],
        verbose=True
    )
    
    # Save analysis
    if y_optimal is not None:
        save_cardinality_analysis(K_optimal, y_optimal, mean_returns, cov_matrix, config)
    
    print(f"\n{'='*80}")
    print(f"RESULT: Optimal cardinality K = {K_optimal}")
    print(f"{'='*80}")

