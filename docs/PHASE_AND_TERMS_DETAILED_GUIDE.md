# Portfolio Optimization Quantum: Phase-by-Phase and Terminology Guide

## 1. Project Architecture at a Glance

This repository has two connected execution styles:

1. Phase pipeline style (phase_01 to phase_08), mainly for methodology clarity and staged runs.
2. Unified evaluator style, where one runner executes horizon and crash scenarios with common logic and outputs.

Main entry scripts:

- [run_portfolio_optimization_quantum.py](run_portfolio_optimization_quantum.py): Orchestrates the paper-style staged pipeline.
- [unified_train_test_compare.py](unified_train_test_compare.py): Main baseline evaluator for horizon plus crash reporting.
- [run_all_end_to_end.py](run_all_end_to_end.py): Master script that chains core pipeline and unified evaluations.
- [run_crash_analysis_wrapper.py](run_crash_analysis_wrapper.py): Convenience wrapper for crash module runs.

---

## 2. What Each Phase File Does

## 2.1 Phase 01: Data Preparation

File: [phase_01_data_preparation.py](phase_01_data_preparation.py)

Primary responsibility:

- Loads raw price history.
- Filters and validates stock universe.
- Splits historical train and test partitions.
- Computes returns, annualized mean returns, covariance, Sharpe proxies.
- Builds sector summary and writes prepared artifacts.

Core work steps in this phase:

1. Load config and sector map.
2. Load raw dataset and parse Date.
3. Clean nulls and low-history names.
4. Compute daily returns and annualized statistics.
5. Rank/select a reduced candidate universe.
6. Save data artifacts for downstream phases.

Typical outputs produced:

- data/mean_returns.npy
- data/covariance_matrix.npy
- data/sharpe_ratios.npy
- data/returns_matrix.npy
- data/prices_timeseries.csv
- data/returns_timeseries.csv
- data/universe_metadata.json
- data/test_data.csv

Why it matters:

- Garbage in, garbage out. This phase controls data quality, which dominates optimization quality.

---

## 2.2 Phase 02: Cardinality Determination

File: [phase_02_cardinality_determination.py](phase_02_cardinality_determination.py)

Primary responsibility:

- Derive portfolio size K from convex optimization before discrete selection.

Implemented idea:

- Solve a convex Sharpe-style formulation for continuous weights y.
- Infer effective K from y (rounded sum with guardrails).

Core method details:

- Solvers: CVXOPT first, then ECOS, then SCS fallback.
- No-short constraint on y.
- Excess return normalization constraint.
- Clamp final K to practical bounds.

Output:

- portfolios/cardinality_analysis.json

Why it matters:

- K is a first-order control knob. Too small gives concentration risk; too large dilutes edge.

---

## 2.3 Phase 03: QUBO Formulation

File: [phase_03_qubo_formulation.py](phase_03_qubo_formulation.py)

Primary responsibility:

- Convert stock subset selection into a QUBO matrix.

What it builds:

- Risk term from covariance.
- Return reward term from expected return.
- Cardinality penalty term for selecting about K names.
- Downside risk diagonal penalty.
- Sector concentration penalty on same-sector pairs.

Important internal logic:

- Adaptive lambda scaling based on problem size and matrix magnitudes.
- Symmetrization of QUBO matrix.
- Optional sector structure awareness from sector JSON.

Outputs:

- quantum/qubo_matrix.npy
- quantum/qubo_metadata.json

Why it matters:

- This is the core translation from finance objective to combinatorial energy landscape.

---

## 2.4 Phase 04: Quantum Selection (Simulated Annealing)

File: [phase_04_quantum_selection.py](phase_04_quantum_selection.py)

Primary responsibility:

- Solve the QUBO and choose discrete stock basket.

How it works:

1. Converts QUBO matrix into binary quadratic model.
2. Uses simulated annealing sampler for many reads.
3. Validates candidate solutions against constraints.
4. Chooses lowest-energy valid solution.

Constraint checks applied:

- Target cardinality.
- Minimum sector diversity.
- Maximum sector concentration.

Output:

- portfolios/selected_stocks.json

Why it matters:

- This stage decides membership: which assets are in or out.

---

## 2.5 Phase 05: Rebalancing Logic

File: [phase_05_rebalancing.py](phase_05_rebalancing.py)

Primary responsibility:

- Apply periodic portfolio maintenance logic over time.

Implemented policy:

- Quarterly rebalance schedule.
- Identify underperformers among current holdings.
- Replace with sector-matched candidates.
- Track trade counts and transaction cost estimate.

Why it matters:

- Even a good initial basket drifts. Rebalancing restores intent and manages decay.

---

## 2.6 Phase 06: Continuous Weight Optimization

File: [phase_06_weight_optimization.py](phase_06_weight_optimization.py)

Primary responsibility:

- Assign continuous capital weights to selected stocks with constraints.

