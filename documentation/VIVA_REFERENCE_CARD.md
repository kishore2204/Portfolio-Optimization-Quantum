# 🎤 VIVA REFERENCE CARD
## Fixed Constants QUBO Portfolio Optimization

---

## 🎯 Quick Explanations (30 seconds each)

### Q: "What are your QUBO constants?"

**Concise Answer**:
"We use fixed constants: q=0.5 (risk weight), β=0.3 (downside penalty), and adaptive λ computed via formula λ=clip(10×scale×(N/K), 50-500). Sector penalty γ=0.1λ is derived. This ensures reproducibility without overfitting."

---

### Q: "Why fixed instead of tuned?"

**Concise Answer**:
"Grid search over 144 regimes risks overfitting to test data. Our fixed constants are:
1. Theoretically justified (q=0.5 is literature standard)
2. Pre-determined (no data leakage)
3. Reproducible (identical results always)
4. Scientifically defensible

The adaptive λ formula scales with data magnitude, ensuring constraint satisfaction across different datasets without manual tuning."

---

### Q: "Explain the λ (cardinality) formula"

**Concise Answer**:
"λ enforces exactly K assets. Formula: λ = clip(10 × scale × (N/K), 50-500)

Where:
- N = total assets (e.g., 207)
- K = target assets (e.g., 25)
- scale = max(mean(covariance), mean(returns), max(variance))

Example: If scale=0.25, N=100, K=20:
λ = 10 × 0.25 × (100/20) = 12.5 → clipped to 50

Clipping prevents numerical issues across different datasets."

---

### Q: "How does γ (sector penalty) work?"

**Concise Answer**:
"γ = 0.1 × λ

We add γ to Q[i,j] only when assets i and j are in the same sector. This penalizes concentration in single sectors without hard constraints.

Combined with max_per_sector = 4, it ensures balanced sector diversification."

---

### Q: "Why β=0.3 for downside?"

**Concise Answer**:
"Downside volatility penalizes crash-prone stocks more than variance does.

β=0.3 balances:
- Too low (0.1): Ignores downside risk → includes crash stocks
- Too high (0.7): Over-penalizes → excludes growth stocks
- 0.3: Sweet spot for equity portfolios

In QUBO diagonal: Q[i,i] += 0.3 × σ_downside_i"

---

### Q: "How do you avoid overfitting?"

**Concise Answer**:
"Three methods:

1. **Fixed constants** determined before seeing test data
2. **Single run only** (no multiple regimes to cherry-pick)
3. **Adaptive λ** uses data-scale formula (not optimized on performance)

Result: Configuration is unbiased and reproducible."

---

### Q: "What if λ ends up clipped?"

**Concise Answer**:
"Clipping to [50, 500] is expected and fine.

If computed λ falls outside range:
- λ < 50: cardinality penalty too weak (small, stable assets)
  → Clamped to 50 (ensures K constraint)
  
- λ > 500: cardinality penalty too strong (high volatility assets)
  → Clamped to 500 (prevents numerical issues)

Clipping prevents instability without manual tune."

---

### Q: "How do constants scale to different datasets?"

**Concise Answer**:
"Fixed constants (q, β) apply to all datasets.

Adaptive λ scales:
- Small universe (N=50): λ = 10 × scale × (50/K) = smaller
- Large universe (N=500): λ = 10 × scale × (500/K) = larger

This scaling ensures constraint is equally effective regardless of universe size."

---

### Q: "Can you change the constants?"

**Concise Answer**:
"Yes, if justified:

Currently:
- q_risk = 0.5 (risk weight: literature standard)
- β_downside = 0.3 (moderate downside protection)
- λ formula = adaptive (ensures numerical stability)
- γ = 0.1λ (proportional sector penalty)

Any change requires:
1. Clear economic justification
2. Documentation in code comments
3. Git commit with explanation
4. Viva defense of rationale"

---

### Q: "Why 10× in the λ formula?"

**Concise Answer**:
"10 × scale × (N/K) is empirically calibrated scaling factor.

- 10 base multiplier: Provides adequate penalty strength
- × scale: Adjusts to dataset magnitude (avoids overflow/underflow)
- × (N/K): Scales with portfolio size ratio

Combined: Ensures λ remains in [50, 500] across typical datasets (N=50-500, K=5-50)"

---

### Q: "What are the constraints?"

**Concise Answer**:
"Hard constraints (enforced):
- Exactly K assets: Enforced by cardinality penalty λ
- Σw = 1: Weight constraint in Sharpe optimization
- w ≥ 0: No shorting
- w ≤ 0.12: Max weight per asset

