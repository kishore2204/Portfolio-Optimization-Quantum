# Portfolio Optimization Quantum: Unified Technical Master Guide

This is the single source of truth for the project.
It combines process flow, formulas, phase functionality, technical glossary, and rationale for why each method is used versus alternatives.

## 1. Objective and scope

The project builds and evaluates portfolios with a hybrid methodology:
1. discrete stock selection through QUBO optimization,
2. continuous weight allocation through classical optimization,
3. robust out-of-sample testing on horizon and crash windows,
4. direct method comparison between Quantum, Greedy, and Classical baselines.

Primary design goals:
- strict no-leakage train/test separation,
- reusable configuration-driven controls,
- comparable evaluation protocol across all methods.

## 2. End-to-end functionality map

Core phase pipeline:
1. `phase_01_data_preparation.py`
2. `phase_02_cardinality_determination.py`
3. `phase_03_qubo_formulation.py`
4. `phase_04_quantum_selection.py`
5. `phase_05_rebalancing.py`
6. `phase_06_weight_optimization.py`
7. `phase_07_strategy_comparison.py`
8. `phase_08_crash_and_regime_evaluation.py`

Unified evaluation engine:
- `unified_train_test_compare.py`

Main runners:
- `run_portfolio_optimization_quantum.py`
- `run_crash_analysis_wrapper.py`
- `run_all_end_to_end.py`

## 3. Data model and notation

- $P_{t,i}$: adjusted price for stock $i$ on date $t$
- $r_{t,i}$: daily simple return for stock $i$
- $\mu_i$: annualized expected return
- $\Sigma$: annualized covariance matrix
- $x_i \in \{0,1\}$: binary inclusion decision
- $w_i$: continuous portfolio weight
- $K$: cardinality (number of selected assets)
- $r_f$: annual risk-free rate
- $N$: candidate universe size

## 4. Dataset selection and universe control

Configured candidate order:
1. `Dataset/prices_timeseries_complete.csv`
2. `data/prices_timeseries.csv`

Selection policy in unified runner:
1. latest end date,
2. highest row count,
3. highest asset count.

### Which dataset is actually used

For `unified_train_test_compare.py` and unified crash/horizon comparison runs:
- The runtime source is selected from `dataset_candidates` in `config/unified_compare_config.json`.
- Current priority is:
	1. `Dataset/prices_timeseries_complete.csv`
	2. `data/prices_timeseries.csv`
- So when `Dataset/prices_timeseries_complete.csv` exists and is valid, that is the dataset actually used.

Why `Portfolio Optimization Quantum/data/` exists:
- That folder stores phase artifacts produced/consumed by the phase pipeline (`phase_01` to `phase_05` style flow), such as:
	- `mean_returns.npy`
	- `covariance_matrix.npy`
	- `returns_matrix.npy`
	- `universe_metadata.json`
	- `test_data.csv`
- These files are used by phase scripts (for example, `phase_02_cardinality_determination.py`, `phase_03_qubo_formulation.py`, `phase_05_rebalancing.py`).

Practical rule:
- Do not remove `Portfolio Optimization Quantum/data/` if you still run the phase pipeline.
- It can be removed only if you fully migrate to unified-runner-only workflows and also remove/retire phase scripts that depend on these artifacts.

Universe modes (config and CLI):
- `full_universe`
- `nifty100_only`

Default mode: `full_universe`.

Why this approach:
- picks the most recent and complete dataset automatically,
- avoids hardcoding one static source,
- supports controlled experiments between broad and restricted universes.

Why not only fixed file paths:
- brittle across environments,
- outdated data risk,
- poor reproducibility when files evolve.

## 5. Phase-by-phase technical details

### Phase 01: Data preparation
File: `phase_01_data_preparation.py`

Main outputs:
- cleaned price time series,
- annualized mean returns and covariance,
- metadata for downstream phases.

Formulas:

Daily return:
$$
r_{t,i} = \frac{P_{t,i}}{P_{t-1,i}} - 1
$$

Annualized mean:
$$
\mu_i = 252\cdot\frac{1}{T}\sum_{t=1}^{T} r_{t,i}
$$

Annualized covariance:
$$
\Sigma = 252\cdot\mathrm{Cov}(r)
$$

