from __future__ import annotations

from pathlib import Path
from typing import Dict

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


def _style():
    plt.style.use("seaborn-v0_8-whitegrid")


def _savefig(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()


def _sample_series_quarterly(series: pd.Series, interval: int = 63) -> tuple:
    """Sample series at regular intervals (quarterly by default = 63 trading days).
    
    Returns: (sampled_index, sampled_values) for sparse plotting with markers.
    """
    indices = np.arange(0, len(series), interval)
    if len(series) - 1 not in indices:
        indices = np.append(indices, len(series) - 1)
    return series.index[indices], series.values[indices]


def plot_comparisons(
    portfolio_values: Dict[str, pd.Series],
    benchmark_values: Dict[str, pd.Series],
    out_dir: str | Path,
):
    out = Path(out_dir)
    _style()

    # 1) Classical vs Quantum vs Quantum+Rebalancing
    fig, ax = plt.subplots(figsize=(14, 8))
    for name in ["Classical", "Quantum", "Quantum_Rebalanced"]:
        if name in portfolio_values:
            x, y = _sample_series_quarterly(portfolio_values[name])
            ax.plot(x, y, label=name, linewidth=3, marker='o', markersize=10)
    ax.set_title("Portfolio Value: Classical vs Quantum vs Quantum+Rebalancing", fontsize=24, fontweight="bold")
    ax.set_xlabel("Time", fontsize=20, fontweight="bold")
    ax.set_ylabel("Portfolio Value", fontsize=20, fontweight="bold")
    ax.legend(fontsize=17, loc="best")
    ax.tick_params(labelsize=15)
    for label in ax.get_xticklabels():
        label.set_fontweight('bold')
    for label in ax.get_yticklabels():
        label.set_fontweight('bold')
    ax.grid(True, alpha=0.3)
    _savefig(out / "1_classical_vs_quantum_vs_rebalanced.png")

    # 2) Quantum vs Quantum+Rebalancing
    fig, ax = plt.subplots(figsize=(14, 8))
    for name in ["Quantum", "Quantum_Rebalanced"]:
        if name in portfolio_values:
            x, y = _sample_series_quarterly(portfolio_values[name])
            ax.plot(x, y, label=name, linewidth=3, marker='o', markersize=10)
    ax.set_title("Quantum vs Quantum+Rebalancing", fontsize=24, fontweight="bold")
    ax.set_xlabel("Time", fontsize=20, fontweight="bold")
    ax.set_ylabel("Portfolio Value", fontsize=20, fontweight="bold")
    ax.legend(fontsize=17, loc="best")
    ax.tick_params(labelsize=15)
    for label in ax.get_xticklabels():
        label.set_fontweight('bold')
    for label in ax.get_yticklabels():
        label.set_fontweight('bold')
    ax.grid(True, alpha=0.3)
    _savefig(out / "2_quantum_vs_rebalanced.png")

    # 3) Quantum vs Quantum+Rebalancing vs Benchmarks
    fig, ax = plt.subplots(figsize=(15, 8))
    for name in ["Quantum", "Quantum_Rebalanced"]:
        if name in portfolio_values:
            x, y = _sample_series_quarterly(portfolio_values[name])
            ax.plot(x, y, label=name, linewidth=3, marker='o', markersize=10)
    for name, series in benchmark_values.items():
        x, y = _sample_series_quarterly(series)
        ax.plot(x, y, label=name, linewidth=2, alpha=0.9, marker='s', markersize=8)
    ax.set_title("Quantum Portfolios vs Benchmarks", fontsize=24, fontweight="bold")
    ax.set_xlabel("Time", fontsize=20, fontweight="bold")
    ax.set_ylabel("Portfolio Value", fontsize=20, fontweight="bold")
    ax.legend(ncol=2, fontsize=17, loc="best")
    ax.tick_params(labelsize=15)
    for label in ax.get_xticklabels():
        label.set_fontweight('bold')
    for label in ax.get_yticklabels():
        label.set_fontweight('bold')
    ax.grid(True, alpha=0.3)
    _savefig(out / "3_quantum_rebalanced_vs_benchmarks.png")

    # 4) Rebalanced vs Non-Rebalanced Portfolio
    fig, ax = plt.subplots(figsize=(14, 8))
    if "Quantum" in portfolio_values:
        x, y = _sample_series_quarterly(portfolio_values["Quantum"])
        ax.plot(x, y, label="Non-Rebalanced", linewidth=3, marker='o', markersize=10)
    if "Quantum_Rebalanced" in portfolio_values:
        x, y = _sample_series_quarterly(portfolio_values["Quantum_Rebalanced"])
        ax.plot(x, y, label="Rebalanced", linewidth=3, marker='o', markersize=10)
    ax.set_title("Rebalanced vs Non-Rebalanced Quantum Portfolio", fontsize=24, fontweight="bold")
    ax.set_xlabel("Time", fontsize=20, fontweight="bold")
    ax.set_ylabel("Portfolio Value", fontsize=20, fontweight="bold")
    ax.legend(fontsize=17, loc="best")
    ax.tick_params(labelsize=15)
    for label in ax.get_xticklabels():
        label.set_fontweight('bold')
    for label in ax.get_yticklabels():
        label.set_fontweight('bold')
    ax.grid(True, alpha=0.3)
    _savefig(out / "4_rebalanced_vs_nonrebalanced.png")
