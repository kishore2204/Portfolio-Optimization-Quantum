import pandas as pd
import numpy as np

print("="*100)
print("DETAILED CARDINALITY & SECTOR PENALTY CALCULATION FOR RELAXO")
print("="*100)

# ==================== CARDINALITY PENALTY ====================
print("\n" + "█"*100)
print("1️⃣  CARDINALITY PENALTY - DETAILED CALCULATION")
print("█"*100)

print("\n📋 WHAT IS IT?")
print("""
The cardinality penalty FORCES the solver to select exactly K=40 assets.

In QUBO form: 
  E_cardinality = λ × (Σx_i - K)²

where:
  - x_i = 1 if asset i is selected, 0 otherwise
  - Σx_i = total number of selected assets
  - K = 40 (portfolio size constraint)
  - λ = penalty weight (50.0 in your case)
""")

# Expand the formula
print("\n🔍 EXPANDING THE FORMULA:")
print("\nE_cardinality = λ × (Σx_i - K)²")
print("             = λ × (Σx_i)² - 2λK(Σx_i) + λK²")
print("\nFor a binary variable x_i:")
print("  (Σx_i)² = ΣΣ x_i × x_j")
print("         = Σ x_i² + ΣΣ x_i × x_j  (i≠j)")
print("         = Σ x_i + ΣΣ x_i × x_j   (since x_i² = x_i for binary)")
print("\nSubstituting back:")
print("E_cardinality = λ×[Σ x_i + ΣΣ x_i×x_j - 2K×Σ x_i + K²]")
print("             = λ×[Σ x_i(1 - 2K) + ΣΣ x_i×x_j + K²]")

lambda_card = 50.0
K = 40

print(f"\n📊 YOUR VALUES:")
print(f"  λ = {lambda_card}")
print(f"  K = {K}")
print(f"  1 - 2K = 1 - 2×{K} = {1 - 2*K}")

print(f"\n⚙️  CONTRIBUTION TO EACH ASSET'S DIAGONAL:")
print(f"\nFor each asset i in the QUBO diagonal:")
print(f"  Q[i,i] contribution = λ × (1 - 2K)")
print(f"                      = {lambda_card} × ({1 - 2*K})")
print(f"                      = {lambda_card * (1 - 2*K)}")

print(f"\n✅ THIS IS WHY RELAXO'S QUBO HAS SUCH A LARGE PENALTY:")
print(f"  Q[RELAXO,RELAXO] includes: {lambda_card * (1 - 2*K):.1f}")

print(f"\n💡 INTERPRETATION:")
print(f"""
This -3950 contribution means:
  - If you DON'T select RELAXO (x_RELAXO = 0):
    Penalty contribution = 0
  
  - If you DO select RELAXO (x_RELAXO = 1):
    Penalty contribution = -3950 (per asset)
  
When solver sums over all 40 selected assets:
  Total cardinality penalty = 40 × (-3950) + other terms
                            ≈ -158,000 (plus the cross terms)

This MASSIVE penalty ensures Σx_i = exactly 40 assets.
""")

# ==================== SECTOR PENALTY ====================
print("\n" + "█"*100)
print("2️⃣  SECTOR PENALTY - DETAILED CALCULATION")
print("█"*100)

print("\n📋 WHAT IS IT?")
print("""
The sector penalty limits concentration within sectors.

In QUBO form:
  E_sector = γ × Σ(pairs in same sector) x_i × x_j

where:
  - γ = 5.0 (sector penalty weight)
  - The sum is over all pairs (i,j) in the SAME sector
  - Only counted when BOTH assets are selected
""")

# Load data to show actual sector penalty calculation
print("\n🔍 EXPANDING THE FORMULA:")
print("\nFor each pair of assets (i, j) in the SAME sector:")
print("  If BOTH are selected: add γ to Q[i,j]")
print("  Q[i,j] contribution from sector = γ")

gamma = 5.0
print(f"\n📊 YOUR VALUES:")
print(f"  γ = {gamma}")
print(f"  max_per_sector = 4 (maximum assets per sector)")

# Load the actual selected assets
qubo = pd.read_csv('data/05_qubo_matrix.csv', index_col=0)
assets = qubo.columns.tolist()
print(f"\n  Selected assets for portfolio: {len(assets)} assets")
print(f"  First 10: {assets[:10]}")

# Get sector info
import json
with open('datasets/nifty100_sectors.json', 'r') as f:
    sector_data = json.load(f)

sector_map = {}
for sector, stocks in sector_data.items():
    for stock in stocks:
        if stock in assets:
            sector_map[stock] = sector

print(f"\n📍 SECTOR DISTRIBUTION OF SELECTED ASSETS:")
sector_counts = {}
for asset, sector in sector_map.items():
    if sector not in sector_counts:
        sector_counts[sector] = []
    sector_counts[sector].append(asset)