Why used:
- simple returns are interpretable and standard for daily equity backtests,
- annualization aligns optimization and reporting scales.

Why not alternatives:
- log returns are valid, but this project keeps simple returns for direct portfolio aggregation consistency,
- higher-frequency features are unnecessary for current daily-horizon objective.

### Phase 02: Cardinality determination
File: `phase_02_cardinality_determination.py`

Function:
- derive data-driven $K$ from convex train-window optimization.

Why used:
- avoids manual fixed-$K$ bias,
- adapts concentration/diversification to regime statistics.

Why not fixed K only:
- fixed $K$ can over-concentrate in unstable regimes or underutilize breadth in stable regimes.

### Phase 03: QUBO formulation
File: `phase_03_qubo_formulation.py`

Binary objective:
$$
\min_{x\in\{0,1\}^N} E(x) = x^TQx
$$

Conceptual decomposition:
$$
E(x)=q\,x^T\Sigma x-\mu^Tx+\lambda(\mathbf{1}^Tx-K)^2+\beta\sum_i\sigma_i^-x_i+E_{sector}(x)
$$

Terms and rationale:
- $q\,x^T\Sigma x$ (risk): penalizes correlated/high-variance sets.
- $-\mu^Tx$ (return): rewards high expected return assets.
- $\lambda(\mathbf{1}^Tx-K)^2$ (cardinality): enforces target count.
- $\beta\sum_i\sigma_i^-x_i$ (downside): penalizes assets with poor downside behavior.
- $E_{sector}(x)$ (diversification): soft-penalizes concentration in one sector.

Cardinality expansion:
$$
(\mathbf{1}^Tx-K)^2 = \sum_i x_i + 2\sum_{i<j}x_ix_j - 2K\sum_i x_i + K^2
$$

Downside deviation:
$$
\mathcal{R}_i^- = \{r_{t,i}: r_{t,i}<0\},\quad
\sigma_i^- = \sqrt{252}\cdot\mathrm{Std}(\mathcal{R}_i^-)
$$

Why used:
- QUBO natively captures pairwise interactions and hard/soft combinatorial constraints,
- downside and sector penalties improve robustness vs pure return ranking.

Why not only mean-variance continuous optimization:
- continuous MVO does not directly model discrete inclusion decisions,
- cardinality constraints are nontrivial in plain continuous form.

### Phase 04: Quantum-inspired selection
File: `phase_04_quantum_selection.py` (plus `qubo_selector.py`)

Solver style:
- simulated annealing over binary states.

Acceptance rule:
$$
\Pr(accept)=e^{-\Delta E/T}
$$

Why used:
- efficient heuristic for large discrete landscapes,
- handles nonconvex binary energy surfaces.

Why not exhaustive search:
- combinatorial explosion: $2^N$ states is intractable for large universes.

Why not simple greedy only:
- greedy can miss globally better combinations when pairwise interactions dominate.

### Phase 05: Rebalancing
File: `phase_05_rebalancing.py`

Function:
- scheduled portfolio refresh with replacement logic and diversification checks.

Why used:
- prevents stale holdings and drift from intended risk profile.

Why not buy-and-hold only:
- persistent regime changes can degrade a fixed basket over long windows.

### Phase 06: Weight optimization
Files: `phase_06_weight_optimization.py`, `quantum/weight_optimizer.py`

Objective:
$$
\max_w\;\frac{w^T\mu-r_f}{\sqrt{w^T\Sigma w}}
$$

Subject to:
$$
\sum_i w_i=1,\quad 0\le w_i\le w_{max}
$$

Why used:
- SLSQP handles equality and box constraints directly,
- translates selected stocks into practical allocations.

Why not equal weights:
- ignores risk/return asymmetry,
- typically inferior Sharpe for heterogeneous assets.

Why not unconstrained optimizer:
- unconstrained solutions can over-concentrate or use infeasible negative weights.

### Phase 07: Strategy comparison
File: `phase_07_strategy_comparison.py`

Function:
- compare strategy-level metrics under same data split and assumptions.

Why used:
- validates whether complexity adds measurable value over baselines.

Why not single-method reporting:
- no counterfactual baseline means no evidence of relative benefit.

### Phase 08: Crash/regime evaluation
File: `phase_08_crash_and_regime_evaluation.py`

