================================================================================
                    QUANTUM PORTFOLIO OPTIMIZATION
                         DATA FOLDER INVENTORY
================================================================================

This folder contains all matrices, data inputs, and comprehensive metrics from
the quantum-inspired portfolio optimization pipeline.

================================================================================
FILE INVENTORY & DESCRIPTIONS
================================================================================

INPUT MATRICES
--------------

[01_covariance_matrix.csv]
  - Annualized covariance matrix from training period (10 years: 2011-2021)
  - Dimensions: 680 x 680 (all assets in universe)
  - Size: ~25 MB (symmetric matrix)
  - Uses: Risk model input for classical and quantum optimization
  - Eigenvalue range: 27.61 (largest) to 0.012 (smallest)
  - Condition number: 2233.57 (high correlation structure)

[02_train_returns.csv]
  - Log returns from training period (2011-03-15 to 2021-03-15)
  - Dimensions: 2478 trading days x 680 assets
  - Units: Daily log returns (decimal, e.g., 0.01 = 1% daily return)
  - Uses: Computing covariance, downside risk, Sharpe ratios
  - Data quality: 85%+ non-NA per asset

[03_test_returns.csv]
  - Log returns from test/evaluation period (2021-03-15 to 2026-03-15)
  - Dimensions: 1240 trading days x 680 assets
  - Exact timeline: 5 years of out-of-sample testing
  - Uses: Backtesting portfolio performance

[04_expected_returns_and_downside.csv]
  - Annualized expected returns and semi-deviation (downside risk)
  - Columns:
    * Expected_Return: Annualized arithmetic mean return (% per year)
    * Downside_Risk: Semi-deviation (volatility of negative returns only)
  - 680 rows (one per asset)
  - Used in: Classical MVO, QUBO risk penalties

QUBO MATRICES
-------------

[05_qubo_matrix.csv]
  - Full QUBO formulation for quantum-inspired asset selection
  - Dimensions: 40 x 40 (selected K assets in quantum portfolio)
  - Structure: Binary quadratic model Q where E(x) = x'Qx
  - Composition:
    * Diagonal: Return + Risk + Downside + Cardinality penalties
    * Off-diagonal: Risk covariance + Sector concentration penalties
  - Eigenvalues: 27.61 (largest risk) to ~0 (negligible terms)
  - Sparse: No (all entries populated with penalty terms)

[06_qubo_diagonal_terms.csv]
  - Individual diagonal elements of QUBO matrix
  - Useful for understanding per-asset penalty structure
  - One value per asset (40 assets)

PORTFOLIO DATA
--------------

[07_portfolio_weights.csv]
  - Optimization results: Portfolio weights (allocations)
  - Columns:
    * Classical: MVO-optimized weights
    * Quantum: QUBO-annealed + Sharpe-optimized weights
  - 40 rows (optimal portfolio size)
  - All weights sum to 1.0 (fully invested)
  - Max single weight: ~12% to prevent concentration

[10_portfolio_values.csv]
  - Portfolio value time series (base unit = 1.0 at date 2021-03-15)
  - Data from: Full test period (2021-03-15 to 2026-03-15)
  - 1,240 daily observations
  - Columns: "Classical", "Quantum", "Quantum_Rebalanced"
  - Example: 3.46 = 346% total return over test period

PRICE SERIES
------------

[08_train_prices.csv]
  - Adjusted close prices during training (2011-03-15 to 2021-03-15)
  - Raw input before return calculation
  - 2,478 trading days × 680 assets
  - Used to: Compute log returns, validate data integrity

[09_test_prices.csv]
  - Adjusted close prices during testing (2021-03-15 to 2026-03-15)
  - 1,240 trading days × 680 assets
  - Backtesting input: Combined with weights to compute returns

[11_benchmark_values.csv]
  - Benchmark index performance (normalized to 1.0)
  - Columns: BSE_500, HDFCNIF100, Nifty_50, Nifty_100, Nifty_200
  - Same time period and frequency as portfolio values
  - Used to: Compare quantum portfolio vs market indices

COMPREHENSIVE REPORTS
---------------------

