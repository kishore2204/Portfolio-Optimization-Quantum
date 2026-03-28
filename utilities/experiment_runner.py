from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product
from pathlib import Path
from typing import Dict, List
import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from data_loader import load_all_data
from preprocessing import clean_prices, time_series_split, annualize_stats
from classical_optimizer import optimize_markowitz, optimize_sharpe
from hybrid_optimizer import HybridConfig, run_quantum_hybrid_selection, portfolio_returns
from rebalancing import RebalanceConfig, run_quarterly_rebalance
from evaluation import value_from_returns, compute_metrics


@dataclass
class SweepConfig:
    train_years: int = 10
    test_years: int = 5
    rf: float = 0.05
    k_ratio: float = 0.06
    max_weight: float = 0.12
    risk_aversion: float = 4.0

    q_risk_values: tuple[float, ...] = (0.8, 1.0, 1.2)
    beta_values: tuple[float, ...] = (0.3, 0.5, 0.7)
    lambda_values: tuple[float, ...] = (3.0, 5.0)
    gamma_values: tuple[float, ...] = (0.2, 0.5)
    rebalance_days_values: tuple[int, ...] = (42, 63)
    transaction_cost_values: tuple[float, ...] = (0.0005, 0.001)

    out_dir: str = "outputs/experiments"


def _normalize_benchmark_prices(bench_px: pd.DataFrame, test_index: pd.DatetimeIndex) -> Dict[str, pd.Series]:
    if bench_px.empty:
        return {}

    aligned = bench_px.reindex(test_index).ffill().bfill()
    out: Dict[str, pd.Series] = {}
    for c in aligned.columns:
        s = pd.to_numeric(aligned[c], errors="coerce").dropna()
        if s.empty:
            continue
        out[c] = s / s.iloc[0]
    return out


def _build_candidate_pool(train_returns: pd.DataFrame, k_target: int) -> list[str]:
    mu = train_returns.mean()
    vol = train_returns.std().replace(0.0, np.nan)
    score = (mu / vol).replace([np.inf, -np.inf], np.nan).dropna()

    pool_n = min(train_returns.shape[1], max(4 * k_target, 100))
    candidates = list(score.sort_values(ascending=False).head(pool_n).index)
    if len(candidates) < k_target:
        candidates = list(train_returns.columns)
    return candidates


def _save_markdown_table(df: pd.DataFrame, path: Path):
    lines = []
    header = "| " + " | ".join(df.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(df.columns)) + " |"
    lines.append(header)
    lines.append(sep)
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(v) for v in row.values) + " |")
    path.write_text("\n".join(lines), encoding="utf-8")


def _sample_series_quarterly(series: pd.Series, interval: int = 63) -> tuple:
    """Sample series at regular intervals (quarterly by default = 63 trading days).
    
    Returns: (sampled_index, sampled_values) for sparse plotting with markers.
    """
    indices = np.arange(0, len(series), interval)
    if len(series) - 1 not in indices:
        indices = np.append(indices, len(series) - 1)
    return series.index[indices], series.values[indices]


def _plot_best_regime_comparison(
    out_dir: Path,
    best_regime_name: str,
    classical: pd.Series,
    quantum_best: pd.Series,
    rebalanced_best: pd.Series,
    benchmarks: Dict[str, pd.Series],
):
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.figure(figsize=(13, 7))

    x, y = _sample_series_quarterly(classical)
    plt.plot(x, y, label="Classical", linewidth=2.5, marker='o', markersize=6)
    
    x, y = _sample_series_quarterly(quantum_best)
    plt.plot(x, y, label=f"Quantum ({best_regime_name})", linewidth=2.5, marker='o', markersize=6)
    
    x, y = _sample_series_quarterly(rebalanced_best)
    plt.plot(x, y, label=f"Quantum+Rebal ({best_regime_name})", linewidth=2.8, marker='o', markersize=6)

    for key in sorted(benchmarks.keys()):
        s = benchmarks[key].reindex(classical.index).ffill().bfill()
        x, y = _sample_series_quarterly(s)
        plt.plot(x, y, label=key, linewidth=1.5, alpha=0.9, marker='s', markersize=4)

    plt.title("Portfolio Value Comparison Across Best Regime and Benchmarks")
    plt.xlabel("Time")
    plt.ylabel("Portfolio Value (Normalized)")
    plt.legend(ncol=2)
    plt.tight_layout()
    plt.savefig(out_dir / "paper_style_best_regime_vs_benchmarks.png", dpi=200)
    plt.close()


