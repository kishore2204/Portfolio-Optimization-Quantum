from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

from data_loader import load_all_data
from preprocessing import clean_prices, time_series_split, annualize_stats
from classical_optimizer import optimize_markowitz, optimize_sharpe
from hybrid_optimizer import HybridConfig, run_quantum_hybrid_selection, portfolio_returns
from rebalancing import RebalanceConfig, run_quarterly_rebalance
from evaluation import value_from_returns, metrics_table, compute_metrics
from visualization import plot_comparisons
from matrix_exporter import export_matrices_and_metrics
from enhanced_visualizations import create_5_comparison_graphs
from multi_dataset_visualizations import create_5_graphs_per_dataset
from full_period_visualizations import create_normal_15y_graphs
from qubo import build_qubo


@dataclass
class ExperimentConfig:
    train_years: int = 10
    test_years: int = 5
    rf: float = 0.05
    k_ratio: float = 0.06
    max_weight: float = 0.12
    risk_aversion: float = 4.0
    out_dir: str = "outputs"


def _normalize_benchmark_prices(bench_px: pd.DataFrame, test_index: pd.DatetimeIndex) -> Dict[str, pd.Series]:
    if bench_px.empty:
        return {}

    aligned = bench_px.reindex(test_index).ffill().bfill()
    out: Dict[str, pd.Series] = {}
    for c in aligned.columns:
        s = pd.to_numeric(aligned[c], errors="coerce").dropna()
        if s.empty:
            continue
        s = s / s.iloc[0]
        out[c] = s
    return out


def _build_candidate_pool(train_returns: pd.DataFrame, k_target: int) -> list[str]:
    mu = train_returns.mean()
    vol = train_returns.std().replace(0.0, np.nan)
    sharpe_like = (mu / vol).replace([np.inf, -np.inf], np.nan).dropna()

    pool_n = min(train_returns.shape[1], max(4 * k_target, 100))
    candidates = list(sharpe_like.sort_values(ascending=False).head(pool_n).index)
    if len(candidates) < k_target:
        candidates = list(train_returns.columns)
    return candidates


