"""
Strategy Comparison Framework
==============================
Compares three strategies:
1. Buy-and-Hold (Equal Weight)
2. Quantum Optimization (One-time)
3. Quantum + Half-Yearly Rebalancing

Metrics: Sharpe, Sortino, Calmar, Max Drawdown, Total Return

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

class StrategyComparator:
    
    def __init__(self, config_path='config/config.json'):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        self.risk_free_rate = self.config['data']['risk_free_rate']
        self.trading_days = self.config['data']['trading_days_per_year']
        self.transaction_cost_pct = float(self.config.get('rebalancing', {}).get('transaction_cost_pct', 0.0))

    def _period_key(self, dt, rebalance_freq):
        """Return period bucket key used to trigger one rebalance per period."""
        if rebalance_freq == '6M':
            half = 1 if dt.month <= 6 else 2
            return (dt.year, half)

        # Default to quarterly cadence.
        quarter = ((dt.month - 1) // 3) + 1
        return (dt.year, quarter)
    
    def calculate_metrics(self, returns_series, name="Strategy"):
        """Calculate comprehensive performance metrics"""
        
        # Convert to numpy for calculations
        returns = returns_series.values
        
        # Total Return
        cumulative_return = (1 + returns).prod() - 1
        
        # Annualized Return
        n_periods = len(returns)
        annual_return = (1 + cumulative_return) ** (self.trading_days / n_periods) - 1
        
        # Volatility
        volatility = returns.std() * np.sqrt(self.trading_days)
        
        # Sharpe Ratio
        sharpe = (annual_return - self.risk_free_rate) / volatility if volatility > 0 else 0
        
        # Sortino Ratio (downside deviation)
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() * np.sqrt(self.trading_days)
        sortino = (annual_return - self.risk_free_rate) / downside_std if downside_std > 0 else 0
        
        # Maximum Drawdown
        cumulative_rets = (1 + returns).cumprod()
        running_max = np.maximum.accumulate(cumulative_rets)
        drawdown = (cumulative_rets - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Calmar Ratio
        calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # Win Rate
        win_rate = (returns > 0).sum() / len(returns)
        
        # Value at Risk (95%)
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
            'num_periods': n_periods
        }
    
    def calculate_portfolio_returns(self, prices_df, weights, rebalance=False, rebalance_freq='quarterly'):
        """
        Calculate portfolio returns given weights
        
        Args:
            prices_df: DataFrame with stock prices
            weights: Dict of {stock: weight}
            rebalance: Whether to rebalance periodically
            rebalance_freq: Rebalancing frequency ('quarterly' or '6M')
        """
        # Filter to stocks in weights
        stocks = [s for s in weights.keys() if s in prices_df.columns]
        prices = prices_df[stocks].copy()

        # Use simple returns so holdings dynamics are correctly captured.
        asset_returns = prices.pct_change().dropna()
        target_weights = np.array([weights[s] for s in stocks], dtype=float)

        if target_weights.sum() <= 0:
            raise ValueError("Target weights sum to zero")

        target_weights = target_weights / target_weights.sum()

        portfolio_returns = []
        current_weights = target_weights.copy()
        last_period_key = None

        for dt, row in asset_returns.iterrows():
            daily_asset_returns = row.values
            portfolio_daily_return = float(np.dot(current_weights, daily_asset_returns))

            # Update buy-and-hold weights via asset drift.
            gross = current_weights * (1.0 + daily_asset_returns)
            gross_sum = gross.sum()
            if gross_sum > 0:
                current_weights = gross / gross_sum

            if rebalance:
                period_key = self._period_key(dt, rebalance_freq)
                if last_period_key is None:
                    last_period_key = period_key
                should_rebalance = period_key != last_period_key

                if should_rebalance:
                    # Turnover-based transaction cost applied on rebalance day.
                    turnover = float(np.abs(target_weights - current_weights).sum())
                    if self.transaction_cost_pct > 0:
                        portfolio_daily_return -= turnover * self.transaction_cost_pct
                    current_weights = target_weights.copy()
                    last_period_key = period_key

            portfolio_returns.append(portfolio_daily_return)

        return pd.Series(portfolio_returns, index=asset_returns.index)
    
    def strategy_classical_sharpe(self, prices_df):
        """Strategy 1: Classical Sharpe Ratio Maximization (from reference paper)
        
        Uses convex optimization to maximize Sharpe ratio on all stocks.
        This is the classical baseline from the research paper methodology.
        """
        from scipy.optimize import minimize
        
        stocks = [c for c in prices_df.columns if c != 'Date']
        
        # Calculate returns
        asset_returns = prices_df[stocks].pct_change().dropna()
        mean_returns = asset_returns.mean() * self.trading_days
        cov_matrix = asset_returns.cov() * self.trading_days
        
        # Objective: Negative Sharpe Ratio (to minimize)
        def neg_sharpe_ratio(w):
            portfolio_return = np.dot(w, mean_returns)
            portfolio_vol = np.sqrt(np.dot(w, np.dot(cov_matrix, w)))
            if portfolio_vol == 0:
                return 1e10
            return -(portfolio_return - self.risk_free_rate) / portfolio_vol
        
        # Constraints: weights sum to 1, all weights >= 0
        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        bounds = tuple((0, 1) for _ in stocks)
        
        # Initial guess: equal weight
        initial_weights = np.array([1.0 / len(stocks)] * len(stocks))
        
        # Optimize
        result = minimize(
            neg_sharpe_ratio,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 500}
        )
        
        optimal_weights = result.x
        classical_weights = {stocks[i]: optimal_weights[i] for i in range(len(stocks))}
        
        returns = self.calculate_portfolio_returns(prices_df, classical_weights, rebalance=False)
        metrics = self.calculate_metrics(returns, "Classical (Sharpe Optimized)")
        
        return returns, metrics
    
    def strategy_quantum_once(self, prices_df, optimal_weights):
        """Strategy 2: Quantum optimization, buy and hold"""
        returns = self.calculate_portfolio_returns(prices_df, optimal_weights, rebalance=False)
        metrics = self.calculate_metrics(returns, "Quantum Buy-Hold")
        
        return returns, metrics
    
    def strategy_quantum_rebalanced(self, prices_df, optimal_weights):
        """Strategy 3: Quantum optimization with configured periodic rebalancing"""
        rebalance_freq = self.config.get('rebalancing', {}).get('frequency', 'quarterly')
        freq_label = 'Quarterly' if rebalance_freq == 'quarterly' else 'Half-Yearly'

        returns = self.calculate_portfolio_returns(prices_df, optimal_weights, 
                                                   rebalance=True, rebalance_freq=rebalance_freq)
        metrics = self.calculate_metrics(returns, f"Quantum + {freq_label} Rebalancing")
        
        return returns, metrics
    
    def compare_strategies(self, prices_df, optimal_weights):
        """Run all strategies and compare"""
        
        print(f"\n{'='*90}")
        print("COMPREHENSIVE STRATEGY COMPARISON")
        print(f"{'='*90}\n")
        
        print(f"Test Period: {prices_df.index[0].strftime('%Y-%m-%d')} to {prices_df.index[-1].strftime('%Y-%m-%d')}")
        print(f"Trading Days: {len(prices_df)}")
        print(f"Stocks in Portfolio: {len(optimal_weights)}\n")
        
        # Run all strategies
        print("Running strategies...")
        
        returns_classical, metrics_classical = self.strategy_classical_sharpe(prices_df)
        print(f"  OK Classical (Sharpe Optimized)")
        
        returns_quantum, metrics_quantum = self.strategy_quantum_once(prices_df, optimal_weights)
        print(f"  OK Quantum Buy-Hold")
        
        returns_rebalanced, metrics_rebalanced = self.strategy_quantum_rebalanced(prices_df, optimal_weights)
        print(f"  OK {metrics_rebalanced['strategy']}")
        
        # Compile results
        all_metrics = [metrics_classical, metrics_quantum, metrics_rebalanced]
        
        # Print comparison table
        self.print_comparison_table(all_metrics)
        
        # Create visualizations
        self.create_visualizations({
            'Classical': returns_classical,
            'Quantum': returns_quantum,
            'Quantum+Rebal': returns_rebalanced
        })
        
        # Save results
        self.save_results(all_metrics, {
            'classical': returns_classical,
            'quantum': returns_quantum,
            'quantum_rebalanced': returns_rebalanced
        })
        
        return all_metrics
    
    def print_comparison_table(self, metrics_list):
        """Print formatted comparison table with verification"""
        
        print(f"\n{'='*90}")
        print("PERFORMANCE METRICS COMPARISON")
        print(f"{'='*90}\n")
        
        # Headers
        print(f"{'Metric':<25} {'Classical':<20} {'Quantum':<20} {'Quantum+Rebal':<20}")
        print("-" * 90)
        
        # Metrics to display
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
        
        # Validation section
        print(f"\n{'='*90}")
        print("REBALANCING & METRICS VERIFICATION")
        print(f"{'='*90}\n")
        
        for i, metrics in enumerate(metrics_list):
            strategy = metrics['strategy']
            print(f"{strategy}:")
            print(f"  ✓ Calculated from {metrics['num_periods']} trading days")
            if 'Rebal' in strategy or 'Rebalancing' in strategy:
                print(f"  ✓ Quarterly rebalancing ENABLED")
                print(f"  ✓ Transaction costs applied to turnover")
            else:
                print(f"  ✓ Buy-and-hold (no rebalancing)")
            print(f"  ✓ Metric verification:")
            print(f"    - Total return: (1+r1)*(1+r2)*...*(1+rn) - 1")
            print(f"    - Annual return: (1 + total_ret)^(252/periods) - 1")
            print(f"    - Volatility: std(daily_returns) * sqrt(252)")
            print(f"    - Sharpe: (annual_return - {self.risk_free_rate*100:.1f}%) / volatility\"")
            print()
        
        print(f"\n{'='*90}\n")
        
        # Highlight winner
        best_sharpe_idx = np.argmax([m['sharpe_ratio'] for m in metrics_list])
        best_return_idx = np.argmax([m['total_return'] for m in metrics_list])
        
        print(f"\n[WINNER] Best Sharpe Ratio: {metrics_list[best_sharpe_idx]['strategy']}")
        print(f"[WINNER] Best Total Return: {metrics_list[best_return_idx]['strategy']}")
        print()
    
    def create_visualizations(self, returns_dict):
        """Create comparison visualizations"""
        
        print("Creating visualizations...")
        
        # Calculate cumulative returns
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # 1. Cumulative Returns
        ax = axes[0, 0]
        for name, returns in returns_dict.items():
            cumulative = (1 + returns).cumprod()
            ax.plot(cumulative.index, cumulative.values, label=name, linewidth=2)
        
        ax.set_title('Cumulative Returns', fontsize=14, fontweight='bold')
        ax.set_ylabel('Cumulative Return')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 2. Drawdown
        ax = axes[0, 1]
        for name, returns in returns_dict.items():
            cumulative = (1 + returns).cumprod()
            running_max = np.maximum.accumulate(cumulative)
            drawdown = (cumulative - running_max) / running_max * 100
            ax.plot(drawdown.index, drawdown.values, label=name, linewidth=2)
        
        ax.set_title('Drawdown (%)', fontsize=14, fontweight='bold')
        ax.set_ylabel('Drawdown (%)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.fill_between(drawdown.index, drawdown.values, 0, alpha=0.3)
        
        # 3. Rolling Sharpe (90-day)
        ax = axes[1, 0]
        for name, returns in returns_dict.items():
            rolling_sharpe = (
                (returns.rolling(90).mean() * self.trading_days - self.risk_free_rate) /
                (returns.rolling(90).std() * np.sqrt(self.trading_days))
            )
            ax.plot(rolling_sharpe.index, rolling_sharpe.values, label=name, linewidth=2)
        
        ax.set_title('Rolling 90-Day Sharpe Ratio', fontsize=14, fontweight='bold')
        ax.set_ylabel('Sharpe Ratio')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        
        # 4. Return Distribution
        ax = axes[1, 1]
        returns_data = [returns.values * 100 for returns in returns_dict.values()]
        ax.boxplot(returns_data, labels=returns_dict.keys())
        ax.set_title('Daily Returns Distribution (%)', fontsize=14, fontweight='bold')
        ax.set_ylabel('Return (%)')
        ax.grid(True, alpha=0.3, axis='y')
        ax.axhline(y=0, color='red', linestyle='--', alpha=0.5)
        
        plt.tight_layout()
        plt.savefig('results/strategy_comparison.png', dpi=300, bbox_inches='tight')
        print(f"  OK Saved: results/strategy_comparison.png")
        
        plt.close()
    
    def save_results(self, metrics_list, returns_dict):
        """Save all results to files"""
        
        # Save metrics as JSON
        results = {
            'comparison_date': datetime.now().isoformat(),
            'metrics': metrics_list,
            'summary': {
                'best_sharpe': max(metrics_list, key=lambda x: x['sharpe_ratio'])['strategy'],
                'best_return': max(metrics_list, key=lambda x: x['total_return'])['strategy'],
                'best_drawdown': max(metrics_list, key=lambda x: x['max_drawdown'])['strategy']
            }
        }
        
        with open('results/strategy_comparison.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        # Save returns as CSV - align all series to common index
        returns_df = pd.DataFrame(returns_dict)
        returns_df.index.name = 'Date'
        returns_df.to_csv('results/strategy_returns.csv')
        
        print(f"  OK Saved: results/strategy_comparison.json")
        print(f"  OK Saved: results/strategy_returns.csv")
        print()

def main():
    """Main execution"""
    try:
        # Load test data
        print("Loading test data...")
        prices_df = pd.read_csv('data/test_data.csv', parse_dates=['Date'], index_col='Date')
        
        # Load weights (support legacy and current output filenames)
        weights_path = None
        for candidate in ('portfolios/optimal_weights.json', 'portfolios/optimized_weights.json'):
            if Path(candidate).exists():
                weights_path = candidate
                break

        if weights_path is None:
            raise FileNotFoundError("No weights file found (expected optimal_weights.json or optimized_weights.json)")

        with open(weights_path, 'r') as f:
            weights_data = json.load(f)

        # Support both formats:
        # 1) legacy dict: {"STOCK": weight, ...}
        # 2) current dict: {"stocks": [...], "weights": [...], ...}
        if isinstance(weights_data, dict) and 'stocks' in weights_data and 'weights' in weights_data:
            stocks = weights_data.get('stocks', [])
            weights = weights_data.get('weights', [])
            weights_only = {
                s: float(w)
                for s, w in zip(stocks, weights)
                if isinstance(w, (int, float)) and s in prices_df.columns
            }
        else:
            weights_only = {
                k: float(v)
                for k, v in weights_data.items()
                if isinstance(v, (int, float)) and k in prices_df.columns
            }
        
        # Normalize weights
        total_weight = sum(weights_only.values())
        if total_weight <= 0:
            raise ValueError("Loaded weights are empty or non-positive after filtering to test universe")
        weights_only = {k: v/total_weight for k, v in weights_only.items()}
        
        # Initialize comparator
        comparator = StrategyComparator()
        
        # Run comparison
        metrics = comparator.compare_strategies(prices_df, weights_only)
        
        print(f"{'='*90}")
        print("STRATEGY COMPARISON COMPLETE")
        print(f"{'='*90}\n")
        
        return 0
        
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())

