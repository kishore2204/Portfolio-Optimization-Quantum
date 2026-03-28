# Fixed Constants Configuration Guide

## Overview

This document explains the **fixed-constant configuration** for the QUBO portfolio optimization model. All constants are theoretically justified and **NOT tuned via hyperparameter search**.

---

## 📋 Configuration Summary

### Fixed Constants

| Parameter | Value | Purpose | Reference |
|-----------|-------|---------|-----------|
| **q** (Risk Weight) | 0.5 | Covariance scaling in QUBO | Literature standard |
| **β** (Downside Volatility) | 0.3 | Downside risk penalty | Moderate protection |
| **λ** (Cardinality) | Adaptive | Enforces exactly K assets | Computed from data |
| **γ** (Sector Penalty) | 0.1 × λ | Prevents concentration | Proportional to λ |

---

## 🔍 Constant Specifications

### 1. Risk Weight (q)

**File**: `config_constants.py` → `Q_RISK`

**Value**: `0.5`

**Purpose**: Controls covariance penalty in QUBO matrix

**Formula**:
$$Q^{cov}_{ij} = q \cdot \Sigma_{ij}$$

Where Σ is the annualized covariance matrix.

**Justification**:
- **q = 0.5** balances portfolio return vs. risk
- Too low (0.1-0.3): Ignores correlation, redundant assets
- Too high (1.0-2.0): Risk-averse, low returns
- **0.5** is literature standard for equity portfolios

**Impact**:
- Higher q → penalizes correlated pairs more → more diversified
- Lower q → allows correlated pairs → concentrated bets

---

### 2. Downside Volatility Weight (β)

**File**: `config_constants.py` → `BETA_DOWNSIDE`

**Value**: `0.3`

**Purpose**: Penalizes crash-prone stocks in QUBO diagonal

**Formula**:
$$Q^{dvol}_{ii} = \beta \cdot \sigma_{downside,i}$$

Where:
$$\sigma_{downside,i} = \sqrt{252} \cdot \sqrt{\frac{1}{T} \sum_{t: r_t < 0} r_t^2}$$

**Justification**:
- **β = 0.3** provides moderate downside protection
- Too low (0.1): Ignores downside risk → includes crash stocks
- Too high (0.7): Over-penalizes → excludes growth stocks
- **0.3** balances growth + protection

**Impact**:
- Complements standard variance (covariance term)
- Prevents selection of high-negative-skew stocks
- Trade-off: High return vs. downside safety

**Example**:
- Stock A: 20% annualized return, 5% downside volatility → q^dvol = 0.3 × 0.05 = 0.015
- Stock B: 15% annualized return, 10% downside volatility → q^dvol = 0.3 × 0.10 = 0.030
- Stock A preferred (lower downside penalty)

---

### 3. Cardinality Penalty (λ) - ADAPTIVE

**File**: `config_constants.py` → `compute_lambda_card()`

**Formula**:
$$\lambda = \text{clip}\left(10 \cdot scale \cdot \frac{N}{K}, 50, 500\right)$$

Where:
- **N** = total number of assets in universe
- **K** = target portfolio size
- **scale** = $\max(\text{mean}(|C|), \text{mean}(|\mu|), \max(\text{diag}(C)))$
- **C** = covariance matrix
- **μ** = returns vector

**Why Adaptive?**

Different datasets have different scales:
- **Small universe** (N=50, K=10): Different penalty strength than
- **Large universe** (N=500, K=25): Different economic meaning

Adaptive formula ensures:
- ✅ Constraint (K assets) always enforced
- ✅ Numerically stable across datasets
- ✅ Not tuned (formula is fixed)

**Example Calculation**:

```
Dataset: N=100 assets, K=20 selected

Compute scale:
  mean(|C|) = 0.015
  mean(|μ|) = 0.08
  max(diag(C)) = 0.25
  scale = max(0.015, 0.08, 0.25) = 0.25

Compute λ:
  λ = 10 × 0.25 × (100/20)
    = 10 × 0.25 × 5
    = 12.5

Apply clipping:
  λ_final = clip(12.5, 50, 500) = 50

Result: λ = 50
```

**Implementation**:

```python
from config_constants import compute_lambda_card

lambda_card = compute_lambda_card(mu=returns_mean, cov=covariance, K=25)
# Returns adaptive value based on data statistics
```

**Why Not Fixed?**

If we used fixed λ (like 5.0):
- Small universe: λ too weak → select 15 instead of 20
- Large universe: λ too strong → numerical issues

Adaptive formula solves this automatically.

---

### 4. Sector Penalty (γ)

**File**: `config_constants.py` → `compute_gamma_sector()`

**Formula**:
$$\gamma = 0.1 \cdot \lambda$$

**Purpose**: Prevents sector concentration

**Applied as**:
$$Q^{sector}_{ij} = \begin{cases}
\gamma & \text{if } i < j \text{ AND sector}(asset_i) = sector(asset_j) \\
0 & \text{otherwise}
\end{cases}$$

**Justification**:
- **Proportional to λ** ensures consistency
- **0.1 factor** prevents over-penalizing
- If λ = 50 → γ = 5.0
- If λ = 200 → γ = 20.0

**Impact**:
- Discourages putting multiple assets from same sector
- Acts as soft diversification (not hard limit)
- Combined with max_per_sector constraint (4 assets)