Function:
- scenario-based stress tests with leakage checks,
- run Quantum, Greedy, Classical under identical windows.

Why used:
- checks robustness outside average conditions,
- captures tail behavior and drawdown resilience.

Why not only standard backtest:
- aggregate backtests can hide stress-period failure modes.

## 6. Unified runner logic and evaluation protocol

File: `unified_train_test_compare.py`

Horizon block:
- auto-generates 6M, 12M, 24M, 36M tests.

Scenario date construction:
- test end = latest available date,
- test start = end minus horizon,
- train end = test start - 1 day,
- train start = train end minus configured train months.

Crash block:
- fixed date windows from config.

Leakage rule:
$$
t_{train,end}<t_{test,start}
$$

If violated, scenario is rejected.

Why used:
- strict temporal validity for out-of-sample claims.

Why not random split:
- random splits leak future market structure into train set for time series tasks.

## 7. Metrics and formulas

Let $r_t^p$ be daily portfolio return.

Cumulative value path:
$$
C_t = \prod_{u=1}^{t}(1+r_u^p)
$$

Total return (%):
$$
100\cdot(C_T-1)
$$

Annualized volatility (%):
$$
100\cdot\sqrt{252}\cdot\mathrm{Std}(r^p)
$$

Sharpe ratio:
$$
\sqrt{252}\cdot\frac{\mathbb{E}[r^p-r_f/252]}{\mathrm{Std}(r^p)}
$$

VaR 95% (%):
$$
100\cdot\mathrm{Percentile}_{5}(r^p)
$$

Max drawdown (%):
$$
100\cdot\min_t\left(\frac{C_t-\max_{u\le t}C_u}{\max_{u\le t}C_u}\right)
$$

Why these metrics:
- return and Sharpe: reward and risk-adjusted reward,
- volatility and drawdown: path-risk and peak-to-trough pain,
- VaR: tail-loss sensitivity.

Why not only return:
- high return can be achieved with unacceptable risk concentration.

## 8. Method definitions and winner logic

Methods compared per scenario:
- Quantum: QUBO + annealing + constrained weighting.
- Greedy: top-scored asset ranking baseline.
- Classical: non-quantum risk-adjusted baseline.

Winner mapping per metric:
- `best_total_return`: max,
- `best_sharpe`: max,
- `best_max_drawdown`: max (least negative),
- `best_var_95`: max (least negative tail).

Why this winner rule:
- keeps metric direction consistent as “higher is better” in reporting.

## 9. Technical glossary with rationale

- QUBO: Binary quadratic objective for discrete selection.
	Why: models interactions and constraints in one energy function.
	Why not linear ranking: cannot capture pairwise covariance penalties.

- BQM: Binary Quadratic Model implementation form of QUBO.
	Why: direct compatibility with annealing solvers.

- Simulated annealing: stochastic search with temperature schedule.
	Why: practical for large nonconvex binary optimization.
	Why not exhaustive: exponential complexity.

- Cardinality ($K$): number of selected assets.
	Why: controls concentration and turnover behavior.

- Covariance shrinkage: blend sample covariance with diagonal target.
	Why: improves out-of-sample stability in high-dimensional settings.
	Why not raw covariance only: noisy estimates for large universes.

- Ensemble selection: multiple seeded runs with consensus vote.
	Why: reduces seed sensitivity and improves robustness.
	Why not single run only: one run can be trapped in local structures.

- Sharpe optimization (SLSQP): constrained continuous weighting.
	Why: practical and interpretable with portfolio constraints.

- Out-of-sample testing: evaluate only on future unseen period.
	Why: realistic generalization estimate.

- Data leakage: train-test overlap or future information contamination.
	Why prevented: leakage inflates reported performance.

## 10. Configuration surfaces

Main controls are in:
- `config/unified_compare_config.json`

Important groups:
- `dataset_candidates`
- `universe_filter`
- `matrix_exports`
- `evaluation`
- `dynamic_k`
- `qubo`
- `weight_optimization`
- `crash_scenarios`

### K and budget configuration (editable vs auto)

- Budget is fully editable in config:
	- `weight_optimization.budget`

