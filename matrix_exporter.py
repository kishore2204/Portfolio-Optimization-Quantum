"""
Matrix and metrics exporter.
Exports all intermediate matrices, QUBO matrices, and comprehensive metrics to data/ folder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import time
import gc
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')


def _safe_export_csv(df: Any, filepath: Path, max_retries: int = 10) -> None:
    """Safely export CSV with retry logic for locked files."""
    import tempfile
    
    tmppath = None
    for attempt in range(max_retries):
        try:
            gc.collect()
            time.sleep(0.1 * (attempt + 1))
            
            # Write to temporary file first
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', dir=filepath.parent) as tmp:
                tmppath = Path(tmp.name)
                
                if isinstance(df, pd.DataFrame):
                    df.to_csv(tmp, index=True)
                elif isinstance(df, pd.Series):
                    df.to_csv(tmp, index=True)
                else:
                    df.to_csv(tmp)
            
            # Atomic replace
            if filepath.exists():
                try:
                    filepath.unlink()
                except:
                    pass
            
            tmppath.replace(filepath)
            time.sleep(0.05)
            return
            
        except (PermissionError, OSError, FileNotFoundError) as e:
            if tmppath and tmppath.exists():
                try:
                    tmppath.unlink()
                except:
                    pass
            
            if attempt < max_retries - 1:
                gc.collect()
            else:
                print(f"  ⚠️  Warning: Could not write {filepath.name} - {str(e)}")


def export_matrices_and_metrics(
    data_dir: Path,
    train_returns: pd.DataFrame,
    test_returns: pd.DataFrame,
    mu_train: pd.Series,
    cov_train: pd.DataFrame,
    downside_train: pd.Series,
    qubo_model: Any,  # QuboModel
    classical_weights: pd.Series,
    quantum_weights: pd.Series,
    portfolio_values: Dict[str, pd.Series],
    benchmark_values: Dict[str, pd.Series],
    train_prices: pd.DataFrame,
    test_prices: pd.DataFrame,
    split_dates: dict,
    config_dict: dict,
) -> None:
    """
    Export all matrices and metrics to CSV and readable formats.
    
    Args:
        data_dir: Output directory
        train_returns: Training returns DataFrame
        test_returns: Test returns DataFrame
        mu_train: Annualized expected returns
        cov_train: Annualized covariance matrix
        downside_train: Downside risk (semi-deviation)
        qubo_model: QuboModel object
        classical_weights: Classical portfolio weights
        quantum_weights: Quantum portfolio weights
        portfolio_values: Dict of portfolio value time series
        benchmark_values: Dict of benchmark value time series
        train_prices: Training prices
        test_prices: Test prices
        split_dates: Dict with train/test date boundaries
        config_dict: Configuration parameters
    """
    data_dir.mkdir(parents=True, exist_ok=True)

    # ==================== 1. Input Matrices ====================
    print("[Exporting] Input matrices...")
    
    # Covariance matrix - ensure row/column labels
    cov_with_index = pd.DataFrame(
        cov_train.values,
        index=cov_train.index,
        columns=cov_train.columns,
    )
    _safe_export_csv(cov_with_index, data_dir / "01_covariance_matrix.csv")
    
    # Returns matrix
    _safe_export_csv(train_returns, data_dir / "02_train_returns.csv")
    _safe_export_csv(test_returns, data_dir / "03_test_returns.csv")
    
    # Mean returns and downside
    stats_df = pd.DataFrame({
        "Expected_Return": mu_train,
        "Downside_Risk": downside_train,
    })
    _safe_export_csv(stats_df, data_dir / "04_expected_returns_and_downside.csv")

    # ==================== 2. QUBO Matrix ====================
    print("[Exporting] QUBO matrices...")
    
    qubo_df = pd.DataFrame(
        qubo_model.Q,
        index=qubo_model.assets,
        columns=qubo_model.assets,
    )
    _safe_export_csv(qubo_df, data_dir / "05_qubo_matrix.csv")
    
    # QUBO diagonal terms
    qubo_diag = pd.Series(
        np.diag(qubo_model.Q),
        index=qubo_model.assets,
        name="Diagonal_Terms"
    )
    _safe_export_csv(qubo_diag, data_dir / "06_qubo_diagonal_terms.csv")

    # ==================== 3. Portfolio Weights ====================
    print("[Exporting] Portfolio weights...")
    
    weights_df = pd.DataFrame({
        "Classical": classical_weights,
        "Quantum": quantum_weights,
    }).fillna(0.0)
    _safe_export_csv(weights_df, data_dir / "07_portfolio_weights.csv")

    # ==================== 4. Prices ====================
    print("[Exporting] Price series...")
    
    _safe_export_csv(train_prices, data_dir / "08_train_prices.csv")
    _safe_export_csv(test_prices, data_dir / "09_test_prices.csv")

    # ==================== 5. Portfolio Values ====================
    print("[Exporting] Portfolio values...")
    
    portfolio_df = pd.DataFrame(portfolio_values)
    _safe_export_csv(portfolio_df, data_dir / "10_portfolio_values.csv")

    if benchmark_values:
        benchmark_df = pd.DataFrame(benchmark_values)
        _safe_export_csv(benchmark_df, data_dir / "11_benchmark_values.csv")

    # ==================== 6. QUBO Inputs (All Components) ====================
    print("[Exporting] QUBO inputs breakdown...")
    
    qubo_inputs = _export_qubo_inputs(
        mu_train=mu_train,
        cov_train=cov_train,
        downside_train=downside_train,
        qubo_model=qubo_model,
        config_dict=config_dict,
        data_dir=data_dir,
    )

    # ==================== 7. Constants (Fixed & Adaptive) ====================
    print("[Exporting] All constants...")
    
    _export_all_constants(
        config_dict=config_dict,
        qubo_model=qubo_model,
        data_dir=data_dir,
    )

    # ==================== 8. Comprehensive Metrics Report ====================
    print("[Exporting] Comprehensive metrics report...")
    
    report = _build_comprehensive_report(
        train_returns=train_returns,
        test_returns=test_returns,
        mu_train=mu_train,
        cov_train=cov_train,
        downside_train=downside_train,
        qubo_model=qubo_model,
        classical_weights=classical_weights,
        quantum_weights=quantum_weights,
        portfolio_values=portfolio_values,
        benchmark_values=benchmark_values,
        split_dates=split_dates,
        config_dict=config_dict,
    )
    
    report_path = data_dir / "12_COMPREHENSIVE_METRICS_REPORT.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"✓ Report saved to {report_path}")


def _build_comprehensive_report(
    train_returns: pd.DataFrame,
    test_returns: pd.DataFrame,
    mu_train: pd.Series,
    cov_train: pd.DataFrame,
    downside_train: pd.Series,
    qubo_model: Any,
    classical_weights: pd.Series,
    quantum_weights: pd.Series,
    portfolio_values: Dict[str, pd.Series],
    benchmark_values: Dict[str, pd.Series],
    split_dates: dict,
    config_dict: dict,
) -> str:
    """Build a comprehensive human-readable metrics report."""
    
    lines = []
    lines.append("=" * 80)
    lines.append("QUANTUM-INSPIRED PORTFOLIO OPTIMIZATION - COMPREHENSIVE METRICS REPORT")
    lines.append("=" * 80)
    lines.append("")

    # ==================== SECTION 1: Dataset Overview ====================
    lines.append("\n[1] DATASET OVERVIEW")
    lines.append("-" * 80)
    lines.append(f"  Total Assets in Universe:          {train_returns.shape[1]}")
    lines.append(f"  Training Period:                   {split_dates.get('train_start')} to {split_dates.get('train_end')}")
    lines.append(f"  Test Period:                       {split_dates.get('test_start')} to {split_dates.get('test_end')}")
    lines.append(f"  Training Days:                     {train_returns.shape[0]}")
    lines.append(f"  Test Days:                         {test_returns.shape[0]}")
    lines.append("")

    # ==================== SECTION 2: Risk Statistics ====================
    lines.append("\n[2] ANNUALIZED RISK STATISTICS (Training Period)")
    lines.append("-" * 80)
    lines.append(f"  Universe Mean Return:              {mu_train.mean():.6f}")
    lines.append(f"  Universe Min Return:               {mu_train.min():.6f}")
    lines.append(f"  Universe Max Return:               {mu_train.max():.6f}")
    lines.append(f"  Universe Mean Volatility:          {train_returns.std().mean():.6f}")
    lines.append(f"  Covariance Matrix Eigenvalues:")
    eigenvalues = np.linalg.eigvals(cov_train.values)
    eigenvalues_sorted = np.sort(eigenvalues)[::-1]
    lines.append(f"    - Largest:                       {eigenvalues_sorted[0]:.6f}")
    lines.append(f"    - Smallest:                      {eigenvalues_sorted[-1]:.6f}")
    lines.append(f"    - Condition Number:              {eigenvalues_sorted[0] / eigenvalues_sorted[-1]:.2f}")
    lines.append(f"  Downside Risk (Semi-Deviation):    {downside_train.mean():.6f} avg")
    lines.append("")

    # ==================== SECTION 3: Classical Portfolio ====================
    lines.append("\n[3] CLASSICAL PORTFOLIO (MVO + Sharpe)")
    lines.append("-" * 80)
    nonzero_classical = (classical_weights > 0).sum()
    lines.append(f"  Selected Assets:                   {nonzero_classical}")
    lines.append(f"  Portfolio Concentration (HHI):     {(classical_weights ** 2).sum():.4f}")
    lines.append(f"  Max Weight:                        {classical_weights.max():.4f}")
    lines.append(f"  Top 5 Assets by Weight:")
    top_5_classical = classical_weights.nlargest(5)
    for asset, weight in top_5_classical.items():
        lines.append(f"    - {asset}: {weight:.4f}")
    lines.append("")

    # ==================== SECTION 4: Quantum Portfolio ====================
    lines.append("\n[4] QUANTUM PORTFOLIO (QUBO + Annealing + Sharpe)")
    lines.append("-" * 80)
    nonzero_quantum = (quantum_weights > 0).sum()
    lines.append(f"  Selected Assets:                   {nonzero_quantum}")
    lines.append(f"  Portfolio Concentration (HHI):     {(quantum_weights ** 2).sum():.4f}")
    lines.append(f"  Max Weight:                        {quantum_weights.max():.4f}")
    lines.append(f"  Top 5 Assets by Weight:")
    top_5_quantum = quantum_weights.nlargest(5)
    for asset, weight in top_5_quantum.items():
        lines.append(f"    - {asset}: {weight:.4f}")
    lines.append("")

    # ==================== SECTION 5: QUBO Configuration ====================
    lines.append("\n[5] QUBO CONFIGURATION")
    lines.append("-" * 80)
    lines.append(f"  QUBO Matrix Size:                  {qubo_model.Q.shape}")
    lines.append(f"  QUBO Diagonal Mean:                {np.diag(qubo_model.Q).mean():.6f}")
    lines.append(f"  QUBO Off-Diagonal Mean:            {(qubo_model.Q - np.diag(np.diag(qubo_model.Q))).mean():.6f}")
    lines.append(f"  QUBO Sparsity:                     {1.0 - np.count_nonzero(qubo_model.Q) / qubo_model.Q.size:.4f}")
    lines.append("")

    # ==================== SECTION 6: Performance Metrics ====================
    lines.append("\n[6] TEST PERIOD PERFORMANCE METRICS")
    lines.append("-" * 80)
    
    # Portfolio metrics
    for pname, pvals in portfolio_values.items():
        if pvals is None or pvals.empty:
            continue
        
        total_ret = (pvals.iloc[-1] / pvals.iloc[0]) - 1.0
        log_rets = np.diff(np.log(pvals.values))
        log_rets = log_rets[~np.isnan(log_rets)]
        ann_ret = np.mean(log_rets) * 252 if len(log_rets) > 0 else 0.0
        ann_vol = np.std(log_rets) * np.sqrt(252) if len(log_rets) > 0 else 0.0
        sharpe = (ann_ret - 0.05) / ann_vol if ann_vol > 0 else 0.0
        
        # Max drawdown
        running_max = np.maximum.accumulate(pvals.values)
        dd = (pvals.values - running_max) / running_max
        max_dd = np.min(dd)
        
        lines.append(f"\n  Portfolio: {pname}")
        lines.append(f"    Total Return:                   {total_ret:.4f} ({total_ret*100:.2f}%)")
        lines.append(f"    Annualized Return:             {ann_ret:.4f} ({ann_ret*100:.2f}%)")
        lines.append(f"    Annualized Volatility:         {ann_vol:.4f} ({ann_vol*100:.2f}%)")
        lines.append(f"    Sharpe Ratio (rf=5%):          {sharpe:.4f}")
        lines.append(f"    Maximum Drawdown:              {max_dd:.4f} ({max_dd*100:.2f}%)")
    
    # Benchmark metrics
    if benchmark_values:
        lines.append(f"\n  Benchmarks:")
        for bname, bvals in benchmark_values.items():
            if bvals is None or bvals.empty:
                continue
            total_ret = (bvals.iloc[-1] / bvals.iloc[0]) - 1.0
            log_rets = np.diff(np.log(bvals.values))
            log_rets = log_rets[~np.isnan(log_rets)]
            ann_ret = np.mean(log_rets) * 252 if len(log_rets) > 0 else 0.0
            ann_vol = np.std(log_rets) * np.sqrt(252) if len(log_rets) > 0 else 0.0
            sharpe = (ann_ret - 0.05) / ann_vol if ann_vol > 0 else 0.0
            
            lines.append(f"    {bname}:")
            lines.append(f"      Total Return:               {total_ret:.4f} ({total_ret*100:.2f}%)")
            lines.append(f"      Annualized Return:          {ann_ret:.4f} ({ann_ret*100:.2f}%)")
            lines.append(f"      Annualized Volatility:      {ann_vol:.4f} ({ann_vol*100:.2f}%)")
            lines.append(f"      Sharpe Ratio (rf=5%):       {sharpe:.4f}")
    
    lines.append("")

    # ==================== SECTION 7: Comparison ====================
    lines.append("\n[7] PORTFOLIO COMPARISON SUMMARY")
    lines.append("-" * 80)
    
    if "Classical" in portfolio_values and "Quantum" in portfolio_values:
        c_val = portfolio_values["Classical"]
        q_val = portfolio_values["Quantum"]
        if not c_val.empty and not q_val.empty:
            c_ret = (c_val.iloc[-1] / c_val.iloc[0]) - 1.0
            q_ret = (q_val.iloc[-1] / q_val.iloc[0]) - 1.0
            outperformance = q_ret - c_ret
            lines.append(f"  Classical vs Quantum:")
            lines.append(f"    Quantum Outperformance:        {outperformance:.4f} ({outperformance*100:.2f}%)")
    
    lines.append("")

    # ==================== SECTION 8: Configuration ====================
    lines.append("\n[8] CONFIGURATION PARAMETERS")
    lines.append("-" * 80)
    for key, val in sorted(config_dict.items()):
        lines.append(f"  {key}: {val}")
    lines.append("")

    lines.append("\n" + "=" * 80)
    lines.append("END OF REPORT")
    lines.append("=" * 80)

    return "\n".join(lines)


def _export_qubo_inputs(
    mu_train: pd.Series,
    cov_train: pd.DataFrame,
    downside_train: pd.Series,
    qubo_model: Any,
    config_dict: dict,
    data_dir: Path,
) -> dict:
    """
    Export all QUBO input components separately for inspection.
    
    Creates:
    - QUBO_inputs_expected_returns.csv: μ (expected returns)
    - QUBO_inputs_downside_risk.csv: σ_down (downside volatility)
    - QUBO_inputs_linear_terms.csv: Diagonal components of QUBO
    - QUBO_inputs_summary.txt: Human-readable summary
    """
    
    # 1. Expected returns (μ)
    mu_df = pd.DataFrame({
        "Asset": mu_train.index,
        "Expected_Return_Annual": mu_train.values,
    })
    mu_df.set_index("Asset", inplace=True)
    _safe_export_csv(mu_df, data_dir / "QUBO_inputs_expected_returns.csv")
    
    # 2. Downside risk (σ_down)
    downside_df = pd.DataFrame({
        "Asset": downside_train.index,
        "Downside_Risk_Annual": downside_train.values,
    })
    downside_df.set_index("Asset", inplace=True)
    _safe_export_csv(downside_df, data_dir / "QUBO_inputs_downside_risk.csv")
    
    # 3. Linear terms (covariance + expected returns penalty + downside penalty)
    q_risk = config_dict.get("q_risk", 0.5)
    beta_downside = config_dict.get("beta_downside", 0.3)
    
    # Extract covariance diagonals
    cov_diag = np.diag(cov_train.values)
    
    # Linear terms = -μ + β*σ_down (from QUBO construction)
    linear_terms = -mu_train.values + beta_downside * downside_train.values
    
    linear_df = pd.DataFrame({
        "Asset": mu_train.index,
        "Covariance_Diagonal": cov_diag,
        "Expected_Return_Penalty": -mu_train.values,
        "Downside_Risk_Penalty": (beta_downside * downside_train.values),
        "Total_Linear_Term": linear_terms,
    })
    linear_df.set_index("Asset", inplace=True)
    _safe_export_csv(linear_df, data_dir / "QUBO_inputs_linear_terms.csv")
    
    # 4. Covariance correlation matrix (for reference)
    cov_std = np.sqrt(np.diag(cov_train.values))
    corr_matrix = cov_train.values / np.outer(cov_std, cov_std)
    corr_df = pd.DataFrame(corr_matrix, index=cov_train.index, columns=cov_train.columns)
    _safe_export_csv(corr_df, data_dir / "QUBO_inputs_correlation_matrix.csv")
    
    # 5. Summary document
    summary_lines = []
    summary_lines.append("=" * 80)
    summary_lines.append("QUBO INPUT COMPONENTS - SUMMARY")
    summary_lines.append("=" * 80)
    summary_lines.append("")
    
    summary_lines.append("[1] COVARIANCE MATRIX")
    summary_lines.append("-" * 80)
    summary_lines.append(f"Shape: {cov_train.shape}")
    summary_lines.append(f"Diagonal Mean: {np.mean(cov_diag):.6f}")
    summary_lines.append(f"Diagonal Min: {np.min(cov_diag):.6f}")
    summary_lines.append(f"Diagonal Max: {np.max(cov_diag):.6f}")
    summary_lines.append("")
    
    summary_lines.append("[2] EXPECTED RETURNS (μ)")
    summary_lines.append("-" * 80)
    summary_lines.append(f"Mean: {mu_train.mean():.6f}")
    summary_lines.append(f"Min: {mu_train.min():.6f}")
    summary_lines.append(f"Max: {mu_train.max():.6f}")
    summary_lines.append(f"Std Dev: {mu_train.std():.6f}")
    summary_lines.append("")
    
    summary_lines.append("[3] DOWNSIDE RISK (σ_down)")
    summary_lines.append("-" * 80)
    summary_lines.append(f"Mean: {downside_train.mean():.6f}")
    summary_lines.append(f"Min: {downside_train.min():.6f}")
    summary_lines.append(f"Max: {downside_train.max():.6f}")
    summary_lines.append(f"Std Dev: {downside_train.std():.6f}")
    summary_lines.append("")
    
    summary_lines.append("[4] LINEAR TERMS BREAKDOWN")
    summary_lines.append("-" * 80)
    summary_lines.append(f"Expected Return Penalty (mean): {(-mu_train.values).mean():.6f}")
    summary_lines.append(f"Downside Risk Penalty (mean): {(beta_downside * downside_train.values).mean():.6f}")
    summary_lines.append(f"Total Linear Term (mean): {linear_terms.mean():.6f}")
    summary_lines.append("")
    
    summary_lines.append("[5] CORRELATION MATRIX STATS")
    summary_lines.append("-" * 80)
    summary_lines.append(f"Mean Correlation: {(corr_matrix[np.triu_indices_from(corr_matrix, k=1)]).mean():.6f}")
    summary_lines.append(f"Min Correlation: {(corr_matrix[np.triu_indices_from(corr_matrix, k=1)]).min():.6f}")
    summary_lines.append(f"Max Correlation: {(corr_matrix[np.triu_indices_from(corr_matrix, k=1)]).max():.6f}")
    summary_lines.append("")
    
    summary_lines.append("=" * 80)
    summary_lines.append("END QUBO INPUTS SUMMARY")
    summary_lines.append("=" * 80)
    
    summary_path = data_dir / "QUBO_inputs_summary.txt"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))
    
    return {"status": "exported"}


def _export_all_constants(
    config_dict: dict,
    qubo_model: Any,
    data_dir: Path,
) -> None:
    """
    Export all constants (fixed and adaptive) in separate CSV files.
    
    Creates:
    - CONSTANTS_FIXED.csv: Fixed parameter values
    - CONSTANTS_ADAPTIVE.csv: Computed/adaptive constants
    - CONSTANTS_full_summary.txt: Human-readable complete summary
    """
    
    # ==================== Fixed Constants ====================
    fixed_constants = {
        "q_risk": "Risk weighting in QUBO covariance term",
        "beta_downside": "Downside risk penalty coefficient",
        "max_weight": "Maximum weight per asset constraint",
        "max_per_sector": "Maximum assets per sector constraint",
        "risk_free_rate": "Risk-free rate for Sharpe ratio",
        "transaction_cost": "Transaction cost per unit turnover",
        "lookback_days": "Lookback window for rebalancing (days)",
        "rebalance_days": "Rebalancing cadence (days)",
        "annealing_t0": "Initial temperature for simulated annealing",
        "annealing_t1": "Final temperature for simulated annealing",
        "annealing_steps": "Number of annealing iterations",
    }
    
    fixed_df_list = []
    for const_name, description in fixed_constants.items():
        value = config_dict.get(const_name, None)
        fixed_df_list.append({
            "Constant": const_name,
            "Value": value,
            "Description": description,
            "Source": "config_constants.py (Fixed)",
        })
    
    fixed_df = pd.DataFrame(fixed_df_list)
    _safe_export_csv(fixed_df, data_dir / "CONSTANTS_FIXED.csv")
    
    # ==================== Adaptive Constants ====================
    adaptive_constants = {
        "lambda_card": "Cardinality penalty (computed from scale and N/K ratio)",
        "gamma_sector": "Sector penalty (0.1 × lambda_card)",
    }
    
    adaptive_df_list = []
    for const_name, description in adaptive_constants.items():
        value = config_dict.get(const_name, None)
        adaptive_df_list.append({
            "Constant": const_name,
            "Value": value,
            "Description": description,
            "Source": "Computed (Adaptive)",
        })
    
    adaptive_df = pd.DataFrame(adaptive_df_list)
    _safe_export_csv(adaptive_df, data_dir / "CONSTANTS_ADAPTIVE.csv")
    
    # ==================== Full Summary Document ====================
    summary_lines = []
    summary_lines.append("=" * 80)
    summary_lines.append("COMPLETE CONSTANTS REFERENCE")
    summary_lines.append("=" * 80)
    summary_lines.append("")
    
    summary_lines.append("[PART 1: FIXED CONSTANTS]")
    summary_lines.append("-" * 80)
    summary_lines.append("These constants are fixed in config_constants.py")
    summary_lines.append("")
    
    for const_name, description in fixed_constants.items():
        value = config_dict.get(const_name, "NOT SET")
        summary_lines.append(f"{const_name:25} = {value}")
        summary_lines.append(f"{'':25}   {description}")
        summary_lines.append("")
    
    summary_lines.append("")
    summary_lines.append("[PART 2: ADAPTIVE CONSTANTS]")
    summary_lines.append("-" * 80)
    summary_lines.append("These constants are computed based on problem size and scale")
    summary_lines.append("")
    
    for const_name, description in adaptive_constants.items():
        value = config_dict.get(const_name, "NOT SET")
        summary_lines.append(f"{const_name:25} = {value}")
        summary_lines.append(f"{'':25}   {description}")
        summary_lines.append("")
    
    summary_lines.append("")
    summary_lines.append("[PART 3: DERIVED VALUES]")
    summary_lines.append("-" * 80)
    summary_lines.append(f"QUBO Matrix Size:         {qubo_model.Q.shape}")
    summary_lines.append(f"Number of Selected Assets: {len(qubo_model.assets)}")
    summary_lines.append(f"Targeting Portfolio K:     {config_dict.get('selected_k', 'NOT SET')}")
    summary_lines.append("")
    
    summary_lines.append("[PART 4: FORMULAS]")
    summary_lines.append("-" * 80)
    summary_lines.append("")
    summary_lines.append("Lambda (Cardinality Penalty) Computation:")
    summary_lines.append("  λ = clip(10 × scale × (N / K), 50, 500)")
    summary_lines.append("  where:")
    summary_lines.append("    N = number of assets in candidate universe")
    summary_lines.append("    K = target portfolio size")
    summary_lines.append("    scale = max(|diagonal terms|) of QUBO")
    summary_lines.append("")
    
    summary_lines.append("Gamma (Sector Penalty) Computation:")
    summary_lines.append("  γ = 0.1 × λ")
    summary_lines.append("")
    
    summary_lines.append("QUBO Objective Function:")
    summary_lines.append("  E(x) = x^T Q x")
    summary_lines.append("  where Q = q_risk × Σ + linear_terms + cardinality_penalty + sector_penalty")
    summary_lines.append("")
    
    summary_lines.append("Sharpe Ratio Calculation:")
    summary_lines.append("  Sharpe = (μ_p - r_f) / σ_p")
    summary_lines.append("  where:")
    summary_lines.append("    μ_p = portfolio annualized expected return")
    summary_lines.append("    σ_p = portfolio annualized volatility")
    summary_lines.append("    r_f = risk-free rate (5%)")
    summary_lines.append("")
    
    summary_lines.append("=" * 80)
    summary_lines.append("All constants are accessible in data/ folder CSV files")
    summary_lines.append("=" * 80)
    
    summary_path = data_dir / "CONSTANTS_full_summary.txt"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))
    
    print(f"✓ Constants exported to {data_dir}/")
    print(f"  - CONSTANTS_FIXED.csv")
    print(f"  - CONSTANTS_ADAPTIVE.csv")
    print(f"  - CONSTANTS_full_summary.txt")
