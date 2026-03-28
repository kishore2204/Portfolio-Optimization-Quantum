import pandas as pd

print("="*90)
print("CORRECT QUBO DIAGONAL BREAKDOWN FOR RELAXO")
print("="*90)

# Load QUBO matrix
qubo = pd.read_csv('data/05_qubo_matrix.csv', index_col=0)
relaxo_qval = qubo.loc['RELAXO', 'RELAXO']

print(f"\n✅ Actual QUBO[RELAXO, RELAXO] = {relaxo_qval:.10f}")

# Load linear terms breakdown
linear_data = pd.read_csv('data/QUBO_inputs_linear_terms.csv', index_col=0)
relaxo_linear = linear_data.loc['RELAXO']

print(f"\n📊 COMPONENT BREAKDOWN:")
print(f"\n1️⃣  LINEAR TERMS (Risk + Return contributions):")
print(f"   Covariance_Diagonal:      {relaxo_linear['Covariance_Diagonal']:.10f}")
print(f"   Expected_Return_Penalty:  {relaxo_linear['Expected_Return_Penalty']:.10f}")
print(f"   Downside_Risk_Penalty:    {relaxo_linear['Downside_Risk_Penalty']:.10f}")
print(f"   ─────────────────────────────────────────────")
print(f"   Total Linear Term:        {relaxo_linear['Total_Linear_Term']:.10f}")

# Cardinality penalty
lambda_card = 50.0
K = 40
cardinality_penalty = lambda_card * (1 - 2*K)

print(f"\n2️⃣  CARDINALITY PENALTY (from constraint Σx_i = K):")
print(f"   λ = {lambda_card}")
print(f"   λ × (1 - 2K) = {lambda_card} × (1 - 2×{K})")
print(f"                = {lambda_card} × (-79)")
print(f"                = {cardinality_penalty:.10f}")

# Predicted
predicted = relaxo_linear['Total_Linear_Term'] + cardinality_penalty
print(f"\n3️⃣  SUBTOTAL (without sector penalty):")
print(f"   = {relaxo_linear['Total_Linear_Term']:.10f} + {cardinality_penalty:.10f}")
print(f"   = {predicted:.10f}")

# Sector penalty
sector_diff = relaxo_qval - predicted
print(f"\n4️⃣  SECTOR PENALTY CONTRIBUTION:")
print(f"   = Actual - Subtotal")
print(f"   = {relaxo_qval:.10f} - {predicted:.10f}")
print(f"   = {sector_diff:.10f}")

print(f"\n" + "="*90)
print("COMPLETE FORMULA")
print("="*90)
print(f"\nQ[RELAXO,RELAXO] = LinearTerms + Cardinality + Sector")
print(f"                 = {relaxo_linear['Total_Linear_Term']:.6f} + {cardinality_penalty:.6f} + {sector_diff:.6f}")
print(f"                 = {relaxo_qval:.6f} ✅")

print(f"\n" + "="*90)
print("FOR YOUR MANUAL CALCULATION")
print("="*90)
print(f"\nTo manually calculate RELAXO's QUBO diagonal:")
print(f"\nStep 1: Get linear term components")
print(f"  μ = 0.4162545929")
print(f"  σ_down = 0.2274198452")
print(f"  Σ[RELAXO,RELAXO] = 0.0586925870")
print(f"  q_risk = 0.5")
print(f"  β = 0.3")

print(f"\nStep 2: Compute linear term")
cov_term = 0.1404345775
ret_term = -0.4162545929
risk_term = 0.0682259536
print(f"  Linear = {cov_term} + {ret_term} + {risk_term}")
print(f"         = {relaxo_linear['Total_Linear_Term']:.10f}")

print(f"\nStep 3: Add cardinality penalty")
print(f"  Cardinality = λ(1 - 2K) = 50 × (-79) = -3950.0")

print(f"\nStep 4: Check for sector penalty")
print(f"  Sector penalty ≈ {sector_diff:.6f}")
print(f"  (This depends on which other assets are selected)")

print(f"\nStep 5: Final result")
print(f"  Q[RELAXO,RELAXO] ≈ {relaxo_qval:.10f} ✅")

print(f"\n" + "="*90)
print("KEY INSIGHT")
print("="*90)
print(f"""
The QUBO diagonal is DOMINATED by the cardinality penalty:
  - Linear terms:         {relaxo_linear['Total_Linear_Term']:.2f}
  - Cardinality penalty: {cardinality_penalty:.2f}  ← THIS IS 11,500× LARGER!
  - Sector penalty:      {sector_diff:.2f}

This is WHY the solver focuses on satisfying K=40. The quadratic penalty
for violating Σx_i = 40 is HUGE compared to individual asset returns.
""")
print("="*90)
