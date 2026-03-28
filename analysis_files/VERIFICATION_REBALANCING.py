"""
CRITICAL VERIFICATION: Quantum+Rebalanced Portfolio Performance Analysis
=========================================================================

Purpose: Verify that the 374.28% return is CORRECT or INCORRECT
         by tracing through the rebalancing logic step-by-step.

Checking:
1. Daily return calculations
2. Rebalancing logic (every 63 days)
3. Portfolio value accumulation
4. Comparison with benchmarks
5. Why rebalancing shows such high performance
"""

import pandas as pd
import numpy as np
from pathlib import Path
from data_loader import load_all_data
from preprocessing import clean_prices, time_series_split, annualize_stats
from evaluation import compute_metrics
from rebalancing import RebalanceConfig, run_quarterly_rebalance
from hybrid_optimizer import portfolio_returns

root = Path(__file__).resolve().parent
dataset_root = root / "datasets"
data_dir = root / "data"

print("\n" + "="*80)
print("CRITICAL VERIFICATION: REBALANCING PERFORMANCE ANALYSIS")
print("="*80)

# Load original data
print("\n[STEP 1] Loading data...")
bundle = load_all_data(dataset_root)
prices = clean_prices(bundle.asset_prices)
split = time_series_split(prices, train_years=10, test_years=5)

train_r = split.train_returns
test_r = split.test_returns
test_dates = test_r.index

print(f"  Train period: {train_r.index[0].date()} to {train_r.index[-1].date()}")
print(f"  Test period: {test_r.index[0].date()} to {test_r.index[-1].date()}")
print(f"  Test days: {len(test_r)}")
print(f"  Assets: {len(train_r.columns)}")

# Load pre-computed portfolio values
print("\n[STEP 2] Loading pre-computed portfolio values...")
pv_df = pd.read_csv(data_dir / "10_portfolio_values.csv", index_col='Date', parse_dates=True)

classical_value = pv_df['Classical']
quantum_value = pv_df['Quantum']
quantum_rebal_value = pv_df['Quantum_Rebalanced']

print(f"  Classical final value: {classical_value.iloc[-1]:.6f}")
print(f"  Quantum final value: {quantum_value.iloc[-1]:.6f}")
print(f"  Quantum+Rebalanced final value: {quantum_rebal_value.iloc[-1]:.6f}")

# Calculate returns from values
print("\n[STEP 3] Computing returns from portfolio values...")

def returns_from_values(values):
    return np.log(values / values.shift(1)).dropna()

classical_ret = returns_from_values(classical_value)
quantum_ret = returns_from_values(quantum_value)
rebal_ret = returns_from_values(quantum_rebal_value)

print(f"  Classical mean daily return: {classical_ret.mean():.6f}")
print(f"  Quantum mean daily return: {quantum_ret.mean():.6f}")
print(f"  Rebalanced mean daily return: {rebal_ret.mean():.6f}")

# Rebalancing event analysis
print("\n[STEP 4] Analyzing rebalancing events...")
K = 15
rebalance_cadence = 63

dates_analyzed = []
rebalance_points = []

for i, dt in enumerate(test_dates):
    if i % rebalance_cadence == 0:
        rebalance_points.append((i, dt))

print(f"  Rebalancing events (every {rebalance_cadence} days): {len(rebalance_points)}")
print(f"  First rebalance at day {rebalance_points[0][0]}: {rebalance_points[0][1].date()}")
print(f"  Last rebalance at day {rebalance_points[-1][0]}: {rebalance_points[-1][1].date()}")

# Segment-by-segment performance analysis
print("\n[STEP 5] Performance by rebalancing segment...")

cumulative_return = 1.0
segment_returns = []

for seg_idx in range(len(rebalance_points)):
    if seg_idx < len(rebalance_points) - 1:
        start_day = rebalance_points[seg_idx][0]
        end_day = rebalance_points[seg_idx + 1][0]
    else:
        start_day = rebalance_points[seg_idx][0]
        end_day = len(test_r) - 1
    
    # Get values for this segment
    seg_val_start = quantum_rebal_value.iloc[start_day]
    seg_val_end = quantum_rebal_value.iloc[end_day]
    seg_return = (seg_val_end / seg_val_start - 1.0) * 100
    
    segment_returns.append({
        'segment': seg_idx,
        'start_date': test_dates[start_day].date(),
        'end_date': test_dates[end_day].date(),
        'days': end_day - start_day,
        'return_pct': seg_return,
        'start_value': seg_val_start,
        'end_value': seg_val_end
    })

seg_df = pd.DataFrame(segment_returns)
print("\n" + seg_df.to_string(index=False))

avg_segment_return = seg_df['return_pct'].mean()
print(f"\n  Average return per segment: {avg_segment_return:.2f}%")
print(f"  Number of segments: {len(segment_returns)}")

# Volatility and Sharpe analysis
print("\n[STEP 6] Risk-adjusted performance metrics...")

metrics_classical = compute_metrics(classical_value, rf=0.05)
metrics_quantum = compute_metrics(quantum_value, rf=0.05)
metrics_rebal = compute_metrics(quantum_rebal_value, rf=0.05)

