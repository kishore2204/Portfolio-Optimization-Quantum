import pandas as pd

# Check portfolio weights
df = pd.read_csv('data/07_portfolio_weights.csv', index_col=0)
classical_selected = (df['Classical'] > 0.0001).sum()
quantum_selected = (df['Quantum'] > 0.0001).sum()

print(f"✅ PORTFOLIO WEIGHTS:")
print(f"   Classical assets selected: {classical_selected}")
print(f"   Quantum assets selected:   {quantum_selected}")

print(f"\n✅ QUBO MATRIX:")
qubo_df = pd.read_csv('data/05_qubo_matrix.csv', index_col=0)
print(f"   Size: {qubo_df.shape[0]} × {qubo_df.shape[1]}")
print(f"   Symmetric: {((qubo_df.values == qubo_df.values.T).all())}")

print(f"\n✅ CONSTANTS (Fixed):")
const_df = pd.read_csv('data/CONSTANTS_FIXED.csv')
for idx, row in const_df.iterrows():
    print(f"   {row['Constant']:20} = {row['Value']}")
