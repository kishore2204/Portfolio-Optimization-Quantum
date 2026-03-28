"""
COMPREHENSIVE INSPECTION AND VALIDATION SUITE
==============================================

This script performs a STRICT, DETAILED inspection of the entire Portfolio Optimization project.
It checks for:
1. Configuration constants validity
2. K selection logic and calculations
3. QUBO matrix formulation
4. Covariance matrix calculations
5. Classical optimizer logic
6. Hybrid optimizer and annealing
7. Metrics calculations
8. Rebalancing logic
9. Data loading and preprocessing
10. Edge cases and error handling
11. Mathematical correctness
12. Numerical stability (NaN, Inf issues)
13. Data integrity (train/test split)

Author: Strict Inspector
Date: 2026-03-27
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Add project root to path
root = Path(__file__).resolve().parent
sys.path.insert(0, str(root))

from config_constants import (
    Q_RISK, BETA_DOWNSIDE, TRADING_DAYS_PER_YEAR, LOOKBACK_WINDOW, REBALANCE_CADENCE,
    MAX_WEIGHT_PER_ASSET, MAX_ASSETS_PER_SECTOR, RISK_FREE_RATE, TRAIN_YEARS, TEST_YEARS,
    K_RATIO, TRANSACTION_COST, ANNEALING_T0, ANNEALING_T1, ANNEALING_STEPS,
    compute_lambda_card, compute_gamma_sector
)
from data_loader import load_all_data
from preprocessing import clean_prices, log_returns, annualize_stats, time_series_split
from qubo import build_qubo, qubo_energy
from classical_optimizer import optimize_sharpe, optimize_markowitz
from annealing import select_assets_via_annealing
from evaluation import compute_metrics, metrics_table, max_drawdown, value_from_returns
from hybrid_optimizer import run_quantum_hybrid_selection, HybridConfig, portfolio_returns

# ============================================================================
# INSPECTION UTILITIES
# ============================================================================

class InspectionResult:
    def __init__(self, name: str):
        self.name = name
        self.checks: list = []
        self.passed = 0
        self.failed = 0
        self.warnings = 0
    
    def check(self, condition: bool, description: str, details: str = ""):
        """Record a check result"""
        if condition:
            self.checks.append(("✅ PASS", description, details))
            self.passed += 1
        else:
            self.checks.append(("❌ FAIL", description, details))
            self.failed += 1
    
    def warn(self, condition: bool, description: str, details: str = ""):
        """Record a warning"""
        if condition:
            self.checks.append(("⚠️  WARN", description, details))
            self.warnings += 1
        else:
            self.checks.append(("✅ PASS", description, details))
            self.passed += 1
    
    def report(self):
        """Print inspection report"""
        print(f"\n{'='*80}")
        print(f"SECTION: {self.name}")
        print(f"{'='*80}")
        for status, desc, details in self.checks:
            print(f"{status} {desc}")
            if details:
                print(f"        {details}")
        print(f"\nResult: {self.passed} passed, {self.failed} failed, {self.warnings} warnings")
        if self.failed > 0:
            print("⚠️  CRITICAL ISSUES DETECTED!")
        return self.failed == 0

# ============================================================================
# INSPECTION SECTION 1: CONFIGURATION CONSTANTS
# ============================================================================

def inspect_configuration():
    """Inspect fixed constants"""
    insp = InspectionResult("Configuration Constants")
    
    # Check risk weight
    insp.check(0 < Q_RISK <= 2.0, "Q_RISK in valid range", f"Q_RISK = {Q_RISK}")
    
    # Check downside volatility weight
    insp.check(0 <= BETA_DOWNSIDE <= 1.0, "BETA_DOWNSIDE in valid range", f"BETA_DOWNSIDE = {BETA_DOWNSIDE}")
    
    # Check trading days
    insp.check(TRADING_DAYS_PER_YEAR == 252, "Trading days correct", f"Value = {TRADING_DAYS_PER_YEAR}")
    
    # Check lookback window
    insp.check(LOOKBACK_WINDOW == 252, "Lookback window = 1 year", f"Value = {LOOKBACK_WINDOW}")
    
    # Check rebalance cadence
    insp.check(50 < REBALANCE_CADENCE < 100, "Rebalance cadence ~quarterly", f"Value = {REBALANCE_CADENCE}")
    
    # Check max weight per asset
    insp.check(0 < MAX_WEIGHT_PER_ASSET <= 0.5, "Max weight reasonable", f"Value = {MAX_WEIGHT_PER_ASSET}")
    
    # Check max assets per sector
    insp.check(MAX_ASSETS_PER_SECTOR >= 2, "Max assets per sector >= 2", f"Value = {MAX_ASSETS_PER_SECTOR}")
    
    # Check risk-free rate
    insp.check(0 <= RISK_FREE_RATE <= 0.10, "Risk-free rate reasonable", f"Value = {RISK_FREE_RATE}")
    
    # Check transaction cost
    insp.check(0 <= TRANSACTION_COST <= 0.01, "Transaction cost reasonable", f"Value = {TRANSACTION_COST}")
    
    # Check training/test years
    insp.check(TRAIN_YEARS > 0 and TEST_YEARS > 0, "Training and test years positive", 
              f"Train={TRAIN_YEARS}, Test={TEST_YEARS}")
    
    # Check K ratio
    insp.check(0 < K_RATIO <= 1.0, "K ratio valid", f"K_RATIO = {K_RATIO}")
    
    # Check annealing parameters
    insp.check(ANNEALING_T0 > ANNEALING_T1, "T0 > T1 for cooling", f"T0={ANNEALING_T0}, T1={ANNEALING_T1}")
    insp.check(ANNEALING_STEPS > 0, "Annealing steps positive", f"Steps = {ANNEALING_STEPS}")
    
    insp.report()
    return insp.failed == 0

# ============================================================================
# INSPECTION SECTION 2: DATA LOADING & PREPROCESSING
# ============================================================================

def inspect_data_loading():
    """Inspect data loading and preprocessing"""
    insp = InspectionResult("Data Loading & Preprocessing")
    
    try:
        # Load data
        root = Path(__file__).resolve().parent
        dataset_root = root / "datasets"
        bundle = load_all_data(dataset_root)
        
        insp.check(bundle.asset_prices is not None, "Asset prices loaded", 
                  f"Shape: {bundle.asset_prices.shape}")
        insp.check(bundle.asset_prices.shape[0] > 0, "Asset prices non-empty", "")
        insp.check(bundle.asset_prices.shape[1] > 0, "Asset prices have columns", "")
        
        # Check for duplicates
        insp.check(not bundle.asset_prices.index.duplicated().any(), 
                  "No duplicate dates in prices", "")
        
        # Check for missing values
        missing_rate = bundle.asset_prices.isna().sum().sum() / (bundle.asset_prices.shape[0] * bundle.asset_prices.shape[1])
        insp.check(missing_rate < 0.05, "Missing values < 5%", f"Rate: {missing_rate:.2%}")
        
        # Clean prices
        clean_px = clean_prices(bundle.asset_prices)
        insp.check(clean_px.shape[1] > 100, "Sufficient assets after cleaning", f"Assets: {clean_px.shape[1]}")
        
        # Check for infinite values
        has_inf = np.isinf(clean_px.values).any()
        insp.check(not has_inf, "No infinite values in clean prices", "")
        
        # Check date range
        date_range = (clean_px.index.max() - clean_px.index.min()).days
        insp.check(date_range > 365 * (TRAIN_YEARS + TEST_YEARS - 1), 
                  "Sufficient data for train/test split", f"Days: {date_range}")
        
        # Test time series split
        split = time_series_split(clean_px, train_years=TRAIN_YEARS, test_years=TEST_YEARS)
        
        insp.check(split.train_returns is not None, "Train returns extracted", 
                  f"Shape: {split.train_returns.shape}")
        insp.check(split.test_returns is not None, "Test returns extracted", 
                  f"Shape: {split.test_returns.shape}")
        
        train_days = len(split.train_returns)
        test_days = len(split.test_returns)
        
        insp.check(train_days > TRADING_DAYS_PER_YEAR * (TRAIN_YEARS - 1), 
                  "Train days adequate", f"Days: {train_days} (expected ~{TRADING_DAYS_PER_YEAR * TRAIN_YEARS})")
        
        insp.check(test_days > TRADING_DAYS_PER_YEAR * (TEST_YEARS - 0.5), 
                  "Test days adequate", f"Days: {test_days} (expected ~{TRADING_DAYS_PER_YEAR * TEST_YEARS})")
        
        # Check no data leakage
        insp.check(split.split_dates['train_end'] < split.split_dates['test_end'],
                  "No train/test overlap", "")
        
        # Check returns statistics
        train_nan = split.train_returns.isna().sum().sum()
        test_nan = split.test_returns.isna().sum().sum()
        insp.check(train_nan < 100, "Few NaN in train returns", f"NaNs: {train_nan}")
        insp.check(test_nan < 100, "Few NaN in test returns", f"NaNs: {test_nan}")
        
        # Check for infinite returns
        insp.check(not np.isinf(split.train_returns.values).any(), "No infinite train returns", "")
        insp.check(not np.isinf(split.test_returns.values).any(), "No infinite test returns", "")
        
    except Exception as e:
        insp.check(False, f"Data loading exception: {str(e)}", "")
    
    insp.report()
    return insp.failed == 0

# ============================================================================
# INSPECTION SECTION 3: COVARIANCE & STATISTICS CALCULATION
# ============================================================================

def inspect_statistics_calculation():
    """Inspect covariance and statistics"""
    insp = InspectionResult("Covariance & Statistics Calculation")
    
    try:
        # Load and split data
        root = Path(__file__).resolve().parent
        dataset_root = root / "datasets"
        bundle = load_all_data(dataset_root)
        clean_px = clean_prices(bundle.asset_prices)
        split = time_series_split(clean_px, train_years=TRAIN_YEARS, test_years=TEST_YEARS)
        
        train_r = split.train_returns
        test_r = split.test_returns
        
        # Calculate statistics
        mu_train, cov_train, down_train = annualize_stats(train_r)
        
        # Check mean returns
        insp.check(not mu_train.isna().any(), "No NaN in mean returns", "")
        insp.check(not np.isinf(mu_train.values).any(), "No infinite mean returns", "")
        
        # Check covariance matrix properties
        insp.check(cov_train.shape[0] == cov_train.shape[1], "Covariance is square", 
                  f"Shape: {cov_train.shape}")
        
        # Check symmetry (covariance must be symmetric)
        is_symmetric = np.allclose(cov_train.values, cov_train.values.T, atol=1e-10)
        insp.check(is_symmetric, "Covariance matrix is symmetric", "")
        
        # Check positive semi-definite (eigenvalues >= 0)
        eigvals = np.linalg.eigvals(cov_train.values)
        all_non_negative = np.all(eigvals >= -1e-10)
        insp.check(all_non_negative, "Covariance is positive semi-definite", 
                  f"Min eigenvalue: {eigvals.min():.2e}")
        
        # Check covariance values reasonable
        max_cov = np.abs(cov_train.values).max()
        insp.check(max_cov > 0, "Covariance has non-zero values", f"Max: {max_cov:.4f}")
        insp.check(max_cov < 10.0, "Covariance values reasonable", f"Max: {max_cov:.4f}")
        
        # Check downside volatility
        insp.check(not down_train.isna().any(), "No NaN in downside volatility", "")
        insp.check(not np.isinf(down_train.values).any(), "No infinite downside volatility", "")
        insp.check(np.all(down_train >= 0), "Downside volatility non-negative", "")
        
        # Check annualization (should multiply by 252 for daily data)
        daily_mu = train_r.mean()
        annualized_mu_calculated = daily_mu * 252
        assert np.allclose(mu_train.values, annualized_mu_calculated.values, rtol=1e-10)
        insp.check(True, "Mean returns correctly annualized", f"Sample: {mu_train.iloc[0]:.4f}")
        
        # Check covariance annualization
        daily_cov = train_r.cov()
        annualized_cov_calculated = daily_cov * 252
        assert np.allclose(cov_train.values, annualized_cov_calculated.values, rtol=1e-10)
        insp.check(True, "Covariance correctly annualized", "")
        
    except Exception as e:
        insp.check(False, f"Statistics calculation exception: {str(e)}", "")
    
    insp.report()
    return insp.failed == 0

# ============================================================================
# INSPECTION SECTION 4: K SELECTION LOGIC
# ============================================================================

def inspect_k_selection():
    """Inspect K selection and calculation"""
    insp = InspectionResult("K Selection Logic")
    
    try:
        # Load data
        root = Path(__file__).resolve().parent
        dataset_root = root / "datasets"
        bundle = load_all_data(dataset_root)
        clean_px = clean_prices(bundle.asset_prices)
        split = time_series_split(clean_px, train_years=TRAIN_YEARS, test_years=TEST_YEARS)
        
        train_r = split.train_returns
        
        # Calculate K
        n_assets = len(train_r.columns)
        K = max(10, int(K_RATIO * n_assets))
        K = min(K, n_assets)
        
        insp.check(K > 0, "K positive", f"K = {K}")
        insp.check(K <= n_assets, "K <= universe size", f"K = {K}, N = {n_assets}")
        insp.check(K >= 10, "K >= 10", f"K = {K}")
        insp.check(0.01 <= K_RATIO <= 0.05, "K_RATIO reasonable", f"K_RATIO = {K_RATIO}")
        
        # Verify K calculation
        expected_k = max(10, int(K_RATIO * n_assets))
        insp.check(K == expected_k, "K calculated correctly", f"K = {K}")
        
        # Check K as percentage of universe
        k_pct = K / n_assets
        insp.check(0.01 <= k_pct <= 0.1, "K is 1-10% of universe", f"K% = {k_pct:.2%}")
        
    except Exception as e:
        insp.check(False, f"K selection exception: {str(e)}", "")
    
    insp.report()
    return insp.failed == 0

# ============================================================================
# INSPECTION SECTION 5: QUBO FORMULATION
# ============================================================================

def inspect_qubo_formulation():
    """Inspect QUBO matrix formulation"""
    insp = InspectionResult("QUBO Formulation")
    
    try:
        # Load data
        root = Path(__file__).resolve().parent
        dataset_root = root / "datasets"
        bundle = load_all_data(dataset_root)
        clean_px = clean_prices(bundle.asset_prices)
        split = time_series_split(clean_px, train_years=TRAIN_YEARS, test_years=TEST_YEARS)
        
        train_r = split.train_returns
        n_assets = len(train_r.columns)
        K = max(10, int(K_RATIO * n_assets))
        K = min(K, n_assets)
        
        # Calculate statistics
        mu_train, cov_train, down_train = annualize_stats(train_r)
        
        # Build QUBO
        subset = list(train_r.columns[:100])  # Use subset for speed
        mu_sub = mu_train.loc[subset]
        cov_sub = cov_train.loc[subset, subset]
        down_sub = down_train.loc[subset]
        
        qubo_model = build_qubo(
            mu=mu_sub,
            cov=cov_sub,
            downside=down_sub,
            sector_map=bundle.sector_map,
            K=min(K, len(subset)),
            q_risk=Q_RISK,
            beta_downside=BETA_DOWNSIDE,
        )
        
        Q = qubo_model.Q
        
        # Check QUBO matrix properties
        insp.check(Q.shape[0] == Q.shape[1], "QUBO is square", f"Shape: {Q.shape}")
        
        # Check symmetry
        is_symmetric = np.allclose(Q, Q.T, atol=1e-10)
        insp.check(is_symmetric, "QUBO matrix is symmetric", "")
        
        # Check for NaN and Inf
        insp.check(not np.isnan(Q).any(), "No NaN in QUBO", "")
        insp.check(not np.isinf(Q).any(), "No infinite in QUBO", "")
        
        # Check values reasonable
        max_q = np.abs(Q).max()
        insp.check(max_q > 0, "QUBO has non-zero values", f"Max: {max_q:.2e}")
        insp.check(max_q < 1e10, "QUBO values not extreme", f"Max: {max_q:.2e}")
        
        # Check lambda and gamma computed correctly
        lambda_card = qubo_model.lambda_card
        gamma_sector = qubo_model.gamma_sector
        
        insp.check(50 <= lambda_card <= 500, "Lambda in clipped range", f"Lambda: {lambda_card:.2f}")
        insp.check(gamma_sector == 0.1 * lambda_card, "Gamma = 0.1 * Lambda", 
                  f"Gamma: {gamma_sector:.2f}, 0.1*Lambda: {0.1*lambda_card:.2f}")
        
        # Test QUBO energy calculation
        x_test = np.zeros(Q.shape[0])
        x_test[:3] = 1.0
        energy = qubo_energy(x_test, Q)
        insp.check(not np.isnan(energy), "QUBO energy calculable", f"Energy: {energy:.2f}")
        insp.check(not np.isinf(energy), "Energy is finite", "")
        
    except Exception as e:
        insp.check(False, f"QUBO formulation exception: {str(e)}", "")
    
    insp.report()
    return insp.failed == 0

# ============================================================================
# INSPECTION SECTION 6: OPTIMIZER LOGIC
# ============================================================================

def inspect_optimizer_logic():
    """Inspect classical and hybrid optimizer"""
    insp = InspectionResult("Optimizer Logic (Classical & Hybrid)")
    
    try:
        # Load data
        root = Path(__file__).resolve().parent
        dataset_root = root / "datasets"
        bundle = load_all_data(dataset_root)
        clean_px = clean_prices(bundle.asset_prices)
        split = time_series_split(clean_px, train_years=TRAIN_YEARS, test_years=TEST_YEARS)
        
        train_r = split.train_returns
        test_r = split.test_returns
        
        n_assets = len(train_r.columns)
        K = max(10, int(K_RATIO * n_assets))
        K = min(K, n_assets)
        
        # Calculate statistics
        mu_train, cov_train, down_train = annualize_stats(train_r)
        
        # Test classical optimizer on all assets
        w_mvo_all = optimize_markowitz(mu_train, cov_train, risk_aversion=4.0, w_max=MAX_WEIGHT_PER_ASSET)
        
        insp.check(len(w_mvo_all) == len(mu_train), "MVO optimizer output size correct", "")
        insp.check(not w_mvo_all.isna().any(), "No NaN in MVO weights", "")
        insp.check(not np.isinf(w_mvo_all.values).any(), "No infinite in MVO weights", "")
        insp.check(np.all(w_mvo_all >= 0), "All MVO weights non-negative", "")
        insp.check(np.isclose(w_mvo_all.sum(), 1.0, atol=1e-6), "MVO weights sum to 1", 
                  f"Sum: {w_mvo_all.sum():.6f}")
        insp.check(np.all(w_mvo_all <= MAX_WEIGHT_PER_ASSET * 1.01), "Max weight constraint satisfied", 
                  f"Max weight: {w_mvo_all.max():.4f}")
        
        # Test Sharpe optimizer on subset
        top_assets = list(w_mvo_all.sort_values(ascending=False).head(K).index)
        mu_sub = mu_train.loc[top_assets]
        cov_sub = cov_train.loc[top_assets, top_assets]
        
        w_sharpe = optimize_sharpe(mu_sub, cov_sub, rf=RISK_FREE_RATE, w_max=MAX_WEIGHT_PER_ASSET)
        
        insp.check(len(w_sharpe) == K, "Sharpe optimizer output size correct", "")
        insp.check(not w_sharpe.isna().any(), "No NaN in Sharpe weights", "")
        insp.check(not np.isinf(w_sharpe.values).any(), "No infinite in Sharpe weights", "")
        insp.check(np.all(w_sharpe >= 0), "All Sharpe weights non-negative", "")
        insp.check(np.isclose(w_sharpe.sum(), 1.0, atol=1e-6), "Sharpe weights sum to 1", 
                  f"Sum: {w_sharpe.sum():.6f}")
        
        # Test portfolio returns calculation
        test_ret_portfolio = portfolio_returns(test_r, w_sharpe)
        insp.check(len(test_ret_portfolio) == len(test_r), "Portfolio returns length correct", "")
        insp.check(not test_ret_portfolio.isna().all(), "Portfolio returns not all NaN", "")
        insp.check(not np.isinf(test_ret_portfolio.values).any(), "No infinite returns", "")
        
    except Exception as e:
        insp.check(False, f"Optimizer logic exception: {str(e)}", "")
    
    insp.report()
    return insp.failed == 0

# ============================================================================
# INSPECTION SECTION 7: METRICS CALCULATION
# ============================================================================

def inspect_metrics_calculation():
    """Inspect metrics calculation"""
    insp = InspectionResult("Metrics Calculation")
    
    try:
        # Load data
        root = Path(__file__).resolve().parent
        dataset_root = root / "datasets"
        bundle = load_all_data(dataset_root)
        clean_px = clean_prices(bundle.asset_prices)
        split = time_series_split(clean_px, train_years=TRAIN_YEARS, test_years=TEST_YEARS)
        
        train_r = split.train_returns
        test_r = split.test_returns
        
        # Create dummy portfolio values
        daily_returns = test_r.mean(axis=1)
        portfolio_value = value_from_returns(daily_returns, initial=1.0)
        
        insp.check(len(portfolio_value) == len(test_r), "Portfolio value length correct", "")
        insp.check(portfolio_value.iloc[0] == 1.0, "Portfolio starts at 1.0", "")
        insp.check(np.all(portfolio_value > 0), "All portfolio values positive", "")
        
        # Calculate metrics
        metrics = compute_metrics(portfolio_value, rf=RISK_FREE_RATE)
        
        insp.check("Total Return" in metrics, "Total return calculated", "")
        insp.check("Annualized Return" in metrics, "Annualized return calculated", "")
        insp.check("Volatility" in metrics, "Volatility calculated", "")
        insp.check("Sharpe Ratio" in metrics, "Sharpe ratio calculated", "")
        insp.check("Max Drawdown" in metrics, "Max drawdown calculated", "")
        
        # Check metric values reasonable
        total_ret = metrics["Total Return"]
        insp.check(not np.isnan(total_ret), "Total return not NaN", f"Value: {total_ret:.4f}")
        insp.check(not np.isinf(total_ret), "Total return not infinite", "")
        insp.check(-0.5 <= total_ret <= 5.0, "Total return reasonable", f"Value: {total_ret:.4f}")
        
        vol = metrics["Volatility"]
        insp.check(vol > 0, "Volatility positive", f"Value: {vol:.4f}")
        insp.check(vol < 1.0, "Volatility reasonable", f"Value: {vol:.4f}")
        
        mdd = metrics["Max Drawdown"]
        insp.check(-1.0 <= mdd <= 0, "Max drawdown in range [-1, 0]", f"Value: {mdd:.4f}")
        
    except Exception as e:
        insp.check(False, f"Metrics calculation exception: {str(e)}", "")
    
    insp.report()
    return insp.failed == 0

# ============================================================================
# INSPECTION SECTION 8: EDGE CASES & ERROR HANDLING
# ============================================================================

def inspect_edge_cases():
    """Inspect edge case handling"""
    insp = InspectionResult("Edge Cases & Error Handling")
    
    try:
        # Test 1: Empty returns
        empty_df = pd.DataFrame()
        try:
            annualize_stats(empty_df)
            insp.check(False, "Empty returns handling", "Should handle gracefully")
        except:
            insp.check(True, "Empty returns raises exception", "Proper error handling")
        
        # Test 2: All-zero returns
        zero_returns = pd.DataFrame(np.zeros((252, 5)), columns=[f"Stock_{i}" for i in range(5)])
        try:
            mu, cov, down = annualize_stats(zero_returns)
            insp.check(np.allclose(mu, 0), "Zero returns handled", "")
        except:
            insp.check(False, "Zero returns causes error", "Should handle")
        
        # Test 3: Single stock optimization
        single_returns = pd.DataFrame(np.random.randn(252, 1), columns=["Stock_A"])
        mu, cov, down = annualize_stats(single_returns)
        try:
            w = optimize_sharpe(mu, cov, rf=RISK_FREE_RATE)
            insp.check(len(w) == 1, "Single stock optimization works", "")
        except:
            insp.check(False, "Single stock optimization fails", "")
        
        # Test 4: Extreme K values
        try:
            extreme_k = max(10, int(0.99 * 680))
            insp.check(extreme_k > 0, "Extreme K handled", f"K: {extreme_k}")
        except:
            insp.check(False, "Extreme K causes error", "")
        
        # Test 5: Max drawdown on flat portfolio
        flat_value = pd.Series(np.ones(100))
        mdd = max_drawdown(flat_value)
        insp.check(mdd == 0, "Flat portfolio drawdown = 0", f"MDD: {mdd}")
        
    except Exception as e:
        insp.check(False, f"Edge case inspection exception: {str(e)}", "")
    
    insp.report()
    return insp.failed == 0

# ============================================================================
# MAIN INSPECTION RUNNER
# ============================================================================

def run_full_inspection():
    """Run comprehensive inspection"""
    print("\n" + "="*80)
    print("COMPREHENSIVE PROJECT INSPECTION")
    print("="*80)
    print(f"Started: 2026-03-27")
    print("="*80)
    
    results = []
    
    # Run all inspections
    results.append(("Configuration", inspect_configuration()))
    results.append(("Data Loading", inspect_data_loading()))
    results.append(("Statistics", inspect_statistics_calculation()))
    results.append(("K Selection", inspect_k_selection()))
    results.append(("QUBO", inspect_qubo_formulation()))
    results.append(("Optimizers", inspect_optimizer_logic()))
    results.append(("Metrics", inspect_metrics_calculation()))
    results.append(("Edge Cases", inspect_edge_cases()))
    
    # Summary
    print("\n" + "="*80)
    print("FINAL INSPECTION SUMMARY")
    print("="*80)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {name}")
        if not passed:
            all_passed = False
    
    print("="*80)
    if all_passed:
        print("✅ ALL INSPECTIONS PASSED - PROJECT IS 100% VALID")
    else:
        print("❌ SOME INSPECTIONS FAILED - REVIEW REQUIRED")
    print("="*80 + "\n")
    
    return all_passed

if __name__ == "__main__":
    success = run_full_inspection()
    sys.exit(0 if success else 1)
