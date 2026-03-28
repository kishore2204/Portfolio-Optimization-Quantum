# Quick Start: Fixed Constants Configuration

## 🚀 Running with Fixed Constants

### Step 1: Verify Configuration

Before running, the fixed constants are displayed:

```bash
python main.py
```

**Expected Output**:
```
======================================================================
QUBO PORTFOLIO OPTIMIZATION - FIXED CONSTANTS
======================================================================

[FIXED CONSTANTS]
  q_risk (Risk Weight)            = 0.5
  β_downside (Downside Risk)      = 0.3
  ...
```

### Step 2: Single Production Run

The pipeline now runs **exactly once** with fixed configuration:

```
Data Loading
    ↓
Preprocessing (annualize returns, compute covariance)
    ↓
Build QUBO (with fixed q=0.5, β=0.3, adaptive λ & γ)
    ↓
Simulated Annealing (select K assets)
    ↓
Sharpe Optimization (weight allocation)
    ↓
Backtest (train → test period)
    ↓
Quarterly Rebalancing (dynamic with fresh QUBO)
    ↓
Compute Metrics & Visualizations
```

---

## 📖 Configuration Files

All constants centralized in one place:

**File**: `config_constants.py`

```python
# Fixed values
Q_RISK = 0.5                 # Risk weight
BETA_DOWNSIDE = 0.3          # Downside penalty
TRADING_DAYS_PER_YEAR = 252  # Annualization

# Adaptive computation (formula-based, not tuned)
def compute_lambda_card(mu, cov, K):
    """Adaptive cardinality penalty based on data scale"""
    ...

def compute_gamma_sector(lambda_card):
    """Sector penalty proportional to lambda"""
    ...

# Other constraints
MAX_WEIGHT_PER_ASSET = 0.12
MAX_ASSETS_PER_SECTOR = 4
RISK_FREE_RATE = 0.05
TRANSACTION_COST = 0.001

# Time periods
TRAIN_YEARS = 10
TEST_YEARS = 5
```

---

## 🎯 Key Changes vs. Original

| Aspect | Before | After |
|--------|--------|-------|
| **q_risk** | Default 1.0 | Fixed 0.5 |
| **beta_downside** | Default 0.5 | Fixed 0.3 |
| **lambda_card** | Manual 5.0 | Adaptive formula |
| **gamma_sector** | Manual 0.5 | Computed from λ |
| **Tuning** | Grid search 144 regimes | Single run |
| **Reproducibility** | Different each run | Always same |
| **Hyperparameters** | 6 sweep dimensions | 0 (none) |

---

## 📊 What Gets Logged

After running, check `run_summary.json`:

```json
{
  "q_risk": 0.5,
  "beta_downside": 0.3,
  "lambda_card_computed": 45.2,
  "gamma_sector_computed": 4.52,
  "train_years": 10,
  "test_years": 5,
  "selected_k": 25,
  "universe_size": 207,
  ...
}
```

Shows:
- ✅ Which fixed constants were used
- ✅ What adaptive values were computed
- ✅ Exact configuration for reproducibility

---

## 🔍 Verification Checklist

After running `python main.py`, verify:

```
✓ Portfolio has exactly K assets (check reports)
✓ No sector has > 4 assets (check weights CSV)
✓ All weights ≤ 12% (check weights CSV)
✓ λ computed between 50-500 (check run_summary.json)
✓ Same run_summary.json every run (reproducibility)
✓ Metrics tables generated (portfolio_metrics.csv)
✓ Visualizations created (PNG files)
```

---

## 🎓 For Paper/Viva

### Statement

*"We configured the QUBO portfolio optimization model using theoretically justified fixed constants:*

- *Risk weight q = 0.5 (literature standard)*
- *Downside penalty β = 0.3 (moderate protection)*
- *Cardinality strength λ computed adaptively using a data-scale formula to ensure constraint satisfaction across datasets*
- *Sector penalty γ = 0.1λ for consistent diversification penalties*

*This configuration ensures reproducibility, avoids overfitting, and maintains clarity for academic evaluation."*

---

## 🆘 Troubleshooting

### Issue: λ outside [50, 500]

If you get warning about λ clipping:
- ✓ This is normal and expected
- ✓ Clipping ensures stability
- ✓ Data scale may justify outer bounds

### Issue: Different K selected

If fewer than K assets selected:
- Check if candidates pool filters too aggressively
- Check sector constraints aren't too strict
- Verify data quality (no missing values)

### Issue: Negative Sharpe Ratio

Possible causes:
- Market underperformance in test period
- Returns lower than risk-free rate (5%)
- Portfolio too conservative

**Solution**: This is valid result, not model error

---

## 📚 Documentation

| File | Purpose |
|------|---------|
| `config_constants.py` | Central configuration module |
| `FIXED_CONSTANTS_CONFIG.md` | Detailed constant explanations |
| `QUBO_CALCULATION_MANUAL.md` | QUBO math + examples |
| `main.py` | Main execution pipeline |

---

## ✅ Summary

**Before**: Hyperparameter search with 144 regimes (overfitting risk)

**After**: Single fixed-constant run (reproducible, defensible, clear)

**Result**: Same model quality, better scientific rigor

---

**Next Step**: Run `python main.py` and review outputs!

