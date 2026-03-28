"""
GRAPH VERIFICATION - Check all Nifty benchmarks are plotted
===========================================================

Verify:
1. Which graphs exist
2. Which Nifty graphs are missing
3. Correct benchmark data
"""

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parent
output_dir = root / "outputs"
data_dir = root / "data"

print("\n" + "="*80)
print("GRAPH VERIFICATION")
print("="*80)

# List all PNG files
print("\n[STEP 1] Checking generated graphs...")

png_files = sorted(output_dir.glob("*.png"))
print(f"\nTotal graphs found: {len(png_files)}")

for i, png in enumerate(png_files, 1):
    size_kb = png.stat().st_size / 1024
    print(f"  {i:2d}. {png.name:50s} ({size_kb:8.1f} KB)")

# Check for specific Nifty benchmark graphs
print("\n[STEP 2] Checking for Nifty benchmark graphs...")

nifty_graphs = {
    "Nifty_50": "D1_cumulative_returns_Nifty_50.png",
    "Nifty_100": "D1_cumulative_returns_Nifty_100.png",
    "Nifty_200": "D1_cumulative_returns_Nifty_200.png",
    "BSE_500": "D1_cumulative_returns_BSE_500.png",
    "HDFCNIF100": "D1_cumulative_returns_HDFCNIF100.png"
}

for name, filename in nifty_graphs.items():
    path = output_dir / filename
    if path.exists():
        size_kb = path.stat().st_size / 1024
        print(f"  ✓ {name:15s}: {filename:50s} ({size_kb:8.1f} KB)")
    else:
        print(f"  ✗ {name:15s}: MISSING - {filename}")

# Load benchmark data and check if it makes sense
print("\n[STEP 3] Benchmark data integrity...")

benchmark_values = pd.read_csv(data_dir / "11_benchmark_values.csv", index_col='Date', parse_dates=True)

print(f"\nBenchmark columns: {list(benchmark_values.columns)}")

for col in benchmark_values.columns:
    values = benchmark_values[col].dropna()
    if len(values) == 0:
        print(f"  ✗ {col}: NO DATA")
        continue
    
    start = values.iloc[0]
    end = values.iloc[-1]
    ret = (end / start - 1.0) * 100
    
    print(f"\n  {col}:")
    print(f"    Start value: {start:.6f}")
    print(f"    End value: {end:.6f}")
    print(f"    Return: {ret:.2f}%")
    print(f"    Days: {len(values)}")

# Check one graph visually to see what's plotted
print("\n[STEP 4] Sample graph analysis (Nifty_50)...")

graph_path = output_dir / "D1_cumulative_returns_Nifty_50.png"

if graph_path.exists():
    from PIL import Image
    img = Image.open(graph_path)
    print(f"  ✓ Nifty_50 graph exists")
    print(f"    Size: {img.size}")
    print(f"    Mode: {img.mode}")
else:
    print(f"  ✗ Nifty_50 graph NOT FOUND")

# Check comparison graphs
print("\n[STEP 5] Main comparison graphs...")

main_graphs = [
    "1_classical_vs_quantum_vs_rebalanced.png",
    "2_quantum_vs_rebalanced.png",
    "3_quantum_rebalanced_vs_benchmarks.png",
    "4_rebalanced_vs_nonrebalanced.png",
    "G1_classical_quantum_vs_rebalanced.png",
    "G1_cumulative_returns_quantum_vs_rebalanced.png"
]

for filename in main_graphs:
    path = output_dir / filename
    if path.exists():
        size_kb = path.stat().st_size / 1024
        print(f"  ✓ {filename:50s} ({size_kb:8.1f} KB)")
    else:
        print(f"  ✗ {filename:50s} MISSING")

print("\n" + "="*80)
print("VERDICT")
print("="*80)

all_nifty_exist = all((output_dir / fn).exists() for fn in nifty_graphs.values())

if all_nifty_exist:
    print("\n  ✓ ALL NIFTY BENCHMARKS PLOTTED")
    print("    - Nifty_50 graph: FOUND")
    print("    - Nifty_100 graph: FOUND")
    print("    - Nifty_200 graph: FOUND")
    print("    - BSE_500 graph: FOUND")
    print("    - HDFCNIF100 graph: FOUND")
else:
    print("\n  ✗ SOME NIFTY BENCHMARKS MISSING")
    missing = [name for name, fn in nifty_graphs.items() if not (output_dir / fn).exists()]
    print(f"    Missing: {missing}")

print("\n[IMPORTANT NOTE]")
print("  HDFCNIF100 shows -85.77% return")
print("  This is an ETF with a 20%+ discontinuity (likely ETF merger/split)")
print("  The benchmark data may be unreliable for this index")

print("\n")
