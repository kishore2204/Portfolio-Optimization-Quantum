#!/usr/bin/env python3
"""
Master Runner for NIFTY 200 Comprehensive Portfolio Analysis
==========================================================

Orchestrates:
1. Scenario metrics generation (all scenarios/horizons/crashes)
2. Strategy comparison (Greedy vs Quantum vs Quantum+Rebalance)
3. Adaptive K determination
4. Final aggregated report generation

Uses NIFTY 200 universe for all scenarios.

Author: Enhanced Portfolio System
Date: March 2026
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import subprocess
import pandas as pd
import numpy as np

def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 90)
    print(f" {title.center(88)}")
    print("=" * 90 + "\n")

def run_step(step_name, script_path, description=""):
    """Run a Python script as a step"""
    print(f"\n[STEP] {step_name}")
    if description:
        print(f"       {description}")
    print(f"       Running: {script_path}")
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=Path(__file__).parent,
            capture_output=False,
            timeout=600
        )
        
        if result.returncode == 0:
            print(f"       ✓ Success")
            return True
        else:
            print(f"       ✗ Failed (exit code: {result.returncode})")
            return False
    except subprocess.TimeoutExpired:
        print(f"       ✗ Timeout")
        return False
    except Exception as e:
        print(f"       ✗ Error: {str(e)}")
        return False

def load_json(path):
    """Load JSON file"""
    with open(path, 'r') as f:
        return json.load(f)

def generate_final_report(output_dir: Path):
    """Generate final aggregated report"""
    
    print_header("GENERATING FINAL AGGREGATED REPORT")
    
    scenario_metrics_path = output_dir / 'scenario_metrics_nifty200.json'
    adaptive_k_path = output_dir / 'adaptive_k_report_nifty200.json'
    strategy_comparison_path = output_dir / 'strategy_comparison_nifty200_comprehensive.json'
    
    final_report = {
        'generated_at': datetime.now().isoformat(),
        'title': 'NIFTY 200 Portfolio Optimization - Comprehensive Analysis',
        'sections': {}
    }
    
    # Load scenario metrics
    if scenario_metrics_path.exists():
        print("Loading scenario metrics...")
        scenario_metrics = load_json(scenario_metrics_path)
        
        # Filter out None values
        valid_scenarios = {k: v for k, v in scenario_metrics.items() if v is not None}
        
        scenario_summary = {
            'total_scenarios': len(valid_scenarios),
            'avg_portfolio_sharpe': float(np.mean([
                s['portfolio_metrics']['test_sharpe'] 
                for s in valid_scenarios.values()
            ])) if valid_scenarios else 0
        }
        
        final_report['sections']['scenario_metrics'] = {
            'summary': scenario_summary,
            'count': len(valid_scenarios)
        }
        print(f"  OK Loaded {scenario_summary['total_scenarios']} scenarios")
    
    # Load adaptive K report
    if adaptive_k_path.exists():
        print("Loading adaptive K analysis...")
        adaptive_k = load_json(adaptive_k_path)
        final_report['sections']['adaptive_k_analysis'] = adaptive_k
        print(f"  OK Loaded adaptive K methodology")
    
    # Load strategy comparison
    if strategy_comparison_path.exists():
        print("Loading strategy comparison...")
        strategy_comp = load_json(strategy_comparison_path)
        final_report['sections']['strategy_comparison'] = strategy_comp
        print(f"  OK Loaded strategy comparison")
    
    # Generate summary statistics
    if 'strategy_comparison' in final_report['sections']:
        comp = final_report['sections']['strategy_comparison']
        final_report['summary'] = {
            'total_scenarios': comp.get('total_scenarios', 0),
            'system_performance': comp.get('summary', {}),
            'recommendations': generate_recommendations(comp.get('summary', {}))
        }
    
    # Save final report
    output_file = output_dir / 'final_analysis_report_nifty200.json'
    with open(output_file, 'w') as f:
        json.dump(final_report, f, indent=2, default=str)
    
    return final_report

def generate_recommendations(summary: dict) -> list:
    """Generate recommendations based on results"""
    recommendations = []
    
    if not summary:
        return recommendations
    
    wins = summary.get('strategy_wins', {})
    sharpes = summary.get('average_sharpe', {})
    outperf = summary.get('quantum_outperformance', {})
    
    # Check quantum performance
    if wins.get('Quantum_WithRebalance', 0) > wins.get('Greedy', 0):
        win_diff = wins['Quantum_WithRebalance'] - wins['Greedy']
        recommendations.append(
            f"Quantum strategy with adaptive rebalancing outperformed greedy selection by {win_diff} scenarios"
        )
    
    # Check Sharpe improvement
    quantum_sharpe = sharpes.get('Quantum_WithRebalance', 0)
    greedy_sharpe = sharpes.get('Greedy', 0)
    if quantum_sharpe > greedy_sharpe:
        improvement = (quantum_sharpe - greedy_sharpe) / (abs(greedy_sharpe) + 1e-6) * 100
        recommendations.append(
            f"Average Sharpe ratio improved by {improvement:.2f}% with quantum+rebalance"
        )
    
    if not recommendations:
        recommendations.append("Consider running with different K_sell values for further optimization")
    
    return recommendations

def print_summary(final_report):
    """Print summary of results"""
    
    print_header("FINAL ANALYSIS SUMMARY")
    
    if 'summary' in final_report:
        summary = final_report['summary']
        
        print(f"Total Scenarios Analyzed: {summary.get('total_scenarios', 0)}")
        
        if 'system_performance' in summary:
            perf = summary['system_performance']
            
            print(f"\nStrategy Performance:")
            wins = perf.get('strategy_wins', {})
            for strategy, win_count in wins.items():
                print(f"  {strategy}: {win_count} wins")
            
            print(f"\nAverage Sharpe Ratios:")
            sharpes = perf.get('average_sharpe', {})
            for strategy, sharpe in sharpes.items():
                print(f"  {strategy}: {sharpe:.4f}")
            
            outperf = perf.get('quantum_outperformance', {})
            if outperf:
                print(f"\nQuantum Outperformance:")
                print(f"  Wins vs Greedy: {outperf.get('vs_greedy', 0)}")
                print(f"  Sharpe Improvement: {outperf.get('sharpe_improvement', 0):.4f}")
        
        print(f"\nRecommendations:")
        for i, rec in enumerate(summary.get('recommendations', []), 1):
            print(f"  {i}. {rec}")

def main():
    """Main execution flow"""
    
    print_header("NIFTY 200 PORTFOLIO OPTIMIZATION - MASTER RUNNER")
    
    root_dir = Path(__file__).parent
    output_dir = root_dir / 'results'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Configuration:")
    print(f"  Root Directory: {root_dir}")
    print(f"  Output Directory: {output_dir}")
    print(f"  Universe: NIFTY 200")
    print(f"  Timestamp: {datetime.now().isoformat()}")
    
    # Step 1: Generate scenario metrics
    step1_ok = run_step(
        "Scenario Metrics Generation",
        root_dir / "scenario_metrics_generator.py",
        "Analyze all scenarios (crashes, bulls, present) with NIFTY 200"
    )
    
    # Step 2: Run strategy comparison
    step2_ok = run_step(
        "Strategy Comparison",
        root_dir / "strategy_comparison_nifty200.py",
        "Compare Greedy vs Quantum vs Quantum+Rebalance across scenarios"
    )
    
    # Step 3: Generate final report
    print_header("AGGREGATING RESULTS")
    final_report = generate_final_report(output_dir)
    
    # Print summary
    print_summary(final_report)
    
    # Print completion
    print_header("EXECUTION COMPLETE")
    
    print("Generated Output Files:")
    output_files = [
        'scenario_metrics_nifty200.json',
        'adaptive_k_report_nifty200.json',
        'strategy_comparison_nifty200_comprehensive.json',
        'final_analysis_report_nifty200.json'
    ]
    
    for filename in output_files:
        filepath = output_dir / filename
        status = "✓" if filepath.exists() else "✗"
        print(f"  {status} {filename}")
    
    print(f"\nAll results saved to: {output_dir}")
    print(f"Main report: {output_dir / 'final_analysis_report_nifty200.json'}")
    
    return 0 if (step1_ok and step2_ok) else 1

if __name__ == '__main__':
    sys.exit(main())