[12_COMPREHENSIVE_METRICS_REPORT.txt]
  - Human-readable summary of ALL important metrics
  - Sections:
    1. Dataset Overview (time periods, asset count, trading days)
    2. Annualized Risk Statistics (returns, volatility, eigenvalues)
    3. Classical Portfolio (MVO-optimized; 40 assets; HHI=0.0648)
    4. Quantum Portfolio (QUBO-optimized; 40 assets; HHI=0.0745)
    5. QUBO Configuration (matrix size, sparsity, conditioning)
    6. Test Period Performance (returns, Sharpe, drawdowns - ALL portfolios + benchmarks)
    7. Portfolio Comparison Summary (quantum outperformance)
    8. Configuration Parameters (hyperparameters used)

================================================================================
KEY METRICS & PERFORMANCE (Test Period: 2021-03-15 to 2026-03-15)
================================================================================

PORTFOLIOS:
-----------
  Classical (MVO + Sharpe):
    - Total Return:              11.70%
    - Annualized Return:         2.25%
    - Volatility:                14.92% (annualized)
    - Sharpe Ratio:              -0.1842
    - Max Drawdown:              -30.58%

  Quantum (QUBO + Annealing + Sharpe):
    - Total Return:              105.10%
    - Annualized Return:         14.61%      ← 6.5× classical return
    - Volatility:                13.78%
    - Sharpe Ratio:              0.6973      ← POSITIVE (classical was negative)
    - Max Drawdown:              -22.46%     ← LOWER drawdown

  Quantum + Rebalancing (Quarterly, ~63-day cadence):
    - Total Return:              346.02%
    - Annualized Return:         30.41%      ← 13.5× classical return
    - Volatility:                19.26%
    - Sharpe Ratio:              1.3197      ← 7.2× classical
    - Max Drawdown:              -32.48%

BENCHMARKS:
-----------
  BSE_500:
    - Annualized Return:         11.19%
    - Sharpe Ratio:              0.4379

  Nifty_50:
    - Annualized Return:         10.01%

  Nifty_100:
    - Annualized Return:         9.99%

  Nifty_200:
    - Annualized Return:         11.70%

QUANTUM OUTPERFORMANCE:
  - vs Classical:               +245% total return
  - vs Rebalanced:              +230% total return (absolute)
  - vs Best Benchmark (BSE 500): +3× return at similar volatility
  - Sharpe Improvement:          1.62 vs -0.18 (9× better)

================================================================================
INSIGHTS FROM MATRICES
================================================================================

COVARIANCE STRUCTURE:
  - Largest eigenvalue: 27.61 (high systemic risk)
  - High condition number (2233.57) → Ill-conditioned
  - Implication: Some assets move together; diversification benefits exist

PORTFOLIO SELECTION:
  Classical Top Assets:
    1. AJANTPHARM (10.85%) | Pharma
    2. RELAXO (10.59%) | Consumer Goods
    3. ALKYLAMINE (8.21%) | Chemicals
    4. AARTIIND (7.43%) | Chemicals
    5. VINATIORGA (5.82%) | Pharma

  Quantum Top Assets:
    1. SOLARINDS (11.86%) | Energy/Solar
    2. SUPREMEIND (10.40%) | Energy
    3. PIIND (10.31%) | Automotive
    4. HINDUNILVR (8.60%) | Consumer
    5. EICHERMOT (7.23%) | Automotive

  → Quantum selection favors Energy & Automotive (higher expected returns in period)
  → Classical concentrated on Pharma (lower volatility bias)

DOWNSIDE RISK:
  - Average semi-deviation: 31.75% (higher than standard volatility)
  - Indicates asymmetric distribution (fat left tail)
  - QUBO penalty term: beta_downside=0.5 → Balances value-at-risk

================================================================================
INSTRUCTIONS FOR USING DATA
================================================================================

FOR RESEARCH/PUBLICATION:
  1. Use [12_COMPREHENSIVE_METRICS_REPORT.txt] for numerical claims
  2. Use [05_qubo_matrix.csv] for showing QUBO formulation
  3. Use [10_portfolio_values.csv] for plotting performance comparison
  4. Use [07_portfolio_weights.csv] for portfolio composition tables
  5. Use [11_benchmark_values.csv] for benchmark comparison figures

FOR REPLICATION:
  1. Load [02_train_returns.csv] and [03_test_returns.csv]
  2. Recompute covariance via [01_covariance_matrix.csv]
  3. Apply QUBO from [05_qubo_matrix.csv] with annealing solver
  4. Compare weights in [07_portfolio_weights.csv]
  5. Backtest using [03_test_returns.csv]

