"""
Matrix and metrics exporter.
Exports all intermediate matrices, QUBO matrices, and comprehensive metrics to data/ folder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd


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
    
    # Covariance matrix
    cov_train.to_csv(data_dir / "01_covariance_matrix.csv")
    
    # Returns matrix
    train_returns.to_csv(data_dir / "02_train_returns.csv")
    test_returns.to_csv(data_dir / "03_test_returns.csv")
    
    # Mean returns and downside
    stats_df = pd.DataFrame({
        "Expected_Return": mu_train,
        "Downside_Risk": downside_train,
    })
    stats_df.to_csv(data_dir / "04_expected_returns_and_downside.csv")

    # ==================== 2. QUBO Matrix ====================
    print("[Exporting] QUBO matrices...")
    
    qubo_df = pd.DataFrame(
        qubo_model.Q,
        index=qubo_model.assets,
        columns=qubo_model.assets,
    )
    qubo_df.to_csv(data_dir / "05_qubo_matrix.csv")
    
    # QUBO diagonal terms
    qubo_diag = pd.Series(
        np.diag(qubo_model.Q),
        index=qubo_model.assets,
        name="Diagonal_Terms"
    )
    qubo_diag.to_csv(data_dir / "06_qubo_diagonal_terms.csv")

    # ==================== 3. Portfolio Weights ====================
    print("[Exporting] Portfolio weights...")
    
    weights_df = pd.DataFrame({
        "Classical": classical_weights,
        "Quantum": quantum_weights,
    }).fillna(0.0)
    weights_df.to_csv(data_dir / "07_portfolio_weights.csv")

    # ==================== 4. Prices ====================
    print("[Exporting] Price series...")
    
    train_prices.to_csv(data_dir / "08_train_prices.csv")
    test_prices.to_csv(data_dir / "09_test_prices.csv")

    # ==================== 5. Portfolio Values ====================
    print("[Exporting] Portfolio values...")
    
    portfolio_df = pd.DataFrame(portfolio_values)
    portfolio_df.to_csv(data_dir / "10_portfolio_values.csv")

    if benchmark_values:
        benchmark_df = pd.DataFrame(benchmark_values)
        benchmark_df.to_csv(data_dir / "11_benchmark_values.csv")

    # ==================== 6. Comprehensive Metrics Report ====================
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
    with open(report_path, "w") as f:
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
