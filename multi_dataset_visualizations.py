"""
Multi-dataset comparison visualizations.
Creates 5 graph types for each dataset (benchmark/index).
Total: 25 graphs (5 types × 5 datasets)
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def _normalize_benchmark_with_discontinuity_fix(benchmark_series: pd.Series, dataset_name: str) -> pd.Series:
    """
    Normalize benchmark handling ETF mergers/splits/discontinuities.
    
    Detects sudden value drops (>20%) that indicate ETF events and adjusts normalization
    to ensure continuous growth curves.
    """
    if benchmark_series is None or benchmark_series.empty:
        return pd.Series()
    
    # Clean data
    series = pd.to_numeric(benchmark_series, errors="coerce").dropna()
    if series.empty:
        return series / series.iloc[0] if not series.empty else series
    
    # Check for discontinuities (sudden drops > 20%)
    # This typically indicates ETF merger/split
    pct_changes = series.pct_change().abs()
    discontinuity_threshold = 0.20
    has_discontinuities = (pct_changes > discontinuity_threshold).any()
    
    if has_discontinuities and dataset_name.lower() == "HDFCNIF100":
        # For HDFCNIF100, detect the discontinuity point
        discontinuity_idx = np.where(pct_changes > discontinuity_threshold)[0]
        if len(discontinuity_idx) > 0:
            split_point = discontinuity_idx[0]
            
            # Normalize in two segments and splice them
            before = series.iloc[:split_point+1].copy()
            after = series.iloc[split_point+1:].copy()
            
            # Normalize each segment separately
            before_normalized = before / before.iloc[0]
            
            # Adjust after to connect smoothly to before
            splice_value = before_normalized.iloc[-1]
            after_normalized = (after / after.iloc[0]) * splice_value
            
            # Combine
            result = pd.concat([before_normalized, after_normalized.iloc[1:]])
            return result.sort_index()
    
    # Default normalization
    return series / series.iloc[0]

def create_5_graphs_per_dataset(
    portfolio_values: Dict[str, pd.Series],
    benchmark_values: Dict[str, pd.Series],
    output_dir: Path,
) -> Dict[str, list[str]]:
    """
    Create 5 graph types for each dataset.
    
    Args:
        portfolio_values: Dict with "Quantum", "Quantum_Rebalanced" portfolio values
        benchmark_values: Dict with benchmark time series (keys: index names)
        output_dir: Output directory for graphs
        
    Returns:
        Dict mapping dataset name to list of generated file paths
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    results = {}

    print("\n[Multi-Dataset Visualizations] Creating 5 graphs per dataset...")
    print(f"Datasets to process: {list(benchmark_values.keys())}")

    for dataset_name, benchmark_series in benchmark_values.items():
        if benchmark_series.empty:
            continue

        print(f"\n  Processing: {dataset_name}")
        generated_files = _create_graphs_for_dataset(
            portfolio_values=portfolio_values,
            benchmark_series=benchmark_series,
            dataset_name=dataset_name,
            output_dir=output_dir,
        )
        results[dataset_name] = generated_files
        print(f"    ✓ Generated {len(generated_files)} graphs")

    return results


def _create_graphs_for_dataset(
    portfolio_values: Dict[str, pd.Series],
    benchmark_series: pd.Series,
    dataset_name: str,
    output_dir: Path,
) -> list[str]:
    """Create ONLY Graph 1 (Cumulative Returns) for a specific dataset."""
    generated = []

    # Type 1: Cumulative Returns Overlay (ONLY THIS GRAPH)
    path1 = _create_cumulative_returns_comparison(
        portfolio_values, benchmark_series, dataset_name, output_dir
    )
    generated.append(path1)
    print(f"      ✓ Graph 1: Cumulative Returns")

    # Skipped: Graph 2-5 (user only wants cumulative returns)
    # path2 = _create_rolling_sharpe_comparison(...)
    # path3 = _create_relative_performance(...)
    # path4 = _create_volatility_return_scatter(...)
    # path5 = _create_drawdown_comparison(...)

    return generated


