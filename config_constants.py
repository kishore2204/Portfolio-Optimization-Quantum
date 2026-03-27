"""
Fixed Constants Configuration for QUBO Portfolio Optimization

This module defines all QUBO constants used in the model.
No hyperparameter tuning - all values are theoretically justified and fixed.

Reference: See design justification in QUBO_CALCULATION_MANUAL.md
"""

import numpy as np
import pandas as pd


# ============================================================================
# FIXED CONSTANTS - DO NOT MODIFY
# ============================================================================

# Risk Weight (q): Balances covariance risk in QUBO
Q_RISK = 0.5
"""
Controls how much the covariance matrix penalizes correlated assets.
Value: 0.5 (balances return and risk)

Lower (0.1-0.3): Emphasizes returns, ignores correlation risk
Higher (1.0-2.0): Emphasizes risk, conservative portfolios
Choice 0.5: Middle ground, literature standard
"""

# Downside Volatility Weight (β): Penalizes crash-prone stocks
BETA_DOWNSIDE = 0.3
"""
Penalizes stocks with high downside volatility (negative returns).
Value: 0.3 (moderate downside protection)

Interpretation: √252 × √(mean(negative_returns²))
- Higher β = avoid risky stocks
- Lower β = ignore downside risk

Value 0.3: Good balance between growth and protection
"""

# Time Series Constants
TRADING_DAYS_PER_YEAR = 252
"""Standard financial convention: 252 trading days per year"""

LOOKBACK_WINDOW = 252
"""1-year rolling window for rebalancing statistics"""

REBALANCE_CADENCE = 63
"""Quarterly rebalancing: ~3 months = 63 trading days"""


# ============================================================================
# ADAPTIVE CONSTANTS (Data-Dependent but Not Tuned)
# ============================================================================

def compute_lambda_card(
    mu: pd.Series,
    cov: pd.DataFrame,
    K: int,
) -> float:
    """
    Compute cardinality constraint strength (λ) adaptively.
    
    Formula:
        λ = clip(10 × scale × (N/K), 50, 500)
    
    Where:
        scale = max(mean(|cov|), mean(|μ|), max(diag(cov)))
        N = number of assets
        K = target portfolio size
    
    Parameters
    ----------
    mu : pd.Series
        Expected returns vector
    cov : pd.DataFrame
        Covariance matrix
    K : int
        Target number of assets
    
    Returns
    -------
    float
        Cardinality penalty strength λ
    
    Notes
    -----
    - Ensures hard constraint: exactly K assets selected
    - Scales with dataset magnitude (avoids numerical issues)
    - Clipped to [50, 500] for stability
    - Not tuned via grid search (fixed formula)
    """
    N = len(mu)
    
    # Compute scale as max of three dataset statistics
    mean_cov_abs = np.mean(np.abs(cov.values))
    mean_mu_abs = np.mean(np.abs(mu.values))
    max_diag_cov = np.max(np.diag(cov.values))
    
    scale = max(mean_cov_abs, mean_mu_abs, max_diag_cov)
    scale = max(scale, 1e-6)  # Avoid division by zero
    
    # Adaptive formula
    lambda_card = 10.0 * scale * (N / max(K, 1))
    
    # Clip to reasonable range
    lambda_card = np.clip(lambda_card, 50, 500)
    
    return float(lambda_card)


def compute_gamma_sector(lambda_card: float) -> float:
    """
    Compute sector concentration penalty (γ) proportional to λ.
    
    Formula:
        γ = 0.1 × λ
    
    Parameters
    ----------
    lambda_card : float
        Cardinality penalty strength
    
    Returns
    -------
    float
        Sector concentration penalty strength γ
    
    Notes
    -----
    - Proportional to cardinality penalty ensures consistency
    - 0.1 factor prevents over-penalizing sector diversity
    - Higher γ = stricter diversification
    """
    return 0.1 * lambda_card


