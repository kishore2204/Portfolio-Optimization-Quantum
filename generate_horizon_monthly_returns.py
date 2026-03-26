"""
Generate 4 Separate Horizon Graphs with Monthly Returns
========================================================
Creates individual line graphs for each horizon (6M, 12M, 24M, 36M)
showing monthly returns comparison between Classical, Quantum, and Quantum+Rebal strategies.

Author: Enhanced Portfolio System
Date: March 2026
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import json
import warnings
warnings.filterwarnings('ignore')

plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

class HorizonMonthlyReturnsGenerator:
    
    def __init__(self, results_dir='results', output_dir='results/horizon_analysis'):
        self.results_dir = Path(results_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load strategy returns
        self.strategy_returns = self._load_strategy_returns()
        
        # Define horizons
        self.horizons = {
            '6M': 126,    # ~6 months of trading days
            '12M': 252,   # ~1 year
            '24M': 504,   # ~2 years
            '36M': 756    # ~3 years
        }
        
    def _load_strategy_returns(self):
        """Load daily returns for all strategies"""
        csv_file = self.results_dir / 'strategy_returns.csv'
        
        if not csv_file.exists():
            raise FileNotFoundError(f"Expected {csv_file} with strategy returns")
        
        df = pd.read_csv(csv_file, index_col='Date', parse_dates=True)
        return df
    
    def _aggregate_to_monthly(self, daily_returns):
        """Convert daily returns to monthly returns"""
        # Compound daily returns to get monthly returns
        daily_df = pd.DataFrame(daily_returns)
        monthly_returns = (1 + daily_df).resample('ME').prod() - 1
        return monthly_returns
    
    def _create_horizon_graph(self, horizon_name, horizon_days):
        """Create a line graph for a specific horizon"""
        
        # Take only the required number of trading days
        test_returns = self.strategy_returns.iloc[:horizon_days].copy()
        
        if len(test_returns) < 2:
            print(f"  Warning: Not enough data for {horizon_name} horizon (only {len(test_returns)} days)")
            return
        
        # Aggregate to monthly returns
        monthly = self._aggregate_to_monthly(test_returns)
        
        if len(monthly) < 1:
            print(f"  Warning: Not enough monthly periods for {horizon_name} horizon")
            return
        
        # Create figure
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Plot lines for each strategy
        colors = {'classical': '#1f77b4', 'quantum': '#ff7f0e', 'quantum_rebalanced': '#2ca02c'}
        linestyles = {'classical': '-', 'quantum': '--', 'quantum_rebalanced': '-.'}
        linewidths = {'classical': 2.5, 'quantum': 2.5, 'quantum_rebalanced': 3}
        markers = {'classical': 'o', 'quantum': 's', 'quantum_rebalanced': '^'}
        labels = {'classical': 'Classical', 'quantum': 'Quantum', 'quantum_rebalanced': 'Quantum+Rebal'}
        
        for col_name in ['classical', 'quantum', 'quantum_rebalanced']:
            if col_name in monthly.columns:
                monthly_pct = monthly[col_name] * 100  # Convert to percentage
                ax.plot(
                    range(len(monthly)),
                    monthly_pct.values,
                    label=labels[col_name],
                    color=colors[col_name],
                    linestyle=linestyles[col_name],
                    linewidth=linewidths[col_name],
                    marker=markers[col_name],
                    markersize=8,
                    alpha=0.85
                )
        
        # Formatting
        ax.set_title(
            f'{horizon_name} Horizon: Monthly Returns Comparison\n({len(monthly)} months, {horizon_days} trading days)',
            fontsize=16, fontweight='bold', pad=20
        )
        ax.set_xlabel('Month', fontsize=12, fontweight='bold')
        ax.set_ylabel('Monthly Return (%)', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.8, alpha=0.7)
        
        # Set x-axis to show month numbers
        ax.set_xticks(range(0, len(monthly), max(1, len(monthly)//10)))
        ax.set_xticklabels([f'M{i+1}' for i in range(0, len(monthly), max(1, len(monthly)//10))])
        
        # Format y-axis as percentage
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.1f}%'))
        
        # Legend
        ax.legend(
            loc='best',
            fontsize=11,
            framealpha=0.95,
            edgecolor='black'
        )
        
        plt.tight_layout()
        
        # Save figure
        output_file = self.output_dir / f'horizon_{horizon_name}_monthly_returns.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {output_file.name}")
        plt.close()
        
        # Print summary statistics
        self._print_horizon_summary(horizon_name, monthly)
    
    def _print_horizon_summary(self, horizon_name, monthly_returns):
        """Print summary statistics for the horizon"""
        
        print(f"\n  {horizon_name} Horizon Summary:")
        print(f"  {'─' * 70}")
        
        strategy_map = {'classical': 'Classical', 'quantum': 'Quantum', 'quantum_rebalanced': 'Quantum+Rebal'}
        
        for col_name, display_name in strategy_map.items():
            if col_name in monthly_returns.columns:
                returns = monthly_returns[col_name]
                total_return = (1 + returns).prod() - 1
                avg_monthly = returns.mean()
                std_monthly = returns.std()
                positive_months = (returns > 0).sum()
                total_months = len(returns)
                
                print(f"  {display_name}:")
                print(f"    Total Return: {total_return*100:>7.2f}%")
                print(f"    Avg Monthly:  {avg_monthly*100:>7.2f}%")
                print(f"    Volatility:   {std_monthly*100:>7.2f}%")
                print(f"    Win Rate:     {(positive_months/total_months)*100:>7.1f}% ({positive_months}/{total_months})")
    
    def generate_all_horizons(self):
        """Generate graphs for all horizons"""
        
        print(f"\n{'='*70}")
        print("GENERATING HORIZON MONTHLY RETURNS GRAPHS")
        print(f"{'='*70}\n")
        
        print(f"Test Period: {self.strategy_returns.index[0].strftime('%Y-%m-%d')} to {self.strategy_returns.index[-1].strftime('%Y-%m-%d')}")
        print(f"Total Trading Days: {len(self.strategy_returns)}\n")
        
        for horizon_name, horizon_days in self.horizons.items():
            print(f"Processing {horizon_name} horizon ({horizon_days} trading days)...")
            self._create_horizon_graph(horizon_name, horizon_days)
        
        print(f"\n{'='*70}")
        print(f"All graphs saved to: {self.output_dir}")
        print(f"{'='*70}\n")


def main():
    try:
        generator = HorizonMonthlyReturnsGenerator()
        generator.generate_all_horizons()
        
        print("\n✓ Horizon monthly returns graphs generated successfully!")
        return 0
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
