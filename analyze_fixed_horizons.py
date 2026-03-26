"""
Fixed Horizon Analysis: 10Y, 5Y, 1Y
Generates strategy comparison graphs for each time horizon
"""

import pandas as pd
import numpy as np
import os
import json
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['font.size'] = 10

def calculate_metrics(returns_series):
    """Calculate 8 key metrics from daily returns"""
    total_return = (1 + returns_series).prod() - 1
    num_days = len(returns_series)
    annual_return = (1 + total_return) ** (252 / num_days) - 1
    volatility = returns_series.std() * np.sqrt(252)
    
    # Sharpe Ratio (assuming 6% risk-free rate)
    rfr = 0.06
    sharpe = (annual_return - rfr) / volatility if volatility > 0 else 0
    
    # Sortino Ratio (downside volatility)
    downside_returns = returns_series[returns_series < 0]
    downside_std = downside_returns.std() * np.sqrt(252)
    sortino = (annual_return - rfr) / downside_std if downside_std > 0 else 0
    
    # Max Drawdown
    cumsum = (1 + returns_series).cumprod()
    running_max = cumsum.expanding().max()
    drawdown = (cumsum - running_max) / running_max
    max_drawdown = drawdown.min()
    
    # Calmar Ratio
    calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
    
    # Win Rate
    win_rate = (returns_series > 0).sum() / len(returns_series)
    
    return {
        'Total Return': total_return,
        'Annual Return': annual_return,
        'Volatility': volatility,
        'Sharpe': sharpe,
        'Sortino': sortino,
        'Max Drawdown': max_drawdown,
        'Calmar': calmar,
        'Win Rate': win_rate
    }

def generate_comparison_graphs(horizon_returns, horizon_name, strategy_names):
    """Generate 3-panel comparison graph for a horizon"""
    
    metrics_data = {}
    for strategy in strategy_names:
        if strategy in horizon_returns.columns:
            metrics_data[strategy] = calculate_metrics(horizon_returns[strategy].dropna())
    
    # 3-panel figure
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle(f'{horizon_name} Analysis - Strategy Comparison', fontsize=14, fontweight='bold')
    
    # Panel 1: Cumulative Returns
    ax1 = axes[0]
    for strategy in strategy_names:
        if strategy in horizon_returns.columns:
            cum_returns = (1 + horizon_returns[strategy].dropna()).cumprod()
            ax1.plot(cum_returns.index, cum_returns.values, label=strategy, linewidth=2)
    ax1.set_title('Cumulative Returns', fontweight='bold')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Growth of $1')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Panel 2: Total Return Bars
    ax2 = axes[1]
    total_returns = [metrics_data[s]['Total Return'] * 100 for s in strategy_names if s in metrics_data]
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    bars = ax2.bar(range(len(strategy_names)), total_returns, color=colors[:len(strategy_names)])
    ax2.set_title('Total Return (%)', fontweight='bold')
    ax2.set_xticks(range(len(strategy_names)))
    ax2.set_xticklabels(strategy_names, rotation=15, ha='right')
    ax2.set_ylabel('Return (%)')
    # Add value labels on bars
    for i, (bar, val) in enumerate(zip(bars, total_returns)):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5, f'{val:.1f}%', 
                ha='center', va='bottom', fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')
    
    # Panel 3: Risk vs Return Scatter (Sharpe Analysis)
    ax3 = axes[2]
    for i, strategy in enumerate(strategy_names):
        if strategy in metrics_data:
            ax3.scatter(metrics_data[strategy]['Volatility'] * 100, 
                       metrics_data[strategy]['Annual Return'] * 100,
                       s=300, alpha=0.6, color=colors[i], label=strategy)
            # Annotate with Sharpe ratio
            sharpe = metrics_data[strategy]['Sharpe']
            ax3.annotate(f"Sharpe: {sharpe:.2f}", 
                        xy=(metrics_data[strategy]['Volatility'] * 100, 
                            metrics_data[strategy]['Annual Return'] * 100),
                        xytext=(5, 5), textcoords='offset points', fontsize=9)
    ax3.set_title('Risk vs Return (Sharpe Analysis)', fontweight='bold')
    ax3.set_xlabel('Volatility (Annual %)')
    ax3.set_ylabel('Annual Return (%)')
    ax3.legend(loc='best')
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig, metrics_data

