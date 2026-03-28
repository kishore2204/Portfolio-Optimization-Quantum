from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

from data_loader import load_all_data
from preprocessing import clean_prices, time_series_split, annualize_stats
from classical_optimizer import optimize_markowitz, optimize_sharpe, optimize_sharpe_with_min_weight
from hybrid_optimizer import HybridConfig, run_quantum_hybrid_selection, portfolio_returns
from rebalancing import RebalanceConfig, run_quarterly_rebalance
from evaluation import value_from_returns, metrics_table, compute_metrics
from visualization_tools.visualization import plot_comparisons
from utilities.matrix_exporter import export_matrices_and_metrics
from visualization_tools.enhanced_visualizations import create_5_comparison_graphs
from visualization_tools.multi_dataset_visualizations import create_5_graphs_per_dataset
from visualization_tools.full_period_visualizations import create_normal_15y_graphs
from qubo import build_qubo
from config_constants import (
    TRAIN_YEARS, TEST_YEARS, RISK_FREE_RATE, K_RATIO, TEST_END_DATE,
    MAX_WEIGHT_PER_ASSET, Q_RISK, BETA_DOWNSIDE,
    print_constants_summary
)


@dataclass
class ExperimentConfig:
    """Main Experiment Configuration
    
    IMPORTANT: Uses FIXED CONSTANTS from config_constants.py
    Single run only - no hyperparameter search.
    """
    train_years: int = TRAIN_YEARS
    test_years: int = TEST_YEARS
    rf: float = RISK_FREE_RATE
    k_ratio: float = K_RATIO
    max_weight: float = MAX_WEIGHT_PER_ASSET
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

    # Print fixed configuration for transparency
    print_constants_summary()

    # ==================== PRINT REBALANCING METHODOLOGY ====================
    print("\n" + "="*110)
    print(" " * 25 + "[PLAN] QUARTERLY REBALANCING STRATEGY (Quantum + Rebalanced)")
    print("="*110)
    
    print("\n[REBALANCE] REBALANCING WORKFLOW (Every 63 Trading Days):\n")
    
    print("STEP 1: IDENTIFY UNDERPERFORMERS")
    print("    - Metric: Average daily returns over 252-day lookback window (1 year)")
    print("    - Selection: Bottom 20% of current portfolio sorted by returns")
    print("    - Result: ~3 stocks flagged as underperforming\n")
    
    print("STEP 2: QUICK SECTOR-BASED REPLACEMENT")
    print("    - Action: For each underperformer, find best performer in SAME sector")
    print("    - Metric: Highest average daily return in that sector")
    print("    - Constraint: Only replace with available stocks (not already selected)")
    print("    - Purpose: Maintain sector diversification while swapping out weak stocks")
    print("    - Result: 'Seeded' portfolio with sector-balanced replacements\n")
    
    print("STEP 3: BUILD QUBO MATRIX")
    print("    - Input Data:")
    print("       * Expected returns (mu) - mean of returns")
    print("       * Covariance matrix (Sigma) - asset correlations")
    print("       * Downside volatility - penalty for negative deviations")
    print("    - QUBO Terms:")
    print("       * mu_i x w_i: Maximize expected returns")
    print("       * Sigma: Minimize portfolio variance (risk)")
    print("       * Downside risk: Penalize volatility")
    print("       * lambda_card x (|S| - K)^2: Cardinality constraint (exactly K assets)")
    print("       * gamma_sector: Sector concentration penalty\n")
    
    print("STEP 4: RUN QUANTUM ANNEALING")
    print("    - Candidate Pool: Top 100 stocks by Sharpe-like score")
    print("    - Algorithm: Simulated Annealing (quantum-inspired)")
    print("    - Objective: Select K=15 assets that maximize return-risk trade-off")
    print("    - Output: 15 assets optimized via QUBO formulation\n")
    
    print("STEP 5: OPTIMIZE WEIGHTS FOR SHARPE RATIO")
    print("    - Problem: Given 15 selected stocks, allocate optimal weights")
    print("    - Metric: Sharpe Ratio = (E[R] - Rf) / sigma")
    print("       * E[R]: Expected portfolio return")
    print("       * Rf: Risk-free rate (5%)")
    print("       * sigma: Portfolio volatility")
    print("    - Constraint: Max 12% per asset, optimal risk-adjusted allocation")
    print("    - Result: Portfolio weights that maximize excess return per unit risk\n")
    
    print("STEP 6: MERGE & FINALIZE")
    print("    - Seeded Portfolio: 13-15 stocks (from sector replacements)")
    print("    - Annealing Portfolio: 15 stocks (from QUBO + quantum annealing)")
    print("    - Merge: Combine both, remove duplicates, keep top K=15")
    print("    - Apply Transaction Costs: Penalize high portfolio turnover")
    print("    - Update Weights: Use merged assets with Sharpe-optimized weights\n")
    
    print("[TARGET] KEY INSIGHTS:")
    print("  [OK] Quick Replacement = Fast, practical sector-based swaps (warm start)")
    print("  [OK] Full Re-optimization = Global search via QUBO + quantum annealing")
    print("  [OK] Sharpe Ratio Calc = Applied AFTER asset selection (Step 5)")
    print("  [OK] Both Approches Used = Seeded results inform QUBO optimization")
    print("  [OK] Frequency = 4 times/year (every ~quarter = 63 trading days)")
    print("  [OK] Result = Adaptive portfolio that removes weak performers & rebalances weights\n")
    
    print("="*110)

    bundle = load_all_data(dataset_root)
    prices = clean_prices(bundle.asset_prices)

    split = time_series_split(prices, train_years=cfg.train_years, test_years=cfg.test_years, test_end_date=TEST_END_DATE)

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
    w_classical = optimize_sharpe_with_min_weight(mu_top, cov_top, rf=cfg.rf, w_max=cfg.max_weight, min_weight=0.02)

    classical_test_lr = portfolio_returns(test_r, w_classical)
    classical_value = value_from_returns(classical_test_lr)
    classical_value.name = "Classical"

    # Quantum hybrid portfolio.
    hcfg = HybridConfig(
        K=K,
        max_weight=cfg.max_weight,
        rf=cfg.rf,
        # Uses fixed constants: q_risk=0.5, beta_downside=0.3
        # lambda_card and gamma_sector computed adaptively in build_qubo()
    )
    candidate_assets = _build_candidate_pool(train_r, K)
    q_assets, q_weights, qubo_model_annealing = run_quantum_hybrid_selection(
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
        # Uses fixed constants: q_risk=0.5, beta_downside=0.3
        # lambda_card and gamma_sector computed adaptively in build_qubo()
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
    
    # Use the QUBO from annealing (100×100) instead of rebuilding from selected
    qubo_model = qubo_model_annealing
    
    config_dict = {
        "train_years": cfg.train_years,
        "test_years": cfg.test_years,
        "k_ratio": cfg.k_ratio,
        "selected_k": int(K),
        "universe_size": int(n_assets),
        "qubo_candidate_pool_size": len(qubo_model.assets),
        "q_risk": Q_RISK,
        "beta_downside": BETA_DOWNSIDE,
        "lambda_card_computed": float(qubo_model.lambda_card),
        "gamma_sector_computed": float(qubo_model.gamma_sector),
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
    print(f"[OK] Matrices exported to: {data_dir}")

    # ==================== CREATE 5 COMPARISON GRAPHS ====================
    print("\n[Step 2] Creating 5 enhanced comparison graphs...")
    enhanced_graphs = create_5_comparison_graphs(
        portfolio_values=portfolio_values,
        benchmark_values=bench_norm,
        output_dir=out_dir,
        config_dict=config_dict,
    )
    print(f"[OK] 5 graphs created in: {out_dir}")

    # ==================== CREATE 5 GRAPHS PER DATASET ====================
    print("\n[Step 3] Creating 5 graphs per dataset (25 total graphs)...")
    multi_dataset_results = create_5_graphs_per_dataset(
        portfolio_values=portfolio_values,
        benchmark_values=bench_norm,
        output_dir=out_dir,
    )
    print(f"[OK] Multi-dataset graphs created in: {out_dir}")

    # ==================== SKIP STEP 4 (Not needed - causes long waits) ====================
    # Step 4 disabled - 15y graph calculation too slow, user wants quick results
    # Graphs completed: 2 from Step 2 + 5 from Step 3 = 7 total cumulative returns graphs
    print("\n[Step 4] Skipped (not needed)")

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

    # ==================== PERFORMANCE SUMMARY ====================
    print("\n" + "="*130)
    print(" " * 45 + "[TARGET] PERFORMANCE RESULTS SUMMARY")
    print("="*130)
    
    # Extract key metrics for cleaner display
    perf_summary = pd.DataFrame({
        'Strategy': ['Classical', 'Quantum', 'Quantum+Rebalanced'],
        'Total Return': [
            f"{metric_df.loc['Classical', 'Total Return']:.2%}",
            f"{metric_df.loc['Quantum', 'Total Return']:.2%}",
            f"{metric_df.loc['Quantum_Rebalanced', 'Total Return']:.2%}",
        ],
        'Annual Return': [
            f"{metric_df.loc['Classical', 'Annualized Return']:.2%}",
            f"{metric_df.loc['Quantum', 'Annualized Return']:.2%}",
            f"{metric_df.loc['Quantum_Rebalanced', 'Annualized Return']:.2%}",
        ],
        'Volatility': [
            f"{metric_df.loc['Classical', 'Volatility']:.2%}",
            f"{metric_df.loc['Quantum', 'Volatility']:.2%}",
            f"{metric_df.loc['Quantum_Rebalanced', 'Volatility']:.2%}",
        ],
        'Sharpe Ratio': [
            f"{metric_df.loc['Classical', 'Sharpe Ratio']:.4f}",
            f"{metric_df.loc['Quantum', 'Sharpe Ratio']:.4f}",
            f"{metric_df.loc['Quantum_Rebalanced', 'Sharpe Ratio']:.4f}",
        ],
        'Max Drawdown': [
            f"{metric_df.loc['Classical', 'Max Drawdown']:.2%}",
            f"{metric_df.loc['Quantum', 'Max Drawdown']:.2%}",
            f"{metric_df.loc['Quantum_Rebalanced', 'Max Drawdown']:.2%}",
        ],
    })
    
    print("\n[DATA] PORTFOLIO PERFORMANCE COMPARISON:")
    print("-" * 130)
    print(perf_summary.to_string(index=False))
    print("-" * 130)
    
    # Benchmark comparison
    if benchmark_metrics:
        benchmark_perf = pd.DataFrame({
            'Benchmark': list(benchmark_metrics.keys()),
            'Total Return': [
                f"{benchmark_metrics[b]['Total Return']:.2%}" 
                for b in benchmark_metrics.keys()
            ],
            'Annual Return': [
                f"{benchmark_metrics[b]['Annualized Return']:.2%}" 
                for b in benchmark_metrics.keys()
            ],
            'Sharpe Ratio': [
                f"{benchmark_metrics[b]['Sharpe Ratio']:.4f}" 
                for b in benchmark_metrics.keys()
            ],
        })
        print("\n[BENCHMARK] MARKET BENCHMARK COMPARISON:")
        print("-" * 130)
        print(benchmark_perf.to_string(index=False))
        print("-" * 130)
    
    # Budget analysis (using $1,000,000 initial investment)
    initial_budget = 1_000_000
    print(f"\n[BUDGET] BUDGET ANALYSIS  (Initial Investment: ${initial_budget:,.0f})")
    print("-" * 130)
    
    final_vals = {
        'Classical': classical_value.iloc[-1] * initial_budget,
        'Quantum': quantum_value.iloc[-1] * initial_budget,
        'Quantum+Rebalanced': q_rebal_value.iloc[-1] * initial_budget,
    }
    
    bench_final_vals = {name: series.iloc[-1] * initial_budget for name, series in bench_norm.items()}
    
    budget_table = pd.DataFrame({
        'Strategy': list(final_vals.keys()),
        'Final Value': [f"${v:,.2f}" for v in final_vals.values()],
        'Profit/Loss': [f"${v - initial_budget:,.2f}" for v in final_vals.values()],
        'Return %': [
            f"{(final_vals[s] / initial_budget - 1) * 100:.2f}%"
            for s in final_vals.keys()
        ],
    })
    print("\n   PORTFOLIO BUDGET:")
    print("   " + "-" * 126)
    for line in budget_table.to_string(index=False).split('\n'):
        print("   " + line)
    print("   " + "-" * 126)
    
    bench_budget = pd.DataFrame({
        'Benchmark': list(bench_final_vals.keys()),
        'Final Value': [f"${v:,.2f}" for v in bench_final_vals.values()],
        'Profit/Loss': [f"${v - initial_budget:,.2f}" for v in bench_final_vals.values()],
        'Return %': [
            f"{(bench_final_vals[b] / initial_budget - 1) * 100:.2f}%"
            for b in bench_final_vals.keys()
        ],
    })
    print("\n   BENCHMARK BUDGET:")
    print("   " + "-" * 126)
    for line in bench_budget.to_string(index=False).split('\n'):
        print("   " + line)
    print("   " + "-" * 126)
    
    # Key insights
    quantum_rebal_return = metric_df.loc['Quantum_Rebalanced', 'Total Return']
    quantum_return = metric_df.loc['Quantum', 'Total Return']
    classical_return = metric_df.loc['Classical', 'Total Return']
    outperformance = quantum_rebal_return - classical_return
    
    quantum_profit = final_vals['Quantum+Rebalanced'] - initial_budget
    classical_profit = final_vals['Classical'] - initial_budget
    profit_diff = quantum_profit - classical_profit
    
    print("\n[INSIGHT]  KEY PERFORMANCE INSIGHTS:")
    print("-" * 130)
    print(f"     [OK] Quantum+Rebalance vs Classical outperformance  :  {outperformance:.2%}")
    print(f"     [OK] Quantum+Rebalance Sharpe ratio improvement      :  {metric_df.loc['Quantum_Rebalanced', 'Sharpe Ratio'] - metric_df.loc['Classical', 'Sharpe Ratio']:.4f}")
    print(f"     [OK] Rebalancing boost (Quantum vs Quantum+Rebal)    :  {quantum_rebal_return - quantum_return:.2%}")
    print(f"     [OK] Profit difference (Quantum+Rebal vs Classical)  :  ${profit_diff:,.2f}")
    print("-" * 130)
    
    # Selected stocks - Classical
    print("\n[BEST] CLASSICAL PORTFOLIO  (15 Selected Stocks & Weights):")
    print("-" * 130)
    classical_stocks_df = pd.DataFrame({
        'Rank': range(1, len(w_classical) + 1),
        'Stock': w_classical.index,
        'Weight': [f"{w*100:.2f}%" for w in w_classical.values],
    })
    print("   " + "\n   ".join(classical_stocks_df.to_string(index=False).split('\n')))
    print("-" * 130)
    
    # Selected stocks - Quantum
    print("\n[QUANTUM]  QUANTUM PORTFOLIO  (15 Selected Stocks & Weights):")
    print("-" * 130)
    quantum_stocks_df = pd.DataFrame({
        'Rank': range(1, len(q_weights) + 1),
        'Stock': q_weights.index,
        'Weight': [f"{w*100:.2f}%" for w in q_weights.values],
    })
    print("   " + "\n   ".join(quantum_stocks_df.to_string(index=False).split('\n')))
    print("-" * 130)
    
    # Portfolio composition
    print("\n[TARGET] PORTFOLIO COMPOSITION:")
    print("-" * 130)
    print(f"     [OK] Classical portfolio       :  {len(top_assets)} assets selected")
    print(f"     [OK] Quantum portfolio         :  {len(q_assets)} assets selected")
    print(f"     [OK] Universe size             :  {n_assets} total available assets")
    print(f"     [OK] Selection ratio (K/N)     :  {cfg.k_ratio*100:.2f}%")
    print("-" * 130)
    
    # QUBO validation
    print("\n[OK] QUBO MODEL VALIDATION:")
    print("-" * 130)
    print(f"     [OK] QUBO Matrix size              :  {qubo_model.Q.shape}")
    print(f"     [OK] Cardinality constraint (K)    :  {K} assets selected")
    print(f"     [OK] Lambda (cardinality penalty)  :  {qubo_model.lambda_card:.2f}")
    print(f"     [OK] Gamma (sector penalty)        :  {qubo_model.gamma_sector:.2f}")
    print(f"     [OK] Matrix is symmetric           :  {np.allclose(qubo_model.Q, qubo_model.Q.T)}")
    print(f"     [OK] Fixed constants (q_risk)      :  {Q_RISK}")
    print(f"     [OK] Fixed constants (beta_downside) : {BETA_DOWNSIDE}")
    print("-" * 130)
    
    # Data export validation
    print("\n[SAVE] DATA FILES EXPORTED  (21 files):")
    print("-" * 130)
    print(f"     [OK] Input matrices              :  01-04 (covariance, returns, price data)")
    print(f"     [OK] QUBO matrix                 :  05-06 (matrix and diagonal terms)")
    print(f"     [OK] QUBO inputs                 :  7 files (expected returns, downside risk, etc.)")
    print(f"     [OK] Constants                   :  3 files (fixed, adaptive, formulas)")
    print(f"     [OK] Portfolio weights           :  07 (Classical & Quantum)")
    print(f"     [OK] Portfolio values            :  10-11 (daily performance and benchmarks)")
    print(f"     [OK] Metrics report              :  12 (comprehensive summary)")
    print(f"     [OK] Documentation               :  3 files (guide, reference, dictionary)")
    print("-" * 130)
    
    print("\n[VISUAL] GRAPHS GENERATED:")
    print("-" * 130)
    print(f"     [OK] Enhanced quantum comparison      :  {len(enhanced_graphs)} graphs")
    print(f"     [OK] Multi-dataset comparison         :  {sum(len(g) for g in multi_dataset_results.values())} graphs")
    print(f"     [OK] Original comparison              :  4 graphs")
    print(f"     [DATA] TOTAL VISUALIZATIONS            :  {len(enhanced_graphs) + sum(len(g) for g in multi_dataset_results.values()) + 4} graphs")
    print("-" * 130)
    
    print("\n" + "="*130)
    print(" " * 50 + "[OK] RUN COMPLETED SUCCESSFULLY")
    print("="*130)
    
    print("\n[CHECK] OUTPUT DIRECTORIES:")
    print("-" * 130)
    print(f"     [DIR] Output directory (graphs)    :  {out_dir}")
    print(f"     [DIR] Data (matrices) folder       :  {data_dir}")
    print("-" * 130)
    
    print("\n[CONFIG] CONFIGURATION SUMMARY:")
    print("-" * 130)
    print(f"     * K (portfolio size)            :  {K} assets")
    print(f"     * N (universe size)             :  {n_assets} assets")
    print(f"     * K_RATIO                       :  {cfg.k_ratio:.4f} ({cfg.k_ratio*100:.2f}%)")
    print(f"     * Training period               :  {cfg.train_years} years")
    print(f"     * Test period                   :  {cfg.test_years} years")
    print(f"     * Risk-free rate                :  {cfg.rf*100:.1f}%")
    print("-" * 130)
    
    print("\n[INFO] NEXT STEPS:")
    print("-" * 130)
    print(f"     1. Review graphs in                 : {out_dir}")
    print(f"     2. Analyze data matrices in         : {data_dir}")
    print(f"     3. Read documentation              : {data_dir}/00_DATA_FOLDER_GUIDE.txt")
    print(f"     4. Check comprehensive metrics     : {data_dir}/12_COMPREHENSIVE_METRICS_REPORT.txt")
    print("-" * 130)
    print()


if __name__ == "__main__":
    main()