Method in this phase file:

- Convex mean-variance style optimization with solver fallback.
- Long-only, sum-to-one, sector cap constraints.
- Outputs expected return, volatility, Sharpe, diversification ratio.

Outputs:

- portfolios/optimal_weights.json
- portfolios/optimal_weights.csv

Note on architecture:

- In unified and crash evaluators, production weighting is primarily from SLSQP in [quantum/weight_optimizer.py](quantum/weight_optimizer.py), while this phase file is a staged optimization implementation used in the paper pipeline path.

---

## 2.7 Phase 07: Strategy Comparison

File: [phase_07_strategy_comparison.py](phase_07_strategy_comparison.py)

Primary responsibility:

- Compare strategy variants on consistent metrics and visuals.

Compared strategies:

1. Equal-weight buy-and-hold.
2. Quantum buy-and-hold.
3. Quantum with periodic rebalancing.

Metrics produced:

- Total return, annual return, volatility
- Sharpe, Sortino, Calmar
- Max drawdown, win-rate, VaR(95)

Outputs:

- results/strategy_comparison.json
- results/strategy_returns.csv
- results/strategy_comparison.png

---

## 2.8 Phase 08: Crash and Regime Evaluation

File: [phase_08_crash_and_regime_evaluation.py](phase_08_crash_and_regime_evaluation.py)

Primary responsibility:

- Evaluate quantum vs greedy vs classical during stress windows.

Key functions:

- Train/test leakage validation.
- Eligible universe filtering by train coverage and test availability.
- Method-specific stock selection.
- SLSQP-based weight optimization.
- Scenario backtest and risk metric reporting.

Outputs include:

- real_quantum_crash_results.json
- real_quantum_crash_analysis.png

Why it matters:

- Regime behavior under stress is where many strategies fail in practice.

---

## 3. Unified Baseline Engine (Most Operationally Important)

File: [unified_train_test_compare.py](unified_train_test_compare.py)

What this runner adds on top of phases:

1. Automatic dataset candidate selection by recency and completeness.
2. Full-universe or NIFTY100-only filtering switch.
3. Horizon scenario generation with rolling or expanding train windows.
4. Dynamic scenario-wise K derivation option.
5. One standard output JSON with per-scenario metrics and winner counts.
6. Optional matrix artifact export per scenario.

Why this is usually the primary baseline runner:

- It gives consistent apples-to-apples outputs across horizon and crash families using one config and one report format.

---

## 4. Detailed Terminology and Concepts

## 4.1 QUBO

QUBO means Quadratic Unconstrained Binary Optimization.

General form:

$$
\min_{x \in \{0,1\}^n} x^T Q x
$$

Interpretation in this project:

- x_i = 1 means stock i is selected.
- x_i = 0 means stock i is not selected.
- Q encodes return reward, risk penalty, and constraints as energy terms.

Finance decomposition used:

$$
E(x) = q\,x^T\Sigma x - \mu^T x + \lambda(\mathbf{1}^T x - K)^2 + \text{extras}
$$

Where:

- $x^T\Sigma x$ penalizes correlated risk.
- $-\mu^Tx$ rewards higher expected return.
- Cardinality penalty keeps selected count near K.
- Extras include downside and sector penalties.

---

## 4.2 Simulated Annealing

Simulated annealing is a probabilistic search method for hard discrete optimization.

Mechanics:

1. Start from an initial feasible basket.
2. Propose small random move (for fixed-K, often a swap 1->0 and 0->1).
3. Compute energy change $\Delta E$.
4. Accept always if better ($\Delta E<0$), else accept with probability:

$$
P(\text{accept}) = e^{-\Delta E / T}
$$

5. Reduce temperature T gradually.

Why it works:

- Early high T allows escaping local traps.
- Late low T refines around strong solutions.

In your codebase:

- Custom SA appears in [qubo_selector.py](qubo_selector.py).
- Ocean/Neal SA path appears in [phase_04_quantum_selection.py](phase_04_quantum_selection.py).

---

## 4.3 SLSQP

SLSQP = Sequential Least Squares Programming.

It is a constrained nonlinear optimizer well-suited for continuous portfolio weights.

In your project, SLSQP is used for Sharpe optimization in [quantum/weight_optimizer.py](quantum/weight_optimizer.py):

Objective solved:

$$
\max_w \frac{w^T\mu - r_f}{\sqrt{w^T\Sigma w}}
$$

implemented as minimizing negative Sharpe.

Constraints used:

- Sum-to-one: $\sum_i w_i = 1$
- Long-only: $w_i \ge 0$
- Per-position cap: $w_i \le w_{max}$ (for example 0.40)

Why it matters:

- QUBO picks members; SLSQP allocates capital efficiently among members.

---

## 4.4 Covariance

Covariance between assets i and j:

$$
\operatorname{Cov}(R_i,R_j)=\mathbb{E}[(R_i-\mu_i)(R_j-\mu_j)]
$$

