# Manual Matrix Validation (Step-by-Step)

This note shows how to manually compute one element from stock prices and match it with the saved matrix values.

I use the same files your pipeline generated:

- `data/prices_timeseries.csv`
- `data/returns_timeseries.csv`
- `data/returns_matrix.npy`
- `data/mean_returns.npy`
- `data/covariance_matrix.npy`
- `data/universe_metadata.json`

---

## 1) Index Mapping (Very Important)

From `data/universe_metadata.json`:

- Stock index 0 = TVSMOTOR
- Stock index 1 = PERSISTENT

Matrix dimensions:

- Returns rows (time points): `T = 693`
- Stocks (columns): `N = 29`

So:

- `returns_matrix[t, 0]` means TVSMOTOR daily return on row `t`
- `mean_returns[0]` means annualized mean return of TVSMOTOR
- `covariance_matrix[0, 1]` means annualized covariance between TVSMOTOR and PERSISTENT

---

## 2) Manual Check of One Returns-Matrix Element

Goal: verify one element of `returns_matrix.npy` from prices.

### Target element

- `returns_matrix[0, 0]` (first row, TVSMOTOR column)

In this dataset, first return row corresponds to:

- Previous date: `2021-03-12`
- Current date: `2021-03-15`

TVSMOTOR prices from `data/prices_timeseries.csv`:

- $P_{t-1} = 584.2$
- $P_t = 592.35$

Daily return formula:

$$
r_t = \frac{P_t}{P_{t-1}} - 1
$$

Substitute:

$$
r_t = \frac{592.35}{584.2} - 1 = 0.01395070181444713
$$

Comparison:

- Manual: `0.01395070181444713`
- `returns_timeseries.csv` (same date/stock): `0.0139507018144471`
- `returns_matrix.npy[0,0]`: `0.01395070181444713`

They match (difference only floating-point rounding).

---

## 3) Manual Check of One Mean-Return Element

Goal: verify `mean_returns.npy[0]` for TVSMOTOR.

Pipeline logic in `phase_01_data_preparation.py`:

- Daily mean return is computed from `returns_timeseries`
- Annualized mean return = daily mean * 252

Formula:

$$
\mu_{annual} = \left(\frac{1}{T}\sum_{t=1}^{T} r_t\right) \times 252
$$

Known values for TVSMOTOR:

- $T = 693$
- $\sum r_t = 1.3563355373174326$

Daily mean:

$$
\bar r = \frac{1.3563355373174326}{693} = 0.0019571941375431928
$$

Annualized:

$$
\mu_{annual} = 0.0019571941375431928 \times 252 = 0.49321292266088457
$$

Comparison:

- Manual: `0.49321292266088457`
- `mean_returns.npy[0]`: `0.49321292266088446`

Match confirmed.

---

## 4) Manual Check of One Covariance-Matrix Element

Goal: verify `covariance_matrix.npy[0,1]` (TVSMOTOR vs PERSISTENT).

Pipeline logic in `phase_01_data_preparation.py`:

- Daily covariance from returns data
- Annualized covariance = daily covariance * 252

Formula (sample covariance):

$$
\text{Cov}_{daily}(X,Y) = \frac{\sum_{t=1}^{T}(x_t-\bar x)(y_t-\bar y)}{T-1}
$$

Then annualize:

$$
\text{Cov}_{annual}(X,Y) = \text{Cov}_{daily}(X,Y) \times 252
$$

For TVSMOTOR ($X$) and PERSISTENT ($Y$):

- $T = 693$
- $\bar x = 0.0019571941375431928$
- $\bar y = 0.002297169449198578$
- $\sum (x_t-\bar x)(y_t-\bar y) = 0.03079535153877757$

Daily covariance:

$$
\text{Cov}_{daily} = \frac{0.03079535153877757}{692} = 0.00004450195309071903
$$

Annualized covariance:

$$
\text{Cov}_{annual} = 0.00004450195309071903 \times 252 = 0.011214492178861196
$$

Comparison:

