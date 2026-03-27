import pandas as pd

print("="*90)
print("RELAXO STOCK - INPUT VALUES FOR MANUAL CALCULATION")
print("="*90)

# 1. Expected returns and downside risk
returns_data = pd.read_csv('data/04_expected_returns_and_downside.csv', index_col=0)
relaxo_returns = returns_data.loc['RELAXO']
print("\n1️⃣  EXPECTED RETURNS & DOWNSIDE RISK")
print(f"   μ (Expected Return):    {relaxo_returns['Expected_Return']:.10f}")
print(f"   σ_down (Downside Risk): {relaxo_returns['Downside_Risk']:.10f}")

# 2. QUBO linear terms
linear_data = pd.read_csv('data/QUBO_inputs_linear_terms.csv', index_col=0)
relaxo_linear = linear_data.loc['RELAXO']
print("\n2️⃣  QUBO LINEAR TERMS BREAKDOWN")
print(f"   Covariance_Diagonal:      {relaxo_linear['Covariance_Diagonal']:.10f}")
print(f"   Expected_Return_Penalty:  {relaxo_linear['Expected_Return_Penalty']:.10f}")
print(f"   Downside_Risk_Penalty:    {relaxo_linear['Downside_Risk_Penalty']:.10f}")
print(f"   Total_Linear_Term:        {relaxo_linear['Total_Linear_Term']:.10f}")

# 3. Portfolio weights
weights_data = pd.read_csv('data/07_portfolio_weights.csv', index_col=0)
relaxo_weights = weights_data.loc['RELAXO']
print("\n3️⃣  PORTFOLIO WEIGHTS")
print(f"   Classical Weight:  {relaxo_weights['Classical']:.10f}")
print(f"   Quantum Weight:    {relaxo_weights['Quantum']:.10f}")

# 4. Fixed constants and adaptive constants combined
const_data = pd.read_csv('data/CONSTANTS_FIXED.csv')
print("\n4️⃣  FIXED CONSTANTS FOR CALCULATION")
for idx, row in const_data.iterrows():
    print(f"   {row['Constant']:25s} = {row['Value']}")

const_adap = pd.read_csv('data/CONSTANTS_ADAPTIVE.csv')
print("\n5️⃣  ADAPTIVE CONSTANTS")
for idx, row in const_adap.iterrows():
    print(f"   {row['Constant']:25s} = {row['Value']}")

print("\n" + "="*90)
print("MANUAL CALCULATION VERIFICATION")
print("="*90)

q_risk = 0.5
beta_downside = 0.3
mu = relaxo_returns['Expected_Return']
sigma_down = relaxo_returns['Downside_Risk']
cov_diag = relaxo_linear['Covariance_Diagonal']

print("\nStep 1: Calculate linear term components")
print(f"  Covariance Diagonal (from Σ):  {cov_diag:.10f}")
print(f"  Return penalty (-μ):           {-mu:.10f}")
print(f"  Risk penalty (β × σ_down):     {beta_downside * sigma_down:.10f}")
print(f"                                 (0.3 × {sigma_down:.10f})")

print("\nStep 2: Sum all components")
total = cov_diag - mu + beta_downside * sigma_down
print(f"  Total Linear Term = {cov_diag:.10f} + ({-mu:.10f}) + ({beta_downside * sigma_down:.10f})")
print(f"                    = {total:.10f}")

print("\nStep 3: Verify against CSV")
csv_value = relaxo_linear['Total_Linear_Term']
print(f"  CSV value:  {csv_value:.10f}")
print(f"  Calculated: {total:.10f}")
print(f"  Match: {abs(total - csv_value) < 1e-9} ✓" if abs(total - csv_value) < 1e-9 else f"  Match: False ✗")

print("\n" + "="*90)
print("SUMMARY TABLE FOR MANUAL INPUT")
print("="*90)

summary = pd.DataFrame({
    'Parameter': [
        'μ (Expected Return)',
        'σ_down (Downside Risk)',
        'Σ[RELAXO,RELAXO] (Variance)',
        'q_risk',
        'β_downside',
        'Classical Weight',
        'Quantum Weight',
    ],
    'Value': [
        f"{mu:.10f}",
        f"{sigma_down:.10f}",
        f"{cov_diag:.10f}",
        f"{q_risk}",
        f"{beta_downside}",
        f"{relaxo_weights['Classical']:.10f}",
        f"{relaxo_weights['Quantum']:.10f}",
    ],
    'Formula in QUBO': [
        '-μ (negated for minimization)',
        'β × σ_down',
        'q_risk × Σ[i,i]',
        'Risk weighting constant',
        'Downside risk penalty weight',
        'MVO solution',
        'QUBO + Sharpe solution',
    ]
})

print("\n" + summary.to_string(index=False))

print("\n" + "="*90)
