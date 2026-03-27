import pandas as pd
import os

# Check QUBO matrix dimensions from CSV
qubo_file = 'data/05_qubo_matrix.csv'
qubo_df = pd.read_csv(qubo_file, index_col=0)

print(f"✅ QUBO MATRIX FROM CSV:")
print(f"   Rows: {qubo_df.shape[0]}")
print(f"   Cols: {qubo_df.shape[1]}")
print(f"   Full shape: {qubo_df.shape}")
print(f"   File size: {os.path.getsize(qubo_file)} bytes")

print(f"\n   First 5 assets:")
print(qubo_df.index[:5].tolist())

print(f"\n   Symmetric check: {((qubo_df.values == qubo_df.values.T).all())}")

# Check if it's 100x100 or 14x14
if qubo_df.shape[0] == 100:
    print(f"\n✅ SUCCESS: QUBO is 100×100 (annealing pool)")
elif qubo_df.shape[0] == 14:
    print(f"\n⚠️  QUBO is still 14×14 (final portfolio)")
else:
    print(f"\n❓ QUBO is {qubo_df.shape[0]}×{qubo_df.shape[1]}")
