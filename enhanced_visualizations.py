"""
Enhanced visualization module with 5 comparison graphs for quantum vs quantum_rebalanced.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _sample_series_quarterly(series: pd.Series, interval: int = 63) -> tuple:
    """Sample series at regular intervals (quarterly by default = 63 trading days).
    
    Returns: (sampled_index, sampled_values) for sparse plotting with markers.
    """
    indices = np.arange(0, len(series), interval)
    if len(series) - 1 not in indices:
        indices = np.append(indices, len(series) - 1)
    return series.index[indices], series.values[indices]


def create_5_comparison_graphs(
    portfolio_values: dict,
    benchmark_values: dict,
    output_dir: Path,
    config_dict: Optional[dict] = None,
) -> list[str]:
    """
    Create only the 2 graphs user needs:
    1. G1: Quantum vs Quantum Rebalanced (cumulative returns)
    2. G1_with_classical: Quantum, Quantum Rebalanced, and Classical (cumulative returns)
    
    Returns:
        List of generated image paths
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files = []

    print("[Visualizations] Creating 2 cumulative returns comparison graphs...")

    # Graph 1: Quantum vs Quantum Rebalanced ONLY (as specified)
    fig = _plot_graph_1_cumulative_returns(portfolio_values, output_dir)
    generated_files.append(str(output_dir / "G1_cumulative_returns_quantum_vs_rebalanced.png"))
    print(f"  ✓ Graph 1: Cumulative Returns (Quantum vs Quantum Rebalanced)")

    # Graph 2: NEW - Quantum, Quantum Rebalanced, AND Classical
    fig = _plot_graph_1_with_classical(portfolio_values, output_dir)
    generated_files.append(str(output_dir / "G1_classical_quantum_vs_rebalanced.png"))
    print(f"  ✓ Graph 2: Cumulative Returns (Classical + Quantum + Quantum Rebalanced)")

    return generated_files


def _plot_graph_1_cumulative_returns(portfolio_values: dict, output_dir: Path) -> None:
    """Graph 1: Cumulative Returns of Quantum vs Quantum_Rebalanced."""
    fig, ax = plt.subplots(figsize=(14, 7))
    
    colors = {"Quantum": "#1f77b4", "Quantum_Rebalanced": "#ff7f0e"}
    
    for name in ["Quantum", "Quantum_Rebalanced"]:
        if name in portfolio_values and not portfolio_values[name].empty:
            values = portfolio_values[name]
            cumulative_returns = (values / values.iloc[0] - 1) * 100
            x, y = _sample_series_quarterly(cumulative_returns)
            ax.plot(x, y, label=name, linewidth=2.5, color=colors.get(name), alpha=0.8, 
                   marker='o', markersize=6)
    
    ax.set_xlabel("Date", fontsize=12, fontweight="bold")
    ax.set_ylabel("Cumulative Returns (%)", fontsize=12, fontweight="bold")
    ax.set_title("Cumulative Returns: Quantum vs Quantum_Rebalanced", 
                fontsize=14, fontweight="bold")
    ax.legend(fontsize=11, loc="best")
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color="black", linestyle="--", linewidth=0.8, alpha=0.5)
    
    plt.tight_layout()
    plt.savefig(output_dir / "G1_cumulative_returns_quantum_vs_rebalanced.png", dpi=300, bbox_inches="tight")
    plt.close()


def _plot_graph_2_rolling_sharpe(portfolio_values: dict, output_dir: Path) -> None:
    """Graph 2: Rolling 252-day Sharpe Ratio."""
    fig, ax = plt.subplots(figsize=(14, 7))
    
    colors = {"Quantum": "#1f77b4", "Quantum_Rebalanced": "#ff7f0e"}
    window = 252  # 1-year rolling window
    
    for name in ["Quantum", "Quantum_Rebalanced"]:
        if name in portfolio_values and not portfolio_values[name].empty:
            values = portfolio_values[name]
            log_returns = np.diff(np.log(values.values))
            
            rolling_mean = pd.Series(log_returns).rolling(window).mean() * 252
            rolling_std = pd.Series(log_returns).rolling(window).std() * np.sqrt(252)
            rolling_sharpe = (rolling_mean - 0.05) / (rolling_std + 1e-8)
            
            # Align index
            rolling_sharpe.index = values.index[1:]
            ax.plot(rolling_sharpe.index, rolling_sharpe.values, 
                   label=name, linewidth=2.5, color=colors.get(name), alpha=0.8)
    
    ax.set_xlabel("Date", fontsize=12, fontweight="bold")
    ax.set_ylabel("Rolling Sharpe Ratio (252-day)", fontsize=12, fontweight="bold")
    ax.set_title("Rolling 1-Year Sharpe Ratio: Quantum vs Quantum_Rebalanced", 
                fontsize=14, fontweight="bold")
    ax.legend(fontsize=11, loc="best")
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color="black", linestyle="--", linewidth=0.8, alpha=0.5)
    
    plt.tight_layout()
    plt.savefig(output_dir / "G2_rolling_sharpe_quantum_vs_rebalanced.png", dpi=300, bbox_inches="tight")
    plt.close()