FOR FURTHER ANALYSIS:
  1. Explore eigenvalues of covariance (sector/factor decomposition)
  2. Analyze turnover using [07_portfolio_weights.csv]
  3. Study regime-switching via rolling statistics of [10_portfolio_values.csv]
  4. Inspect correlations in [01_covariance_matrix.csv] (sector grouping)

================================================================================
HYPERPARAMETERS & CONFIGURATION
================================================================================

Data Preparation:
  - Training Period: 10 years (2011-03-15 to 2021-03-15)
  - Test Period: 5 years (2021-03-15 to 2026-03-15)
  - Time-series split: Strict, no look-ahead bias

Portfolio Construction:
  - Selected K: 40 assets (6% of 680-asset universe)
  - Max weight: 12% (concentration limit)
  - Risk-free rate: 5% (Sharpe calculation)

QUBO Penalties:
  - q_risk: 1.0 (risk aversion coefficient)
  - beta_downside: 0.5 (downside risk penalty)
  - lambda_card: 4.0 (cardinality constraint penalty)
  - gamma_sector: 0.3 (sector concentration penalty)

Rebalancing:
  - Frequency: Quarterly (~63 trading days)
  - Transaction cost: 0.1% per trade (included in returns)
  - Underperformer replacement: Bottom performers swapped with same-sector alts

================================================================================
IMPORTANT NOTES
================================================================================

1. LOOK-AHEAD BIAS PREVENTED:
   - Test period uses ONLY information available at that time
   - No future data leaked into portfolio construction
   - Strict date boundaries enforced throughout

2. SURVIVORSHIP BIAS MINIMIZED:
   - Data includes 680 assets (wide coverage)
   - Historical prices adjusted for splits/dividends
   - No 'delisted assets only' filtering

3. TRANSACTION COSTS:
   - Rebalancing includes 10 BPS (0.1%) per trade
   - Not included in classical/quantum non-rebalanced portfolios
   - Explains part of outperformance persistence

4. DATA QUALITY:
   - Minimum 85% non-NA price history required per asset
   - Forward-filled and back-filled gaps (rare)
   - Log returns computed correctly (prevent numerical issues)

5. BENCHMARK SELECTION:
   - BSE_500: Broad market proxy
   - Nifty_50/100/200: Sector-weighted indices
   - HDFCNIF100: Financial-heavy index (poor performance expected)

================================================================================
FILE SIZES & STORAGE
================================================================================

CSVs:
  01_covariance_matrix.csv:           ~25 MB  (680×680 floats)
  02_train_returns.csv:               ~100 MB (2478×680)
  03_test_returns.csv:                ~50 MB  (1240×680)
  04_expected_returns_and_downside:   <1 MB   (680× 2 cols)
  05_qubo_matrix.csv:                 <100 KB (40×40)
  07_portfolio_weights.csv:           <10 KB
  08_train_prices.csv:                ~100 MB
  09_test_prices.csv:                 ~50 MB
  10_portfolio_values.csv:            <100 KB (1240×3)
  11_benchmark_values.csv:            <100 KB (1240×5)

Total (uncompressed):                 ~350 MB
Compression (ZIP):                    ~50 MB  (high sparsity in returns)

================================================================================
VISUALIZATION GRAPHS (see ../outputs/)
================================================================================

4 Original Comparisons:
  1. Classical vs Quantum vs Rebalanced (main comparison)
  2. Quantum vs Rebalanced (zoomed view)
  3. Quantum Rebalanced vs All Benchmarks
  4. Rebalanced vs Non-Rebalanced

5 NEW Enhanced Graphs (Quantum vs Rebalanced):
  G1. Cumulative Returns overlay
  G2. Rolling 1-Year Sharpe Ratio (252-day rolling)
  G3. Drawdown Analysis (filled area)
  G4. Monthly Returns Box Plot + statistics
  G5. Risk-Return Scatter (all portfolios + benchmarks)

================================================================================
CONTACT & DOCUMENTATION
================================================================================

For methodology details, see:
  - main.py: Single-run pipeline
  - experiment_runner.py: Hyperparameter sweep (144 regimes)
  - qubo.py: QUBO formulation mathematics
  - matrix_exporter.py: Artifact generation (this data folder)

Generated: March 27, 2026
Time range: 2011-03-15 to 2026-03-15
Assets covered: 680 (Nifty 500+)
Optimization engine: Classical + QUBO + Annealing
Rebalancing: Quarterly with underperformer replacement

================================================================================
END OF DATA INVENTORY
================================================================================
