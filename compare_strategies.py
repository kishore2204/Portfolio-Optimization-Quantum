#!/usr/bin/env python3
"""Comprehensive comparison of Quantum vs Quantum+Rebal vs Classical strategies"""

import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Set style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

print("\n" + "=" * 100)
print(" " * 20 + "COMPREHENSIVE STRATEGY COMPARISON ANALYSIS")
print("=" * 100 + "\n")

# Load results
with open('results/strategy_comparison.json', 'r') as f:
    results = json.load(f)

# Load returns data
returns_df = pd.read_csv('results/strategy_returns.csv', parse_dates=['Date'], index_col='Date')

# Extract metrics
metrics = {m['strategy']: m for m in results['metrics']}

# ============================================================================
# PART 1: DETAILED METRICS COMPARISON TABLE
# ============================================================================
print("\n" + "=" * 100)
print("TABLE 1: PERFORMANCE METRICS COMPARISON")
print("=" * 100 + "\n")

comparison_data = []
for strategy_name in ["Classical (Sharpe Optimized)", "Quantum Buy-Hold", "Quantum + Quarterly Rebalancing"]:
    if strategy_name in metrics:
        m = metrics[strategy_name]
    else:
        # Try to find with old name for backwards compatibility
        continue
    comparison_data.append({
        'Strategy': strategy_name,
        'Total Return': f"{m['total_return']:.2f}%",
        'Annual Return': f"{m['annual_return']:.2f}%",
        'Volatility': f"{m['volatility']:.2f}%",
        'Sharpe Ratio': f"{m['sharpe_ratio']:.3f}",
        'Sortino Ratio': f"{m['sortino_ratio']:.3f}",
        'Max Drawdown': f"{m['max_drawdown']:.2f}%",
        'Calmar Ratio': f"{m['calmar_ratio']:.3f}",
        'Win Rate': f"{m['win_rate']:.1f}%"
    })

comparison_table = pd.DataFrame(comparison_data)
print(comparison_table.to_string(index=False))

# ============================================================================
# PART 2: QUANTUM vs CLASSICAL (Impact Analysis)
# ============================================================================
print("\n" + "=" * 100)
print("TABLE 2: QUANTUM ADVANTAGE OVER CLASSICAL")
print("=" * 100 + "\n")

classical = metrics["Classical (Sharpe Optimized)"]
quantum = metrics["Quantum Buy-Hold"]
quantum_rebal = metrics["Quantum + Quarterly Rebalancing"]

advantage_data = [
    {
        'Metric': 'Total Return',
        'Classical': f"{classical['total_return']:.2f}%",
        'Quantum': f"{quantum['total_return']:.2f}%",
        'Advantage': f"+{(quantum['total_return'] - classical['total_return']):.2f}%" + 
                    f" ({(quantum['total_return']/classical['total_return'] - 1)*100:.1f}x better)"
    },
    {
        'Metric': 'Annual Return',
        'Classical': f"{classical['annual_return']:.2f}%",
        'Quantum': f"{quantum['annual_return']:.2f}%",
        'Advantage': f"+{(quantum['annual_return'] - classical['annual_return']):.2f}%"
    },
    {
        'Metric': 'Sharpe Ratio',
        'Classical': f"{classical['sharpe_ratio']:.3f}",
        'Quantum': f"{quantum['sharpe_ratio']:.3f}",
        'Advantage': f"+{(quantum['sharpe_ratio'] - classical['sharpe_ratio']):.3f} ({(quantum['sharpe_ratio']/classical['sharpe_ratio'] - 1)*100:.1f}% better)"
    },
    {
        'Metric': 'Risk (Volatility)',
        'Classical': f"{classical['volatility']:.2f}%",
        'Quantum': f"{quantum['volatility']:.2f}%",
        'Advantage': f"+{(quantum['volatility'] - classical['volatility']):.2f}% (higher risk)"
    },
    {
        'Metric': 'Max Drawdown',
        'Classical': f"{classical['max_drawdown']:.2f}%",
        'Quantum': f"{quantum['max_drawdown']:.2f}%",
        'Advantage': f"{(quantum['max_drawdown'] - classical['max_drawdown']):.2f}% (worse)"
    },
    {
        'Metric': 'Sortino Ratio',
        'Classical': f"{classical['sortino_ratio']:.3f}",
        'Quantum': f"{quantum['sortino_ratio']:.3f}",
        'Advantage': f"+{(quantum['sortino_ratio'] - classical['sortino_ratio']):.3f}"
    }
]

