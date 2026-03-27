import pandas as pd

# Check portfolio weights
df = pd.read_csv('data/07_portfolio_weights.csv', index_col=0)
print(f'Total assets in file: {len(df)}')

classical_selected = (df['Classical'] > 0.0001).sum()
quantum_selected = (df['Quantum'] > 0.0001).sum()

print(f'\nClassical selected (weight > 0.0001): {classical_selected}')
print(f'Quantum selected (weight > 0.0001): {quantum_selected}')

print(f'\nClassical assets with meaningful weights:')
classical_nonzero = df[df['Classical'] > 0.0001]['Classical'].sort_values(ascending=False)
print(f"Count: {len(classical_nonzero)}")
print(classical_nonzero)

print(f'\nQuantum assets with meaningful weights:')
quantum_nonzero = df[df['Quantum'] > 0.0001]['Quantum'].sort_values(ascending=False)
print(f"Count: {len(quantum_nonzero)}")
print(quantum_nonzero)

# Check when files were last modified
import os
print(f"\n\nFile modification times:")
print(f"07_portfolio_weights.csv: {pd.Timestamp(os.path.getmtime('data/07_portfolio_weights.csv'), unit='s')}")
print(f"05_qubo_matrix.csv: {pd.Timestamp(os.path.getmtime('data/05_qubo_matrix.csv'), unit='s')}")