**Example**:
```
If λ = 50, then γ = 5.0

Pair (INFY, TCS) both in IT sector:
  Q[INFY, TCS] += 5.0  (penalty)

Pair (INFY, HDFC) in different sectors:
  Q[INFY, HDFC] += 0.0 (no penalty)

Effect: Slightly discourages IT concentration
```

---

## ⚙️ Implementation

### Import Configuration

```python
from config_constants import (
    Q_RISK,
    BETA_DOWNSIDE,
    compute_lambda_card,
    compute_gamma_sector,
    MAX_WEIGHT_PER_ASSET,
    RISK_FREE_RATE,
    TRADING_DAYS_PER_YEAR,
    # ... other constants
)
```

### Use in QUBO Building

```python
from qubo import build_qubo

qubo_model = build_qubo(
    mu=train_returns.mean(),
    cov=train_returns.cov(),
    downside=downside_vola,
    sector_map=sector_mapping,
    K=25,
    # Optional: override defaults
    # q_risk=0.5,              # Uses Q_RISK by default
    # beta_downside=0.3,       # Uses BETA_DOWNSIDE by default
    # lambda_card=None,        # Computed adaptively by default
    # gamma_sector=None        # Computed from lambda by default
)

# Access computed values
print(f"λ (adaptive) = {qubo_model.lambda_card}")
print(f"γ (adaptive) = {qubo_model.gamma_sector}")
```

### Run Full Pipeline

```bash
python main.py
```

This will:
1. Print configuration summary (via `print_constants_summary()`)
2. Load and preprocess data
3. Build QUBO using fixed constants
4. Run simulated annealing
5. Generate portfolio metrics and visualizations

---

## 📊 Expected Behavior

### What You Should See

```
======================================================================
QUBO PORTFOLIO OPTIMIZATION - FIXED CONSTANTS
======================================================================

[FIXED CONSTANTS]
  q_risk (Risk Weight)            = 0.5
  β_downside (Downside Risk)      = 0.3
  Trading Days per Year           = 252
  Lookback Window (days)          = 252
  Rebalance Cadence (days)        = 63

[ADAPTIVE CONSTANTS (Formula-Based)]
  λ (Cardinality Penalty)         = 10 × scale × (N/K), clipped to [50, 500]
  γ (Sector Penalty)              = 0.1 × λ

[OPTIMIZER PARAMETERS]
  Annealing T₀ (Initial)          = 2.0
  Annealing T₁ (Final)            = 0.005
  Annealing Steps                 = 6000
  Annealing Reads                 = 512

[PORTFOLIO CONSTRAINTS]
  Max Weight per Asset            = 12.0%
  Max Assets per Sector           = 4
  Risk-Free Rate                  = 5.0%
  Transaction Cost                = 0.10%

[EXPERIMENT SETUP]
  Training Period                 = 10 years
  Test Period                     = 5 years
  K Selection Ratio               = 6.0% of universe

======================================================================
```

### Verification Checks

After running, verify:

1. **Cardinality**: Portfolio has exactly K assets ✓
2. **Sector Balance**: No sector has >4 assets ✓
3. **Weights**: All weights ≤ 12% ✓
4. **Reproducibility**: Same results on re-run ✓

---

## 🎓 Explanation for Viva

### For Examiners

> **Q:** "Why fixed constants instead of hyperparameter tuning?"
>
> **A:** "We use theoretically justified fixed values:
> - **q=0.5**: Literature standard balancing risk and return
> - **β=0.3**: Moderate downside protection without over-penalizing
> - **λ**: Adaptive formula based on data scale, not tuned
> - **γ**: Proportional to λ, ensuring consistency
>
> This approach:
> 1. Ensures reproducibility (no random search)
> 2. Maintains scientific rigor (no overfitting to test data)
> 3. Remains interpretable (clear parameter meaning)
> 4. Scales across datasets (adaptive λ)"

### Key Points to Emphasize

1. ✅ **No Data Leakage**: Constants chosen before seeing test data
2. ✅ **Justifiable**: Each constant has economic interpretation
3. ✅ **Reproducible**: Exact same results on re-run
4. ✅ **Scalable**: Works for different universe sizes
5. ✅ **Transparent**: All values logged in run output

---

## 🔧 Modifying Constants (Not Recommended)

If you need to adjust a constant, do so in `config_constants.py`:

```python
# Change risk weight from 0.5 to 0.8
Q_RISK = 0.8

# Change downside penalty from 0.3 to 0.5
BETA_DOWNSIDE = 0.5

# Change clip range for lambda (currently [50, 500])
# Modify compute_lambda_card() function
```

**Important**: Document any changes with rationale!

---

## 📚 Related Files

| File | Purpose |
|------|---------|
| `config_constants.py` | Central configuration module |
| `qubo.py` | Uses constants in build_qubo() |
| `hybrid_optimizer.py` | Uses constants in HybridConfig |
| `rebalancing.py` | Uses constants in RebalanceConfig |
| `main.py` | Prints summary via print_constants_summary() |

---

## 🎯 Summary

**Philosophy**: Theoretically justified, reproducible, no overfitting

**Key Insight**: λ is adaptive (formula-based) but **NOT** tuned; same rationale applies to all constants—they have fixed meanings, not empirically optimized.

This ensures your model is **scientifically sound** and **defensible** in academic context.