def _create_cumulative_returns_comparison(
    portfolio_values: Dict[str, pd.Series],
    benchmark_series: pd.Series,
    dataset_name: str,
    output_dir: Path,
) -> str:
    """Graph Type 1: Cumulative Returns of Quantum, Rebalanced, and Benchmark.
    
    Handles ETF mergers/splits by detecting discontinuities and adjusting normalization.
    """
    fig, ax = plt.subplots(figsize=(14, 7))

    # Normalize benchmark handling ETF discontinuities
    benchmark_cleaned = _normalize_benchmark_with_discontinuity_fix(benchmark_series, dataset_name)

    for name in ["Quantum", "Quantum_Rebalanced"]:
        if name in portfolio_values and not portfolio_values[name].empty:
            values = portfolio_values[name]
            cumulative_returns = (values / values.iloc[0] - 1) * 100
            color = "#1f77b4" if name == "Quantum" else "#ff7f0e"
            ax.plot(
                cumulative_returns.index,
                cumulative_returns.values,
                label=name,
                linewidth=2.5,
                color=color,
                alpha=0.9,
            )

    # Add benchmark
    benchmark_returns = (benchmark_cleaned - 1) * 100
    ax.plot(
        benchmark_returns.index,
        benchmark_returns.values,
        label=f"{dataset_name} (Benchmark)",
        linewidth=2.0,
        color="gray",
        linestyle="--",
        alpha=0.7,
    )

    ax.set_xlabel("Date", fontsize=12, fontweight="bold")
    ax.set_ylabel("Cumulative Returns (%)", fontsize=12, fontweight="bold")
    ax.set_title(
        f"Cumulative Returns: Quantum vs Rebalanced vs {dataset_name}",
        fontsize=14,
        fontweight="bold",
    )
    ax.legend(fontsize=11, loc="best")
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color="black", linestyle="--", linewidth=0.8, alpha=0.5)

    filename = f"D1_cumulative_returns_{dataset_name}.png"
    filepath = output_dir / filename
    plt.tight_layout()
    plt.savefig(filepath, dpi=300, bbox_inches="tight")
    plt.close()

    return str(filepath)


def _create_rolling_sharpe_comparison(
    portfolio_values: Dict[str, pd.Series],
    benchmark_series: pd.Series,
    dataset_name: str,
    output_dir: Path,
) -> str:
    """Graph Type 2: Rolling 1-Year Sharpe Ratio."""
    fig, ax = plt.subplots(figsize=(14, 7))

    window = 252
    rf = 0.05

    for name in ["Quantum", "Quantum_Rebalanced"]:
        if name in portfolio_values and not portfolio_values[name].empty:
            values = portfolio_values[name].values
            log_returns = np.diff(np.log(values))

            rolling_mean = pd.Series(log_returns).rolling(window).mean() * 252
            rolling_std = pd.Series(log_returns).rolling(window).std() * np.sqrt(252)
            rolling_sharpe = (rolling_mean - rf) / (rolling_std + 1e-8)

            rolling_sharpe.index = portfolio_values[name].index[1:]
            color = "#1f77b4" if name == "Quantum" else "#ff7f0e"
            ax.plot(
                rolling_sharpe.index,
                rolling_sharpe.values,
                label=name,
                linewidth=2.5,
                color=color,
                alpha=0.9,
            )

    # Add benchmark Sharpe
    benchmark_log_returns = np.diff(np.log(benchmark_series.values))
    benchmark_rolling_mean = (
        pd.Series(benchmark_log_returns).rolling(window).mean() * 252
    )
    benchmark_rolling_std = (
        pd.Series(benchmark_log_returns).rolling(window).std() * np.sqrt(252)
    )
    benchmark_rolling_sharpe = (benchmark_rolling_mean - rf) / (
        benchmark_rolling_std + 1e-8
    )
    benchmark_rolling_sharpe.index = benchmark_series.index[1:]

    ax.plot(
        benchmark_rolling_sharpe.index,
        benchmark_rolling_sharpe.values,
        label=f"{dataset_name} Sharpe",
        linewidth=2.0,
        color="gray",
        linestyle="--",
        alpha=0.7,
    )

    ax.set_xlabel("Date", fontsize=12, fontweight="bold")
    ax.set_ylabel("Rolling Sharpe Ratio (252-day)", fontsize=12, fontweight="bold")
    ax.set_title(
        f"Rolling 1-Year Sharpe Ratio: Quantum vs Rebalanced vs {dataset_name}",
        fontsize=14,
        fontweight="bold",
    )
    ax.legend(fontsize=11, loc="best")
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color="black", linestyle="--", linewidth=0.8, alpha=0.5)

    filename = f"D2_rolling_sharpe_{dataset_name}.png"
    filepath = output_dir / filename
    plt.tight_layout()
    plt.savefig(filepath, dpi=300, bbox_inches="tight")
    plt.close()

    return str(filepath)