- Manual: `0.011214492178861196`
- `covariance_matrix.npy[0,1]`: `0.011214492178861266`

Match confirmed.

---

## 5) What To Show Your Guide (Presentation Flow)

Use this exact sequence:

1. Show stock index mapping (`0 -> TVSMOTOR`, `1 -> PERSISTENT`).
2. Show one daily return from two prices (single-step arithmetic).
3. Show that this equals `returns_matrix[0,0]`.
4. Show annualized mean formula and substitution for index 0.
5. Show covariance formula and substitution for element `(0,1)`.
6. Conclude that matrix values are reproducible from raw prices/returns.

---

## 6) Quick Replication Checklist

- Confirm same stock order from `universe_metadata.json`.
- Confirm same date alignment as `returns_timeseries.csv` first row.
- Use sample covariance denominator `(T - 1)`.
- Use annualization factor `252`.

If all four are correct, your manual numbers should match the matrix values up to floating-point precision.

---

## 7) Manual QUBO Calculation and Verification

This section answers: how to substitute each QUBO parameter and verify with the saved QUBO matrix.

### 7.1 QUBO formula used in this project

From `phase_03_qubo_formulation.py`, the implemented objective is:

$$
\min\; q\,x^T C x - \mu^T x + \lambda(\mathbf{1}^T x - K)^2 + \beta\,\text{downside penalty} + \text{sector penalty}
$$

Implementation details matter:

1. Start with `Q += q * C`.
2. Add return term on diagonal: `Q[i,i] -= mu[i]`.
3. Add downside penalty on diagonal: `Q[i,i] += beta * downside_dev[i]`.
4. Add cardinality penalty:
	- diagonal: `Q[i,i] += lambda * (1 - 2K)`
	- upper triangle only (`i < j`): `Q[i,j] += 2 * lambda`
5. Add sector penalty to same-sector upper-triangle pairs (`i < j`): `Q[i,j] += sector_penalty`.
6. Final symmetrization used by code:

$$
Q_{final} = Q + Q^T - \text{diag}(\text{diag}(Q))
$$

Because of this, final off-diagonal terms include covariance twice, but cardinality/sector additions once.

---

### 7.2 Where each parameter comes from

- $q$ from `config/config.json -> portfolio.q` = `0.5`
- $K$ from `config/config.json -> portfolio.K` = `8`
- $\beta$ from `config/config.json -> portfolio_optimization.downside_risk_beta` = `0.3`
- $C$ from `data/covariance_matrix.npy`
- $\mu$ from `data/mean_returns.npy`
- downside deviations from `data/returns_matrix.npy` using negative-return std annualized

Adaptive $\lambda$ in code:

$$
\lambda = \text{clip}\left(10 \cdot \max(\text{avg}|C|,\text{avg}|\mu|,\max|\text{diag}(C)|) \cdot \frac{N}{K},\; 50,\; 500\right)
$$

For this run:

- $N = 29$
- $\text{avg}|C| = 0.02845404107539889$
- $\text{avg}|\mu| = 0.2941567689194151$
- $\max|\text{diag}(C)| = 0.3257508566684825$
- scale = `0.3257508566684825`
- raw $\lambda = 10 * 0.3257508566684825 * (29/8) = 11.81...$
- clipped $\lambda = 50.0$

Sector penalty in code:

$$
	ext{sector_penalty} = 0.1 \times \lambda = 5.0
$$

---

### 7.3 Manual calculation for one diagonal element (Q[0,0])

Index mapping from `quantum/qubo_metadata.json`:

- index 0 = TVSMOTOR

Values:

- $C_{00} = 0.08222729229032116$
- $\mu_0 = 0.49321292266088446$
- downside$_0 = 0.16649980365141562$
- $q = 0.5,\; \beta = 0.3,\; \lambda = 50,\; K = 8$

Diagonal formula after symmetrization (same as pre-sym diagonal):

$$
Q_{00} = qC_{00} - \mu_0 + \beta\cdot\text{downside}_0 + \lambda(1-2K)
$$