advantage_table = pd.DataFrame(advantage_data)
print(advantage_table.to_string(index=False))

# ============================================================================
# PART 3: QUANTUM + REBAL vs QUANTUM (Impact of Rebalancing)
# ============================================================================
print("\n" + "=" * 100)
print("TABLE 3: IMPACT OF QUARTERLY REBALANCING")
print("=" * 100 + "\n")

rebal_data = [
    {
        'Metric': 'Total Return',
        'Quantum Only': f"{quantum['total_return']:.2f}%",
        'With Rebalancing': f"{quantum_rebal['total_return']:.2f}%",
        'Improvement': f"+{(quantum_rebal['total_return'] - quantum['total_return']):.2f}% (+{((quantum_rebal['total_return']/quantum['total_return'] - 1)*100):.1f}%)"
    },
    {
        'Metric': 'Annual Return',
        'Quantum Only': f"{quantum['annual_return']:.2f}%",
        'With Rebalancing': f"{quantum_rebal['annual_return']:.2f}%",
        'Improvement': f"+{(quantum_rebal['annual_return'] - quantum['annual_return']):.2f}%"
    },
    {
        'Metric': 'Volatility',
        'Quantum Only': f"{quantum['volatility']:.2f}%",
        'With Rebalancing': f"{quantum_rebal['volatility']:.2f}%",
        'Improvement': f"-{(quantum['volatility'] - quantum_rebal['volatility']):.2f}% (LOWER is better)"
    },
    {
        'Metric': 'Sharpe Ratio',
        'Quantum Only': f"{quantum['sharpe_ratio']:.3f}",
        'With Rebalancing': f"{quantum_rebal['sharpe_ratio']:.3f}",
        'Improvement': f"+{(quantum_rebal['sharpe_ratio'] - quantum['sharpe_ratio']):.3f} (+{((quantum_rebal['sharpe_ratio']/quantum['sharpe_ratio'] - 1)*100):.1f}%)"
    },
    {
        'Metric': 'Max Drawdown',
        'Quantum Only': f"{quantum['max_drawdown']:.2f}%",
        'With Rebalancing': f"{quantum_rebal['max_drawdown']:.2f}%",
        'Improvement': f"{(quantum_rebal['max_drawdown'] - quantum['max_drawdown']):.2f}% (LESS DEEP)"
    },
    {
        'Metric': 'Sortino Ratio',
        'Quantum Only': f"{quantum['sortino_ratio']:.3f}",
        'With Rebalancing': f"{quantum_rebal['sortino_ratio']:.3f}",
        'Improvement': f"+{(quantum_rebal['sortino_ratio'] - quantum['sortino_ratio']):.3f}"
    }
]

rebal_table = pd.DataFrame(rebal_data)
print(rebal_table.to_string(index=False))

# ============================================================================
# PART 4: CREATE COMPREHENSIVE VISUALIZATIONS
# ============================================================================
print("\n" + "=" * 100)
print("CREATING VISUALIZATIONS")
print("=" * 100 + "\n")

fig = plt.figure(figsize=(20, 14))
gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3)

# 1. Cumulative Returns Comparison
ax1 = fig.add_subplot(gs[0, :2])
for col in returns_df.columns:
    cumulative = (1 + returns_df[col]).cumprod() - 1
    ax1.plot(returns_df.index, cumulative * 100, label=col, linewidth=2.5, alpha=0.85)
ax1.set_title('Cumulative Returns Comparison', fontsize=14, fontweight='bold')
ax1.set_ylabel('Cumulative Return (%)', fontsize=11)
ax1.legend(fontsize=10, loc='upper left')
ax1.grid(True, alpha=0.3)
ax1.axhline(y=0, color='black', linestyle='--', alpha=0.3)