def _plot_top_rebalanced_regimes(
    out_dir: Path,
    top_regime_values: Dict[str, pd.Series],
    classical: pd.Series,
):
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.figure(figsize=(13, 7))

    x, y = _sample_series_quarterly(classical)
    plt.plot(x, y, label="Classical Baseline", linewidth=2.0, color="black", marker='o', markersize=6)
    for name, s in top_regime_values.items():
        x, y = _sample_series_quarterly(s)
        plt.plot(x, y, label=name, linewidth=2.0, marker='o', markersize=6)

    plt.title("Top Rebalanced Regimes: Portfolio Value Over Time")
    plt.xlabel("Time")
    plt.ylabel("Portfolio Value (Normalized)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "paper_style_top_rebalanced_regimes.png", dpi=200)
    plt.close()


def run_experiments():
    root = Path(__file__).resolve().parent
    dataset_root = root / "datasets"
    cfg = SweepConfig()

    out_dir = root / cfg.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    bundle = load_all_data(dataset_root)
    prices = clean_prices(bundle.asset_prices)
    split = time_series_split(prices, train_years=cfg.train_years, test_years=cfg.test_years)

    train_r = split.train_returns
    test_r = split.test_returns

    # Classical baseline once.
    mu_train, cov_train, _ = annualize_stats(train_r)
    n_assets = len(train_r.columns)
    K = max(10, int(cfg.k_ratio * n_assets))
    K = min(K, n_assets)

    w_mvo_all = optimize_markowitz(mu_train, cov_train, risk_aversion=cfg.risk_aversion, w_max=cfg.max_weight)
    top_assets = list(w_mvo_all.sort_values(ascending=False).head(K).index)
    w_classical = optimize_sharpe(mu_train.loc[top_assets], cov_train.loc[top_assets, top_assets], rf=cfg.rf, w_max=cfg.max_weight)
    classical_lr = portfolio_returns(test_r, w_classical)
    classical_value = value_from_returns(classical_lr)
    classical_metrics = compute_metrics(classical_value, rf=cfg.rf)

    benchmarks = _normalize_benchmark_prices(bundle.benchmark_prices, test_r.index)

    rows: List[dict] = []
    quantum_values: Dict[str, pd.Series] = {}
    rebalanced_values: Dict[str, pd.Series] = {}

    grid = list(
        product(
            cfg.q_risk_values,
            cfg.beta_values,
            cfg.lambda_values,
            cfg.gamma_values,
            cfg.rebalance_days_values,
            cfg.transaction_cost_values,
        )
    )

    candidate_assets = _build_candidate_pool(train_r, K)

    max_regimes_env = os.getenv("EXP_MAX_REGIMES", "").strip()
    max_regimes = int(max_regimes_env) if max_regimes_env.isdigit() else None
    active_grid = grid[:max_regimes] if max_regimes is not None else grid

    for ridx, (q_risk, beta_d, lmbd, gamma_s, rb_days, tx_cost) in enumerate(active_grid, start=1):
        regime_id = f"R{ridx:03d}"

        hcfg = HybridConfig(
            K=K,
            max_weight=cfg.max_weight,
            rf=cfg.rf,
            q_risk=q_risk,
            beta_downside=beta_d,
            lambda_card=lmbd,
            gamma_sector=gamma_s,
        )

        q_assets, q_w = run_quantum_hybrid_selection(
            train_returns=train_r,
            sector_map=bundle.sector_map,
            config=hcfg,
            candidate_assets=candidate_assets,
        )
        q_lr = portfolio_returns(test_r, q_w)
        q_value = value_from_returns(q_lr)
        q_value.name = regime_id

        rcfg = RebalanceConfig(
            K=K,
            max_weight=cfg.max_weight,
            rf=cfg.rf,
            q_risk=q_risk,
            beta_downside=beta_d,
            lambda_card=lmbd,
            gamma_sector=gamma_s,
            rebalance_days=rb_days,
            transaction_cost=tx_cost,
        )

        q_rebal_value = run_quarterly_rebalance(
            train_returns=train_r,
            test_returns=test_r,
            sector_map=bundle.sector_map,
            config=rcfg,
        )

        m_q = compute_metrics(q_value, rf=cfg.rf)
        m_qr = compute_metrics(q_rebal_value, rf=cfg.rf)

        rows.append(
            {
                "Regime": regime_id,
                "q_risk": q_risk,
                "beta_downside": beta_d,
                "lambda_card": lmbd,
                "gamma_sector": gamma_s,
                "rebalance_days": rb_days,
                "transaction_cost": tx_cost,
                "Q_TotalReturn": m_q["Total Return"],
                "Q_AnnReturn": m_q["Annualized Return"],
                "Q_Vol": m_q["Volatility"],
                "Q_Sharpe": m_q["Sharpe Ratio"],
                "Q_MaxDD": m_q["Max Drawdown"],
                "QR_TotalReturn": m_qr["Total Return"],
                "QR_AnnReturn": m_qr["Annualized Return"],
                "QR_Vol": m_qr["Volatility"],
                "QR_Sharpe": m_qr["Sharpe Ratio"],
                "QR_MaxDD": m_qr["Max Drawdown"],
                "SelectedCount": len(q_assets),
            }
        )

        quantum_values[regime_id] = q_value
        rebalanced_values[regime_id] = q_rebal_value

    regime_df = pd.DataFrame(rows)
    regime_df = regime_df.sort_values("QR_Sharpe", ascending=False).reset_index(drop=True)
    regime_df.to_csv(out_dir / "regime_metrics_full.csv", index=False)

    # Paper-ready summary table.
    top_n = min(12, len(regime_df))
    paper_cols = [
        "Regime",
        "q_risk",
        "beta_downside",
        "lambda_card",
        "gamma_sector",
        "rebalance_days",
        "transaction_cost",
        "Q_AnnReturn",
        "Q_Vol",
        "Q_Sharpe",
        "Q_MaxDD",
        "QR_AnnReturn",
        "QR_Vol",
        "QR_Sharpe",
        "QR_MaxDD",
    ]
    paper_df = regime_df.loc[: top_n - 1, paper_cols].copy()

    for c in ["Q_AnnReturn", "Q_Vol", "Q_Sharpe", "Q_MaxDD", "QR_AnnReturn", "QR_Vol", "QR_Sharpe", "QR_MaxDD"]:
        paper_df[c] = paper_df[c].round(4)

    baseline_row = {
        "Regime": "Classical_Baseline",
        "q_risk": "-",
        "beta_downside": "-",
        "lambda_card": "-",
        "gamma_sector": "-",
        "rebalance_days": "-",
        "transaction_cost": "-",
        "Q_AnnReturn": round(classical_metrics["Annualized Return"], 4),
        "Q_Vol": round(classical_metrics["Volatility"], 4),
        "Q_Sharpe": round(classical_metrics["Sharpe Ratio"], 4),
        "Q_MaxDD": round(classical_metrics["Max Drawdown"], 4),
        "QR_AnnReturn": "-",
        "QR_Vol": "-",
        "QR_Sharpe": "-",
        "QR_MaxDD": "-",
    }

    paper_ready = pd.concat([pd.DataFrame([baseline_row]), paper_df], ignore_index=True)
    paper_ready.to_csv(out_dir / "paper_ready_comparison_table.csv", index=False)
    _save_markdown_table(paper_ready, out_dir / "paper_ready_comparison_table.md")

    try:
        latex_text = paper_ready.to_latex(index=False)
        (out_dir / "paper_ready_comparison_table.tex").write_text(latex_text, encoding="utf-8")
    except Exception:
        pass

    # Charts: best regime and top rebalanced regimes.
    best_regime = regime_df.iloc[0]["Regime"]
    _plot_best_regime_comparison(
        out_dir=out_dir,
        best_regime_name=best_regime,
        classical=classical_value,
        quantum_best=quantum_values[best_regime],
        rebalanced_best=rebalanced_values[best_regime],
        benchmarks=benchmarks,
    )

    top_reb_ids = list(regime_df.head(5)["Regime"])
    top_reb_series = {rid: rebalanced_values[rid] for rid in top_reb_ids}
    _plot_top_rebalanced_regimes(out_dir=out_dir, top_regime_values=top_reb_series, classical=classical_value)

    # Also export value curves for top regimes.
    top_values = pd.DataFrame({"Classical": classical_value})
    for rid in top_reb_ids:
        top_values[f"Quantum_{rid}"] = quantum_values[rid]
        top_values[f"Quantum_Rebalanced_{rid}"] = rebalanced_values[rid]
    for bname, bser in benchmarks.items():
        top_values[bname] = bser.reindex(top_values.index)
    top_values.to_csv(out_dir / "top_regime_value_curves.csv")

    summary = {
        "sweep_config": asdict(cfg),
        "num_regimes": len(active_grid),
        "best_regime": best_regime,
        "dataset_root": str(dataset_root),
        "split_dates": {k: str(v) for k, v in split.split_dates.items()},
    }
    pd.Series(summary, dtype=object).to_json(out_dir / "experiment_summary.json", indent=2)

    print("Experiment sweep completed")
    print(f"Regimes evaluated: {len(active_grid)}")
    print(f"Best regime: {best_regime}")
    print(f"Outputs: {out_dir}")


if __name__ == "__main__":
    run_experiments()