- K is config-controlled and can be either fixed or auto-derived:
	- baseline K: `evaluation.k_stocks`
	- K mode: `evaluation.k_mode`
	- guard rails: `evaluation.k_min`, `evaluation.k_max`
	- scenario dynamic K switch: `dynamic_k.enabled`
	- dynamic method: `dynamic_k.mode = eq7_train_window`
	- dynamic limits: `dynamic_k.k_min`, `dynamic_k.k_max`

Operational rule:
- CLI `--k` overrides config for that run.
- If CLI `--k` is not provided, the runner resolves K from config mode and bounds.
- If dynamic K is enabled, each scenario can get its own K from train-window statistics, still clamped by configured min/max.

### Hyperparameter values and why these specific settings

Values below reflect current defaults in `config/unified_compare_config.json` and are selected as robust starting points, not immutable constants.

- `evaluation.k_mode = auto_from_phase2_if_available`
	Why this value: lets cardinality be derived from train-window statistics when available, while preserving fallback continuity.
	Why not always fixed: one fixed K can be too concentrated in some regimes and too diluted in others.

- `evaluation.k_stocks = 10`, `evaluation.k_min = 8`, `evaluation.k_max = 20`
	Why this range: 10 is a practical center for diversification vs concentration; [8, 20] prevents extreme outputs from dynamic K under noisy windows.
	Why not very small or very large defaults: very small K increases idiosyncratic risk; very large K dilutes signal and reduces combinatorial contrast.

- `evaluation.min_train_coverage = 0.8`
	Why this value: requires strong historical availability before training moments/covariances, while retaining enough candidates.
	Why not 1.0: strict completeness can remove too many assets in real datasets.

- `evaluation.min_test_points = 20`
	Why this value: avoids evaluating on near-empty test slices and keeps metric estimates meaningful.
	Why not tiny values: volatility, VaR, and drawdown become unstable with very short samples.

- `dynamic_k.enabled = true`, `dynamic_k.mode = eq7_train_window`, `dynamic_k.risk_free_rate = 0.06`, `dynamic_k.k_min = 6`, `dynamic_k.k_max = 20`
	Why this setting: Eq.7-style train-window adaptation aligns cardinality with current risk/return geometry; 6% annual RF is a conservative benchmark anchor for Indian-equity style horizons.
	Why capped bounds: prevents dynamic K from collapsing to over-concentrated or over-dispersed corner solutions.

- `qubo.lambda_penalty = null`, `qubo.lambda_base = 50.0`, `qubo.lambda_scale = 10.0`
	Why this choice: uses adaptive cardinality pressure, with strength increasing with universe-to-K ratio; this keeps constraint enforcement stable across different universe sizes.
	Why not a single fixed lambda everywhere: one penalty can be too weak in large universes and too strong in small universes.

- `qubo.downside_beta = 0.3`
	Why this value: adds meaningful downside aversion without overpowering return and covariance terms.
	Why not near zero or near one: near zero ignores downside asymmetry; near one can over-penalize and reduce upside participation.

- `qubo.max_iter = 2000`
	Why this value: balances annealing quality with runtime for repeated multi-scenario experiments.
	Why not very low iterations: lower budgets increase local-minima risk.

- `qubo.covariance_shrinkage_enabled = true`, `qubo.covariance_shrinkage_alpha = auto`, `qubo.covariance_shrinkage_diag_eps = 1e-8`
	Why this choice: automatic shrinkage improves covariance conditioning when assets are many relative to observations; small diagonal floor improves numerical stability.
	Why not raw covariance only: sample covariance can be noisy/ill-conditioned in high-dimensional windows.

- `qubo.ensemble_enabled = true`, `qubo.ensemble_num_seeds = 7`, `qubo.ensemble_seed_step = 101`
	Why these values: 7 seeded runs materially reduce seed sensitivity while keeping runtime manageable; step 101 separates pseudo-random trajectories.
	Why not single-seed only: one annealing trajectory is more sensitive to initialization.

- `weight_optimization.min_weight = 0.0`, `weight_optimization.max_weight = 0.4`
	Why these bounds: long-only and capped concentration produce implementable allocations with no shorting and no single-name dominance.
	Why not unconstrained weights: unconstrained solutions can be unrealistic and unstable.

- `weight_optimization.budget = 1000000`
	Why this value: reporting-scale budget for allocation transparency; relative performance metrics are scale-invariant.
	Why not tied to performance claims: budget affects rupee allocation amounts, not percentage return ordering.

