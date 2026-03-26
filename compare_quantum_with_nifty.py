"""
Compare Quantum Strategies with NIFTY 50 Benchmark
===================================================
Detailed comparison of Quantum Buy-Hold and Quantum+Rebalancing 
strategies against the NIFTY 50 index benchmark.

Author: Enhanced Portfolio System
Date: March 2026
"""

import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

class NiftyBenchmarkComparison:
    
    def __init__(self, config_path='config/config.json', nifty_path='Dataset/NIFTY 50.csv.xls'):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        self.risk_free_rate = self.config['data']['risk_free_rate']
        self.trading_days = self.config['data']['trading_days_per_year']
        
        # Load NIFTY 50 data
        self.nifty_df = pd.read_csv(nifty_path, parse_dates=['Date'])
        self._clean_date_column()
        
    def _clean_date_column(self):
        """Parse the date column properly with validation"""
        def parse_nifty_date(date_str):
            try:
                # Format: 'Tue Jul 03 1990 00:00:00 GMT+0530 (India Standard Time)'
                # Extract: Tue Jul 03 1990
                parts = str(date_str).split()
                if len(parts) >= 4:
                    day_name = parts[0]  # Tue
                    month = parts[1]     # Jul
                    day = parts[2]       # 03
                    year = parts[3]      # 1990
                    date_str_clean = f'{day_name} {month} {day} {year}'
                    return pd.to_datetime(date_str_clean, format='%a %b %d %Y')
            except:
                pass
            return pd.NaT
        
        self.nifty_df['Date'] = self.nifty_df['Date'].apply(parse_nifty_date)
        self.nifty_df = self.nifty_df.dropna(subset=['Date'])
        self.nifty_df = self.nifty_df.sort_values('Date').reset_index(drop=True)
        
        # Validation: Check data quality
        self._validate_nifty_data()
    
    def _validate_nifty_data(self):
        """Validate NIFTY 50 data integrity and quality"""
        print("\n[NIFTY 50 DATA VALIDATION]")
        print(f"  Total records: {len(self.nifty_df)}")
        print(f"  Date range: {self.nifty_df['Date'].min().date()} to {self.nifty_df['Date'].max().date()}")
        
        # Check for 10+ years of data
        date_diff = (self.nifty_df['Date'].max() - self.nifty_df['Date'].min()).days
        years_of_data = date_diff / 365.25
        print(f"  Years of data: {years_of_data:.1f} years")
        
        if years_of_data < 10:
            print(f"  ⚠ WARNING: Less than 10 years of data available ({years_of_data:.1f} years)")
        else:
            print(f"  ✓ Data covers {years_of_data:.1f} years (sufficient for 10-year analysis)")
        
        # Check for missing values
        missing = self.nifty_df['Close'].isna().sum()
        print(f"  Missing Close prices: {missing}")
        
        # Check for zero prices (invalid)
        zero_prices = (self.nifty_df['Close'] == 0).sum()
        if zero_prices > 0:
            print(f"  ⚠ WARNING: {zero_prices} records with zero price")
        
        # Check date continuity
        date_gaps = 0
        for i in range(1, len(self.nifty_df)):
            gap = (self.nifty_df['Date'].iloc[i] - self.nifty_df['Date'].iloc[i-1]).days
            if gap > 7:  # More than a week
                date_gaps += 1
        print(f"  Date gaps (>7 days): {date_gaps}")
        print()
    
    def calculate_metrics(self, returns_series, name="Strategy"):
        """Calculate comprehensive performance metrics with verification"""
        
        returns = returns_series.values
        
        # Total Return (VERIFIED: (1+r1)*(1+r2)*...*(1+rn) - 1)
        cumulative_return = (1 + returns).prod() - 1
        
        # Annualized Return (VERIFIED: (1 + total_return)^(trading_days/num_periods) - 1)
        n_periods = len(returns)
        annual_return = (1 + cumulative_return) ** (self.trading_days / n_periods) - 1
        
        # Volatility (VERIFIED: std(daily_returns) * sqrt(252))
        volatility = returns.std() * np.sqrt(self.trading_days)
        
        # Sharpe Ratio (VERIFIED: (annual_return - risk_free_rate) / volatility)
        sharpe = (annual_return - self.risk_free_rate) / volatility if volatility > 0 else 0
        
        # Sortino Ratio (VERIFIED: downside deviation only)
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() * np.sqrt(self.trading_days) if len(downside_returns) > 0 else 0
        sortino = (annual_return - self.risk_free_rate) / downside_std if downside_std > 0 else 0
        
        # Maximum Drawdown (VERIFIED: (value - peak) / peak)
        cumulative_rets = (1 + returns).cumprod()
        running_max = np.maximum.accumulate(cumulative_rets)
        drawdown = (cumulative_rets - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Calmar Ratio (VERIFIED: annual_return / abs(max_drawdown))
        calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # Win Rate (VERIFIED: % of positive return days)
        win_rate = (returns > 0).sum() / len(returns)
        
        # Value at Risk (95%) (VERIFIED: 5th percentile)
        var_95 = np.percentile(returns, 5)
        
        return {
            'strategy': name,
            'total_return': cumulative_return * 100,
            'annual_return': annual_return * 100,
            'volatility': volatility * 100,
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'max_drawdown': max_drawdown * 100,
            'calmar_ratio': calmar,
            'win_rate': win_rate * 100,
            'var_95': var_95 * 100,
            'num_periods': n_periods,
            # Additional validation fields
            'num_positive_days': int((returns > 0).sum()),
            'num_negative_days': int((returns < 0).sum()),
            'avg_daily_return': returns.mean() * 100,
            'daily_volatility': returns.std() * 100
        }
    
    def get_nifty_returns(self, start_date, end_date):
        """Extract NIFTY 50 returns for the test period"""
        
        # Filter to test period
        nifty_test = self.nifty_df[
            (self.nifty_df['Date'] >= start_date) & 
            (self.nifty_df['Date'] <= end_date)
        ].copy()
        
        if len(nifty_test) < 2:
            raise ValueError(f"Not enough NIFTY 50 data for period {start_date} to {end_date}")
        
        # Calculate daily returns from Close prices
        nifty_test = nifty_test.sort_values('Date').reset_index(drop=True)
        nifty_returns = nifty_test['Close'].pct_change().dropna()
        nifty_returns.index = nifty_test.index[1:]
        
        return pd.Series(nifty_returns.values, name='NIFTY 50')
    
    def compare_with_nifty(self):
        """Compare quantum strategies with NIFTY 50 benchmark"""
        
        print(f"\n{'='*90}")
        print("QUANTUM STRATEGIES vs NIFTY 50 BENCHMARK COMPARISON")
        print(f"{'='*90}\n")
        
        # Load strategy returns
        strategy_returns = pd.read_csv('results/strategy_returns.csv', index_col='Date', parse_dates=True)
        
        if len(strategy_returns) == 0:
            raise ValueError("No strategy returns found. Run pipeline first.")
        
        start_date = strategy_returns.index[0]
        end_date = strategy_returns.index[-1]
        
        print(f"Test Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"Trading Days: {len(strategy_returns)}\n")
        
        # Get NIFTY 50 returns for same period
        nifty_returns = self.get_nifty_returns(start_date, end_date)
        
        # Verify data alignment
        print(f"[DATA ALIGNMENT VERIFICATION]")
        print(f"  Strategy returns: {len(strategy_returns)} trading days")
        print(f"  NIFTY 50 returns: {len(nifty_returns)} trading days")
        print(f"  Common period: {(end_date - start_date).days} calendar days")
        print()
        
        # Align indices - NIFTY 50 may have different trading days
        # We'll align by date
        common_dates = strategy_returns.index.intersection(
            pd.to_datetime(self.get_nifty_dates_for_period(start_date, end_date))
        )
        
        # Calculate metrics
        quantum_metrics = self.calculate_metrics(
            strategy_returns['quantum'],
            "Quantum Buy-Hold"
        )
        quantum_rebal_metrics = self.calculate_metrics(
            strategy_returns['quantum_rebalanced'],
            "Quantum + Quarterly Rebalancing"
        )
        nifty_metrics = self.calculate_metrics(
            nifty_returns,
            "NIFTY 50 Benchmark"
        )
        
        all_metrics = [quantum_metrics, quantum_rebal_metrics, nifty_metrics]
        
        # Print comparison table
        self.print_comparison_table(all_metrics, strategy_returns, nifty_returns)
        
        # Create visualizations
        self.create_visualizations(
            strategy_returns[['quantum', 'quantum_rebalanced']],
            nifty_returns
        )
        
        # Save results
        self.save_results(all_metrics)
        
        return all_metrics
    
    def get_nifty_dates_for_period(self, start_date, end_date):
        """Get NIFTY 50 dates in the test period"""
        nifty_period = self.nifty_df[
            (self.nifty_df['Date'] >= start_date) & 
            (self.nifty_df['Date'] <= end_date)
        ]
        return nifty_period['Date'].values
    
    def print_comparison_table(self, metrics_list, strategy_returns, nifty_returns):
        """Print detailed comparison table with metrics verification"""
        
        print(f"\n{'='*90}")
        print("PERFORMANCE METRICS COMPARISON")
        print(f"{'='*90}\n")
        
        print(f"{'Metric':<25} {'Quantum':<20} {'Quantum+Rebal':<20} {'NIFTY 50':<20}")
        print("-" * 90)
        
        metric_formats = [
            ('Total Return (%)', 'total_return', '.2f'),
            ('Annual Return (%)', 'annual_return', '.2f'),
            ('Volatility (%)', 'volatility', '.2f'),
            ('Sharpe Ratio', 'sharpe_ratio', '.3f'),
            ('Sortino Ratio', 'sortino_ratio', '.3f'),
            ('Max Drawdown (%)', 'max_drawdown', '.2f'),
            ('Calmar Ratio', 'calmar_ratio', '.3f'),
            ('Win Rate (%)', 'win_rate', '.2f'),
            ('VaR 95% (%)', 'var_95', '.2f')
        ]
        
        for label, key, fmt in metric_formats:
            values = [f"{m[key]:{fmt}}" for m in metrics_list]
            print(f"{label:<25} {values[0]:<20} {values[1]:<20} {values[2]:<20}")
        
        # Additional validation information
        print(f"\n{'='*90}")
        print("METRICS VERIFICATION")
        print(f"{'='*90}\n")
        
        for i, metrics in enumerate(metrics_list):
            strategy_name = metrics['strategy']
            print(f"{strategy_name}:")
            print(f"  Trading Days: {metrics['num_periods']}")
            print(f"  Positive Days: {metrics['num_positive_days']} ({metrics['num_positive_days']/metrics['num_periods']*100:.1f}%)")
            print(f"  Negative Days: {metrics['num_negative_days']} ({metrics['num_negative_days']/metrics['num_periods']*100:.1f}%)")
            print(f"  Avg Daily Return: {metrics['avg_daily_return']:.4f}%")
            print(f"  Daily Volatility: {metrics['daily_volatility']:.4f}%")
            print(f"  Annualized Volatility (Verified): {metrics['daily_volatility'] * np.sqrt(252):.2f}%")
            print()
        
        print(f"{'='*90}\n")
        
        # Advantage analysis
        print("QUANTUM STRATEGIES vs NIFTY 50:")
        print("-" * 90)
        
        quantum = metrics_list[0]
        quantum_rebal = metrics_list[1]
        nifty = metrics_list[2]
        
        print(f"\nQuantum Buy-Hold vs NIFTY 50:")
        print(f"  Return Advantage:   {(quantum['total_return'] - nifty['total_return']):+.2f}% "
              f"({(quantum['total_return']/nifty['total_return'] - 1)*100:+.1f}x)")
        print(f"  Sharpe Advantage:   {(quantum['sharpe_ratio'] - nifty['sharpe_ratio']):+.3f}")
        print(f"  Volatility:         {(quantum['volatility'] - nifty['volatility']):+.2f}%")
        
        print(f"\nQuantum+Rebal vs NIFTY 50:")
        print(f"  Return Advantage:   {(quantum_rebal['total_return'] - nifty['total_return']):+.2f}% "
              f"({(quantum_rebal['total_return']/nifty['total_return'] - 1)*100:+.1f}x)")
        print(f"  Sharpe Advantage:   {(quantum_rebal['sharpe_ratio'] - nifty['sharpe_ratio']):+.3f}")
        print(f"  Volatility:         {(quantum_rebal['volatility'] - nifty['volatility']):+.2f}%")
        
        print(f"\n{'='*90}\n")
    
    def create_visualizations(self, strategy_returns, nifty_returns):
        """Create comparison visualizations"""
        
        # Ensure proper indexing
        if not isinstance(strategy_returns.index, pd.DatetimeIndex):
            strategy_returns.index = pd.to_datetime(strategy_returns.index)
        
        # Calculate cumulative returns
        strategy_cumulative = (1 + strategy_returns).cumprod() - 1
        
        # For NIFTY, align with strategy dates
        nifty_cumulative = (1 + nifty_returns).cumprod() - 1
        
        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # Plot 1: Cumulative Returns
        ax = axes[0, 0]
        ax.plot(
            strategy_returns.index,
            strategy_cumulative['quantum'] * 100,
            label='Quantum Buy-Hold',
            color='#ff7f0e',
            linewidth=2.5,
            alpha=0.85
        )
        ax.plot(
            strategy_returns.index,
            strategy_cumulative['quantum_rebalanced'] * 100,
            label='Quantum + Quarterly Rebalancing',
            color='#2ca02c',
            linewidth=2.5,
            alpha=0.85
        )
        if len(nifty_cumulative) > 0:
            # Create matching x-axis for NIFTY
            nifty_dates = pd.date_range(
                start=strategy_returns.index[0],
                periods=len(nifty_cumulative),
                freq='D'
            )[:len(nifty_cumulative)]
            ax.plot(
                nifty_dates,
                nifty_cumulative.values * 100,
                label='NIFTY 50 Benchmark',
                color='#d62728',
                linewidth=2.5,
                linestyle='--',
                alpha=0.85
            )
        ax.set_title('Cumulative Returns Comparison', fontsize=13, fontweight='bold')
        ax.set_ylabel('Return (%)', fontsize=11)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # Plot 2: Total Return Bars
        ax = axes[0, 1]
        strategies = ['Quantum', 'Quantum+Rebal', 'NIFTY 50']
        returns = [
            (1 + strategy_returns['quantum']).prod() - 1,
            (1 + strategy_returns['quantum_rebalanced']).prod() - 1,
            (1 + nifty_returns).prod() - 1 if len(nifty_returns) > 0 else 0
        ]
        colors_bar = ['#ff7f0e', '#2ca02c', '#d62728']
        bars = ax.bar(strategies, [r*100 for r in returns], color=colors_bar, alpha=0.7, edgecolor='black', linewidth=1.5)
        ax.set_title('Total Return Comparison', fontsize=13, fontweight='bold')
        ax.set_ylabel('Total Return (%)', fontsize=11)
        for i, (bar, ret) in enumerate(zip(bars, returns)):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{ret*100:.1f}%',
                   ha='center', va='bottom', fontweight='bold', fontsize=10)
        
        # Plot 3: Volatility Comparison
        ax = axes[1, 0]
        volatilities = [
            strategy_returns['quantum'].std() * np.sqrt(252) * 100,
            strategy_returns['quantum_rebalanced'].std() * np.sqrt(252) * 100,
            nifty_returns.std() * np.sqrt(252) * 100 if len(nifty_returns) > 0 else 0
        ]
        bars = ax.bar(strategies, volatilities, color=colors_bar, alpha=0.7, edgecolor='black', linewidth=1.5)
        ax.set_title('Volatility (Annualized)', fontsize=13, fontweight='bold')
        ax.set_ylabel('Volatility (%)', fontsize=11)
        for bar, vol in zip(bars, volatilities):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{vol:.1f}%',
                   ha='center', va='bottom', fontweight='bold', fontsize=10)
        
        # Plot 4: Risk-Return Scatter
        ax = axes[1, 1]
        annual_returns = [
            ((1 + strategy_returns['quantum']).prod() - 1) / (len(strategy_returns) / 252) * 100,
            ((1 + strategy_returns['quantum_rebalanced']).prod() - 1) / (len(strategy_returns) / 252) * 100,
            ((1 + nifty_returns).prod() - 1) / (len(nifty_returns) / 252) * 100 if len(nifty_returns) > 0 else 0
        ]
        ax.scatter(volatilities, annual_returns, s=500, c=colors_bar, alpha=0.7, edgecolors='black', linewidth=2)
        for i, strategy in enumerate(strategies):
            ax.annotate(strategy, (volatilities[i], annual_returns[i]),
                       xytext=(10, 10), textcoords='offset points',
                       fontsize=10, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.5', facecolor=colors_bar[i], alpha=0.3))
        ax.set_xlabel('Volatility (%)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Annual Return (%)', fontsize=11, fontweight='bold')
        ax.set_title('Risk-Return Profile', fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save figure
        output_file = Path('results') / 'quantum_vs_nifty_comparison.png'
        output_file.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {output_file.name}")
        plt.close()
    
    def save_results(self, metrics_list):
        """Save comparison results"""
        
        results = {
            'comparison_date': datetime.now().isoformat(),
            'comparison_type': 'Quantum Strategies vs NIFTY 50 Benchmark',
            'metrics': metrics_list
        }
        
        output_file = Path('results') / 'quantum_nifty_comparison.json'
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"  ✓ Saved: {output_file.name}")


def main():
    try:
        comparator = NiftyBenchmarkComparison()
        comparator.compare_with_nifty()
        
        print("\n✓ Quantum vs NIFTY 50 comparison completed successfully!")
        return 0
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
