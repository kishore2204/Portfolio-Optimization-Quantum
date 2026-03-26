"""
Scenario-Specific Metrics Generator and Adaptive K Rebalancer
==============================================================

For each scenario (horizon/crash), generates:
1. Selected stocks with expected returns and Sharpe ratios
2. Portfolio allocation weights
3. Adapively determines K_sell based on performance improvement

Uses NIFTY 200 universe for all scenarios and horizons.

Author: Enhanced Portfolio System
Date: March 2026
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')


class ScenarioMetricsGenerator:
    """Generate comprehensive metrics for each scenario"""
    
    def __init__(self, config_path='config/config.json'):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        # Load NIFTY 200 sectors mapping
        with open('config/nifty200_sectors.json', 'r') as f:
            sectors_data = json.load(f)
        
        self.nifty200_stocks = set()
        for sector_stocks in sectors_data['NIFTY_200_STOCKS'].values():
            self.nifty200_stocks.update(sector_stocks)
        
        self.trading_days_per_year = self.config['data']['trading_days_per_year']
    
    def load_scenario_data(self, prices_df: pd.DataFrame, scenario_config: Dict) -> Tuple[pd.DataFrame, Dict]:
        """
        Load and split data for given scenario
        Returns: (train_df, test_df, metadata)
        """
        train_start = pd.to_datetime(scenario_config['train_start'])
        train_end = pd.to_datetime(scenario_config['train_end'])
        test_start = pd.to_datetime(scenario_config['test_start'])
        test_end = pd.to_datetime(scenario_config['test_end'])
        
        # Filter to NIFTY 200 stocks - use case-insensitive matching
        all_symbols = set(col for col in prices_df.columns if col != 'Date')
        available_stocks = [col for col in all_symbols 
                           if col.upper() in {s.upper() for s in self.nifty200_stocks}]
        
        if not available_stocks:
            # Fallback: use all available stocks if NIFTY 200 mapping not found
            available_stocks = [col for col in prices_df.columns if col != 'Date'][:100]
        
        # Split data
        train_mask = (prices_df['Date'] >= train_start) & (prices_df['Date'] <= train_end)
        test_mask = (prices_df['Date'] >= test_start) & (prices_df['Date'] <= test_end)
        
        train_data = prices_df[train_mask].copy()
        test_data = prices_df[test_mask].copy()
        
        if len(train_data) == 0 or len(test_data) == 0:
            # Return empty dataframes with proper structure
            return pd.DataFrame({'Date': []}), pd.DataFrame({'Date': []}), {}
        
        # Select available columns
        train_cols = ['Date'] + [col for col in available_stocks if col in train_data.columns]
        test_cols = ['Date'] + [col for col in available_stocks if col in test_data.columns]
        
        train_df = train_data[train_cols].copy()
        test_df = test_data[test_cols].copy()
        
        # Forward fill missing values
        for col in train_df.columns:
            if col != 'Date':
                train_df[col] = train_df[col].fillna(method='ffill').fillna(method='bfill')
        
        for col in test_df.columns:
            if col != 'Date':
                test_df[col] = test_df[col].fillna(method='ffill').fillna(method='bfill')
        
        metadata = {
            'scenario_name': scenario_config.get('description', 'Unknown'),
            'train_period': f"{train_start.date()} to {train_end.date()}",
            'test_period': f"{test_start.date()} to {test_end.date()}",
            'train_days': len(train_df),
            'test_days': len(test_df),
            'available_stocks': len(available_stocks),
            'nifty200_used': True
        }
        
        return train_df, test_df, metadata
    
    def calculate_stock_metrics(self, returns_df: pd.DataFrame, rf_rate: float = 0.06) -> pd.DataFrame:
        """
        Calculate expected return, volatility, and Sharpe ratio for each stock
        """
        annual_returns = returns_df.mean() * self.trading_days_per_year
        annual_std = returns_df.std() * np.sqrt(self.trading_days_per_year)
        sharpe_ratios = (annual_returns - rf_rate) / (annual_std + 1e-6)
        
        metrics = pd.DataFrame({
            'Expected_Return': annual_returns,
            'Volatility': annual_std,
            'Sharpe_Ratio': sharpe_ratios
        }).sort_values('Sharpe_Ratio', ascending=False)
        
        return metrics
    
    def select_portfolio(self, train_df: pd.DataFrame, K: int = 10) -> Tuple[List[str], np.ndarray]:
        """
        Select top K stocks by Sharpe ratio
        Returns: (selected_stocks, prices_selected)
        """
        # Calculate returns
        returns = train_df.iloc[:, 1:].ffill().bfill().pct_change().dropna()
        
        # Get metrics
        metrics = self.calculate_stock_metrics(returns)
        
        # Select top K
        selected_stocks = metrics.head(K).index.tolist()
        prices_selected = train_df[['Date'] + selected_stocks]
        
        return selected_stocks, prices_selected, metrics
    
    def optimize_weights(self, returns_df: pd.DataFrame, selected_stocks: List[str]) -> np.ndarray:
        """
        Simple equal-weight allocation (can be upgraded to Markowitz)
        """
        n_stocks = len(selected_stocks)
        weights = np.ones(n_stocks) / n_stocks
        return weights
    
    def generate_scenario_report(self, scenario_name: str, scenario_config: Dict, 
                                prices_df: pd.DataFrame) -> Dict:
        """
        Generate comprehensive report for single scenario
        """
        print(f"\n{'='*80}")
        print(f"Processing Scenario: {scenario_name}")
        print(f"{'='*80}")
        
        # Load data
        train_df, test_df, metadata = self.load_scenario_data(prices_df, scenario_config)
        
        # Get train returns
        train_returns = train_df.iloc[:, 1:].ffill().bfill().pct_change().dropna()
        
        if len(train_returns) < 5 or len(train_df) < 20:
            print(f"   ⚠ Insufficient training data ({len(train_returns)} days)")
            return None
        
        # Calculate metrics
        train_metrics = self.calculate_stock_metrics(train_returns)
        
        # Select portfolio
        K = self.config['portfolio']['K']  # Default K from config
        selected_stocks, _, selected_metrics = self.select_portfolio(train_df, K)
        
        # Optimize weights
        weights = self.optimize_weights(train_returns[selected_stocks], selected_stocks)
        
        # Calculate test performance
        test_returns = test_df.iloc[:, 1:].ffill().bfill().pct_change().dropna()
        
        if len(test_returns) < 5:
            print(f"   ⚠ Insufficient testing data ({len(test_returns)} days)")
            return None
        
        test_metrics = self.calculate_stock_metrics(test_returns)
        
        portfolio_test_returns = test_returns[selected_stocks].dot(weights)
        portfolio_test_return = portfolio_test_returns.mean() * self.trading_days_per_year
        
        # Calculate volatility properly
        portfolio_variance = np.dot(weights, np.dot(test_returns[selected_stocks].cov().values, weights))
        portfolio_test_vol = np.sqrt(portfolio_variance * self.trading_days_per_year)
        
        portfolio_test_sharpe = (float(portfolio_test_return) - 0.06) / (float(portfolio_test_vol) + 1e-6)
        
        # Build report
        report = {
            'scenario_name': scenario_name,
            'metadata': metadata,
            'selected_stocks': {
                'count': len(selected_stocks),
                'symbols': selected_stocks,
                'metrics': {}
            },
            'weights': {},
            'portfolio_metrics': {
                'test_return': float(portfolio_test_return),
                'test_volatility': float(portfolio_test_vol),
                'test_sharpe': float(portfolio_test_sharpe)
            }
        }
        
        # Add individual stock metrics
        for stock, weight in zip(selected_stocks, weights):
            try:
                train_return = float(train_metrics.loc[stock, 'Expected_Return']) if stock in train_metrics.index else 0.0
                train_sharpe = float(train_metrics.loc[stock, 'Sharpe_Ratio']) if stock in train_metrics.index else 0.0
                test_return = float(test_metrics.loc[stock, 'Expected_Return']) if stock in test_metrics.index else 0.0
                test_sharpe = float(test_metrics.loc[stock, 'Sharpe_Ratio']) if stock in test_metrics.index else 0.0
            except (ValueError, TypeError):
                train_return = 0.0
                train_sharpe = 0.0
                test_return = 0.0
                test_sharpe = 0.0
            
            report['selected_stocks']['metrics'][stock] = {
                'train_return': train_return,
                'train_sharpe': train_sharpe,
                'test_return': test_return,
                'test_sharpe': test_sharpe
            }
            report['weights'][stock] = float(weight)
        
        print(f"   Selected {len(selected_stocks)} stocks")
        print(f"   Portfolio Sharpe (Test): {portfolio_test_sharpe:.4f}")
        
        return report


class AdaptiveKRebalancer:
    """
    Implements adaptive K rebalancing logic
    
    Decision rule: 
    - Replace K_sell stocks only if replacement improves portfolio Sharpe ratio
    - Otherwise, keep portfolio unchanged
    - Learn optimal K_sell for each scenario
    """
    
    def __init__(self, config_path='config/config.json'):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.K_sell_base = self.config['rebalancing']['K_sell']
        self.trading_days_per_year = self.config['data']['trading_days_per_year']
    
    def evaluate_replacement_performance(self, 
                                        current_holdings: List[str],
                                        candidate_stocks: List[str],
                                        train_returns: pd.DataFrame,
                                        test_returns: pd.DataFrame,
                                        K_sell: int) -> Tuple[float, float, bool]:
        """
        Compare current portfolio vs replacement portfolio
        
        Returns: (current_sharpe, replacement_sharpe, should_replace)
        """
        # Calculate current portfolio Sharpe
        current_returns = train_returns[current_holdings].mean() * self.trading_days_per_year
        current_weights = np.ones(len(current_holdings)) / len(current_holdings)
        current_sharpe = (current_returns.mean() - 0.06) / (current_returns.std() + 1e-6)
        
        # Calculate replacement portfolio Sharpe
        if len(candidate_stocks) >= K_sell:
            replacement_stocks = candidate_stocks[:K_sell]
            replacement_holdings = [s for s in current_holdings if s not in replacement_stocks[:K_sell]] + replacement_stocks
            
            if len(replacement_holdings) > 0:
                replacement_returns = train_returns[replacement_holdings].mean() * self.trading_days_per_year
                replacement_weights = np.ones(len(replacement_holdings)) / len(replacement_holdings)
                replacement_sharpe = (replacement_returns.mean() - 0.06) / (replacement_returns.std() + 1e-6)
            else:
                replacement_sharpe = current_sharpe
        else:
            replacement_sharpe = current_sharpe
        
        should_replace = replacement_sharpe > current_sharpe
        
        return float(current_sharpe), float(replacement_sharpe), should_replace
    
    def determine_adaptive_k_sell(self, scenario_report: Dict) -> int:
        """
        Determine adaptive K_sell based on scenario characteristics
        
        Rules:
        - Crash scenarios: More aggressive (K_sell = 6-8)
        - Bull scenarios: Conservative (K_sell = 2-4)
        - Normal scenarios: Standard (K_sell = 4)
        """
        scenario_name = scenario_report['scenario_name']
        sharpe = scenario_report['portfolio_metrics']['test_sharpe']
        
        if 'Crash' in scenario_name or 'Crash' in scenario_report['metadata'].get('scenario_name', ''):
            # Crash scenario - more aggressive replacement
            return max(self.K_sell_base, 6) if sharpe < 0.5 else 4
        elif 'Bull' in scenario_name or 'Recovery' in scenario_name:
            # Bull scenario - conservative replacement
            return max(2, self.K_sell_base - 2)
        else:
            # Normal scenario
            return self.K_sell_base
    
    def generate_adaptive_report(self, scenarios_reports: Dict) -> Dict:
        """
        Generate adaptive K report for all scenarios
        """
        adaptive_report = {
            'generated_at': datetime.now().isoformat(),
            'methodology': 'Adaptive K_sell based on scenario performance',
            'scenarios': {}
        }
        
        for scenario_name, report in scenarios_reports.items():
            if report is None:
                continue
                
            adaptive_k = self.determine_adaptive_k_sell(report)
            
            adaptive_report['scenarios'][scenario_name] = {
                'base_k_sell': self.K_sell_base,
                'adaptive_k_sell': adaptive_k,
                'test_sharpe': report['portfolio_metrics']['test_sharpe'],
                'reason': self._get_adaptation_reason(report, adaptive_k)
            }
        
        return adaptive_report
    
    def _get_adaptation_reason(self, report: Dict, adaptive_k: int) -> str:
        """Explain why K_sell was set to this value"""
        scenario_name = report['scenario_name']
        sharpe = report['portfolio_metrics']['test_sharpe']
        base_k = self.K_sell_base
        
        if adaptive_k > base_k:
            return f"Crash regime detected (Sharpe={sharpe:.4f}). Increase replacement rate."
        elif adaptive_k < base_k:
            return f"Bull regime detected (Sharpe={sharpe:.4f}). Reduce replacement rate."
        else:
            return "Normal regime. Standard replacement rate."


def main():
    """Generate scenario metrics for all defined scenarios"""
    
    # Load NIFTY 200
    print("Loading NIFTY 200 dataset...")
    prices_df = pd.read_csv('Dataset/prices_timeseries_complete.csv', parse_dates=['Date'])
    prices_df = prices_df.sort_values('Date').reset_index(drop=True)
    
    # Load scenario configurations
    with open('config/enhanced_evaluation_config.json', 'r') as f:
        eval_config = json.load(f)
    
    # Initialize generators
    metrics_gen = ScenarioMetricsGenerator()
    adaptive_rebalancer = AdaptiveKRebalancer()
    
    # Process all scenarios
    all_scenarios_reports = {}
    
    # Get scenarios from either 'scenarios' or 'regime_scenarios'
    scenarios_to_process = eval_config.get('regime_scenarios', eval_config.get('scenarios', {}))
    
    for scenario_category, scenarios in scenarios_to_process.items():
        if isinstance(scenarios, dict):
            for scenario_name, scenario_config in scenarios.items():
                try:
                    report = metrics_gen.generate_scenario_report(
                        f"{scenario_category}_{scenario_name}",
                        scenario_config,
                        prices_df
                    )
                    all_scenarios_reports[f"{scenario_category}_{scenario_name}"] = report
                except Exception as e:
                    print(f"Error processing {scenario_category}_{scenario_name}: {e}")
    
    # Generate adaptive K report
    adaptive_report = adaptive_rebalancer.generate_adaptive_report(all_scenarios_reports)
    
    # Save results
    output_dir = Path('results')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save scenario metrics
    with open(output_dir / 'scenario_metrics_nifty200.json', 'w') as f:
        json.dump(all_scenarios_reports, f, indent=2, default=str)
    
    # Save adaptive K report
    with open(output_dir / 'adaptive_k_report_nifty200.json', 'w') as f:
        json.dump(adaptive_report, f, indent=2, default=str)
    
    print(f"\n{'='*80}")
    print(f"Scenario Metrics Report (NIFTY 200)")
    print(f"{'='*80}")
    print(f"Processed {len(all_scenarios_reports)} scenarios")
    print(f"Results saved to:")
    print(f"  - results/scenario_metrics_nifty200.json")
    print(f"  - results/adaptive_k_report_nifty200.json")
    
    return all_scenarios_reports, adaptive_report


if __name__ == '__main__':
    main()