- `matrix_exports.enabled = true` with selected-matrix flags true and full-matrix flags false
	Why this profile: always persist compact, auditable selected-submatrix artifacts while controlling storage growth for repeated runs.
	Why not full matrices by default: full NxN exports can become heavy in full-universe mode.

## 11. Reproducible run commands

End-to-end:

```powershell
python run_all_end_to_end.py
```

Unified all scenarios:

```powershell
python unified_train_test_compare.py --only all
```

Unified horizon only:

```powershell
python unified_train_test_compare.py --only horizon
```

Unified crash only:

```powershell
python unified_train_test_compare.py --only crash
```

Unified with explicit universe mode:

```powershell
python unified_train_test_compare.py --only all --universe-mode full_universe
python unified_train_test_compare.py --only all --universe-mode nifty100_only
```

Crash-only with explicit universe mode:

```powershell
python unified_train_test_compare.py --only crash --universe-mode full_universe
python unified_train_test_compare.py --only crash --universe-mode nifty100_only
```

What appears in terminal during comparison runs:
- All runs compare and print method metrics for:
	- Quantum
	- Greedy
	- Classical
- Per scenario, terminal prints eligible universe size, scenario K, and total return for all three methods.

Core phase runner:

```powershell
python run_portfolio_optimization_quantum.py
```

## 12. Practical decision guidance

- Choose `full_universe` when the objective is maximizing quantum selection advantage across broader combinational opportunity.
- Choose `nifty100_only` when constrained universe comparability or benchmark alignment is the primary requirement.
- Keep dynamic K and robustness settings enabled when target is regime resilience rather than static in-sample fit.

## 13. Testing windows and date anchors

### Horizon tests (6M, 12M, 24M, 36M)

Anchor logic:
- Horizon tests are anchored to the latest date available in the selected dataset, not the machine calendar date.
- `test_end = dataset_latest_date`
- `test_start = test_end - horizon_months + 1 day`
- `train_end = test_start - 1 day`
- `train_start = train_end - train_months_by_horizon[horizon] + 1 day`

Interpretation:
- If your dataset is updated to current market date, horizon tests are effectively up-to-now tests.
- If dataset ends earlier, horizon tests are up-to-that-dataset-end tests.

### Crash tests

Crash windows are explicit fixed date ranges from `crash_scenarios` in config; they are not auto-shifted to a market-stabilized date.

How a crash test window is evaluated (example: 2020-02-20 to 2020-04-30):
- The runner takes all available trading days with `Date >= test_start` and `Date <= test_end` (inclusive boundaries).
- It computes daily asset returns using `pct_change()` inside that window.
- It computes daily portfolio return as the weighted sum of daily stock returns.
- It compounds those daily portfolio returns to build cumulative performance and then computes Total Return, Volatility, Max Drawdown, VaR 95%, and Sharpe.
- There is no weekly/monthly grouping in this test path; it is day-by-day backtesting on the selected date window.

Current configured crash scenarios:
- COVID Peak Crash:
	- Train: 2019-02-20 to 2020-02-19
	- Test: 2020-02-20 to 2020-04-30
- China Bubble Burst Peak:
	- Train: 2014-06-12 to 2015-06-11
	- Test: 2015-06-12 to 2015-09-30
- European Debt Stress:
	- Train: 2011-03-14 to 2012-03-13
	- Test: 2012-03-14 to 2012-09-30
- 2022 Global Bear Phase:
	- Train: 2021-01-01 to 2021-12-31
	- Test: 2022-01-01 to 2022-06-30

Leakage policy (applies to every horizon and crash scenario):
- Train must end strictly before test starts.
- Any overlap is rejected as data leakage.

## 14. Run artifacts and matrices

Yes, QUBO/covariance matrices are involved in the process and can be saved to run artifacts.

Current default in config:
- `matrix_exports.enabled = true`
- `include_selected_covariance = true`
- `include_selected_qubo = true`
- `include_full_covariance = false`
- `include_full_qubo = false`

Meaning of current defaults:
- Saved by default per scenario:
	- selected covariance submatrix
	- selected QUBO submatrix
- Not saved by default:
	- full universe covariance matrix
	- full universe QUBO matrix

To also save full matrices, set the two full flags to `true` in `config/unified_compare_config.json`.