Substitute:

$$
Q_{00} = (0.5)(0.08222729229032116) - 0.49321292266088446 + (0.3)(0.16649980365141562) + 50(1-16)
$$

$$
Q_{00} = 0.04111364614516058 - 0.49321292266088446 + 0.04994994109542469 - 750
$$

$$
Q_{00} = -750.4021493354203
$$

Check with matrix:

- `quantum/qubo_matrix.npy[0,0] = -750.4021493354203` (exact match)

---

### 7.4 Manual calculation for one off-diagonal element (different sectors)

Use $(i,j)=(0,1)$:

- index 0 = TVSMOTOR (Automobile)
- index 1 = PERSISTENT (IT)
- Different sectors, so no sector penalty.

Values:

- $C_{01} = 0.011214492178861266$

Because of the exact code path + final symmetrization:

$$
Q_{01} = 2qC_{01} + 2\lambda
$$

Substitute:

$$
Q_{01} = 2(0.5)(0.011214492178861266) + 100
$$

$$
Q_{01} = 0.011214492178861266 + 100 = 100.01121449217885
$$

Check with matrix:

- `quantum/qubo_matrix.npy[0,1] = 100.01121449217885` (match)

---

### 7.5 Manual calculation for one off-diagonal element (same sector)

Use $(i,j)=(0,9)$:

- index 0 = TVSMOTOR (Automobile)
- index 9 = ESCORTS (Automobile)
- Same sector, so sector penalty applies.

Values:

- $C_{09} = 0.01693284627192812$
- sector penalty = `5.0`

Formula:

$$
Q_{09} = 2qC_{09} + 2\lambda + \text{sector_penalty}
$$

Substitute:

$$
Q_{09} = 2(0.5)(0.01693284627192812) + 100 + 5
$$

$$
Q_{09} = 0.01693284627192812 + 105 = 105.01693284627194
$$

Check with matrix:

- `quantum/qubo_matrix.npy[0,9] = 105.01693284627194` (match)

---

### 7.6 What to present to your guide

1. Show parameter source file for each symbol: $q, K, \beta, \lambda, C, \mu$.
2. Compute one diagonal element manually (recommended: `Q[0,0]`).
3. Compute one off-diagonal different-sector element (`Q[0,1]`).
4. Compute one off-diagonal same-sector element (`Q[0,9]`).
5. Compare all three with `quantum/qubo_matrix.npy` values.

If all three match, your QUBO construction is validated end-to-end.

---

## 8) How Downside Is Calculated (and what is stored in downside matrix)

Implementation is in `phase_03_qubo_formulation.py` (`calculate_downside_deviation`).

For each stock $i$:

1. Take daily return series $r_{t,i}$ from `returns_matrix`.
2. Keep only negative returns:

$$
\mathcal{N}_i = \{r_{t,i} \mid r_{t,i} < 0\}
$$

3. Compute downside deviation (annualized):

$$
	ext{downside}_i = \text{std}(\mathcal{N}_i) \cdot \sqrt{252}
$$

4. Edge case in code: if no negative returns exist, fallback to full-return std annualized.

How this enters QUBO diagonal:

$$
Q_{ii} \leftarrow Q_{ii} + \beta \cdot \text{downside}_i
$$

### Saved readable files in `data/`

- `qubo_input_downside_matrix.csv`:
	- Same shape as returns matrix.
	- Each cell is:

$$
	ext{downside\_matrix}_{t,i} =
\begin{cases}
r_{t,i}, & r_{t,i} < 0\\
0, & r_{t,i} \ge 0
\end{cases}
$$

- `qubo_input_downside_deviation.csv`:
	- Per-stock annualized downside deviation used in QUBO.

Other QUBO input CSVs exported to `data/`:

- `qubo_input_mean_returns.csv`
- `qubo_input_covariance_matrix.csv`
- `qubo_input_returns_matrix.csv`
- `qubo_input_stock_sector_map.csv`
- `qubo_input_parameters.csv`