What it means:

- Positive covariance: assets tend to move together.
- Negative covariance: one may offset the other.

Portfolio variance is not weighted sum of individual variances only:

$$
\sigma_p^2 = w^T\Sigma w
$$

So pairwise co-movement dominates diversification behavior.

---

## 4.5 Correlation

Correlation is normalized covariance:

$$
\rho_{ij} = \frac{\operatorname{Cov}(R_i,R_j)}{\sigma_i\sigma_j}
$$

Range: [-1, 1].

Practical reading:

- Near +1: little diversification benefit.
- Near 0: weak dependency.
- Near -1: strong hedge behavior.

Covariance drives optimization directly; correlation helps interpret structure.

---

## 4.6 Cardinality

Cardinality K is number of selected assets.

Binary expression:

$$
\sum_i x_i = K
$$

In QUBO, hard equality is converted into soft penalty:

$$
\lambda(\sum_i x_i - K)^2
$$

Why cardinality is crucial:

- Small K: concentrated alpha plus concentration risk.
- Large K: diversification plus dilution.

Your framework supports:

- Fixed K from config.
- Dynamic K using phase-02 style derivation.

---

## 4.7 Risk-Free Rate

Risk-free rate $r_f$ is used in Sharpe and target return normalization.

Sharpe:

$$
\text{Sharpe} = \frac{R_p-r_f}{\sigma_p}
$$

Your code includes date-based dynamic proxy in [quantum/weight_optimizer.py](quantum/weight_optimizer.py) to reflect regime-level policy-rate shifts.

---

## 4.8 Downside Risk and Downside Deviation

Downside deviation focuses only on negative returns, unlike standard deviation which treats upside and downside symmetrically.

Used here as an additional diagonal penalty to avoid assets with severe downside behavior in stress periods.

---

## 4.9 Max Drawdown

Max drawdown is the worst peak-to-trough loss over the period:

$$
\text{MDD} = \min_t\left(\frac{V_t-\max_{s\le t}V_s}{\max_{s\le t}V_s}\right)
$$

Why important:

- Captures pain investors actually feel.
- Often more practical than volatility for mandate controls.

---

## 4.10 VaR (95%)

Value-at-Risk at 95% is the 5th percentile of daily return distribution.

Interpretation:

- A VaR(95) of -2% means on 5% worst days, daily loss is worse than 2%.

Limitation:

- VaR does not tell severity beyond that threshold (tail beyond tail).

---

## 4.11 Train/Test Leakage

Leakage means information from the future leaks into model training.

Your code explicitly checks and enforces:

- train_end < test_start
- positive gap days

Leakage checks are central in [phase_08_crash_and_regime_evaluation.py](phase_08_crash_and_regime_evaluation.py) and reused by the unified runner.

---

## 4.12 Rolling vs Expanding Windows

Rolling window:

- Fixed lookback length (for example 60 months) slides forward.
- Better recency, less stale data.

Expanding window:

- Starts from initial date and grows over time.
- More data, potentially more regime mixing.

Your baseline uses rolling for horizons and fixed 12M pre-crash training windows for crash scenarios.

---

## 5. Data and Artifact Flow

End-to-end flow summary:

1. Phase 01 writes cleaned statistics and metadata.
2. Phase 02 derives K and writes cardinality report.
3. Phase 03 writes QUBO matrix and metadata.
4. Phase 04 writes selected stock basket.
5. Phase 06 or SLSQP module writes weights.
6. Phase 07 and Phase 08 write comparison outputs and charts.
7. Unified runner writes full scenario report plus winner counts.

Key output report for baseline analysis:

- [results/unified_train_test_compare.json](results/unified_train_test_compare.json)

Reference tables used in your paper package:

- [model_reach_paper/tables/base_horizon_total_return.csv](model_reach_paper/tables/base_horizon_total_return.csv)
- [model_reach_paper/tables/base_crash_total_return.csv](model_reach_paper/tables/base_crash_total_return.csv)
- [model_reach_paper/tables/base_metric_leader_counts.csv](model_reach_paper/tables/base_metric_leader_counts.csv)

---

## 6. Practical Reading Notes

1. Discrete stage and continuous stage solve different mathematical problems. Keep them separate conceptually.
2. K, train-window policy, and risk metric priority are first-order design decisions.
3. Return leadership and downside leadership can differ. Always read winner counts by metric, not only by total return.
4. For deployment, monitor turnover and costs because rebalance alpha can vanish after friction.

---

## 7. If You Want This as a Formal Paper Skeleton

This guide can be lifted into a paper structure directly:

1. Introduction and motivation.
2. Data and preprocessing.
3. Two-stage optimization method.
4. Experimental design (horizon plus crash).
5. Results by metric and regime.
6. Sensitivity analysis (K and window).
7. Limitations and governance policy.
8. Conclusion.