def _plot_graph_3_drawdown_analysis(portfolio_values: dict, output_dir: Path) -> None:
    """Graph 3: Drawdown Analysis."""
    fig, ax = plt.subplots(figsize=(14, 7))
    
    colors = {"Quantum": "#1f77b4", "Quantum_Rebalanced": "#ff7f0e"}
    
    for name in ["Quantum", "Quantum_Rebalanced"]:
        if name in portfolio_values and not portfolio_values[name].empty:
            values = portfolio_values[name].values
            running_max = np.maximum.accumulate(values)
            drawdown = (values - running_max) / running_max * 100
            
            ax.fill_between(portfolio_values[name].index, drawdown, 0, 
                            alpha=0.3, color=colors.get(name), label=name)
            ax.plot(portfolio_values[name].index, drawdown, 
                   linewidth=1.5, color=colors.get(name))
    
    ax.set_xlabel("Date", fontsize=12, fontweight="bold")
    ax.set_ylabel("Drawdown (%)", fontsize=12, fontweight="bold")
    ax.set_title("Drawdown Analysis: Quantum vs Quantum_Rebalanced", 
                fontsize=14, fontweight="bold")
    ax.legend(fontsize=11, loc="best")
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / "G3_drawdown_quantum_vs_rebalanced.png", dpi=300, bbox_inches="tight")
    plt.close()


