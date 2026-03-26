from __future__ import annotations

from pathlib import Path
from typing import Dict

import matplotlib.pyplot as plt
import pandas as pd


def _style():
    plt.style.use("seaborn-v0_8-whitegrid")


def _savefig(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def plot_comparisons(
    portfolio_values: Dict[str, pd.Series],
    benchmark_values: Dict[str, pd.Series],
    out_dir: str | Path,
):
    out = Path(out_dir)
    _style()

    # 1) Classical vs Quantum vs Quantum+Rebalancing
    plt.figure(figsize=(12, 6))
    for name in ["Classical", "Quantum", "Quantum_Rebalanced"]:
        if name in portfolio_values:
            plt.plot(portfolio_values[name].index, portfolio_values[name].values, label=name, linewidth=2.0)
    plt.title("Portfolio Value: Classical vs Quantum vs Quantum+Rebalancing")
    plt.xlabel("Time")
    plt.ylabel("Portfolio Value")
    plt.legend()
    _savefig(out / "1_classical_vs_quantum_vs_rebalanced.png")

    # 2) Quantum vs Quantum+Rebalancing
    plt.figure(figsize=(12, 6))
    for name in ["Quantum", "Quantum_Rebalanced"]:
        if name in portfolio_values:
            plt.plot(portfolio_values[name].index, portfolio_values[name].values, label=name, linewidth=2.0)
    plt.title("Quantum vs Quantum+Rebalancing")
    plt.xlabel("Time")
    plt.ylabel("Portfolio Value")
    plt.legend()
    _savefig(out / "2_quantum_vs_rebalanced.png")

    # 3) Quantum vs Quantum+Rebalancing vs Benchmarks
    plt.figure(figsize=(13, 7))
    for name in ["Quantum", "Quantum_Rebalanced"]:
        if name in portfolio_values:
            plt.plot(portfolio_values[name].index, portfolio_values[name].values, label=name, linewidth=2.2)
    for name, series in benchmark_values.items():
        plt.plot(series.index, series.values, label=name, linewidth=1.4, alpha=0.9)
    plt.title("Quantum Portfolios vs Benchmarks")
    plt.xlabel("Time")
    plt.ylabel("Portfolio Value")
    plt.legend(ncol=2)
    _savefig(out / "3_quantum_rebalanced_vs_benchmarks.png")

    # 4) Rebalanced vs Non-Rebalanced Portfolio
    plt.figure(figsize=(12, 6))
    if "Quantum" in portfolio_values:
        plt.plot(portfolio_values["Quantum"].index, portfolio_values["Quantum"].values, label="Non-Rebalanced", linewidth=2.0)
    if "Quantum_Rebalanced" in portfolio_values:
        plt.plot(portfolio_values["Quantum_Rebalanced"].index, portfolio_values["Quantum_Rebalanced"].values, label="Rebalanced", linewidth=2.0)
    plt.title("Rebalanced vs Non-Rebalanced Quantum Portfolio")
    plt.xlabel("Time")
    plt.ylabel("Portfolio Value")
    plt.legend()
    _savefig(out / "4_rebalanced_vs_nonrebalanced.png")