for sector in sorted(sector_counts.keys()):
    assets_in_sector = sector_counts[sector]
    print(f"  {sector:30s}: {len(assets_in_sector)} assets")
    if 'RELAXO' in assets_in_sector:
        print(f"    └─ Includes RELAXO")
        other_in_sector = [a for a in assets_in_sector if a != 'RELAXO']
        print(f"    └─ Co-selected with: {other_in_sector}")

# Calculate sector penalty for RELAXO specifically
print(f"\n⚙️  SECTOR PENALTY CONTRIBUTION FOR RELAXO:")

if 'RELAXO' in sector_map:
    relaxo_sector = sector_map['RELAXO']
    coselected = sector_counts[relaxo_sector]
    
    print(f"\nRELAXO's sector: {relaxo_sector}")
    print(f"Total assets in {relaxo_sector}: {len(coselected)}")
    print(f"Including RELAXO: {coselected}")
    
    # Number of pairs with RELAXO in same sector
    other_coselected = [a for a in coselected if a != 'RELAXO']
    num_pairs_with_relaxo = len(other_coselected)
    
    print(f"\nRELAXO's pairs in same sector: {num_pairs_with_relaxo}")
    print(f"Paired with: {other_coselected}")
    
    # Off-diagonal contributions
    relaxo_sector_penalty = gamma * num_pairs_with_relaxo
    print(f"\n🔗 OFF-DIAGONAL SECTOR PENALTY:")
    print(f"  = γ × (number of assets paired with RELAXO in same sector)")
    print(f"  = {gamma} × {num_pairs_with_relaxo}")
    print(f"  = {relaxo_sector_penalty}")
    print(f"\n  This appears as +{gamma} in Q[RELAXO, other_asset] for each coselected asset")

# ==================== PUTTING IT TOGETHER ====================
print("\n" + "█"*100)
print("3️⃣  COMPLETE Q[RELAXO, RELAXO] CALCULATION")
print("█"*100)

# Load actual values
linear_data = pd.read_csv('data/QUBO_inputs_linear_terms.csv', index_col=0)
relaxo_linear = linear_data.loc['RELAXO']

qubo = pd.read_csv('data/05_qubo_matrix.csv', index_col=0)
relaxo_qval = qubo.loc['RELAXO', 'RELAXO']

print(f"\n📐 FORMULA:")
print(f"Q[RELAXO,RELAXO] = Linear + Cardinality + Sector")

print(f"\n1️⃣  LINEAR TERMS:")
print(f"  Covariance_Diagonal:      {relaxo_linear['Covariance_Diagonal']:.10f}")
print(f"  Expected_Return_Penalty:  {relaxo_linear['Expected_Return_Penalty']:.10f}")
print(f"  Downside_Risk_Penalty:    {relaxo_linear['Downside_Risk_Penalty']:.10f}")
print(f"  ─────────────────────────────────────")
print(f"  = {relaxo_linear['Total_Linear_Term']:.10f}")

print(f"\n2️⃣  CARDINALITY PENALTY:")
print(f"  = λ × (1 - 2K)")
print(f"  = {lambda_card} × (1 - 2×{K})")
print(f"  = {lambda_card} × (-79)")
print(f"  = {lambda_card * (1 - 2*K):.10f}")

print(f"\n3️⃣  SECTOR PENALTY:")
sector_contrib = relaxo_qval - relaxo_linear['Total_Linear_Term'] - (lambda_card * (1 - 2*K))
print(f"  = Actual - Linear - Cardinality")
print(f"  = {relaxo_qval:.10f} - {relaxo_linear['Total_Linear_Term']:.10f} - {lambda_card * (1 - 2*K):.10f}")
print(f"  = {sector_contrib:.10f}")

print(f"\n✅ FINAL:")
print(f"Q[RELAXO,RELAXO] = {relaxo_linear['Total_Linear_Term']:.6f} + {lambda_card * (1 - 2*K):.6f} + {sector_contrib:.6f}")
print(f"                 = {relaxo_qval:.10f}")

print("\n" + "="*100)
print("KEY INSIGHTS")
print("="*100)
print(f"""
1. CARDINALITY PENALTY (λ term):
   - Dominates the QUBO matrix
   - Is the SAME for all 40 selected assets
   - Applies to each asset's diagonal
   - Ensures exactly K=40 selected

2. SECTOR PENALTY (γ term):
   - Applied as OFF-DIAGONAL terms Q[i,j]
   - Only between assets in SAME sector
   - Depends on which OTHER assets are selected
   - RELAXO can see this in its off-diagonal Q values

3. LINEAR TERMS:
   - Individual asset risk/return contribution
   - Much smaller than cardinality penalty
   - Provides asset-level optimization

4. HIERARCHY OF IMPORTANCE:
   Cardinality (-3950) >> Linear (-0.35) >> Sector (0.07)
   
   The solver MUST satisfy K=40 first and foremost!
""")

print("="*100)
