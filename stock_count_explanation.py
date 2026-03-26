#!/usr/bin/env python3
"""Detailed breakdown of stock counts through the pipeline"""

print("\n" + "="*80)
print("DETAILED BREAKDOWN: FROM DATASET TO QUBO")
print("="*80)

print("""
STEP 1: RAW DATASET
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Source: Dataset/prices_timeseries_complete.csv
  Stocks: 2,248
  Date range: 2011-03-14 to 2026-03-11
  Sectors: All Indian equities (NSE & BSE)

STEP 2: PHASE 01 FILTERING (Data Preparation)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Filter 1: NIFTY 100 universe selection
    Input:  2,248 stocks
    Filter: Keep only NIFTY 100 configured stocks (113 possible)
    Output: ~100-113 stocks (after matching with dataset)

  Filter 2: Minimum history requirement
    Input:  100-113 stocks
    Filter: Keep only stocks with ≥ 1,000 days of data
    Output: Typically ~100 stocks (most NIFTY 100 have long history)

  Filter 3: Price floor filter
    Input:  ~100 stocks
    Filter: Keep stocks trading above ₹10
    Output: ~100 stocks (most liquid stocks meet this)

  ✓ RESULT: 100 stocks prepared for QUBO

STEP 3: PHASE 03 QUBO FORMULATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Input:  100 stocks
  QUBO:   Creates 100×100 binary quadratic model
          - 100 variables (x₁, x₂, ..., x₁₀₀)
          - One variable per stock (binary: 0 or 1)
          - Pairwise interactions: 100×100 = 10,000 terms

  ✓ RESULT: 100×100 QUBO matrix

STEP 4: PHASE 04 QUANTUM SELECTION (Solver)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Input:  100×100 QUBO matrix
  Solver: Simulated Annealing (5000 reads)
  
  - Evaluates different combinations of the 100 stocks
  - Tries to minimize energy: E(x) = x^T Q x
  - Constraint: Select exactly K = 8 stocks
  - Also enforces: ≥5 sectors, no sector >35% weight
  
  ✓ OUTPUT: 8 stocks selected from 100

STEP 5: PHASE 06 WEIGHT OPTIMIZATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Input:  8 selected stocks
  Solver: CVXPY (convex Sharpe ratio maximization)
  Constraint: Weights sum to 1, no short selling, sector limits
  
  ✓ OUTPUT: 8 portfolio weights allocated


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DIRECT ANSWER TO YOUR QUESTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"How many stocks does it take from the dataset while calculating the QUBO?"

  QUBO CALCULATION USES: 100 stocks
  
  ├─ Creates a 100×100 matrix
  ├─ Each variable represents one stock (binary: 0 or 1)
  ├─ 100 × 100 = 10,000 pairwise interaction terms
  └─ Solver selects K=8 from these 100

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRACTICAL NOTES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Dataset source: 2,248 stocks (NSE + BSE)
2. Filtered to: 100 stocks (NIFTY 100 universe)
3. QUBO matrix: 100 × 100
4. Final portfolio: 8 stocks selected

Can I change the universe size?
  ✓ Yes, in config/config.json
  ✓ Increase universe_size: Larger QUBO matrix (slower)
  ✓ Example: universe_size = 50 → 50×50 QUBO, faster
  ✓ Example: universe_size = 200 → 200×200 QUBO, much slower

What are the 100 stocks?
  → NIFTY 100 index stocks (top caps, most liquid)
  → See: config/nifty100_sectors.json (113 configured, ~100 available)

Why 100 and not full 2,248?
  1. Computational: 2248×2248 QUBO too large for solver
  2. Data: Not all 2248 have sufficient history
  3. Practical: NIFTY 100 are most tradeable
  4. Design: Balance between universe size and computation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