def _plot_graph_4_monthly_returns(portfolio_values: dict, output_dir: Path) -> None:
    """Graph 4: Monthly Returns Distribution as Box Plot."""
    fig, ax = plt.subplots(figsize=(14, 7))
    
    monthly_returns_dict = {}
    
    for name in ["Quantum", "Quantum_Rebalanced"]:
        if name in portfolio_values and not portfolio_values[name].empty:
            values = portfolio_values[name]
            # Convert to monthly returns
            monthly_values = values.resample("M").last()
            monthly_log_returns = np.diff(np.log(monthly_values.values)) * 100
            monthly_returns_dict[name] = monthly_log_returns
    
    # Create box plot
    if monthly_returns_dict:
        positions = np.arange(len(monthly_returns_dict))
        bp = ax.boxplot(
            [monthly_returns_dict[name] for name in ["Quantum", "Quantum_Rebalanced"]],
            positions=positions,
            widths=0.6,
            patch_artist=True
        )
        ax.set_xticklabels(["Quantum", "Quantum_Rebalanced"])
        
        colors = ["#1f77b4", "#ff7f0e"]
        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        
        ax.set_ylabel("Monthly Returns (%)", fontsize=12, fontweight="bold")
        ax.set_title("Monthly Returns Distribution: Quantum vs Quantum_Rebalanced", 
                    fontsize=14, fontweight="bold")
        ax.grid(True, alpha=0.3, axis="y")
        
        # Add statistics
        for i, name in enumerate(["Quantum", "Quantum_Rebalanced"]):
            returns = monthly_returns_dict[name]
            mean_ret = np.mean(returns)
            std_ret = np.std(returns)
            ax.text(positions[i], ax.get_ylim()[1] * 0.95, 
                   f"μ={mean_ret:.2f}%\nσ={std_ret:.2f}%",
                   ha="center", fontsize=10, bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(output_dir / "G4_monthly_returns_quantum_vs_rebalanced.png", dpi=300, bbox_inches="tight")
    plt.close()


def _plot_graph_5_risk_return_scatter(
    portfolio_values: dict,
    benchmark_values: dict,
    output_dir: Path
) -> None:
    """Graph 5: Risk vs Return Scatter with all portfolios and benchmarks."""
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Compute risk-return metrics
    portfolios_data = {}
    
    # Portfolio metrics
    for name in ["Classical", "Quantum", "Quantum_Rebalanced"]:
        if name in portfolio_values and not portfolio_values[name].empty:
            values = portfolio_values[name].values
            log_returns = np.diff(np.log(values))
            log_returns = log_returns[~np.isnan(log_returns)]
            
            ann_return = np.mean(log_returns) * 252 if len(log_returns) > 0 else 0.0
            ann_vol = np.std(log_returns) * np.sqrt(252) if len(log_returns) > 0 else 0.0
            
            portfolios_data[name] = {"return": ann_return, "volatility": ann_vol}
    
    # Benchmark metrics
    benchmarks_data = {}
    if benchmark_values:
        for name, values in benchmark_values.items():
            if not values.empty:
                log_returns = np.diff(np.log(values.values))
                log_returns = log_returns[~np.isnan(log_returns)]
                
                ann_return = np.mean(log_returns) * 252 if len(log_returns) > 0 else 0.0
                ann_vol = np.std(log_returns) * np.sqrt(252) if len(log_returns) > 0 else 0.0
                
                benchmarks_data[name] = {"return": ann_return, "volatility": ann_vol}
    
    # Plot portfolios
    portfolio_colors = {
        "Classical": "#2ca02c",
        "Quantum": "#1f77b4",
        "Quantum_Rebalanced": "#ff7f0e"
    }
    portfolio_markers = {
        "Classical": "s",
        "Quantum": "o",
        "Quantum_Rebalanced": "^"
    }
    
    for name, data in portfolios_data.items():
        ax.scatter(data["volatility"] * 100, data["return"] * 100, 
                  s=200, marker=portfolio_markers.get(name, "o"),
                  color=portfolio_colors.get(name), alpha=0.8,
                  label=name, edgecolors="black", linewidth=1.5)
        # Add label
        ax.annotate(name, 
                   (data["volatility"] * 100, data["return"] * 100),
                   xytext=(5, 5), textcoords="offset points", fontsize=10, fontweight="bold")
    
    # Plot benchmarks
    benchmark_marker = "D"
    for name, data in benchmarks_data.items():
        ax.scatter(data["volatility"] * 100, data["return"] * 100, 
                  s=120, marker=benchmark_marker,
                  color="gray", alpha=0.6, edgecolors="black", linewidth=1)
        ax.annotate(name.replace("_", " "), 
                   (data["volatility"] * 100, data["return"] * 100),
                   xytext=(5, -10), textcoords="offset points", fontsize=9, style="italic")
    
    ax.set_xlabel("Risk (Annualized Volatility %)", fontsize=12, fontweight="bold")
    ax.set_ylabel("Return (Annualized %)", fontsize=12, fontweight="bold")
    ax.set_title("Risk-Return Profile: Portfolios vs Benchmarks", 
                fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11, loc="best", scatterpoints=1)
    
    plt.tight_layout()
    plt.savefig(output_dir / "G5_risk_return_scatter_all.png", dpi=300, bbox_inches="tight")
    plt.close()

def _plot_all_strategies_cumulative(portfolio_values: dict, output_dir: Path) -> None:
    """NEW Graph 6: All Strategies - Classical + Quantum + Quantum_Rebalanced."""
    fig, ax = plt.subplots(figsize=(14, 7))
    
    colors = {
        "Classical": "#2ca02c",
        "Quantum": "#1f77b4",
        "Quantum_Rebalanced": "#ff7f0e"
    }
    
    for name in ["Classical", "Quantum", "Quantum_Rebalanced"]:
        if name in portfolio_values and not portfolio_values[name].empty:
            values = portfolio_values[name]
            cumulative_returns = (values / values.iloc[0] - 1) * 100
            ax.plot(cumulative_returns.index, cumulative_returns.values,
                   label=name, linewidth=2.5, color=colors.get(name), alpha=0.85)
    
    ax.set_xlabel("Date", fontsize=12, fontweight="bold")
    ax.set_ylabel("Cumulative Returns (%)", fontsize=12, fontweight="bold")
    ax.set_title("All Strategies: Classical vs Quantum vs Quantum_Rebalanced",
                fontsize=14, fontweight="bold")
    ax.legend(fontsize=11, loc="best")
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color="black", linestyle="--", linewidth=0.8, alpha=0.5)
    
    plt.tight_layout()
    plt.savefig(output_dir / "G6_all_strategies_cumulative_returns.png", dpi=300, bbox_inches="tight")
    plt.close()