def _create_relative_performance(
    portfolio_values: Dict[str, pd.Series],
    benchmark_series: pd.Series,
    dataset_name: str,
    output_dir: Path,
) -> str:
    """Graph Type 3: Relative Performance vs Benchmark."""
    fig, ax = plt.subplots(figsize=(14, 7))

    benchmark_normalized = benchmark_series / benchmark_series.iloc[0]

    for name in ["Quantum", "Quantum_Rebalanced"]:
        if name in portfolio_values and not portfolio_values[name].empty:
            values = portfolio_values[name]
            # Relative performance = portfolio / benchmark
            relative_perf = (values / values.iloc[0]) / (benchmark_normalized) - 1
            relative_perf_pct = relative_perf * 100

            color = "#1f77b4" if name == "Quantum" else "#ff7f0e"
            ax.plot(
                relative_perf_pct.index,
                relative_perf_pct.values,
                label=name,
                linewidth=2.5,
                color=color,
                alpha=0.9,
            )

    ax.set_xlabel("Date", fontsize=12, fontweight="bold")
    ax.set_ylabel(f"Relative Performance vs {dataset_name} (%)", fontsize=12, fontweight="bold")
    ax.set_title(
        f"Relative Performance: Quantum & Rebalanced vs {dataset_name}",
        fontsize=14,
        fontweight="bold",
    )
    ax.legend(fontsize=11, loc="best")
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color="black", linestyle="--", linewidth=0.8, alpha=0.5)
    ax.fill_between(
        ax.get_xlim(), 0, 1, transform=ax.get_xaxis_transform(), alpha=0.05, color="green"
    )

    filename = f"D3_relative_performance_{dataset_name}.png"
    filepath = output_dir / filename
    plt.tight_layout()
    plt.savefig(filepath, dpi=300, bbox_inches="tight")
    plt.close()

    return str(filepath)


