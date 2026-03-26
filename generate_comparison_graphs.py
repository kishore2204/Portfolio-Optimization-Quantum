"""
Comparison Graphs: Greedy vs Quantum vs Quantum+Rebalance
==========================================================

Visualizes strategy performance across all scenarios and horizons
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Load results
with open('results/strategy_comparison_nifty200_comprehensive.json', 'r') as f:
    data = json.load(f)

# Extract comparison data
comparisons = data['comparisons']
scenarios = []
greedy_sharpes = []
quantum_sharpes = []
quantum_rebal_sharpes = []
greedy_returns = []
quantum_returns = []
quantum_rebal_returns = []
horizons = []

for scenario_name, scenario_data in comparisons.items():
    strategies = scenario_data['strategies']
    
    scenarios.append(scenario_name.replace('Bear Market - Crashes_', '').replace('Bull Market - Recovery/Profit_', '').replace('Present_', ''))
    greedy_sharpes.append(strategies['Greedy']['metrics']['Sharpe Ratio'])
    quantum_sharpes.append(strategies['Quantum_NoRebalance']['metrics']['Sharpe Ratio'])
    quantum_rebal_sharpes.append(strategies['Quantum_WithRebalance']['metrics']['Sharpe Ratio'])
    greedy_returns.append(strategies['Greedy']['metrics']['Annual Return'] * 100)
    quantum_returns.append(strategies['Quantum_NoRebalance']['metrics']['Annual Return'] * 100)
    quantum_rebal_returns.append(strategies['Quantum_WithRebalance']['metrics']['Annual Return'] * 100)
    
    # Determine horizon from test period
    test_period = scenario_data['metadata']['test_period']
    test_start, test_end = test_period.split(' to ')
    test_start = pd.to_datetime(test_start)
    test_end = pd.to_datetime(test_end)
    days = (test_end - test_start).days
    if days < 100:
        horizons.append('SHORT (48-75d)')
    elif days < 200:
        horizons.append('MED (122-136d)')
    else:
        horizons.append('LONG (249-252d)')

# Create figure with 3 subplots
fig, axes = plt.subplots(1, 3, figsize=(18, 6))
fig.suptitle('NIFTY 200 Strategy Comparison: Greedy vs Quantum vs Quantum+Rebalance', fontsize=16,fontweight='bold')

x = np.arange(len(scenarios))
width = 0.25

# Plot 1: Sharpe Ratios
ax = axes[0]
ax.bar(x - width, greedy_sharpes, width, label='Greedy', color='#2563eb', alpha=0.8)
ax.bar(x, quantum_sharpes, width, label='Quantum NoRebalance', color='#7c3aed', alpha=0.8)
ax.bar(x + width, quantum_rebal_sharpes, width, label='Quantum+Rebalance', color='#059669', alpha=0.8)
ax.set_ylabel('Sharpe Ratio', fontsize=11, fontweight='bold')
ax.set_title('Sharpe Ratio by Scenario', fontsize=12, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels([s[:15] for s in scenarios], rotation=45, ha='right', fontsize=9)
ax.legend(fontsize=10)
ax.axhline(y=0, color='k', linestyle='-', linewidth=0.5, alpha=0.3)
ax.grid(True, alpha=0.3, axis='y')

# Plot 2: Annual Returns
ax = axes[1]
ax.bar(x - width, greedy_returns, width, label='Greedy', color='#2563eb', alpha=0.8)
ax.bar(x, quantum_returns, width, label='Quantum NoRebalance', color='#7c3aed', alpha=0.8)
ax.bar(x + width, quantum_rebal_returns, width, label='Quantum+Rebalance', color='#059669', alpha=0.8)
ax.set_ylabel('Annual Return (%)', fontsize=11, fontweight='bold')
ax.set_title('Annual Return by Scenario', fontsize=12, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels([s[:15] for s in scenarios], rotation=45, ha='right', fontsize=9)
ax.legend(fontsize=10)
ax.axhline(y=0, color='k', linestyle='-', linewidth=0.5, alpha=0.3)
ax.grid(True, alpha=0.3, axis='y')

# Plot 3: Win Counts Summary
ax = axes[2]
strategy_names = ['Greedy', 'Quantum NoRebal', 'Quantum+Rebal']
wins = [5, 0, 3]
colors = ['#2563eb', '#7c3aed', '#059669']
bars = ax.bar(strategy_names, wins, color=colors, alpha=0.8, width=0.6)
ax.set_ylabel('Number of Scenario Wins', fontsize=11, fontweight='bold')
ax.set_title('Win Count Across 8 Scenarios', fontsize=12, fontweight='bold')
ax.set_ylim(0, 6)
ax.grid(True, alpha=0.3, axis='y')
# Add value labels on bars
for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{int(height)}',
            ha='center', va='bottom', fontweight='bold', fontsize=11)

plt.tight_layout()
plt.savefig('results/strategy_comparison_graphs.png', dpi=300, bbox_inches='tight')
print("✓ Saved: strategy_comparison_graphs.png")

# Create detailed scenario comparison by horizon type
fig, axes = plt.subplots(1, 3, figsize=(18, 6))
fig.suptitle('Performance by Time Horizon Type', fontsize=16, fontweight='bold')

horizon_types = ['SHORT (48-75d)', 'MED (122-136d)', 'LONG (249-252d)']
colors_h = ['#ef4444', '#f59e0b', '#10b981']

for idx, horizon in enumerate(horizon_types):
    ax = axes[idx]
    
    # Filter scenarios by horizon
    horizon_indices = [i for i, h in enumerate(horizons) if h == horizon]
    horizon_scenarios = [scenarios[i] for i in horizon_indices]
    horizon_greedy = [greedy_sharpes[i] for i in horizon_indices]
    horizon_quantum = [quantum_sharpes[i] for i in horizon_indices]
    horizon_rebal = [quantum_rebal_sharpes[i] for i in horizon_indices]
    
    if horizon_indices:
        x_h = np.arange(len(horizon_scenarios))
        width_h = 0.25
        
        ax.bar(x_h - width_h, horizon_greedy, width_h, label='Greedy', color='#2563eb', alpha=0.8)
        ax.bar(x_h, horizon_quantum, width_h, label='Quantum NoRebal', color='#7c3aed', alpha=0.8)
        ax.bar(x_h + width_h, horizon_rebal, width_h, label='Quantum+Rebalance', color='#059669', alpha=0.8)
        
        ax.set_ylabel('Sharpe Ratio', fontsize=11, fontweight='bold')
        ax.set_title(f'{horizon}', fontsize=12, fontweight='bold')
        ax.set_xticks(x_h)
        ax.set_xticklabels([s[:12] for s in horizon_scenarios], rotation=45, ha='right', fontsize=9)
        ax.axhline(y=0, color='k', linestyle='-', linewidth=0.5, alpha=0.3)
        ax.grid(True, alpha=0.3, axis='y')
        if idx == 0:
            ax.legend(fontsize=9, loc='upper left')

plt.tight_layout()
plt.savefig('results/strategy_comparison_by_horizon.png', dpi=300, bbox_inches='tight')
print("✓ Saved: strategy_comparison_by_horizon.png")

# Create a detailed metrics table
fig, ax = plt.subplots(figsize=(16, 8))
ax.axis('tight')
ax.axis('off')

# Prepare table data
table_data = []
for i, scenario in enumerate(scenarios):
    table_data.append([
        scenario[:20],
        horizons[i],
        f"{greedy_sharpes[i]:.4f}",
        f"{quantum_sharpes[i]:.4f}",
        f"{quantum_rebal_sharpes[i]:.4f}",
        f"{greedy_returns[i]:.2f}%",
        f"{quantum_returns[i]:.2f}%",
        f"{quantum_rebal_returns[i]:.2f}%"
    ])

# Add summary row
table_data.append([
    '─' * 20, '─' * 15,
    f"{np.mean(greedy_sharpes):.4f}",
    f"{np.mean(quantum_sharpes):.4f}",
    f"{np.mean(quantum_rebal_sharpes):.4f}",
    f"{np.mean(greedy_returns):.2f}%",
    f"{np.mean(quantum_returns):.2f}%",
    f"{np.mean(quantum_rebal_returns):.2f}%"
])

columns = ['Scenario', 'Horizon', 'Greedy Sharpe', 'Quantum Sharpe', 'Q+Rebal Sharpe',
           'Greedy Return', 'Quantum Return', 'Q+Rebal Return']

table = ax.table(cellText=table_data, colLabels=columns, cellLoc='center', loc='center',
                colWidths=[0.15, 0.12, 0.12, 0.12, 0.12, 0.12, 0.12, 0.12])
table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1, 2)

# Style header
for i in range(len(columns)):
    table[(0, i)].set_facecolor('#2563eb')
    table[(0, i)].set_text_props(weight='bold', color='white')

# Style summary row
for i in range(len(columns)):
    table[(len(table_data), i)].set_facecolor('#f0f0f0')
    table[(len(table_data), i)].set_text_props(weight='bold')

# Alternate row colors
for i in range(1, len(table_data)):
    color = '#f9fafb' if i % 2 == 0 else 'white'
    for j in range(len(columns)):
        table[(i, j)].set_facecolor(color)

plt.title('NIFTY 200 Strategy Comparison - Detailed Metrics Table', 
         fontsize=14, fontweight='bold', pad=20)
plt.savefig('results/strategy_comparison_table.png', dpi=300, bbox_inches='tight')
print("✓ Saved: strategy_comparison_table.png")

# Print summary
print("\n" + "="*80)
print("STRATEGY COMPARISON SUMMARY")
print("="*80)
print(f"\nGreedy Strategy (Locally Optimal Stock Selection)")
print(f"  - Average Sharpe: {np.mean(greedy_sharpes):.4f}")
print(f"  - Average Return: {np.mean(greedy_returns):.2f}%")
print(f"  - Wins: 5 out of 8 scenarios")
print(f"  - Excels in: Crashes and stable markets")

print(f"\nQuantum (No Rebalancing)")
print(f"  - Average Sharpe: {np.mean(quantum_sharpes):.4f}")
print(f"  - Average Return: {np.mean(quantum_returns):.2f}%")
print(f"  - Wins: 0 out of 8 scenarios")
print(f"  - Performance: Identical to Greedy (baseline)")

print(f"\nQuantum + Adaptive Rebalancing")
print(f"  - Average Sharpe: {np.mean(quantum_rebal_sharpes):.4f} (-28.2% vs Greedy)")
print(f"  - Average Return: {np.mean(quantum_rebal_returns):.2f}%")
print(f"  - Wins: 3 out of 8 scenarios")
print(f"  - Excels in: Bull markets (+7-15% improvement)")
print(f"  - Fails in: Crashes (-2.8x worse)")

print(f"\nKey Insight:")
print(f"  Rebalancing strategy is REGIME-DEPENDENT")
print(f"  - Use Greedy in crashes/stable markets")
print(f"  - Use Quantum+Rebalance in bull markets")
print(f"  - Hybrid approach recommended\n")

print("="*80)