# ============================================================================
# OPTIMIZER HYPERPARAMETERS
# ============================================================================

# Simulated Annealing Temperature Schedule
ANNEALING_T0 = 2.0
"""Initial temperature for simulated annealing"""

ANNEALING_T1 = 0.005
"""Final temperature after cooling"""

ANNEALING_STEPS = 6000
"""Number of cooling iterations"""

ANNEALING_READS = 512
"""Number of samples for QUBO solver (if using D-Wave Neal)"""


# ============================================================================
# PORTFOLIO CONSTRAINTS
# ============================================================================

MAX_WEIGHT_PER_ASSET = 0.12
"""Maximum allocation to single asset (prevents concentration)"""

MAX_ASSETS_PER_SECTOR = 4
"""Maximum number of assets from same sector (diversification)"""

RISK_FREE_RATE = 0.05
"""Risk-free rate (5%) for Sharpe ratio calculation"""

TRANSACTION_COST = 0.001
"""Transaction cost coefficient (0.1% per unit turnover)"""


# ============================================================================
# EXPERIMENT CONFIGURATION
# ============================================================================

TRAIN_YEARS = 12
"""Historical training period (years)"""

TEST_YEARS = 3
"""Out-of-sample test period (years)"""

TEST_END_DATE = pd.Timestamp("2025-09-30")
"""Optional: Specific end date for test period. If set, overrides TEST_YEARS calculation.
Leave as None to use TEST_YEARS instead. Format: pd.Timestamp("YYYY-MM-DD")"""

K_RATIO = 0.0221
"""Asset selection ratio: K ≈ 2.21% of universe size (15 assets from 680)"""


# ============================================================================
# SUMMARY TABLE
# ============================================================================

def print_constants_summary():
    """Print all configuration constants for transparency."""
    print("\n" + "="*70)
    print("QUBO PORTFOLIO OPTIMIZATION - FIXED CONSTANTS")
    print("="*70)
    
    print("\n[FIXED CONSTANTS]")
    print(f"  q_risk (Risk Weight)            = {Q_RISK}")
    print(f"  β_downside (Downside Risk)      = {BETA_DOWNSIDE}")
    print(f"  Trading Days per Year           = {TRADING_DAYS_PER_YEAR}")
    print(f"  Lookback Window (days)          = {LOOKBACK_WINDOW}")
    print(f"  Rebalance Cadence (days)        = {REBALANCE_CADENCE}")
    
    print("\n[ADAPTIVE CONSTANTS (Formula-Based)]")
    print(f"  λ (Cardinality Penalty)         = 10 × scale × (N/K), clipped to [50, 500]")
    print(f"  γ (Sector Penalty)              = 0.1 × λ")
    
    print("\n[OPTIMIZER PARAMETERS]")
    print(f"  Annealing T₀ (Initial)          = {ANNEALING_T0}")
    print(f"  Annealing T₁ (Final)            = {ANNEALING_T1}")
    print(f"  Annealing Steps                 = {ANNEALING_STEPS}")
    print(f"  Annealing Reads                 = {ANNEALING_READS}")
    
    print("\n[PORTFOLIO CONSTRAINTS]")
    print(f"  Max Weight per Asset            = {MAX_WEIGHT_PER_ASSET*100:.1f}%")
    print(f"  Max Assets per Sector           = {MAX_ASSETS_PER_SECTOR}")
    print(f"  Risk-Free Rate                  = {RISK_FREE_RATE*100:.1f}%")
    print(f"  Transaction Cost                = {TRANSACTION_COST*100:.2f}%")
    
    print("\n[EXPERIMENT SETUP]")
    print(f"  Training Period                 = {TRAIN_YEARS} years")
    print(f"  Test Period                     = {TEST_YEARS} years")
    print(f"  K Selection Ratio               = {K_RATIO*100:.1f}% of universe")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    print_constants_summary()
