# QUBO Calculation for Horizons: 6M vs 12M Example

## Understanding Horizon-Specific Calculations

The **same QUBO matrix** (100×100) is used for all horizon scenarios (6M, 12M, 24M, 36M).

However, the **backtest window differs**:

| Horizon | Training Period | Test Period | Duration |
|---------|-----------------|------------|----------|
| **6M** | Last 60 months | Last 6 months | Quick feedback |
| **12M** | Last 60 months | Last 12 months | Longer hold |
| **24M** | Last 60 months | Last 24 months | Multi-year |
| **36M** | Last 60 months | Last 36 months | Long-term |

---

## Key Insight: QUBO is Data-Dependent

Although the **matrix formula** is the same, the **input values** (μ, C, downside) come from **historical data**.

### What Changes Between Horizons?

In the current system:
- **QUBO matrix**: Computed once from **60-month training on full dataset**
- **Stock selection**: Same for all horizons (top 8 from QUBO)
- **Backtest window**: Different - tests the portfolio over different holding periods

### What Could Change (Advanced Setup):

If you wanted **horizon-specific QUBO matrices**, you would:
1. Split data into 6M, 12M, 24M, 36M chunks
2. Compute μ, C, downside for **each horizon separately**
3. Build separate QUBO matrices
4. Solve each independently

---

## Example: 6-Month Horizon Calculation

### Step 1: Define Your Data Window

```
Today: March 2026
6M Horizon:
  - Training: 60 months back = Sept 2020 → Sept 2025
  - Testing: Oct 2025 → Mar 2026 (6 months)
```

### Step 2: Select Data for Horizon

From time series, extract daily returns for **training window**:

```python
# Example: TVSMOTOR returns for 6M horizon training
train_start = "2020-09-12"
train_end = "2025-09-11"

returns_6m = returns_timeseries.loc[train_start:train_end, 'TVSMOTOR']
print(f"6M training returns: {len(returns_6m)} days")  # ~1260 days = 5 years
```

### Step 3: Calculate 6M-Specific Inputs

**Mean Return (annualized):**
```
μ_6M = mean(daily_returns) × 252

For TVSMOTOR in 6M horizon:
μ_6M = 0.00196 × 252 = 0.4932  (same as overall if training window similar)
```

**Covariance (annualized):**
```
C_6M[i,j] = cov(returns_i, returns_j) × 252

For TVSMOTOR-PERSISTENT:
C_6M[0,1] = 0.0000444 × 252 = 0.0112  (same pattern)
```

**Downside Deviation (annualized):**
```
For TVSMOTOR:
negative_returns = [r for r in returns if r < 0]
downside_6M = std(negative_returns) × √252

For TVSMOTOR: 0.1665  (40% of stocks have downside ~0.16-0.17)
```

### Step 4: Build 6M QUBO Matrix (Same Process)

Once you have μ_6M, C_6M, downside_6M, follow the **exact same 6-step formula**:

```
Q_6M[0,0] = q×C_6M[0,0] - μ_6M[0] + β×downside_6M[0] + λ(1-2K)
          = 0.5×0.0822 - 0.4932 + 0.3×0.1665 + 61.73×(-15)
          = -926.40  (same result)

Q_6M[0,1] = q×C_6M[0,1] + 2×λ + sector_penalty
          = 0.5×0.0112 + 2×61.73 + 0 (different sectors)
          = 123.48  (same result)
```

### Step 5: 6M Backtest

Apply the optimized portfolio to **test period**:

```
Test window: Oct 2025 → Mar 2026 (6 months)

Daily returns of selected 8-stock portfolio:
r_6m_day = sum(w_i × r_i) for each day

Cumulative return (6M):
R_6m = Π(1 + r_daily) - 1

Example: If portfolio returned 5.1% over 6 months
Sharpe_6m = (R_6m - r_f) / σ_6m
         = (0.051 - 0.06/2) / σ
```

---

## Example: 12-Month Horizon Calculation

### Step 1: Define 12M Window

```
12M Horizon:
  - Training: 60 months back = Sept 2020 → Sept 2025  (same as 6M!)
  - Testing: Oct 2025 → Sep 2026 (12 months)
```

*In the current setup, training identical, testing window longer.*

### Step 2: Calculate 12M-Specific Inputs

Since training window is **same 60 months**, the **QUBO matrix identical**:

```
μ_12M = μ_6M (same training data)
C_12M = C_6M (same training data)
downside_12M = downside_6M (same training data)

Therefore:
Q_12M = Q_6M
```

### Step 3: Selected Portfolio is Identical

Both 6M and 12M select the **same 8 stocks** from the same QUBO:

```
Optimized weights for both:
- TVSMOTOR: 27.4%
- PERSISTENT: 24.5%
- TRENT: 18.9%
- ADANIPOWER: 12.6%
- PRESTIGE: 16.7%
- Others: 0%

(Same 8-stock portfolio for both horizons)
```

### Step 4: 12M Backtest (Longer Window)

Apply same portfolio to **longer test period**:

```
Test window: Oct 2025 → Sep 2026 (12 months, 252 trading days)

Daily returns of selected 8-stock portfolio:
r_12m_day = sum(w_i × r_i) for each day

Cumulative return (12M):
R_12m = Π(1 + r_daily) - 1

Example: If portfolio returned 18.3% over 12 months
Sharpe_12m = (R_12m - r_f) / σ_12m
          = (0.183 - 0.06) / σ
          = 0.123 / σ
```

### Key Difference: Longer Compounding

Even with **same portfolio**, the results differ:

| Metric | 6M Horizon | 12M Horizon | Reason |
|--------|-----------|------------|--------|
| Training | Sept 2020-2025 | Sept 2020-2025 | **Same** |
| Test Period | Oct 2025-Mar 2026 | Oct 2025-Sep 2026 | **6M vs 12M** |
| Market Conditions | Q4 2025, Q1 2026 | Includes Q4 2025-Q3 2026 | Longer exposure |
| Cumulative Return | 5.1% | 18.3% | More compounding |
| Days Held | ~126 | ~252 | Exactly 2x |
| Volatility | Lower | May vary | Depends on 2026 conditions |
| Sharpe Ratio | May be higher | May be lower | Risk-adjusted differs |

---

## Detailed Comparison Table: 6M vs 12M Example

### For TVSMOTOR (Stock 0)

#### 6M Horizon
```python
# Training data: Sept 2020 - Sept 2025
daily_returns_6m = [-0.002, 0.005, -0.001, ..., 0.003]  # ~1260 days
mean_return_6m = 0.00196 per day = 0.4932 annualized
std_dev_6m = 0.00661 per day = 0.1665 annualized (downside only)

# QUBO input
μ[0] = 0.4932
downside[0] = 0.1665

# Selected weight from SLSQP
w[0] = 0.2736  (27.36% allocation)

# Backtest: Oct 2025 - Mar 2026
test_returns_6m = [0.008, -0.002, 0.004, ...]  # ~126 days
portfolio_return_6m = 0.051  (5.1%)
portfolio_sharpe_6m = 1.23
```

#### 12M Horizon
```python
# Training data: SAME Sept 2020 - Sept 2025
daily_returns_12m = [-0.002, 0.005, -0.001, ..., 0.003]  # Same 1260 days
mean_return_12m = 0.4932  # SAME
std_dev_12m = 0.1665  # SAME

# QUBO input
μ[0] = 0.4932  (SAME)
downside[0] = 0.1665  (SAME)

# Selected weight from SLSQP
w[0] = 0.2736  (SAME 27.36% allocation)

# Backtest: Oct 2025 - Sep 2026
test_returns_12m = [0.008, -0.002, 0.004, ..., 0.012, ..., -0.001, ...]  # ~252 days
portfolio_return_12m = 0.183  (18.3%)  <- Different market from extended period
portfolio_sharpe_12m = 1.07  <- Lower Sharpe due to more volatility
```

---

## How to Calculate for Your Specific Horizon

### Quick Reference: 6M Horizon

```python
import pandas as pd
import numpy as np

# Load time series
returns = pd.read_csv('data/returns_timeseries.csv', index_col=0, parse_dates=True)

# Define 6M horizon
train_end = pd.Timestamp('2025-09-11')  # 60 months back from test start
test_start = pd.Timestamp('2025-09-12')
test_end = pd.Timestamp('2026-03-11')

# Extract training data
train_returns = returns.loc[:'2025-09-11']

# Calculate 6M-specific inputs
mu_6m = train_returns.mean() * 252  # Annualized
cov_6m = train_returns.cov() * 252  # Annualized

# Downside
negative_returns_6m = train_returns[train_returns < 0]
downside_6m = negative_returns_6m.std() * np.sqrt(252)

# Extract test data
test_returns = returns.loc['2025-09-12':'2026-03-11']

# Calculate portfolio returns
w = [0.2736, 0.2449, 0.1885, 0.1261, 0.1669, 0, 0, 0]  # 8 selected stocks
daily_portfolio_returns = (test_returns.iloc[:, :8] @ np.array(w)).values
cumulative_6m = np.prod(1 + daily_portfolio_returns) - 1

print(f"6M Training μ[TVSMOTOR]: {mu_6m[0]:.4f}")
print(f"6M Training downside[TVSMOTOR]: {downside_6m[0]:.4f}")
print(f"6M Cumulative Return: {cumulative_6m:.2%}")
```

### Quick Reference: 12M Horizon

```python
# Define 12M horizon
train_end = pd.Timestamp('2025-09-11')  # SAME training (60 months)
test_start = pd.Timestamp('2025-09-12')
test_end = pd.Timestamp('2026-09-11')  # 12M instead of 6M

# Calculate 12M inputs (SAME as 6M since training identical)
mu_12m = train_returns.mean() * 252  # Same
cov_12m = train_returns.cov() * 252  # Same
downside_12m = negative_returns_6m.std() * np.sqrt(252)  # Same

# Extract test data (longer window)
test_returns = returns.loc['2025-09-12':'2026-09-11']

# Calculate portfolio returns (same weights)
w = [0.2736, 0.2449, 0.1885, 0.1261, 0.1669, 0, 0, 0]
daily_portfolio_returns = (test_returns.iloc[:, :8] @ np.array(w)).values
cumulative_12m = np.prod(1 + daily_portfolio_returns) - 1

print(f"12M Training μ[TVSMOTOR]: {mu_12m[0]:.4f}")  # SAME as 6M
print(f"12M Cumulative Return: {cumulative_12m:.2%}")
print(f"Difference: {cumulative_12m - cumulative_6m:.2%}")
```