Soft constraints (encouraged):
- Sector diversity: γ penalty (max 4 per sector as hard backup)
- Low downside risk: β penalty in QUBO"

---

### Q: "How does rebalancing use fixed constants?"

**Concise Answer**:
"Quarterly rebalancing:
1. Every 63 days (quarterly: 252÷4)
2. Identify underperformers (bottom 20%)
3. Build new QUBO with fresh data
4. Use fresh λ (computed from new statistics)
5. Keep fixed q, β same

Result: Adapts to market changes while maintaining constant principles."

---

## 📊 KEY NUMBERS (for quick reference)

```
Fixed Constants:
  q_risk            = 0.5
  β_downside        = 0.3
  
Time Constants:
  Trading days/year = 252
  Train period      = 10 years
  Test period       = 5 years
  Rebal cadence     = 63 days (quarterly)
  Lookback window   = 252 days (1 year)
  
Constraints:
  K = 6% of assets (e.g., ~25 stocks)
  max_weight = 12% per asset
  max_per_sector = 4 assets
  
Optimizer:
  SLSQP method (Sharpe optimization)
  Simulated Annealing (QUBO solver)
  
Performance (expected):
  Classical:        2.3% annualized, -0.18 Sharpe
  Quantum:         15.6% annualized,  0.76 Sharpe
  Quantum+Rebal:   35.8% annualized,  1.59 Sharpe
```

---

## 🔍 COMMON CHALLENGES

### "Why does classical portfolio do so poorly?"

**Answer**: "Classical uses MVO top-K heuristic—picks assets by weight, not by selection quality. Our QUBO directly optimizes which K assets minimize portfolio risk while maximizing return. Direct optimization > weight-based heuristic."

### "What if Sharpe turns negative?"

**Answer**: "Valid outcome in bear markets. Means returns < risk-free rate (5%). Not a model failure—market failure. Model correctly identifies underperformance."

### "How is quantum better scientifically?"

**Answer**: "Three reasons:
1. **Direct problem formulation**: Select K assets (not infer from weights)
2. **Integrated constraints**: Returns + risk + cardinality + sectors in one Q matrix
3. **NP-hard optimization**: Simulated annealing finds near-optimal (not greedy)"

### "Can you guarantee optimal solution?"

**Answer**: "No. Asset selection with K=25 from N=207 has C(207,25)≈10^47 possibilities. NP-hard problem. Simulated annealing finds near-optimal with high probability. Our approach is rigorous heuristic, not guarantee."

---

## ✅ CHECKLIST (Before Viva)

- [ ] Can explain q=0.5 choice quickly
- [ ] Can derive λ formula step-by-step
- [ ] Know difference: fixed vs. tuned constants
- [ ] Understand trade-off: q, β, λ, γ
- [ ] Can run `python config_constants.py` to see summary
- [ ] Know constants file location and have it open
- [ ] Can show run_summary.json with computed values
- [ ] Understand why classical < quantum
- [ ] Ready to explain overfitting avoidance
- [ ] Know answers to all 11 Q&A above

---

## 📱 QUICK FILES TO OPEN

```
During viva, have these open:
1. config_constants.py              ← Show fixed values
2. run_summary.json                 ← Show computed λ, γ
3. portfolio_metrics.csv            ← Show results
4. FIXED_CONSTANTS_CONFIG.md        ← Detailed reference
5. QUBO_CALCULATION_MANUAL.md       ← Math reference
```

---

## 💡 POWER STATEMENTS

> "We chose fixed constants to ensure scientific rigor. No data in choice, no overfitting to outcomes, full reproducibility."

> "Adaptive λ scales with data magnitude, not with portfolio performance. It ensures our cardinality constraint works across all datasets."

> "Our model is defensible: every constant has documented rationale, no empirical tuning, explicit constraint satisfaction."

> "Quantum beats classical because we directly optimize asset selection, not infer it from weight allocation."

> "Reproducibility is key: same input → same output always. This is how science works."

---

## 🎯 GOAL OF VIVA

Examiner wants to verify:
1. ✅ You understand QUBO formulation
2. ✅ You justify every design choice
3. ✅ You avoid overfitting/p-hacking
4. ✅ You document and reproduce results
5. ✅ You compare fairly (classical vs quantum)

**Your constants setup addresses all these.**

---

**Last Updated**: March 27, 2026
**Status**: Ready for Viva

---

**Good luck! 🎓**
