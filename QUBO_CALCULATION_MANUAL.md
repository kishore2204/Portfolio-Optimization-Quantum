# QUBO Matrix Calculation Manual
## Step-by-Step Guide with Complete Formulas and Explanations

---

## Table of Contents
1. [Overview & Purpose](#overview--purpose)
2. [Input Data Preparation](#input-data-preparation)
3. [QUBO Matrix Construction](#qubo-matrix-construction)
4. [Mathematical Formulas](#mathematical-formulas)
5. [Detailed Step-by-Step Calculation](#detailed-step-by-step-calculation)
6. [Example Calculation](#example-calculation-with-real-data)
7. [Energy Evaluation](#energy-evaluation)

---

## Overview & Purpose

### What is QUBO?
**QUBO** = **Quadratic Unconstrained Binary Optimization**

A QUBO model is represented by a matrix **Q** of size **n × n**, where:
- **n** = number of assets/variables
- **Q[i,j]** = coefficients in the optimization problem
- Goal: Find binary solution **x** ∈ {0,1}^n that **minimizes** `x^T Q x`

### Portfolio Optimization Context
In this project, the QUBO matrix is used to:
- **Select exactly K assets** from n available assets
- **Maximize expected returns** and **minimize downside volatility**
- **Respect sector concentration limits** (diversity)
- Solve via **simulated annealing** (quantum-inspired optimization)

---

## Input Data Preparation

### Where do the inputs come from?

#### **Step 0: Data Processing Pipeline**

```
Raw Price Data
    ↓
Clean Prices (preprocessing.py → clean_prices)
    ↓
Calculate Log Returns (preprocessing.py → log_returns)
    ↓
Annualized Statistics (preprocessing.py → annualize_stats)
    ↓
Extract: μ (returns), Σ (covariance), σ_downside (downside volatility)
    ↓
QUBO Builder (qubo.py → build_qubo)
```

### **Input 1: Expected Returns Vector μ (mu)**

**File Location**: Computed in `preprocessing.py` → `annualize_stats()`

**Calculation**:
```
μ_i = mean(returns_i) × 252
```

Where:
- `returns_i` = log returns of asset i from training data
- `252` = number of trading days per year (annualization factor)

**Example**:
- If asset "HDFCBANK" has average daily log return = 0.0005
- Then: μ_HDFCBANK = 0.0005 × 252 = **0.126 (12.6% annualized)**

**Data Structure**: `pd.Series` with index = asset names

```
        Asset      μ (annualized return)
        ───────────────────────────────
        HDFCBANK   0.126
        INFY       0.082
        TCS        0.095
        RELIANCE   0.071
```

---

### **Input 2: Covariance Matrix Σ (Sigma)**

**File Location**: Computed in `preprocessing.py` → `annualize_stats()`

**Calculation**:
```
Σ = (daily_returns.cov()) × 252
```

Where:
- `returns.cov()` = Pearson covariance of daily log returns
- Diagonal elements Σ[i,i] = variance of asset i
- Off-diagonal Σ[i,j] = covariance between assets i and j

**Mathematical Formula**:
```
Σ[i,j] = 252 × E[(r_i - μ_{daily,i})(r_j - μ_{daily,j})]
```

**Example Covariance Matrix** (4 assets):
```
          HDFC      INFY      TCS       RELIANCE
HDFC      0.0456   0.0084    0.0091    0.0125
INFY      0.0084   0.0298    0.0067    0.0042
TCS       0.0091   0.0067    0.0356    0.0068
RELIANCE  0.0125   0.0042    0.0068    0.0512
```

**Key Properties**:
- Symmetric: Σ[i,j] = Σ[j,i]
- Positive semi-definite (all eigenvalues ≥ 0)
- Diagonal = variance (always > 0)
- Off-diagonal = covariance (can be positive or negative)

**Data Structure**: `pd.DataFrame` with shape (n, n)

---

### **Input 3: Downside Volatility Vector σ_downside**

**File Location**: Computed in `preprocessing.py` → `annualize_stats()`

**Calculation**:
```
σ_downside_i = √252 × √(mean(min(r_i, 0)²))
```

Where:
- `r_i` = daily log returns of asset i
- `min(r_i, 0)` = take only **negative** returns (downward movements)
- Square and average them
- Take square root for volatility scale

**Alternative Formula**:
```
σ_downside_i = √252 × √(
    (1/T) × Σ_{t=1}^T max(0, -r_{i,t})²
)
```

**Example**:
```
Asset      σ_downside (annualized)
───────────────────────────────────
HDFCBANK   0.0892
INFY       0.0756
TCS        0.0814
RELIANCE   0.1043
```

**Why Downside Volatility?**
- Investors care more about **downside risk** (losses) than upside
- Standard deviation treats up and down movements equally
- Downside volatility only penalizes negative returns

**Data Structure**: `pd.Series` with index = asset names

---

### **Input 4: Sector Mapping Dictionary**

**File Location**: Loaded in `data_loader.py` → `_load_sector_map()`

**Structure**:
```python
sector_map = {
    "HDFCBANK": "Finance",
    "ICICIBANK": "Finance",
    "INFY": "IT",
    "TCS": "IT",
    "RELIANCE": "Oil & Gas",
    "MARUTI": "Automobile"
}
```

**Purpose**: Track which assets belong to which sector for concentration penalties

**Data Structure**: `Dict[str, str]` (asset_name → sector_name)

---

### **Input 5: Configuration Parameters**

These are **knobs** you can tune:

```python
@dataclass
class HybridConfig:
    K: int = 25                    # Target number of assets to select
    q_risk: float = 1.0            # Covariance weight
    beta_downside: float = 0.5     # Downside volatility penalty weight
    lambda_card: float = 5.0       # Cardinality constraint strength
    gamma_sector: float = 0.5      # Sector concentration penalty
    max_per_sector: int = 4        # Max assets per sector
```

---

## QUBO Matrix Construction

### **Mathematical Definition**

The QUBO matrix **Q** is an **n × n** symmetric matrix where the optimization objective is:

$$\text{minimize: } E(x) = x^T Q x = \sum_{i=0}^{n-1} \sum_{j=0}^{n-1} Q_{ij} x_i x_j$$

Subject to:
- $x_i \in \{0, 1\}$ for all i (binary: asset selected or not)

### **Expanded Form**:

$$E(x) = \sum_{i=0}^{n-1} Q_{ii} x_i^2 + \sum_{i=0}^{n-1} \sum_{j=i+1}^{n-1} 2 Q_{ij} x_i x_j$$

Since $x_i^2 = x_i$ when $x_i \in \{0,1\}$, we can simplify to:

$$E(x) = \sum_{i=0}^{n-1} Q_{ii} x_i + \sum_{i=0}^{n-1} \sum_{j=i+1}^{n-1} 2 Q_{ij} x_i x_j$$

---

## Mathematical Formulas

### **Complete QUBO Energy Function**

The QUBO matrix is decomposed into **5 distinct components**:

$$Q_{ij} = Q^{cov}_{ij} + Q^{ret}_{ij} + Q^{dvol}_{ij} + Q^{card}_{ij} + Q^{sect}_{ij}$$

Let me define each component:

---

### **Component 1: Covariance (Risk) Term - $Q^{cov}$**

**Formula**:
$$Q^{cov}_{ij} = q\_risk \times \Sigma_{ij}$$

Where:
- $\Sigma_{ij}$ = annualized covariance matrix element
- $q\_risk$ = risk weighting parameter (typically 1.0)

**Purpose**: Penalize portfolio variance (using more highly correlated assets costs more energy)

**Direction**: Positive values increase energy → discourage selection

**Matrix Form**:
```
Q^{cov} = q_risk × Σ

Example (q_risk = 1.0):
Q^{cov} = [[0.0456, 0.0084, 0.0091, 0.0125],
           [0.0084, 0.0298, 0.0067, 0.0042],
           [0.0091, 0.0067, 0.0356, 0.0068],
           [0.0125, 0.0042, 0.0068, 0.0512]]
```

**Key Insight**: 
- Only appears in **diagonal** and **all pairs** (both diagonal and off-diagonal)
- High covariance = high Q values = higher energy if those assets are both selected

---

### **Component 2: Return (Negative) Term - $Q^{ret}$**

**Formula**:
$$Q^{ret}_{ii} = -\mu_i \quad \text{(only on diagonal)}$$

Where:
- $\mu_i$ = expected annual return of asset i
- Negative sign because we want to **minimize energy** when **returns are high**

**Purpose**: Encourage selection of high-return assets

**Direction**: Negative values **decrease energy** → encourage selection

**Example (same 4 assets)**:
```
Q^{ret} = [[-0.126,  0,      0,      0],
           [0,      -0.082,  0,      0],
           [0,       0,     -0.095,  0],
           [0,       0,      0,     -0.071]]
```

**Key Insight**:
- Only appears on **diagonal** (i=j only)
- Linear preference for each individual asset
- Negative μ means: "selecting this asset REDUCES the total energy"

---

### **Component 3: Downside Volatility Term - $Q^{dvol}$**

**Formula**:
$$Q^{dvol}_{ii} = \beta\_downside \times \sigma\_downside_i \quad \text{(only on diagonal)}$$

Where:
- $\beta\_downside$ = downside volatility weight (typically 0.5)
- $\sigma\_downside_i$ = downside volatility of asset i

**Purpose**: Penalize selection of assets with high downside volatility (losses)

**Direction**: Positive values **increase energy** → discourage selecting risky assets

**Example**:
```
Q^{dvol} = [[0.5×0.0892,   0,            0,            0],
            [0,             0.5×0.0756,  0,            0],
            [0,             0,            0.5×0.0814,  0],
            [0,             0,            0,            0.5×0.1043]]
         = [[0.0446,   0,       0,       0],
            [0,        0.0378,  0,       0],
            [0,        0,       0.0407,  0],
            [0,        0,       0,       0.0522]]
```

**Key Insight**:
- Competes with **return term** (negative)
- Trade-off: High return vs. high downside risk
- Only on diagonal, complements return term

---

### **Component 4: Cardinality Constraint Term - $Q^{card}$**

**Formula (Expansion of $(∑_i x_i - K)^2$)**:

$$\begin{align}
Q^{card}_{ii} &= \lambda\_card × (1 - 2K) \\
Q^{card}_{ij} &= \lambda\_card \quad \text{(for all } i \neq j \text{)}
\end{align}$$

Where:
- $\lambda\_card$ = cardinality constraint strength (typically 4-5)
- $K$ = target number of assets to select

**Derivation** (why this formula?):

We want to enforce: $∑_{i=0}^{n-1} x_i = K$

Using Lagrange multiplier approach, we add penalty:
$$\lambda\_card × (∑_{i=0}^{n-1} x_i - K)^2$$

Expanding:
$$\begin{align}
(∑ x_i - K)^2 &= (∑ x_i)^2 - 2K(∑ x_i) + K^2 \\
&= ∑_i x_i^2 + ∑_{i≠j} x_i x_j - 2K∑_i x_i + K^2 \\
&= ∑_i x_i + ∑_{i<j} 2x_i x_j - 2K∑_i x_i + K^2 \quad \text{(since } x_i^2 = x_i \text{)}
\end{align}$$

Rearranging by coefficients:
- Coefficient of $x_i$: $1 - 2K$
- Coefficient of $x_i x_j$ (i ≠ j): $2 = 1 + 1$ from symmetric expansion

In Q matrix form (accounting for $x_i x_j = x_j x_i$):
- Diagonal: $\lambda\_card × (1 - 2K)$
- Off-diagonal: $\lambda\_card$ (both Q[i,j] and Q[j,i])

**Example** (K=2, λ=4.0, n=4):
```
Q^{card} = [[4×(1-2×2), 4,         4,         4],
            [4,         4×(1-4),  4,         4],
            [4,         4,        4×(1-4),  4],
            [4,         4,        4,        4×(1-4)]]
         = [[-12, 4,  4,  4],
            [4,  -12, 4,  4],
            [4,   4, -12, 4],
            [4,   4,  4, -12]]
```

**Key Insight**:
- Diagonal terms are **negative** (encourage 0s and 1s, discourage fractional values)
- Off-diagonal terms are **positive** (penalize multiple selections)
- Together they create a "just K" behavior: selecting exactly K assets minimizes energy

**Why $(∑ x_i - K)^2$ is effective**:
- If $∑ x_i = K$: contributes 0 to energy
- If $∑ x_i > K$: contributes positive energy cost
- If $∑ x_i < K$: contributes positive energy cost
- Forces toward exactly K selections

---

### **Component 5: Sector Concentration Term - $Q^{sect}$**

**Formula**:
$$Q^{sect}_{ij} = \begin{cases}
\gamma\_sector & \text{if } i < j \text{ AND sector}(asset_i) = sector(asset_j) \\
0 & \text{otherwise}
\end{cases}$$

Applied symmetrically: if $Q^{sect}_{ij} = \gamma\_sector$, then $Q^{sect}_{ji} = \gamma\_sector$

Where:
- $\gamma\_sector$ = sector concentration penalty weight (typically 0.3-0.5)
- $sector(asset)$ = sector mapping from data_loader

**Purpose**: Discourage putting multiple assets from the same sector together

**Example** (with sectors: HDFC→Finance, INFY→IT, TCS→IT, REL→Oil&Gas):
```
Detection:
- INFY (IT) and TCS (IT) → SAME SECTOR
- All others → different sectors

Q^{sect} = [[0,      0,           0,      0],
            [0,      0,      0.5,    0],      # INFY-TCS pair
            [0,   0.5,       0,      0],      # TCS-INFY pair  
            [0,      0,           0,      0]]
```

**Key Insight**:
- Only appears between assets in the **same sector**
- Positive values **increase energy** → discourage concentration
- Acts as diversity constraint without hard upper bounds

---

## Detailed Step-by-Step Calculation

### **Complete Algorithm**

```
Input:
  - mu: pd.Series of expected returns (length n)
  - cov: pd.DataFrame of covariance matrix (shape n×n)
  - downside: pd.Series of downside volatility (length n)
  - sector_map: Dict[str, str] mapping assets to sectors
  - K: int, target number of assets
  - q_risk: float, covariance weight (default 1.0)
  - beta_downside: float, downside penalty (default 0.5)
  - lambda_card: float, cardinality strength (default 5.0)
  - gamma_sector: float, sector penalty (default 0.5)

Output:
  - Q: np.ndarray of shape (n, n), the QUBO matrix
  - assets: List[str], asset names in order
```

---

### **Step 1: Extract Asset Names and Initialize**

```python
assets = list(mu.index)                    # ['HDFCBANK', 'INFY', 'TCS', 'RELIANCE']
n = len(assets)                            # n = 4

mu_v = mu.values                           # [0.126, 0.082, 0.095, 0.071]
cov_m = cov.loc[assets, assets].values    # Extract 4×4 covariance submatrix
down_v = downside.loc[assets].values      # [0.0892, 0.0756, 0.0814, 0.1043]
```

**Result**:
- `assets`: List of 4 asset names
- `n`: 4
- Vectors ready for matrix operations

---

### **Step 2: Initialize Q Matrix with Covariance Term**

```python
Q = q_risk * cov_m.copy()
```

This creates the base Q matrix as:
$$Q = q\_risk × \Sigma$$

**Example** (q_risk = 1.0):
```
Q = [[0.0456, 0.0084, 0.0091, 0.0125],
     [0.0084, 0.0298, 0.0067, 0.0042],
     [0.0091, 0.0067, 0.0356, 0.0068],
     [0.0125, 0.0042, 0.0068, 0.0512]]
```

**At this point**: Only risk component is active.

---

### **Step 3: Add Return and Downside Volatility Terms (Diagonal)**

```python
for i in range(n):
    Q[i, i] += -mu_v[i] + beta_downside * down_v[i]
```

This performs:
$$Q_{ii} := Q_{ii} - \mu_i + \beta\_downside × \sigma\_downside_i$$

**Calculation for each asset**:

```
Asset 0 (HDFCBANK):
  Q[0,0] = 0.0456 + (-0.126) + (0.5 × 0.0892)
         = 0.0456 - 0.126 + 0.0446
         = -0.0358

Asset 1 (INFY):
  Q[1,1] = 0.0298 + (-0.082) + (0.5 × 0.0756)
         = 0.0298 - 0.082 + 0.0378
         = -0.0144

Asset 2 (TCS):
  Q[2,2] = 0.0356 + (-0.095) + (0.5 × 0.0814)
         = 0.0356 - 0.095 + 0.0407
         = 0.0113

Asset 3 (RELIANCE):
  Q[3,3] = 0.0512 + (-0.071) + (0.5 × 0.1043)
         = 0.0512 - 0.071 + 0.0522
         = 0.0324
```

**Result Matrix after Step 3**:
```
Q = [[-0.0358,  0.0084,  0.0091,  0.0125],
     [ 0.0084, -0.0144,  0.0067,  0.0042],
     [ 0.0091,  0.0067,  0.0113,  0.0068],
     [ 0.0125,  0.0042,  0.0068,  0.0324]]
```

**Interpretation**:
- Negative diagonal values = assets worth selecting (positive μ - penalty)
- HDFCBANK has most negative value → highest net return preference
- TCS has positive value → after downside penalty, less attractive

---

### **Step 4: Add Cardinality Constraint Terms**

#### **Step 4a: Diagonal Terms**

```python
for i in range(n):
    Q[i, i] += lambda_card * (1.0 - 2.0 * K)
```

This adds:
$$Q_{ii} := Q_{ii} + \lambda\_card × (1 - 2K)$$

**Calculation** (λ_card = 5.0, K = 2):
```
For all i:
  Q[i,i] += 5.0 × (1 - 2×2)
          = 5.0 × (1 - 4)
          = 5.0 × (-3)
          = -15.0

Q[0,0] = -0.0358 + (-15.0) = -15.0358
Q[1,1] = -0.0144 + (-15.0) = -15.0144
Q[2,2] =  0.0113 + (-15.0) = -14.9887
Q[3,3] =  0.0324 + (-15.0) = -14.9676
```

#### **Step 4b: Off-Diagonal Terms**

```python
for i in range(n):
    for j in range(i + 1, n):
        Q[i, j] += lambda_card
        Q[j, i] += lambda_card
```

This adds:
$$Q_{ij} := Q_{ij} + \lambda\_card \quad \forall i < j$$

Applied to both upper and lower triangles (symmetric).

**Calculation** (λ_card = 5.0):
```
Q[0,1] = 0.0084 + 5.0 = 5.0084
Q[1,0] = 0.0084 + 5.0 = 5.0084
Q[0,2] = 0.0091 + 5.0 = 5.0091
Q[2,0] = 0.0091 + 5.0 = 5.0091
Q[0,3] = 0.0125 + 5.0 = 5.0125
Q[3,0] = 0.0125 + 5.0 = 5.0125
Q[1,2] = 0.0067 + 5.0 = 5.0067
Q[2,1] = 0.0067 + 5.0 = 5.0067
Q[1,3] = 0.0042 + 5.0 = 5.0042
Q[3,1] = 0.0042 + 5.0 = 5.0042
Q[2,3] = 0.0068 + 5.0 = 5.0068
Q[3,2] = 0.0068 + 5.0 = 5.0068
```

**Result Matrix after Step 4**:
```
Q = [[-15.0358,  5.0084,  5.0091,  5.0125],
     [  5.0084, -15.0144, 5.0067,  5.0042],
     [  5.0091,  5.0067, -14.9887, 5.0068],
     [  5.0125,  5.0042,  5.0068, -14.9676]]
```

---

### **Step 5: Add Sector Concentration Penalty**

```python
for i in range(n):
    si = sector_map.get(assets[i], "UNKNOWN")
    for j in range(i + 1, n):
        sj = sector_map.get(assets[j], "UNKNOWN")
        if si == sj:
            Q[i, j] += gamma_sector
            Q[j, i] += gamma_sector
```

This checks: if assets i and j are in **same sector**, add γ_sector to both Q[i,j] and Q[j,i].

**Sector Mapping (assumed)**:
```
sector_map = {
    'HDFCBANK': 'Finance',
    'INFY': 'IT',
    'TCS': 'IT',
    'RELIANCE': 'Oil & Gas'
}
```

**Sector Check**:
- HDFCBANK (Finance) vs INFY (IT) → Different → No change
- HDFCBANK (Finance) vs TCS (IT) → Different → No change
- HDFCBANK (Finance) vs RELIANCE (Oil&Gas) → Different → No change
- INFY (IT) vs TCS (IT) → **SAME** → Add γ_sector
- INFY (IT) vs RELIANCE (Oil&Gas) → Different → No change
- TCS (IT) vs RELIANCE (Oil&Gas) → Different → No change

**Calculation** (γ_sector = 0.5):
```
Q[1,2] = 5.0067 + 0.5 = 5.5067
Q[2,1] = 5.0067 + 0.5 = 5.5067
```

**Final Result Matrix after Step 5**:
```
Q = [[-15.0358,  5.0084,  5.0091,  5.0125],
     [  5.0084, -15.0144, 5.5067,  5.0042],
     [  5.0091,  5.5067, -14.9887, 5.0068],
     [  5.0125,  5.0042,  5.0068, -14.9676]]
```

**Interpretation**:
- Pair (INFY, TCS) has higher penalty (5.5067 vs 5.0067)
- Discourages selecting both INFY and TCS together
- All other pairs unaffected

---

## Example Calculation with Real Data

### **Full Step-by-Step Example**

Let's use the 4-asset example throughout. Here's the complete flow:

#### **Input Data Summary**

```
Assets:     ['HDFCBANK', 'INFY', 'TCS', 'RELIANCE']
    
μ (returns):        [0.126, 0.082, 0.095, 0.071]

Σ (covariance):
    [[0.0456, 0.0084, 0.0091, 0.0125],
     [0.0084, 0.0298, 0.0067, 0.0042],
     [0.0091, 0.0067, 0.0356, 0.0068],
     [0.0125, 0.0042, 0.0068, 0.0512]]

σ_downside:         [0.0892, 0.0756, 0.0814, 0.1043]

sector_map:         {'HDFCBANK': 'Finance', 'INFY': 'IT', 'TCS': 'IT', 'RELIANCE': 'Oil&Gas'}

Configuration:
    K = 2 (select 2 assets)
    q_risk = 1.0
    beta_downside = 0.5
    lambda_card = 5.0
    gamma_sector = 0.5
```

#### **Building Q Matrix Step by Step**

**Step 1: Start with Covariance**
```
Q_cov = 1.0 × Σ = Σ
(initialized above)
```

**Step 2: Add Returns and Downside Volatility**
```
Q_cov[0,0] += -0.126 + 0.5×0.0892 = -0.0358
Q_cov[1,1] += -0.082 + 0.5×0.0756 = -0.0144
Q_cov[2,2] += -0.095 + 0.5×0.0814 = 0.0113
Q_cov[3,3] += -0.071 + 0.5×0.1043 = 0.0324

Q = [[-0.0358,  0.0084,  0.0091,  0.0125],
     [ 0.0084, -0.0144,  0.0067,  0.0042],
     [ 0.0091,  0.0067,  0.0113,  0.0068],
     [ 0.0125,  0.0042,  0.0068,  0.0324]]
```

**Step 3: Add Cardinality Constraints**
```
Diagonal: Add 5.0 × (1 - 2×2) = -15.0 to all Q[i,i]

Q[0,0] = -0.0358 - 15.0 = -15.0358
Q[1,1] = -0.0144 - 15.0 = -15.0144
Q[2,2] =  0.0113 - 15.0 = -14.9887
Q[3,3] =  0.0324 - 15.0 = -14.9676

Off-diagonal: Add 5.0 to all Q[i,j] where i ≠ j

Q[0,1] = Q[1,0] = 0.0084 + 5.0 = 5.0084
Q[0,2] = Q[2,0] = 0.0091 + 5.0 = 5.0091
Q[0,3] = Q[3,0] = 0.0125 + 5.0 = 5.0125
Q[1,2] = Q[2,1] = 0.0067 + 5.0 = 5.0067
Q[1,3] = Q[3,1] = 0.0042 + 5.0 = 5.0042
Q[2,3] = Q[3,2] = 0.0068 + 5.0 = 5.0068

Q = [[-15.0358,  5.0084,  5.0091,  5.0125],
     [  5.0084, -15.0144, 5.0067,  5.0042],
     [  5.0091,  5.0067, -14.9887, 5.0068],
     [  5.0125,  5.0042,  5.0068, -14.9676]]
```

**Step 4: Add Sector Penalties**
```
Check pairs:
- (0,1): HDFCBANK (Finance) vs INFY (IT) → Different ✗
- (0,2): HDFCBANK (Finance) vs TCS (IT) → Different ✗
- (0,3): HDFCBANK (Finance) vs RELIANCE (Oil&Gas) → Different ✗
- (1,2): INFY (IT) vs TCS (IT) → SAME ✓ → Add 0.5

Q[1,2] = 5.0067 + 0.5 = 5.5067
Q[2,1] = 5.0067 + 0.5 = 5.5067

- (1,3): INFY (IT) vs RELIANCE (Oil&Gas) → Different ✗
- (2,3): TCS (IT) vs RELIANCE (Oil&Gas) → Different ✗

Final Q = [[-15.0358,  5.0084,  5.0091,  5.0125],
           [  5.0084, -15.0144, 5.5067,  5.0042],
           [  5.0091,  5.5067, -14.9887, 5.0068],
           [  5.0125,  5.0042,  5.0068, -14.9676]]
```

---

## Energy Evaluation

### **Computing Portfolio Energy**

Once the QUBO matrix Q is built, any candidate solution **x** has an **energy** value:

$$E(x) = x^T Q x$$

#### **Example Solutions**

##### **Solution 1: x = [1, 0, 0, 1]** (Select HDFCBANK and RELIANCE)

```
Q × x:
Q[0,:] × x = [-15.0358×1 + 5.0084×0 + 5.0091×0 + 5.0125×1]
            = [-15.0358 + 0 + 0 + 5.0125]
            = [-10.0233]

Q[1,:] × x = [5.0084×1 + (-15.0144)×0 + 5.5067×0 + 5.0042×1]
            = [5.0084 + 0 + 0 + 5.0042]
            = [10.0126]

Q[2,:] × x = [5.0091×1 + 5.5067×0 + (-14.9887)×0 + 5.0068×1]
            = [5.0091 + 0 + 0 + 5.0068]
            = [10.0159]

Q[3,:] × x = [5.0125×1 + 5.0042×0 + 5.0068×0 + (-14.9676)×1]
            = [5.0125 + 0 + 0 - 14.9676]
            = [-9.9551]

Qx = [-10.0233, 10.0126, 10.0159, -9.9551]^T

E([1,0,0,1]) = x^T × (Qx)
             = [1, 0, 0, 1] · [-10.0233, 10.0126, 10.0159, -9.9551]^T
             = 1×(-10.0233) + 0×10.0126 + 0×10.0159 + 1×(-9.9551)
             = -10.0233 - 9.9551
             = -19.9784
```

##### **Solution 2: x = [1, 1, 0, 0]** (Select HDFCBANK and INFY)

```
Q × x:
Q[0,:] × x = [-15.0358×1 + 5.0084×1 + 5.0091×0 + 5.0125×0]
            = [-15.0358 + 5.0084]
            = [-10.0274]

Q[1,:] × x = [5.0084×1 + (-15.0144)×1 + 5.5067×0 + 5.0042×0]
            = [5.0084 - 15.0144]
            = [-10.0060]

Q[2,:] × x = [5.0091×1 + 5.5067×1 + (-14.9887)×0 + 5.0068×0]
            = [5.0091 + 5.5067]
            = [10.5158]

Q[3,:] × x = [5.0125×1 + 5.0042×1 + 5.0068×0 + (-14.9676)×0]
            = [5.0125 + 5.0042]
            = [10.0167]

Qx = [-10.0274, -10.0060, 10.5158, 10.0167]^T

E([1,1,0,0]) = x^T × (Qx)
             = [1, 1, 0, 0] · [-10.0274, -10.0060, 10.5158, 10.0167]^T
             = 1×(-10.0274) + 1×(-10.0060) + 0 + 0
             = -20.0334
```

##### **Comparison**

```
x = [1, 0, 0, 1] (HDFCBANK + RELIANCE):  E = -19.9784
x = [1, 1, 0, 0] (HDFCBANK + INFY):      E = -20.0334 ← LOWER (Better!)
```

**Interpretation**:
- Solution [1,1,0,0] has **lower energy** = **preferred by optimization algorithm**
- INFY+HDFCBANK are better than HDFCBANK+RELIANCE
- Why? Despite RELIANCE having lower return, the covariance penalty is too high

##### **Solution 3: x = [1, 1, 1, 0]** (Select 3 assets - violates K=2)

```
Cardinality penalty kicks in:
Sum(x) = 3, but K = 2
Excess = 3 - 2 = 1

Penalty from (∑x - K)^2:
= (3 - 2)^2 = 1
Scaled by λ = 5.0
Total cardinality penalty = 5.0

This additional penalty makes this solution WORSE,
preventing selection of > K assets.
```

---

### **Why Energy Minimization Works**

The QUBO energy function cleverly encodes all constraints:

```
minimize E(x) = minimize [
    + Risk (covariance)           → Avoid highly correlated pairs
    - Returns (negative)          → Prefer high-return assets
    + Downside Penalty            → Avoid risky assets
    + Cardinality Penalty         → Force exactly K selections
    + Sector Penalty              → Avoid concentration in
]
```

The **simulated annealing algorithm** explores solutions and gradually reduces temperature, converging toward low-energy states that satisfy all constraints.

---

## Summary: Complete QUBO Construction

### **Final Formula**

The complete Q matrix is built as:

$$\begin{align}
Q_{ij} &= q\_risk \cdot \Sigma_{ij}   &\text{(Covariance)}\\ 
&\quad + \delta_{ij}(-\mu_i + \beta\_downside \cdot \sigma\_downside_i)   &\text{(Return + Downside)}\\ 
&\quad + \lambda\_card \cdot (1 - 2K) \cdot \delta_{ij}   &\text{(Cardinality diagonal)}\\ 
&\quad + \lambda\_card \cdot (1 - \delta_{ij})   &\text{(Cardinality off-diagonal)}\\ 
&\quad + \gamma\_sector \cdot \mathbb{1}[\text{same sector}](1 - \delta_{ij})   &\text{(Sector concentration)}
\end{align}$$

Where:
- $\delta_{ij}$ = Kronecker delta (1 if i=j, else 0)
- $\mathbb{1}[\cdot]$ = indicator function (1 if condition true, else 0)
- $\Sigma_{ij}$ = annualized covariance between assets i and j

### **Computational Complexity**

| Step | Operation | Complexity | Time |
|------|-----------|-----------|------|
| 1 | Initialize Q with covariance | O(n²) | ~0.1ms (n=100) |
| 2 | Add diagonal returns/downside | O(n) | <0.01ms |
| 3 | Add cardinality constraints | O(n²) | ~0.1ms |
| 4 | Add sector penalties | O(n²) | ~0.1ms |
| **Total** | **Build Q matrix** | **O(n²)** | **~0.3ms** |

For n=100 assets, Q is a 100×100 matrix built in milliseconds.

---

## Quick Reference

### **All Parameters and Their Roles**

```
Input Parameters:
├── μ: Expected returns (annualized)
│   └─ Determines return preference
├── Σ: Covariance matrix
│   └─ Encodes risk (volatility & correlation)
├── σ_downside: Downside volatility
│   └─ Penalizes loss volatility
├── sector_map: Asset → Sector mapping
│   └─ Identifies concentration pairs
└── K: Target number of assets
    └─ Enforced via cardinality constraint

Configuration Knobs:
├── q_risk: Covariance weight
│   └─ Higher = more risk-averse
├── beta_downside: Downside penalty
│   └─ Higher = penalize downside more
├── lambda_card: Cardinality strength
│   └─ Higher = stricter K constraint
└── gamma_sector: Sector penalty
    └─ Higher = stronger diversification
```

### **Energy Function Interpretation**

```
Low Energy States (preferred):
  ✓ Return ≥ risk adjustment
  ✓ Exactly K assets selected
  ✓ Low covariance between selected assets
  ✓ Diverse sectors

High Energy States (avoided):
  ✗ Low/negative returns
  ✗ Too many or too few assets
  ✗ Highly correlated assets
  ✗ Concentrated in one sector
```

---

## Appendix: Code Walkthrough

### **Where to Find in Source Code**

**File**: [qubo.py](../qubo.py)

**Function**: `build_qubo()`

**Key Lines**:
- Line 33: Covariance initialization
- Line 36-37: Return + Downside diagonal terms
- Line 39-42: Cardinality constraints
- Line 44-50: Sector concentration penalties

**Called by**:
- [hybrid_optimizer.py](../hybrid_optimizer.py) line 45 (quantum selection)
- [rebalancing.py](../rebalancing.py) line 112 (quarterly refresh)
- [main.py](../main.py) line 166 (export for analysis)
- [experiment_runner.py](../experiment_runner.py) (parameter sweep)

---

## End of Manual

This document provides complete step-by-step explanation of QUBO matrix construction in the portfolio optimization system. Each component is mathematically justified and practically explained with examples.

For implementation details, refer to the actual [qubo.py](../qubo.py) file.
For related concepts, see:
- [Simulated Annealing](annealing.py) - solves the QUBO
- [Preprocessing](preprocessing.py) - generates μ, Σ, σ_downside
- [Data Loader](data_loader.py) - provides sector_map
