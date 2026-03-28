import pandas as pd
import numpy as np

# Load QUBO matrix
qubo = pd.read_csv('data/05_qubo_matrix.csv', index_col=0)
relaxo_qval = qubo.loc['RELAXO', 'RELAXO']

print("="*90)
print("QUBO MATRIX DIAGONAL VALUE FOR RELAXO - COMPLETE BREAKDOWN")
print("="*90)
print(f"\nActual QUBO[RELAXO, RELAXO] = {relaxo_qval:.10f}")

# Load constants
const_adap = pd.read_csv('data/CONSTANTS_ADAPTIVE.csv')
lambda_card = const_adap[const_adap['Constant'] == 'lambda_card']['Value'].values[0]
print(f"\nλ (cardinality penalty) = {lambda_card}")

K = 40
cardinality_penalty = lambda_card * (1 - 2*K)
print(f"\n1️⃣  CARDINALITY PENALTY TERM")
print(f"   Formula: λ × (1 - 2K)")
print(f"   = {lambda_card} × (1 - 2×{K})")
print(f"   = {lambda_card} × ({1 - 2*K})")
print(f"   = {cardinality_penalty:.10f}")

# Load linear terms
linear_data = pd.read_csv('data/QUBO_inputs_linear_terms.csv', index_col=0)
relaxo_linear = linear_data.loc['RELAXO']
total_linear = relaxo_linear['Total_Linear_Term']

print(f"\n2️⃣  LINEAR TERM COMPONENTS")
print(f"   Covariance Diagonal:     {relaxo_linear['Covariance_Diagonal']:.10f}")
print(f"   Return Penalty (-μ):     {relaxo_linear['Expected_Return_Penalty']:.10f}")
print(f"   Risk Penalty (β×σ_down): {relaxo_linear['Downside_Risk_Penalty']:.10f}")
print(f"   ─────────────────────────────────────")
print(f"   Total Linear Term:       {total_linear:.10f}")

# Covariance contribution
cov_data = pd.read_csv('data/01_covariance_matrix.csv', index_col=0)
cov_diag = cov_data.loc['RELAXO', 'RELAXO']
q_risk = 0.5

print(f"\n3️⃣  BREAKDOWN IN QUBO_inputs_linear_terms.csv")
print(f"   (Already includes risk weighting q_risk={q_risk})")
print(f"   Total_Linear_Term = {total_linear:.10f}")

# Total should be
predicted_diagonal = total_linear + cardinality_penalty
print(f"\n" + "="*90)
print("CORRECT FORMULA FOR DIAGONAL")
print("="*90)
print(f"\nQ[RELAXO, RELAXO] = Linear_term + Cardinality_penalty")
print(f"                  = {total_linear:.10f} + {cardinality_penalty:.10f}")
print(f"                  = {predicted_diagonal:.10f}")
print(f"\nActual QUBO value = {relaxo_qval:.10f}")
print(f"Difference        = {abs(predicted_diagonal - relaxo_qval):.10f}")

if abs(predicted_diagonal - relaxo_qval) < 1e-6:
    print(f"✅ MATCH! Calculation is CORRECT")
else:
    print(f"❌ DOES NOT MATCH - checking for sector penalty...")
    
    # Check sector penalty
    const_all = pd.read_csv('data/CONSTANTS_ADAPTIVE.csv')
    gamma = const_all[const_all['Constant'] == 'gamma_sector']['Value'].values[0]
    print(f"\n   γ (sector penalty) = {gamma}")
    print(f"   Sector contribution to diagonal may vary by sector")

print(f"\n" + "="*90)
print("SUMMARY FOR MANUAL CALCULATION")
print("="*90)
print(f"\nWhen doing manual QUBO calculation for RELAXO:")
print(f"\n1. Linear term (from risk + returns):")
print(f"   Q_linear = {total_linear:.10f}")
print(f"\n2. Add cardinality penalty:")
print(f"   Q_cardinality = {cardinality_penalty:.10f}")
print(f"\n3. Add sector penalty (if applicable):")
print(f"   Q_sector = varies by coselection")
print(f"\n4. Final diagonal:")
print(f"   Q[RELAXO,RELAXO] ≈ {relaxo_qval:.10f}")
print(f"\n" + "="*90)