print("\nClassical Portfolio:")
for k, v in metrics_classical.items():
    print(f"  {k}: {v:.4f}")

print("\nQuantum Portfolio:")
for k, v in metrics_quantum.items():
    print(f"  {k}: {v:.4f}")

print("\nQuantum+Rebalanced Portfolio:")
for k, v in metrics_rebal.items():
    print(f"  {k}: {v:.4f}")

# Rebalancing boost analysis
print("\n[STEP 7] Rebalancing boost quantification...")

boost = metrics_rebal['Total Return'] - metrics_quantum['Total Return']
boost_pct = (boost / metrics_quantum['Total Return']) * 100 if metrics_quantum['Total Return'] != 0 else 0

print(f"  Quantum return: {metrics_quantum['Total Return']:.4f} ({metrics_quantum['Total Return']*100:.2f}%)")
print(f"  Quantum+Rebalanced return: {metrics_rebal['Total Return']:.4f} ({metrics_rebal['Total Return']*100:.2f}%)")
print(f"  Boost from rebalancing: {boost:.4f} ({boost_pct:.2f}% improvement)")

# Monthly performance analysis
print("\n[STEP 8] Monthly performance analysis...")

# Group by month
pv_rebal_monthly = quantum_rebal_value.resample('M').last()
monthly_returns = np.log(pv_rebal_monthly / pv_rebal_monthly.shift(1)).dropna() * 100

print(f"  Months analyzed: {len(monthly_returns)}")
print(f"  Average monthly return: {monthly_returns.mean():.2f}%")
print(f"  Monthly return volatility: {monthly_returns.std():.2f}%")
print(f"  Best month: {monthly_returns.max():.2f}%")
print(f"  Worst month: {monthly_returns.min():.2f}%")
print(f"  Positive months: {(monthly_returns > 0).sum()} / {len(monthly_returns)}")

# Benchmark comparison
print("\n[STEP 9] Benchmark comparison...")

benchmark_df = pd.read_csv(data_dir / "11_benchmark_values.csv", index_col='Date', parse_dates=True)

print("\nBenchmark final values:")
for col in benchmark_df.columns:
    if benchmark_df[col].iloc[-1] > 0:
        bench_return = (benchmark_df[col].iloc[-1] / benchmark_df[col].iloc[0] - 1.0) * 100
        print(f"  {col}: {benchmark_df[col].iloc[-1]:.6f} ({bench_return:.2f}% return)")

rebal_return_pct = (quantum_rebal_value.iloc[-1] / quantum_rebal_value.iloc[0] - 1.0) * 100
print(f"\n  Quantum+Rebalanced: {quantum_rebal_value.iloc[-1]:.6f} ({rebal_return_pct:.2f}% return)")

if not benchmark_df.empty and 'BSE_500' in benchmark_df.columns:
    bse_return = (benchmark_df['BSE_500'].iloc[-1] / benchmark_df['BSE_500'].iloc[0] - 1.0) * 100
    outperformance = rebal_return_pct - bse_return
    print(f"\n  Outperformance vs BSE_500: {outperformance:.2f}%")

# Value path analysis
print("\n[STEP 10] Portfolio value milestones...")

milestones = [
    ("Start", 0),
    ("Day 252 (1 yr)", 252 if 252 < len(quantum_rebal_value) else len(quantum_rebal_value)-1),
    ("Day 630 (2.5 yr)", 630 if 630 < len(quantum_rebal_value) else len(quantum_rebal_value)-1),
    ("Day 1008 (4 yr)", 1008 if 1008 < len(quantum_rebal_value) else len(quantum_rebal_value)-1),
    ("End", len(quantum_rebal_value)-1),
]

for label, day_idx in milestones:
    val = quantum_rebal_value.iloc[day_idx]
    cum_ret = (val / quantum_rebal_value.iloc[0] - 1.0) * 100
    print(f"  {label:20s}: {val:10.2f} ({cum_ret:8.2f}%)")

print("\n" + "="*80)
print("VERIFICATION COMPLETE")
print("="*80)

# VERDICT
print("\n[VERDICT]")

if metrics_rebal['Total Return'] > 3.0:  # 300%+
    print("  WARNING: Rebalancing shows EXTREMELY HIGH performance (>300%)")
    print("  This requires verification of:")
    print("    1. Daily return calculations are correct")
    print("    2. Rebalancing frequency (63 days) is correct")
    print("    3. No double-counting or lookahead bias")
    print("    4. Transaction costs applied correctly")
    print("    5. Portfolio weights sum to 1.0 at each rebalance")
else:
    print("  Rebalancing performance is within expected range")

if np.isnan(metrics_rebal['Sharpe Ratio']):
    print("\n  ERROR: Sharpe ratio is NaN - check volatility calculation")
elif metrics_rebal['Sharpe Ratio'] > 2.0:
    print(f"\n  NOTE: Sharpe ratio of {metrics_rebal['Sharpe Ratio']:.4f} is very high")
    print("        (typically >2.0 is exceptional)")
else:
    print(f"\n  Sharpe ratio of {metrics_rebal['Sharpe Ratio']:.4f} is reasonable")

print("\n")
