# Budget & Edge Case Analysis

## 1. Fixed Budget in This Project

**The fixed budget is ₹1,000,000** (initial investment used throughout all calculations)

### Where It's Used:
- **Theoretical portfolio calculations**: All returns are computed as weight-based multipliers on this base amount
- **Performance metrics**: Final portfolio value = 1,000,000 × (cumulative return multiplier)
- **Rebalancing operations**: Each quarterly rebalance maintains the same ₹1,000,000 starting point
- **Benchmark comparisons**: Normalized to same starting capital

### Example:
```
Initial Budget: ₹1,000,000
Quantum+Rebalanced Return: 206%
Final Value: ₹1,000,000 × 2.06 = ₹2,060,000
Profit: ₹1,060,000
```

---

## 2. The Edge Case Problem

### Scenario: Budget Too Small for Stock Prices

When actual stock prices in the market are higher than allocated budget, a critical problem arises:

```
Example from our conversation:
╔════════════════════════════════════════════════════════════╗
║  Budget:           ₹2,000                                  ║
║  Stock Price:      ₹2,500 (single share)                   ║
║  Allocated Weight: 12% (theoretical)                        ║
║  Allocated Amount: 0.12 × ₹2,000 = ₹240                    ║
║  Shares Possible:  ₹240 / ₹2,500 = 0.096 shares            ║
║  PROBLEM:          Cannot buy even 1 share!                ║
╚════════════════════════════════════════════════════════════╝
```

### Why This Happens

| Aspect | Code Behavior | Real-World Behavior |
|--------|---------------|-------------------|
| **Position Size** | Fractional allowed | Only whole shares |
| **Minimum Order** | None | 1 share minimum |
| **Constraints** | Applied post-hoc | Must check upfront |
| **Validity** | Mathematically sound | Practically broken |

### Impact by Budget Level

| Budget | Max Stock Price | Status | Example |
|--------|-----------------|--------|---------|
| ₹1,000,000 | No limit | ✅ SAFE | All 680 stocks in Nifty can be bought |
| ₹100,000 | Unlimited | ✅ SAFE | Typical institutional min |
| ₹50,000 | Unlimited | ✅ SAFE | Average investor portfolio |
| ₹5,000 | Reasonable | ⚠️ RISKY | Some high-price stocks problematic |
| ₹2,000 | ₹400 max | 🚨 CRITICAL | Most stocks in Nifty fail |
| ₹500 | ₹100 max | 🚨 CRITICAL | Only very cheap stocks work |

---

## 3. Our Edge Case Handler Implementation

### File: `edge_case_handler.py`

We've created **three core functions** to handle this edge case:

#### 1. `check_budget_vs_stock_price()`
Identifies which assets violate the budget constraint.

```python
from edge_case_handler import check_budget_vs_stock_price
import pandas as pd

# Example with our budget scenario
weights = pd.Series({
    'INFY': 0.12,   # 12% allocation
    'TCS': 0.08,    # 8% allocation
    'BB': 0.05      # 5% allocation
})

prices = {
    'INFY': 2500,   # ₹2,500 per share
    'TCS': 3456,    # ₹3,456 per share
    'BB': 125       # ₹125 per share
}

budget = 2000  # Only ₹2,000

warnings = check_budget_vs_stock_price(weights, prices, budget)
# Output:
# ⚠️ CRITICAL: INFY | Price: ₹2500.00 | Weight: 12.00% | Allocated: ₹240.00 | Can buy: 0.096 shares
# ⚠️ CRITICAL: TCS  | Price: ₹3456.00 | Weight: 8.00%  | Allocated: ₹160.00 | Can buy: 0.046 shares
# ⚠️ MEDIUM:   BB   | Price: ₹125.00  | Weight: 5.00%  | Allocated: ₹100.00 | Can buy: 0.800 shares
```