def _plot_classical_quantum_rebalanced_detailed(portfolio_values: dict, output_dir: Path) -> None:
    """NEW Graph 7: Classical + Quantum + Quantum_Rebalanced detailed comparison (2 subplots)."""
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    
    # Color scheme
    colors = {
        "Classical": "#2ca02c",
        "Quantum": "#1f77b4",
        "Quantum_Rebalanced": "#ff7f0e"
    }
    
    # Subplot 1: All three strategies
    ax = axes[0]
    for name in ["Classical", "Quantum", "Quantum_Rebalanced"]:
        if name in portfolio_values and not portfolio_values[name].empty:
            values = portfolio_values[name]
            cumulative_returns = (values / values.iloc[0] - 1) * 100
            ax.plot(cumulative_returns.index, cumulative_returns.values,
                   label=name, linewidth=2.5, color=colors.get(name), alpha=0.85)
    
    ax.set_ylabel("Cumulative Returns (%)", fontsize=11, fontweight="bold")
    ax.set_title("All Three Strategies Comparison",
                fontsize=13, fontweight="bold")
    ax.legend(fontsize=10, loc="best")
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color="black", linestyle="--", linewidth=0.8, alpha=0.5)
    
    # Subplot 2: Quantum vs Quantum_Rebalanced (with Classical reference)
    ax = axes[1]
    for name in ["Classical", "Quantum", "Quantum_Rebalanced"]:
        if name in portfolio_values and not portfolio_values[name].empty:
            values = portfolio_values[name]
            cumulative_returns = (values / values.iloc[0] - 1) * 100
            linestyle = ":" if name == "Classical" else "-"
            linewidth = 2.0 if name == "Classical" else 2.5
            alpha = 0.5 if name == "Classical" else 0.85
            ax.plot(cumulative_returns.index, cumulative_returns.values,
                   label=name, linewidth=linewidth, color=colors.get(name), 
                   linestyle=linestyle, alpha=alpha)
    
    ax.set_xlabel("Date", fontsize=11, fontweight="bold")
    ax.set_ylabel("Cumulative Returns (%)", fontsize=11, fontweight="bold")
    ax.set_title("Quantum Strategy Focus (Classical shown as reference)",
                fontsize=13, fontweight="bold")
    ax.legend(fontsize=10, loc="best")
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color="black", linestyle="--", linewidth=0.8, alpha=0.5)
    
    plt.tight_layout()
    plt.savefig(output_dir / "G7_classical_quantum_rebalanced_detailed.png", dpi=300, bbox_inches="tight")
    plt.close()

def _plot_graph_1_with_classical(portfolio_values: dict, output_dir: Path) -> None:
    """NEW Graph: Cumulative Returns of Classical, Quantum, and Quantum_Rebalanced."""
    fig, ax = plt.subplots(figsize=(14, 7))
    
    colors = {
        "Classical": "#2ca02c",
        "Quantum": "#1f77b4", 
        "Quantum_Rebalanced": "#ff7f0e"
    }
    
    # Plot all three strategies
    for name in ["Classical", "Quantum", "Quantum_Rebalanced"]:
        if name in portfolio_values and not portfolio_values[name].empty:
            values = portfolio_values[name]
            cumulative_returns = (values / values.iloc[0] - 1) * 100
            x, y = _sample_series_quarterly(cumulative_returns)
            ax.plot(x, y, label=name, linewidth=2.5, color=colors[name], alpha=0.8,
                   marker='o', markersize=6)
    
    ax.set_xlabel("Date", fontsize=12, fontweight="bold")
    ax.set_ylabel("Cumulative Returns (%)", fontsize=12, fontweight="bold")
    ax.set_title("Cumulative Returns: Classical vs Quantum vs Quantum_Rebalanced", 
                fontsize=14, fontweight="bold")
    ax.legend(fontsize=11, loc="best")
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color="black", linestyle="--", linewidth=0.8, alpha=0.5)
    
    plt.tight_layout()
    plt.savefig(output_dir / "G1_classical_quantum_vs_rebalanced.png", dpi=300, bbox_inches="tight")
    plt.close()