def main():
    root = Path(__file__).resolve().parent
    dataset_root = root / "datasets"
    cfg = ExperimentConfig()

    bundle = load_all_data(dataset_root)
    prices = clean_prices(bundle.asset_prices)

    split = time_series_split(prices, train_years=cfg.train_years, test_years=cfg.test_years)

    train_r = split.train_returns
    test_r = split.test_returns

    mu_train, cov_train, _ = annualize_stats(train_r)

    # Classical portfolios on train set.
    n_assets = len(train_r.columns)
    K = max(10, int(cfg.k_ratio * n_assets))
    K = min(K, n_assets)

    w_mvo_all = optimize_markowitz(mu_train, cov_train, risk_aversion=cfg.risk_aversion, w_max=cfg.max_weight)
    top_assets = list(w_mvo_all.sort_values(ascending=False).head(K).index)

    mu_top = mu_train.loc[top_assets]
    cov_top = cov_train.loc[top_assets, top_assets]
    w_classical = optimize_sharpe(mu_top, cov_top, rf=cfg.rf, w_max=cfg.max_weight)

    classical_test_lr = portfolio_returns(test_r, w_classical)
    classical_value = value_from_returns(classical_test_lr)
    classical_value.name = "Classical"

    # Quantum hybrid portfolio.
    hcfg = HybridConfig(
        K=K,
        max_weight=cfg.max_weight,
        rf=cfg.rf,
    )
    candidate_assets = _build_candidate_pool(train_r, K)
    q_assets, q_weights = run_quantum_hybrid_selection(
        train_r,
        bundle.sector_map,
        hcfg,
        candidate_assets=candidate_assets,
    )
    quantum_test_lr = portfolio_returns(test_r, q_weights)
    quantum_value = value_from_returns(quantum_test_lr)
    quantum_value.name = "Quantum"

    # Quantum + quarterly rebalancing.
    rcfg = RebalanceConfig(
        K=K,
        max_weight=cfg.max_weight,
        rf=cfg.rf,
    )
    q_rebal_value = run_quarterly_rebalance(train_r, test_r, bundle.sector_map, rcfg)

    portfolio_values: Dict[str, pd.Series] = {
        "Classical": classical_value,
        "Quantum": quantum_value,
        "Quantum_Rebalanced": q_rebal_value,
    }

    bench_norm = _normalize_benchmark_prices(bundle.benchmark_prices, test_r.index)

    # Save outputs.
    out_dir = root / cfg.out_dir
    out_dir.mkdir(exist_ok=True, parents=True)

    metric_df = metrics_table(portfolio_values, rf=cfg.rf)
    metric_df.to_csv(out_dir / "portfolio_metrics.csv")

    combined_values = pd.DataFrame(portfolio_values)
    for bname, bser in bench_norm.items():
        combined_values[bname] = bser.reindex(combined_values.index)
    combined_values.to_csv(out_dir / "portfolio_and_benchmark_values.csv")

    # Build full table with portfolio and benchmark metrics for easy review.
    benchmark_metrics = {
        name: compute_metrics(series.reindex(test_r.index).ffill().bfill(), rf=cfg.rf)
        for name, series in bench_norm.items()
    }
    full_metrics_df = pd.concat(
        [
            metric_df,
            pd.DataFrame(benchmark_metrics).T if benchmark_metrics else pd.DataFrame(),
        ],
        axis=0,
    )
    full_metrics_df.to_csv(out_dir / "full_comparison_metrics.csv")

    plot_comparisons(portfolio_values, bench_norm, out_dir)

    # ==================== EXPORT MATRICES AND METRICS ====================
    print("\n[Step 1] Exporting matrices to data/ folder...")
    data_dir = root / "data"
    
    # Compute downside risk for export
    _, _, downside_train = annualize_stats(train_r)
    
    # Build QUBO for quantum portfolio
    mu_top = mu_train.loc[q_assets]
    cov_top = cov_train.loc[q_assets, q_assets]
    sector_map_top = {a: bundle.sector_map.get(a, "UNKNOWN") for a in q_assets}
    
    qubo_model = build_qubo(
        mu=mu_top,
        cov=cov_top,
        downside=downside_train.loc[q_assets],
        sector_map=sector_map_top,
        K=K,
        q_risk=1.0,
        beta_downside=0.5,
        lambda_card=4.0,
        gamma_sector=0.3,
    )
    
    config_dict = {
        "train_years": cfg.train_years,
        "test_years": cfg.test_years,
        "k_ratio": cfg.k_ratio,
        "selected_k": int(K),
        "universe_size": int(n_assets),
        "risk_aversion": cfg.risk_aversion,
        "max_weight": cfg.max_weight,
        "rf_rate": cfg.rf,
    }
    
    export_matrices_and_metrics(
        data_dir=data_dir,
        train_returns=train_r,
        test_returns=test_r,
        mu_train=mu_train,
        cov_train=cov_train,
        downside_train=downside_train,
        qubo_model=qubo_model,
        classical_weights=w_classical,
        quantum_weights=q_weights,
        portfolio_values=portfolio_values,
        benchmark_values=bench_norm,
        train_prices=split.train_prices,
        test_prices=split.test_prices,
        split_dates=split.split_dates,
        config_dict=config_dict,
    )
    print(f"✓ Matrices exported to: {data_dir}")

    # ==================== CREATE 5 COMPARISON GRAPHS ====================
    print("\n[Step 2] Creating 5 enhanced comparison graphs...")
    enhanced_graphs = create_5_comparison_graphs(
        portfolio_values=portfolio_values,
        benchmark_values=bench_norm,
        output_dir=out_dir,
        config_dict=config_dict,
    )
    print(f"✓ 5 graphs created in: {out_dir}")

    # ==================== CREATE 5 GRAPHS PER DATASET ====================
    print("\n[Step 3] Creating 5 graphs per dataset (25 total graphs)...")
    multi_dataset_results = create_5_graphs_per_dataset(
        portfolio_values=portfolio_values,
        benchmark_values=bench_norm,
        output_dir=out_dir,
    )
    print(f"✓ Multi-dataset graphs created in: {out_dir}")

    # ==================== CREATE 15-YEAR NORMAL DATASET GRAPHS ====================
    print("\n[Step 4] Creating 15-year normal dataset graphs...")
    normal_15y_graphs = create_normal_15y_graphs(
        prices=prices,
        sector_map=bundle.sector_map,
        output_dir=out_dir,
        rf=cfg.rf,
        k_ratio=cfg.k_ratio,
        max_weight=cfg.max_weight,
        risk_aversion=cfg.risk_aversion,
    )
    print(f"✓ 15-year graphs created in: {out_dir}")

    summary = {
        "discovered_files": bundle.discovered_files,
        "split_dates": {
            k: str(v) for k, v in split.split_dates.items()
        },
        "asset_universe_size": int(n_assets),
        "selected_k": int(K),
        "classical_selected_assets": top_assets,
        "quantum_selected_assets": q_assets,
    }
    pd.Series(summary, dtype=object).to_json(out_dir / "run_summary.json", indent=2)

    print("\n" + "="*80)
    print("RUN COMPLETED SUCCESSFULLY")
    print("="*80)
    print(f"\nOutput directory:        {out_dir}")
    print(f"Data (matrices) folder:  {data_dir}")
    
    print("\n[Portfolio Metrics]")
    print(metric_df)
    print("\n[Full Comparison Metrics (Portfolios + Benchmarks)]")
    print(full_metrics_df)
    
    print("\n[Generated Outputs]")
    print("\nOriginal Comparison Images (4):")
    for name in [
        "1_classical_vs_quantum_vs_rebalanced.png",
        "2_quantum_vs_rebalanced.png",
        "3_quantum_rebalanced_vs_benchmarks.png",
        "4_rebalanced_vs_nonrebalanced.png",
    ]:
        print(f"  • {str(out_dir / name)}")
    
    print("\nEnhanced Quantum vs Rebalanced Graphs (5):")
    for graph_path in enhanced_graphs:
        print(f"  • {graph_path}")
    
    print("\nMulti-Dataset Comparison Graphs (5 graphs × 5 datasets = 25 total):")
    for dataset_name, graph_paths in multi_dataset_results.items():
        print(f"  {dataset_name}:")
        for i, graph_path in enumerate(graph_paths, 1):
            print(f"    {i}. {graph_path}")

    print("\n15-Year Normal Dataset Graphs (2):")
    for graph_path in normal_15y_graphs:
        print(f"  • {graph_path}")
    
    print("\nMatrix & Metrics Files in data/ folder:")
    for i in range(1, 13):
        print(f"  • {i:02d}_*.csv or .txt (see data/ folder)")


if __name__ == "__main__":
    main()