def _create_volatility_return_scatter(
    portfolio_values: Dict[str, pd.Series],
    benchmark_series: pd.Series,
    dataset_name: str,
    output_dir: Path,
) -> str:
    """Graph Type 4: Monthly Volatility vs Return scatter."""
    fig, ax = plt.subplots(figsize=(14, 8))

    # Monthly aggregation
    monthly_data = {}

    for name in ["Quantum", "Quantum_Rebalanced"]:
        if name in portfolio_values and not portfolio_values[name].empty:
            values = portfolio_values[name]
            monthly_values = values.resample("M").last()
            monthly_returns = np.diff(np.log(monthly_values.values))

            monthly_data[name] = monthly_returns

    benchmark_monthly = benchmark_series.resample("M").last()
    benchmark_returns = np.diff(np.log(benchmark_monthly.values))

    # Create scatter: each point = rolling 12-month statistics
    window = 12

    for name in ["Quantum", "Quantum_Rebalanced"]:
        if name in monthly_data:
            returns = monthly_data[name]
            volatilities = pd.Series(returns).rolling(window).std() * np.sqrt(12)
            ret_means = pd.Series(returns).rolling(window).mean() * 12

            color = "#1f77b4" if name == "Quantum" else "#ff7f0e"
            marker = "o" if name == "Quantum" else "^"
            ax.scatter(
                volatilities.values * 100,
                ret_means.values * 100,
                s=50,
                alpha=0.6,
                color=color,
                label=name,
                marker=marker,
            )

    # Add benchmark scatter
    benchmark_volatilities = pd.Series(benchmark_returns).rolling(window).std() * np.sqrt(12)
    benchmark_ret_means = pd.Series(benchmark_returns).rolling(window).mean() * 12

    ax.scatter(
        benchmark_volatilities.values * 100,
        benchmark_ret_means.values * 100,
        s=50,
        alpha=0.6,
        color="gray",
        label=f"{dataset_name}",
        marker="D",
    )

    ax.set_xlabel("Annualized Volatility (%)", fontsize=12, fontweight="bold")
    ax.set_ylabel("Annualized Return (%)", fontsize=12, fontweight="bold")
    ax.set_title(
        f"Risk-Return Profile (12-Month Rolling): vs {dataset_name}",
        fontsize=14,
        fontweight="bold",
    )
    ax.legend(fontsize=11, loc="best")
    ax.grid(True, alpha=0.3)

    filename = f"D4_risk_return_scatter_{dataset_name}.png"
    filepath = output_dir / filename
    plt.tight_layout()
    plt.savefig(filepath, dpi=300, bbox_inches="tight")
    plt.close()

    return str(filepath)


def _create_drawdown_comparison(
    portfolio_values: Dict[str, pd.Series],
    benchmark_series: pd.Series,
    dataset_name: str,
    output_dir: Path,
) -> str:
    """Graph Type 5: Drawdown Analysis."""
    fig, ax = plt.subplots(figsize=(14, 7))

    colors = {"Quantum": "#1f77b4", "Quantum_Rebalanced": "#ff7f0e"}

    for name in ["Quantum", "Quantum_Rebalanced"]:
        if name in portfolio_values and not portfolio_values[name].empty:
            values = portfolio_values[name].values
            running_max = np.maximum.accumulate(values)
            drawdown = (values - running_max) / running_max * 100

            ax.fill_between(
                portfolio_values[name].index,
                drawdown,
                0,
                alpha=0.3,
                color=colors.get(name),
                label=name,
            )
            ax.plot(
                portfolio_values[name].index,
                drawdown,
                linewidth=1.5,
                color=colors.get(name),
            )

    # Add benchmark drawdown
    benchmark_values = benchmark_series.values
    benchmark_running_max = np.maximum.accumulate(benchmark_values)
    benchmark_dd = (benchmark_values - benchmark_running_max) / benchmark_running_max * 100

    ax.plot(
        benchmark_series.index,
        benchmark_dd,
        linewidth=2.0,
        color="gray",
        linestyle="--",
        label=f"{dataset_name}",
        alpha=0.7,
    )

    ax.set_xlabel("Date", fontsize=12, fontweight="bold")
    ax.set_ylabel("Drawdown (%)", fontsize=12, fontweight="bold")
    ax.set_title(
        f"Drawdown Analysis: Quantum, Rebalanced vs {dataset_name}",
        fontsize=14,
        fontweight="bold",
    )
    ax.legend(fontsize=11, loc="best")
    ax.grid(True, alpha=0.3)

    filename = f"D5_drawdown_{dataset_name}.png"
    filepath = output_dir / filename
    plt.tight_layout()
    plt.savefig(filepath, dpi=300, bbox_inches="tight")
    plt.close()

    return str(filepath)