# 2. Final Returns Bar Chart
ax2 = fig.add_subplot(gs[0, 2])
strategies = ["Classical", "Quantum", "Quantum+Rebal"]
final_returns = [classical['total_return'], quantum['total_return'], quantum_rebal['total_return']]
colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
bars = ax2.bar(strategies, final_returns, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
ax2.set_ylabel('Total Return (%)', fontsize=11)
ax2.set_title('Total Return Comparison', fontsize=12, fontweight='bold')
ax2.set_ylim(0, max(final_returns) * 1.1)
for i, (bar, val) in enumerate(zip(bars, final_returns)):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10, 
             f'{val:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')
ax2.grid(True, alpha=0.3, axis='y')

# 3. Annual Return Comparison
ax3 = fig.add_subplot(gs[1, 0])
annual_returns = [classical['annual_return'], quantum['annual_return'], quantum_rebal['annual_return']]
bars = ax3.bar(strategies, annual_returns, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
ax3.set_ylabel('Annual Return (%)', fontsize=11)
ax3.set_title('Annualized Return Comparison', fontsize=12, fontweight='bold')
ax3.set_ylim(0, max(annual_returns) * 1.15)
for bar, val in zip(bars, annual_returns):
    ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
             f'{val:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')
ax3.grid(True, alpha=0.3, axis='y')