def create_15y_cumulative_returns_graph(
    prices: pd.DataFrame,
    output_dir: Path,
) -> str:
    """
    Create 15-year cumulative returns graph for Classical, Quantum, and Quantum_Rebalanced
    using the full price history.
    
    This is a SIMPLIFIED version that only creates the one graph needed.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Ensure prices are sorted by index
        prices = prices.sort_index()
        
        # Log returns
        log_returns = np.diff(np.log(prices.values), axis=0)
        returns_df = pd.DataFrame(log_returns, index=prices.index[1:], columns=prices.columns)
        
        # Compute 3 strategies on full price history
        portfolio_values_15y = {}
        
        # Classical (Markowitz on all assets)
        from classical_optimizer import optimize_markowitz, optimize_sharpe
        mu = returns_df.mean()
        cov = returns_df.cov()
        
        w_mvo = optimize_markowitz(mu, cov, risk_aversion=4.0, w_max=0.12)
        classical_returns = (returns_df @ w_mvo).values
        classical_value = np.cumprod(1 + classical_returns)
        portfolio_values_15y["Classical"] = pd.Series(classical_value, index=returns_df.index)
        
        # Quantum (simplified quad optimization)
        w_quantum = optimize_sharpe(mu, cov, rf=0.05, w_max=0.12)
        quantum_returns = (returns_df @ w_quantum).values
        quantum_value = np.cumprod(1 + quantum_returns)
        portfolio_values_15y["Quantum"] = pd.Series(quantum_value, index=returns_df.index)
        
        # Quantum Rebalanced (quarterly)
        lookback = 252
        rebalance_freq = 63
        q_rebal_returns = []
        q_rebal_weights = w_quantum.copy()
        
        for i in range(lookback, len(returns_df)):
            # Get lookback window
            window_returns = returns_df.iloc[i-lookback:i]
            mu_window = window_returns.mean()
            cov_window = window_returns.cov()
            w_window = optimize_sharpe(mu_window, cov_window, rf=0.05, w_max=0.12)
            
            # Rebalance every 63 days
            if (i - lookback) % rebalance_freq == 0:
                q_rebal_weights = w_window.copy()
            
            day_return = returns_df.iloc[i] @ q_rebal_weights
            q_rebal_returns.append(day_return)
        
        q_rebal_value = np.cumprod([1] + q_rebal_returns)
        portfolio_values_15y["Quantum_Rebalanced"] = pd.Series(
            q_rebal_value, 
            index=returns_df.index[lookback:]
        )
        
        # Create plot
        fig, ax = plt.subplots(figsize=(15, 8))
        
        colors = {
            "Classical": "#2ca02c",
            "Quantum": "#1f77b4",
            "Quantum_Rebalanced": "#ff7f0e"
        }
        
        for name in ["Classical", "Quantum", "Quantum_Rebalanced"]:
            if name in portfolio_values_15y:
                values = portfolio_values_15y[name]
                cumulative_returns = (values / values.iloc[0] - 1) * 100
                ax.plot(
                    cumulative_returns.index, 
                    cumulative_returns.values,
                    label=name,
                    linewidth=2.5,
                    color=colors[name],
                    alpha=0.85
                )
        
        ax.set_xlabel("Date", fontsize=12, fontweight="bold")
        ax.set_ylabel("Cumulative Returns (%)", fontsize=12, fontweight="bold")
        ax.set_title("15-Year Cumulative Returns: Classical vs Quantum vs Quantum_Rebalanced",
                    fontsize=14, fontweight="bold")
        ax.legend(fontsize=11, loc="best")
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color="black", linestyle="--", linewidth=0.8, alpha=0.5)
        
        plt.tight_layout()
        output_file = output_dir / "15y_1_classical_vs_quantum_vs_rebalanced.png"
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        plt.close()
        
        return str(output_file)
        
    except Exception as e:
        print(f"  WARNING: Could not create 15y graph: {e}")
        return ""

