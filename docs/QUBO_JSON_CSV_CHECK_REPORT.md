# QUBO JSON and CSV Verification Report

## Scope checked

I checked and cross-validated these JSON files:

- config/config.json
- quantum/qubo_metadata.json
- data/universe_metadata.json
- config/nifty100_sectors.json

I checked and used these CSV inputs:

- data/qubo_input_mean_returns.csv
- data/qubo_input_covariance_matrix.csv
- data/qubo_input_returns_matrix.csv
- data/qubo_input_downside_matrix.csv
- data/qubo_input_downside_deviation.csv
- data/qubo_input_parameters_new.csv (current run)
- data/qubo_input_stock_sector_map_new.csv (current run)

And verified against:

- data/qubo_matrix.csv (exported from quantum/qubo_matrix.npy)

## Important note about _new files

Your older files were locked in one run, so two canonical names remain stale for 29-stock output:

- data/qubo_input_parameters.csv -> stale (N_variables = 29)
- data/qubo_input_stock_sector_map.csv -> stale (29 rows)

Current valid files from the 100-stock run are:

- data/qubo_input_parameters_new.csv
- data/qubo_input_stock_sector_map_new.csv

## JSON consistency checks (100-stock run)

- K from config/config.json = 8
- target_K from quantum/qubo_metadata.json = 8
- q from config/config.json = 0.5
- q_parameter from quantum/qubo_metadata.json = 0.5
- n_variables from quantum/qubo_metadata.json = 100
- len(stocks) from data/universe_metadata.json = 100

These match for the current run.

## Shape checks

- mean returns CSV: 100 rows
- covariance CSV: 100 x 100
- returns matrix CSV: 693 x 100
- downside matrix CSV: 693 x 100

## How downside is computed (exact implementation)

For stock i, with daily returns r[t, i]:

1. Keep only negative returns:

$$
\mathcal{N}_i = \{r_{t,i} \mid r_{t,i} < 0\}
$$

2. Compute annualized downside deviation:

$$
\text{downside}_i = \text{std}(\mathcal{N}_i) \cdot \sqrt{252}
$$

3. If no negative returns exist, code uses full-return std annualized.

Downside matrix validation:

- all non-negative returns became 0 in downside matrix
- all negative returns match original returns exactly

## QUBO formula used in code

The matrix is built in this order:

1. Risk term:

$$
Q \leftarrow Q + qC
$$

2. Return term (diagonal):

$$
Q_{ii} \leftarrow Q_{ii} - \mu_i
$$

3. Downside penalty (diagonal):

$$
Q_{ii} \leftarrow Q_{ii} + \beta \cdot \text{downside}_i
$$

4. Cardinality penalty (expanded):

- diagonal:

$$
Q_{ii} \leftarrow Q_{ii} + \lambda(1-2K)
$$

- upper triangle only, i < j:

$$
Q_{ij} \leftarrow Q_{ij} + 2\lambda
$$

5. Sector penalty (upper triangle only, same sector):

$$
Q_{ij} \leftarrow Q_{ij} + 0.1\lambda
$$

6. Symmetrization:

$$
Q_{final} = Q + Q^T - \text{diag}(\text{diag}(Q))
$$

## Parameter substitution from JSON/CSV (current run)

- N = 100
- K = 8
- q = 0.5
- beta = 0.3
- C from data/qubo_input_covariance_matrix.csv
- mu from data/qubo_input_mean_returns.csv
- downside from data/qubo_input_returns_matrix.csv

Adaptive lambda:

$$
\lambda = \text{clip}\left(10\cdot\max(\text{avg}|C|,\text{avg}|\mu|,\max|\text{diag}(C)|)\cdot\frac{N}{K}, 50, 500\right)
$$

For this run:

- lambda = 61.73346648500373
- sector_penalty = 6.173346648500374

## Full-matrix verification result

I rebuilt Q from JSON + CSV inputs and compared element-wise with quantum/qubo_matrix.npy.

- max absolute difference = 2.842170943040401e-14
- mean absolute difference = 4.5474735088646414e-17

This is numerical floating-point noise only, so values match.

## Sample manual element checks

Examples from the 100-stock matrix:

- Q[0,0] TVSMOTOR:
  - rebuilt = -926.4041466104762
  - matrix  = -926.4041466104762