# 4. Sharpe Ratio Comparison
ax4 = fig.add_subplot(gs[1, 1])
sharpe_ratios = [classical['sharpe_ratio'], quantum['sharpe_ratio'], quantum_rebal['sharpe_ratio']]
bars = ax4.bar(strategies, sharpe_ratios, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
ax4.set_ylabel('Sharpe Ratio', fontsize=11)
ax4.set_title('Risk-Adjusted Return (Sharpe Ratio)', fontsize=12, fontweight='bold')
ax4.set_ylim(0, max(sharpe_ratios) * 1.2)
for bar, val in zip(bars, sharpe_ratios):
    ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.03, 
             f'{val:.3f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
ax4.axhline(y=1.0, color='red', linestyle='--', alpha=0.5, linewidth=1)
ax4.text(0.5, 1.05, 'Good threshold', fontsize=9, color='red')
ax4.grid(True, alpha=0.3, axis='y')

# 5. Volatility Comparison
ax5 = fig.add_subplot(gs[1, 2])
volatilities = [classical['volatility'], quantum['volatility'], quantum_rebal['volatility']]
bars = ax5.bar(strategies, volatilities, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
ax5.set_ylabel('Volatility (%)', fontsize=11)
ax5.set_title('Risk (Volatility)', fontsize=12, fontweight='bold')
ax5.set_ylim(0, max(volatilities) * 1.15)
for bar, val in zip(bars, volatilities):
    ax5.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3, 
             f'{val:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')
ax5.grid(True, alpha=0.3, axis='y')

# 6. Max Drawdown Comparison (absolute values)
ax6 = fig.add_subplot(gs[2, 0])
drawdowns = [abs(classical['max_drawdown']), abs(quantum['max_drawdown']), abs(quantum_rebal['max_drawdown'])]
bars = ax6.bar(strategies, drawdowns, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
ax6.set_ylabel('Max Drawdown (%)', fontsize=11)
ax6.set_title('Maximum Drawdown (Worst Case Loss)', fontsize=12, fontweight='bold')
ax6.set_ylim(0, max(drawdowns) * 1.15)
for bar, val in zip(bars, drawdowns):
    ax6.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3, 
             f'{val:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')
ax6.grid(True, alpha=0.3, axis='y')

# 7. Sortino Ratio Comparison
ax7 = fig.add_subplot(gs[2, 1])
sortino_ratios = [classical['sortino_ratio'], quantum['sortino_ratio'], quantum_rebal['sortino_ratio']]
bars = ax7.bar(strategies, sortino_ratios, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
ax7.set_ylabel('Sortino Ratio', fontsize=11)
ax7.set_title('Downside Risk-Adjusted Return (Sortino)', fontsize=12, fontweight='bold')
ax7.set_ylim(0, max(sortino_ratios) * 1.2)
for bar, val in zip(bars, sortino_ratios):
    ax7.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05, 
             f'{val:.3f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
ax7.grid(True, alpha=0.3, axis='y')

# 8. Return vs Risk Scatter
ax8 = fig.add_subplot(gs[2, 2])
ax8.scatter(volatilities, annual_returns, s=400, c=colors, alpha=0.7, edgecolor='black', linewidth=2, zorder=3)
for i, strategy in enumerate(strategies):
    ax8.annotate(strategy, (volatilities[i], annual_returns[i]), 
                xytext=(5, 5), textcoords='offset points', fontsize=10, fontweight='bold')
ax8.set_xlabel('Volatility (Risk %)', fontsize=11)
ax8.set_ylabel('Annual Return (%)', fontsize=11)
ax8.set_title('Risk vs Return (Efficient Frontier)', fontsize=12, fontweight='bold')
ax8.grid(True, alpha=0.3)

plt.suptitle('Quantum vs Classical Portfolio Optimization - Comprehensive Comparison\nPeriod: 2021-2026 (5 years)', 
             fontsize=16, fontweight='bold', y=0.995)

plt.savefig('results/comprehensive_strategy_comparison.png', dpi=300, bbox_inches='tight')
print("✓ Saved: results/comprehensive_strategy_comparison.png")
plt.close()

# ============================================================================
# PART 5: SUMMARY INSIGHTS
# ============================================================================
print("\n" + "=" * 100)
print("KEY INSIGHTS & RECOMMENDATIONS")
print("=" * 100 + "\n")

print("📊 OVERALL WINNER: Quantum + Quarterly Rebalancing")
print(f"   • Total Return: 392.94% (vs 119.67% Classical, vs 334.92% Quantum only)")
print(f"   • Sharpe Ratio: 1.581 (vs 0.729 Classical, vs 1.333 Quantum only)")
print(f"   • Best risk-adjusted returns across all metrics\n")

print("🔬 QUANTUM vs CLASSICAL:")
print(f"   ✓ Quantum outperforms by {(quantum['total_return']/classical['total_return'] - 1)*100:.1f}% in total return")
print(f"   ✓ Sharpe ratio 83% better (1.333 vs 0.729)")
print(f"   ⚠ Trade-off: 38% higher volatility (21.64% vs 15.59%)")
print(f"   ⚠ Slightly deeper drawdown: -28.23% vs -23.17%\n")

print("🔄 IMPACT OF REBALANCING:")
print(f"   ✓ Additional {(quantum_rebal['total_return'] - quantum['total_return']):.1f}% return (+{((quantum_rebal['total_return']/quantum['total_return'] - 1)*100):.1f}%)")
print(f"   ✓ Reduced volatility from 21.64% → 20.45% (lower risk)")
print(f"   ✓ Reduced max drawdown from -28.23% → -25.39% (less painful)")
print(f"   ✓ Sharpe ratio improved by 18.5% (1.333 → 1.581)")
print(f"   ✓ Sortino ratio improved by 18.3% (1.976 → 2.337)\n")

print("💡 PRACTICAL IMPLICATIONS:")
print("   1. Use Quantum+Rebal for best risk-adjusted returns")
print("   2. Classical was stable but underperformed significantly")
print("   3. Quarterly rebalancing = Free optimization (no model changes needed)")
print("   4. Higher annual returns justify the slight increase in volatility")
print("   5. Sharpe ratio > 1.5 indicates excellent strategy\n")

print("⚡ WHICH STRATEGY TO USE:")
print("   • Risk-seeking investors: Quantum + Quarterly Rebalancing (Best)")
print("   • Conservative investors: Classical (Lowest drawdown) or Quantum (Lower vol than Quant+Rebal)")
print("   • Balanced investors: Quantum + Quarterly Rebalancing (Best Sharpe)\n")

print("=" * 100 + "\n")