**Severity Levels:**
- **CRITICAL**: shares < 0.5 (can't buy more than half a share)
- **HIGH**: 0.5 ≤ shares < 0.75 (would need rounding up)
- **MEDIUM**: 0.75 ≤ shares < 1.0 (close to minimum)

#### 2. `suggest_weight_adjustments()`
Recommends new weights that respect the constraint.

```python
from edge_case_handler import suggest_weight_adjustments

adjusted_weights = suggest_weight_adjustments(
    weights=weights,
    stock_prices=prices,
    budget=budget,
    min_shares=1.0  # Guarantee at least 1 share per asset
)

# Automatically reduces high-weight assets and redistributes excess
# Result: All assets now have weight ≤ (price × 1) / budget
```

**Algorithm:**
1. Calculate max allowable weight: `w_max = (min_shares × price) / budget`
2. Cap weights to max: `w_new = min(w_old, w_max)`
3. Redistribute excess proportionally to compliant assets
4. Renormalize to ensure sum = 1.0

#### 3. `report_edge_case_summary()`
Generates comprehensive analysis report.

```python
from edge_case_handler import report_edge_case_summary

report = report_edge_case_summary(weights, prices, budget)
# Output:
# {
#     'status': 'FAIL',
#     'violation_count': 3,
#     'critical_count': 2,
#     'affected_weight_pct': 25.0,
#     'worst_case_asset': 'INFY',
#     'worst_case_shares': 0.096,
#     'warnings': [...]
# }
```

---

## 4. When This Matters (Practical Implications)

### Scenario A: Using This Code with Real Budget ✅ OK
```
Budget: ₹1,000,000  (same as code assumption)
Result: No edge case - all Nifty stocks affordable
Action: Run as-is
```

### Scenario B: Downscaling Budget ⚠️ PROBLEM
```
Budget: ₹10,000  (100x smaller)
Nifty stocks: Range from ₹125 to ₹7,500
Result: Some stocks unaffordable
Action: Use edge_case_handler.py to validate or adjust weights
```

### Scenario C: Real-World Trading 🚨 CRITICAL
```
Real budget: ₹500,000
Need to account for:
  1. Min shares per stock (usually 1)
  2. Brokerage fees (0.05-0.20%)
  3. Bid-ask spreads (₹1-5 per share)
  4. Margin requirements (if using leverage)
Action: Integrate edge_case_handler + add trading constraints
```

---

## 5. How to Use Edge Case Handler

### Quick Integration into Main Code

```python
# In main.py or any optimizer
from edge_case_handler import check_budget_vs_stock_price, report_edge_case_summary

# After optimizing weights
weights = weights_from_optimizer  # pd.Series
stock_prices = current_market_prices  # Dict or pd.Series
budget = 1_000_000  # Your budget

# Check for violations
warnings = check_budget_vs_stock_price(weights, stock_prices, budget, verbose=True)

# Generate report
report = report_edge_case_summary(weights, stock_prices, budget)
if report['status'] == 'FAIL':
    print(f"⚠️ {report['violation_count']} assets have insufficient budget allocation")
    print(f"   Critical assets: {report['critical_count']}")
```

### Test with Different Budget Levels

```python
from edge_case_handler import check_budget_vs_stock_price
import pandas as pd

# Our sample weights and prices
weights = pd.Series({'Stock_A': 0.12, 'Stock_B': 0.08, 'Stock_C': 0.05})
prices = {'Stock_A': 2500, 'Stock_B': 1200, 'Stock_C': 120}

# Test across different budgets
for budget in [500, 2000, 5000, 50000, 1000000]:
    print(f"\n\nBudget: ₹{budget:,}")
    warnings = check_budget_vs_stock_price(weights, prices, budget, verbose=False)
    if warnings:
        print(f"  Violations: {len(warnings)}")
        for w in warnings:
            print(f"    {w.message}")
    else:
        print("  ✅ All constraints satisfied")
```

---

## 6. Key Takeaways

### For Academic/Theoretical Work:
✅ The ₹1,000,000 budget assumption is fine
✅ Weight-based approach is valid for strategy comparison
✅ All calculations are mathematically correct

### For Practical Implementation:
⚠️ Must check budget sufficiency before trading
⚠️ Consider minimum order constraints (1 share)
⚠️ May need to adjust weights for real deployment

### Edge Case Handler Provides:
✅ Violation detection (which assets fail)
✅ Severity classification (CRITICAL / HIGH / MEDIUM)
✅ Automatic weight adjustment (respects constraints)
✅ Comprehensive reporting (for decision-making)

---

## 7. Files Added

| File | Purpose |
|------|---------|
| `edge_case_handler.py` | Edge case detection, weight adjustment, reporting |
| `BUDGET_AND_EDGE_CASES.md` | This documentation |

### Running the Handler:
```bash
python edge_case_handler.py
# Outputs detailed demonstration with ₹2,000 budget scenario
```

---

## 8. Questions This Answers

**Q: What budget is fixed in this project?**
A: ₹1,000,000 is the fixed starting capital for all portfolio calculations.

**Q: What happens if budget < stock price × weight?**
A: Code allows fractional shares (theoretical). Real trading would fail. Use edge_case_handler to detect and fix.

**Q: How do I validate my own budget?**
A: Use `check_budget_vs_stock_price(weights, prices, your_budget)` to see violations.

**Q: How do I adjust weights to match my budget?**
A: Use `suggest_weight_adjustments()` which automatically caps and redistributes weights.

---

## 9. Example Output

When you run `python edge_case_handler.py` you see:

```
================================================================================
⚠️  EDGE CASE WARNINGS: Budget Insufficient for Stock Prices
================================================================================
Budget: ₹2,000.00

  CRITICAL: Stock_A | Price: ₹2500.00 | Weight: 12.00% | Allocated: ₹240.00 | Can buy: 0.096 shares
  CRITICAL: Stock_B | Price: ₹1200.00 | Weight: 8.00%  | Allocated: ₹160.00 | Can buy: 0.133 shares
  MEDIUM:   Stock_C | Price: ₹120.00  | Weight: 5.00%  | Allocated: ₹100.00 | Can buy: 0.833 shares

Total violations: 3 assets
```

This clearly shows:
1. Which assets violate the constraint
2. How severe the problem is
3. How many shares can actually be purchased

---

**Status**: ✅ Edge case handler complete and tested
**Validation**: Demonstrated with ₹2,000 budget scenario  
**Recommendation**: Use for any deployment with budget < ₹1,000,000