- Q[0,1] TVSMOTOR,PERSISTENT:
  - rebuilt = 123.47814746218631
  - matrix  = 123.47814746218631

- Q[0,9] TVSMOTOR,LT:
  - rebuilt = 123.4869081411587
  - matrix  = 123.4869081411587

## How to manually calculate QUBO from input JSON/CSV

1. Read q, K, beta from config/config.json.
2. Read stock order from quantum/qubo_metadata.json.
3. Load:
   - mu from data/qubo_input_mean_returns.csv
   - C from data/qubo_input_covariance_matrix.csv
   - returns from data/qubo_input_returns_matrix.csv
   - sector map from data/qubo_input_stock_sector_map_new.csv
4. Compute downside_i for each stock from negative returns only.
5. Compute lambda using the adaptive formula.
6. Build Q using the exact 6-step order above.
7. Compare against data/qubo_matrix.csv (or quantum/qubo_matrix.npy).

If your stock order and formulas are exactly the same, the matrix matches up to floating-point tolerance.

## SLSQP and Weight Allocation Verification

I also verified the SLSQP weight optimization and final portfolio allocation calculations.

### Files used

- portfolios/optimized_weights.json
- data/mean_returns.npy
- data/covariance_matrix.npy
- data/universe_metadata.json
- config/config.json

And I exported a readable contribution table:

- data/slsqp_weight_allocation_verification.csv

### SLSQP objective and constraints (from code)

Source: quantum/weight_optimizer.py (function optimize_sharpe_slsqp)

The optimizer solves:

$$
\min_w \; -\frac{w^T\mu - r_f}{\sqrt{w^T\Sigma w}}
$$

subject to:

$$
\sum_i w_i = 1
$$

$$
	ext{min\_weight} \le w_i \le \text{max\_weight}
$$

For your run:

- min_weight = 0.0
- max_weight = 0.4
- risk_free_rate = 0.06

### Inputs for the saved optimized portfolio

From portfolios/optimized_weights.json:

- selected stocks = 8
- weights (w) =
  - TVSMOTOR: 0.27355257289053514
  - PERSISTENT: 0.24493310407632066
  - TRENT: 0.18850401044415827
  - ADANIPOWER: 0.12613913097282453
  - PRESTIGE: 0.16687118161616124
  - TATAPOWER: 0.0
  - WESTLIFE: 0.0
  - HCLTECH: ~0.0

### Manual allocation checks

1. Weight sum:

$$
\sum_i w_i = 0.9999999999999999 \approx 1
$$

2. Bounds:

- min weight found = 0.0
- max weight found = 0.27355257289053514
- both satisfy [0.0, 0.4]

3. No-short condition:

- all weights >= 0 is True

### Manual portfolio metric calculations

Let $\mu$ be annual expected return vector and $\Sigma$ annual covariance matrix for the same 8 stocks in the same order.

1. Portfolio return:

$$
R_p = w^T\mu = 0.5775979034271119
$$

2. Portfolio variance:

$$
\sigma_p^2 = w^T\Sigma w = 0.045266121600989584
$$

3. Portfolio volatility:

$$
\sigma_p = \sqrt{\sigma_p^2} = 0.21275836435024026
$$

4. Sharpe ratio:

$$
	ext{Sharpe} = \frac{R_p - r_f}{\sigma_p}
= \frac{0.5775979034271119 - 0.06}{0.21275836435024026}
= 2.4327969666802307
$$

### Match with saved optimization_info

From portfolios/optimized_weights.json optimization_info:

- portfolio_return = 0.5775979034271119
- portfolio_volatility = 0.2127583693821004
- sharpe_ratio = 2.4327969091431565

Differences (manual - saved):

- return diff = 0.0
- volatility diff = -5.031860150772616e-09
- sharpe diff = 5.753707421618515e-08

These are negligible floating-point differences, so the SLSQP and allocation calculations are verified.

### Example contribution calculations (manual)

Return contribution of each stock is $w_i\mu_i$.

Examples:

- TVSMOTOR:

$$
w\mu = 0.27355257289053514 \times 0.49321292266088446 = 0.13491966397674546
$$

- PERSISTENT:

$$
w\mu = 0.24493310407632066 \times 0.5788867011980421 = 0.14178851663293798
$$

Full per-stock contributions are in data/slsqp_weight_allocation_verification.csv.