def main():
    # Load data
    prices_file = 'Dataset/prices_timeseries_complete.csv'
    returns_file = 'results/strategy_returns.csv'
    
    if not os.path.exists(prices_file):
        print(f"Error: {prices_file} not found")
        return
    if not os.path.exists(returns_file):
        print(f"Error: {returns_file} not found")
        return
    
    # Load complete price dataset
    complete_df = pd.read_csv(prices_file, parse_dates=['Date'], index_col='Date')
    start_date = complete_df.index.min()
    end_date = complete_df.index.max()
    
    print(f"Dataset Range: {start_date.date()} to {end_date.date()}")
    
    # Load strategy returns
    returns_df = pd.read_csv(returns_file, parse_dates=['Date'], index_col='Date')
    
    # Define horizons
    horizons = {
        '10Y': end_date - timedelta(days=365*10),
        '5Y': end_date - timedelta(days=365*5),
        '1Y': end_date - timedelta(days=365*1)
    }
    
    strategy_names = ['classical', 'quantum', 'quantum_rebalanced']
    summary = {}
    
    # Create output directory
    os.makedirs('results/horizon_analysis', exist_ok=True)
    
    # Analyze each horizon
    for horizon_name, horizon_start in horizons.items():
        print(f"\n=== {horizon_name} Analysis ===")
        
        # Filter data for this horizon
        horizon_data = returns_df[(returns_df.index >= horizon_start) & (returns_df.index <= end_date)]
        
        if horizon_data.empty:
            print(f"No data for {horizon_name}")
            continue
        
        print(f"Period: {horizon_data.index.min().date()} to {horizon_data.index.max().date()}")
        print(f"Trading Days: {len(horizon_data)}")
        
        # Generate comparison graph
        fig, metrics_data = generate_comparison_graphs(horizon_data, horizon_name, strategy_names)
        
        # Save figure
        output_file = f'results/horizon_analysis/comparison_{horizon_name}.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Saved: {output_file}")
        plt.close(fig)
        
        # Store metrics
        summary[horizon_name] = {}
        for strategy, metrics in metrics_data.items():
            summary[horizon_name][strategy] = {
                'Total Return (%)': round(metrics['Total Return'] * 100, 2),
                'Annual Return (%)': round(metrics['Annual Return'] * 100, 2),
                'Volatility (%)': round(metrics['Volatility'] * 100, 2),
                'Sharpe Ratio': round(metrics['Sharpe'], 3),
                'Sortino Ratio': round(metrics['Sortino'], 3),
                'Max Drawdown (%)': round(metrics['Max Drawdown'] * 100, 2),
                'Calmar Ratio': round(metrics['Calmar'], 3),
                'Win Rate (%)': round(metrics['Win Rate'] * 100, 2)
            }
        
        # Print metrics table
        print(f"\n{horizon_name} Metrics:")
        print("-" * 100)
        print(f"{'Strategy':<20} {'Total Return':<15} {'Annual Return':<15} {'Volatility':<12} {'Sharpe':<10}")
        print("-" * 100)
        for strategy, metrics in summary[horizon_name].items():
            print(f"{strategy:<20} {metrics['Total Return (%)']:>6.2f}% {metrics['Annual Return (%)']:>12.2f}% {metrics['Volatility (%)']:>10.2f}% {metrics['Sharpe Ratio']:>8.3f}")
        print("-" * 100)
    
    # Save summary to JSON
    with open('results/horizon_analysis/horizon_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    print("\nSaved summary to: results/horizon_analysis/horizon_summary.json")
    
    print("\n=== Analysis Complete ===")
    print("Generated graphs:")
    print("  - results/horizon_analysis/comparison_10Y.png")
    print("  - results/horizon_analysis/comparison_5Y.png")
    print("  - results/horizon_analysis/comparison_1Y.png")

if __name__ == '__main__':
    main()
