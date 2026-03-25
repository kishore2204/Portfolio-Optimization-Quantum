#!/usr/bin/env python3
"""
Generate comprehensive comparison summary for rebalancing analysis.
"""

import json
import pandas as pd

def generate_comparison_table():
    """Generate comprehensive comparison table."""
    
    print("[SUMMARY] Generating comprehensive comparison table...\n")
    
    # Load results
    with open('results/unified_train_test_compare.json', 'r') as f:
        report = json.load(f)
    
    # Compile data
    comparison_data = []
    
    # Horizon results
    print("=" * 120)
    print("HORIZON SCENARIOS (Long-term Performance)")
    print("=" * 120)
    
    for scenario_name, scenario_data in report['horizon_results'].items():
        methods = scenario_data['methods']
        
        comparison_data.append({
            'Type': 'Horizon',
            'Scenario': scenario_name,
            'Quantum': f"{methods['Quantum_NoRebalance']['total_return']:.2f}%",
            'Quantum+Rebal': f"{methods['Quantum_Rebalanced']['total_return']:.2f}%",
            'Baseline': f"{methods['Markowitz']['total_return']:.2f}%",
            'Sharpe Q': f"{methods['Quantum_NoRebalance']['sharpe']:.2f}",
            'Sharpe Q+R': f"{methods['Quantum_Rebalanced']['sharpe']:.2f}",
            'Sharpe Base': f"{methods['Markowitz']['sharpe']:.2f}",
            'Winner': 'Quantum+Rebal' if methods['Quantum_Rebalanced']['total_return'] > max(
                methods['Quantum_NoRebalance']['total_return'],
                methods['Markowitz']['total_return']
            ) else ('Quantum' if methods['Quantum_NoRebalance']['total_return'] > methods['Markowitz']['total_return'] else 'Baseline')
        })
        
        print(f"\n{scenario_name}:")
        print(f"  Quantum (No Rebal):   Return={methods['Quantum_NoRebalance']['total_return']:7.2f}% | Sharpe={methods['Quantum_NoRebalance']['sharpe']:6.2f} | Max DD={methods['Quantum_NoRebalance']['max_drawdown']:7.2f}%")
        print(f"  Quantum + Rebal:      Return={methods['Quantum_Rebalanced']['total_return']:7.2f}% | Sharpe={methods['Quantum_Rebalanced']['sharpe']:6.2f} | Max DD={methods['Quantum_Rebalanced']['max_drawdown']:7.2f}%")
        print(f"  Markowitz Baseline:   Return={methods['Markowitz']['total_return']:7.2f}% | Sharpe={methods['Markowitz']['sharpe']:6.2f} | Max DD={methods['Markowitz']['max_drawdown']:7.2f}%")
        
        # Calculate impact
        rebal_impact = methods['Quantum_Rebalanced']['total_return'] - methods['Quantum_NoRebalance']['total_return']
        quantum_vs_baseline = methods['Quantum_NoRebalance']['total_return'] - methods['Markowitz']['total_return']
        
        print(f"  └─ Rebalancing Impact: {rebal_impact:+.2f}% {'↓' if rebal_impact < 0 else '↑'}")
        print(f"  └─ Quantum vs Baseline: {quantum_vs_baseline:+.2f}% {'↓' if quantum_vs_baseline < 0 else '↑'}")
    
    # Crash results
    print("\n" + "=" * 120)
    print("CRASH SCENARIOS (Stress Period Performance)")
    print("=" * 120)
    
    for scenario_name, scenario_data in report['crash_results'].items():
        methods = scenario_data['methods']
        
        comparison_data.append({
            'Type': 'Crash',
            'Scenario': scenario_name,
            'Quantum': f"{methods['Quantum_NoRebalance']['total_return']:.2f}%",
            'Quantum+Rebal': f"{methods['Quantum_Rebalanced']['total_return']:.2f}%",
            'Baseline': f"{methods['Markowitz']['total_return']:.2f}%",
            'Sharpe Q': f"{methods['Quantum_NoRebalance']['sharpe']:.2f}",
            'Sharpe Q+R': f"{methods['Quantum_Rebalanced']['sharpe']:.2f}",
            'Sharpe Base': f"{methods['Markowitz']['sharpe']:.2f}",
            'Winner': 'Quantum+Rebal' if methods['Quantum_Rebalanced']['total_return'] > max(
                methods['Quantum_NoRebalance']['total_return'],
                methods['Markowitz']['total_return']
            ) else ('Quantum' if methods['Quantum_NoRebalance']['total_return'] > methods['Markowitz']['total_return'] else 'Baseline')
        })
        
        print(f"\n{scenario_name}:")
        print(f"  Quantum (No Rebal):   Return={methods['Quantum_NoRebalance']['total_return']:7.2f}% | Sharpe={methods['Quantum_NoRebalance']['sharpe']:6.2f} | Max DD={methods['Quantum_NoRebalance']['max_drawdown']:7.2f}%")
        print(f"  Quantum + Rebal:      Return={methods['Quantum_Rebalanced']['total_return']:7.2f}% | Sharpe={methods['Quantum_Rebalanced']['sharpe']:6.2f} | Max DD={methods['Quantum_Rebalanced']['max_drawdown']:7.2f}%")
        print(f"  Markowitz Baseline:   Return={methods['Markowitz']['total_return']:7.2f}% | Sharpe={methods['Markowitz']['sharpe']:6.2f} | Max DD={methods['Markowitz']['max_drawdown']:7.2f}%")
        
        # Calculate impact
        rebal_impact = methods['Quantum_Rebalanced']['total_return'] - methods['Quantum_NoRebalance']['total_return']
        quantum_vs_baseline = methods['Quantum_NoRebalance']['total_return'] - methods['Markowitz']['total_return']
        
        print(f"  └─ Rebalancing Impact: {rebal_impact:+.2f}% {'↓' if rebal_impact < 0 else '↑'}")
        print(f"  └─ Quantum vs Baseline: {quantum_vs_baseline:+.2f}% {'↓' if quantum_vs_baseline < 0 else '↑'}")
    
    # Summary statistics
    print("\n" + "=" * 120)
    print("SUMMARY STATISTICS")
    print("=" * 120)
    
    df = pd.DataFrame(comparison_data)
    
    print("\nWinner Count (by Return):")
    winner_counts = df['Winner'].value_counts()
    for method, count in winner_counts.items():
        print(f"  {method}: {count} scenarios")
    
    # Save as CSV
    csv_path = 'results/full_rebalance_comparison_summary.csv'
    df.to_csv(csv_path, index=False)
    print(f"\n✓ Full comparison table saved to: {csv_path}")

if __name__ == '__main__':
    generate_comparison_table()