---

## Why Does Performance Differ?

### Same QUBO, Different Results

Even though the **QUBO matrix is identical**:
1. Different market conditions in test periods
2. 6M includes Q4 2025 + Q1 2026 only
3. 12M includes additional Q2-Q3 2026 data

### Example: If Q2-Q3 2026 was Bearish

```
6M (Oct 2025 - Mar 2026): +5.1%  (Before bear market)
12M (Oct 2025 - Sep 2026): +6.2% (Even with bear period, still up but lower annual return)
```

---

## Verification Steps for Horizons

### ✓ For 6M Calculation:
- [ ] Training data is Sept 2020 - Sept 2025 (60 months)
- [ ] Test data is Oct 2025 - Mar 2026 (6 months)
- [ ] μ, C, downside calculated from **training only**
- [ ] QUBO matrix built from these inputs
- [ ] Portfolio backtest applied to **test only**
- [ ] Results match unified_train_test_compare.json["horizon_results"]["Horizon_6M"]

### ✓ For 12M Calculation:
- [ ] Training data is **SAME** Sept 2020 - Sept 2025
- [ ] Test data is Oct 2025 - Sep 2026 (12 months)
- [ ] QUBO matrix **SAME** as 6M (same training data)
- [ ] Portfolio weights **SAME** as 6M
- [ ] Backtest cumulative return typically higher (more days)
- [ ] Sharpe ratio may vary (risk-adjusted over longer period)

---

## Cross-Verify Against Report

Navigate to results/unified_train_test_compare.json:

```json
{
  "horizon_results": {
    "Horizon_6M": {
      "assets_in_universe": 109,
      "K_selected": 8,
      "methods": {
        "quantum": {
          "total_return_pct": 5.1,
          "sharpe_ratio": 1.23
        }
      },
      "winners": {
        "total_return": "Quantum"
      }
    },
    "Horizon_12M": {
      "assets_in_universe": 109,
      "K_selected": 8,
      "methods": {
        "quantum": {
          "total_return_pct": 18.3,
          "sharpe_ratio": 1.07
        }
      }
    }
  }
}
```

**Verify these match your manual calculation!**

---

## Key Takeaways for Horizon Learning

1. **QUBO matrix is data-dependent** - changes if you use different training windows
2. **In current system**, all horizons use **same QUBO** because same 60-month training
3. **Test periods differ** - 6M, 12M, 24M, 36M have different holding durations
4. **Portfolio selection identical** - same 8 stocks for all horizons
5. **Performance varies** - due to different market conditions in test windows
6. **Sharpe ratio is risk-adjusted** - may go down with longer horizon despite higher returns

---

## Advanced: Horizon-Specific QUBO (If You Want to Implement)

To build **separate QUBO for each horizon**:

```python
def build_qubo_for_horizon(horizon_days):
    """
    Build horizon-specific QUBO:
    - 6M = 126 days training + 126 days test
    - 12M = 252 days training + 252 days test  
    - 24M = 504 days training + 504 days test
    """
    
    # Extract training window
    train_window = returns_timeseries[-horizon_days*2:-horizon_days]
    
    # Calculate horizon-specific inputs
    mu = train_window.mean() * 252
    cov = train_window.cov() * 252
    downside = compute_downside(train_window)
    
    # Build QUBO (same 6-step process)
    Q = build_qubo_matrix(mu, cov, downside, params)
    
    return Q, mu, cov, downside

# Compare matrices
Q_6m = build_qubo_for_horizon(126)[0]
Q_12m = build_qubo_for_horizon(252)[0]

print(f"6M Q[0,0]: {Q_6m[0,0]:.4f}")
print(f"12M Q[0,0]: {Q_12m[0,0]:.4f}")
print(f"Difference: {abs(Q_6m[0,0] - Q_12m[0,0]):.6f}")

# If different, stocks selected may differ!
```

This advanced approach gives **horizon-specific portfolios** - potentially better risk-adjusted returns.

---

## Summary Table

| Aspect | Current System | Advanced System |
|--------|---|---|
| **Training** | 60-month for all horizons | Window-specific |
| **QUBO** | 1 matrix (100×100) | 4 matrices (1 per horizon) |
| **Portfolio** | Same 8-stock mix | Potentially different per horizon |
| **Backtest** | 6M, 12M, 24M, 36M windows | Adjusted windows |
| **Complexity** | Simpler | More computing |
| **Robustness** | May benefit from longer training | May overfit to short windows |

---

Use this guide to understand **exactly how QUBO changes (or stays the same) across horizons** and how to calculate it yourself!
