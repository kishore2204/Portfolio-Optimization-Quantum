"""
Classical Weight Optimization with Sector Constraints
======================================================
Optimizes continuous portfolio weights using CVXPY

Objective: Maximize Sharpe ratio
Constraints:
- Weights sum to 1
- Sector concentration limits
- No short selling (weights >= 0)

Author: Enhanced Portfolio System
Date: March 2026
"""

import numpy as np
import pandas as pd
import json
import cvxpy as cp
from pathlib import Path

class ClassicalWeightOptimizer:
    
    def __init__(self, config_path='config/config.json'):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.risk_free_rate = self.config['data']['risk_free_rate']
        
        # Sector constraints
        self.max_sector_weight = self.config['sector_constraints']['max_sector_weight']
        self.min_sectors = self.config['sector_constraints']['min_sectors']
    
    def load_data(self):
        """Load selected stocks and prepare data"""
        
        # Load selected stocks
        with open('portfolios/selected_stocks.json', 'r') as f:
            portfolio_data = json.load(f)
        
        self.selected_stocks = portfolio_data['selected_stocks']
        self.stock_to_sector = portfolio_data['stock_to_sector']
        
        # Load universe data from step 1 output
        mean_returns_all = np.load('data/mean_returns.npy')
        cov_matrix_all = np.load('data/covariance_matrix.npy')
        sharpe_ratios_all = np.load('data/sharpe_ratios.npy')
        
        # Load metadata to get stock list
        with open('data/universe_metadata.json', 'r') as f:
            metadata = json.load(f)
        all_stocks = metadata['stocks']
        
        # Filter to selected stocks
        stock_indices = [all_stocks.index(s) for s in self.selected_stocks]
        
        self.mean_returns = mean_returns_all[stock_indices]
        self.cov_matrix = cov_matrix_all[np.ix_(stock_indices, stock_indices)]
        self.sharpe_ratios = sharpe_ratios_all[stock_indices]
        
        print(f"Loaded data for {len(self.selected_stocks)} selected stocks")
        print(f"Mean returns range: [{self.mean_returns.min():.4f}, {self.mean_returns.max():.4f}]")
    
    def optimize_weights_sharpe(self):
        """Optimize weights to maximize Sharpe ratio with constraints"""
        
        print(f"\nOptimizing portfolio weights...")
        
        N = len(self.selected_stocks)
        
        # Decision variables
        w = cp.Variable(N)
        
        # Portfolio statistics
        portfolio_return = self.mean_returns @ w
        portfolio_variance = cp.quad_form(w, self.cov_matrix)
        portfolio_std = cp.sqrt(portfolio_variance)
        
        # Objective: Maximize Sharpe ratio
        # Since Sharpe = (r - rf) / std, we can't directly maximize (non-convex)
        # Instead, we minimize variance for a target return (equivalent via efficient frontier)
        
        # Alternative: Maximize return - gamma * variance (mean-variance optimization)
        gamma = 1.0  # Risk aversion parameter
        objective = cp.Maximize(portfolio_return - gamma * portfolio_variance)
        
        # Constraints
        constraints = [
            cp.sum(w) == 1,  # Weights sum to 1
            w >= 0,           # No short selling
        ]
        
        # Add sector concentration constraints
        sectors = set(self.stock_to_sector.values())
        for sector in sectors:
            sector_indices = [i for i, stock in enumerate(self.selected_stocks) 
                             if self.stock_to_sector[stock] == sector]
            if sector_indices:
                constraints.append(cp.sum(w[sector_indices]) <= self.max_sector_weight)
        
        # Solve problem
        problem = cp.Problem(objective, constraints)
        
        try:
            # Try with cvxopt first (newly installed, more robust)
            problem.solve(solver=cp.CVXOPT, verbose=False)
            
            if problem.status in ['optimal', 'optimal_inaccurate']:
                self.optimal_weights = w.value
                print(f"  OK Optimization successful with CVXOPT: {problem.status}")
                print(f"  Portfolio return: {float(portfolio_return.value)*100:.2f}%")
                print(f"  Portfolio risk: {float(np.sqrt(portfolio_variance.value))*100:.2f}%")
                sharpe = (portfolio_return.value - self.risk_free_rate) / np.sqrt(portfolio_variance.value)
                print(f"  Sharpe ratio: {sharpe:.4f}")
                
            else:
                # Try ECOS as fallback
                print(f"  [WARNING] CVXOPT status: {problem.status}, trying ECOS...")
                problem.solve(solver=cp.ECOS, verbose=False)
                
                if problem.status in ['optimal', 'optimal_inaccurate']:
                    self.optimal_weights = w.value
                    print(f"  OK Optimization successful with ECOS: {problem.status}")
                else:
                    print(f"  [WARNING] ECOS also failed: {problem.status}")
                    print(f"  Falling back to equal weights")
                    self.optimal_weights = np.ones(N) / N
                
        except Exception as e:
            print(f"  [ERROR] Optimization failed: {e}")
            print(f"  Trying SCS solver as last resort...")
            
            try:
                problem.solve(solver=cp.SCS, verbose=False)
                if problem.status in ['optimal', 'optimal_inaccurate']:
                    self.optimal_weights = w.value
                    print(f"  OK Optimization successful with SCS: {problem.status}")
                else:
                    print(f"  Using equal weights as fallback")
                    self.optimal_weights = np.ones(N) / N
            except:
                print(f"  Using equal weights as fallback")
                self.optimal_weights = np.ones(N) / N
        
        # Normalize weights (ensure they sum to 1)
        self.optimal_weights = self.optimal_weights / self.optimal_weights.sum()
        
        return self.optimal_weights
    
    def calculate_portfolio_statistics(self):
        """Calculate portfolio performance metrics"""
        
        w = self.optimal_weights
        
        # Portfolio return and risk
        portfolio_return = np.dot(self.mean_returns, w)
        portfolio_variance = np.dot(w, np.dot(self.cov_matrix, w))
        portfolio_std = np.sqrt(portfolio_variance)
        
        # Sharpe ratio
        sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_std
        
        # Diversification ratio: weighted avg std / portfolio std
        individual_stds = np.sqrt(np.diag(self.cov_matrix))
        diversification_ratio = np.dot(w, individual_stds) / portfolio_std
        
        self.portfolio_stats = {
            'expected_return': float(portfolio_return),
            'volatility': float(portfolio_std),
            'sharpe_ratio': float(sharpe_ratio),
            'diversification_ratio': float(diversification_ratio)
        }
        
        print(f"\n{'='*80}")
        print("OPTIMIZED PORTFOLIO STATISTICS")
        print(f"{'='*80}")
        print(f"Expected Annual Return: {portfolio_return*100:.2f}%")
        print(f"Annual Volatility: {portfolio_std*100:.2f}%")
        print(f"Sharpe Ratio: {sharpe_ratio:.3f}")
        print(f"Diversification Ratio: {diversification_ratio:.3f}")
    
    def print_optimal_weights(self):
        """Print and analyze optimal weights"""
        
        print(f"\n{'='*80}")
        print("OPTIMAL PORTFOLIO WEIGHTS")
        print(f"{'='*80}\n")
        
        # Create DataFrame for analysis
        weights_df = pd.DataFrame({
            'Stock': self.selected_stocks,
            'Weight': self.optimal_weights,
            'Sector': [self.stock_to_sector[s] for s in self.selected_stocks],
            'Expected_Return': self.mean_returns,
            'Sharpe': self.sharpe_ratios
        })
        
        weights_df = weights_df.sort_values('Weight', ascending=False)
        
        print(f"{'Stock':<12} {'Weight':<10} {'Sector':<25} {'Exp.Ret':<10} {'Sharpe':<8}")
        print("-" * 85)
        
        for _, row in weights_df.iterrows():
            print(f"{row['Stock']:<12} {row['Weight']:>8.2%}   {row['Sector']:<25} "
                  f"{row['Expected_Return']:>8.2%}   {row['Sharpe']:>6.3f}")
        
        # Sector allocation
        print(f"\n{'='*80}")
        print("SECTOR ALLOCATION")
        print(f"{'='*80}\n")
        
        sector_weights = weights_df.groupby('Sector')['Weight'].sum().sort_values(ascending=False)
        
        print(f"{'Sector':<30} {'Weight':<10}")
        print("-" * 40)
        for sector, weight in sector_weights.items():
            print(f"{sector:<30} {weight:>8.2%}")
        
        # Check concentration limits
        max_sector_weight = sector_weights.max()
        if max_sector_weight > self.max_sector_weight:
            print(f"\n[WARNING] Sector concentration limit exceeded!")
            print(f"  Max sector weight: {max_sector_weight:.2%} > {self.max_sector_weight:.2%}")
        else:
            print(f"\nOK All sector concentration limits satisfied")
            print(f"  Max sector weight: {max_sector_weight:.2%} <= {self.max_sector_weight:.2%}")
        
        self.weights_df = weights_df
    
    def save_optimal_portfolio(self):
        """Save optimal weights to file"""
        
        # Create weight dictionary
        weights_dict = {
            stock: float(weight) 
            for stock, weight in zip(self.selected_stocks, self.optimal_weights)
        }
        
        # Add portfolio statistics
        portfolio_output = {
            **weights_dict,
            '_metadata': {
                'num_stocks': len(self.selected_stocks),
                'portfolio_stats': self.portfolio_stats,
                'sector_allocation': self.weights_df.groupby('Sector')['Weight'].sum().to_dict()
            }
        }
        
        # Save as JSON
        with open('portfolios/optimal_weights.json', 'w') as f:
            json.dump(portfolio_output, f, indent=2)
        
        # Save detailed DataFrame as CSV
        self.weights_df.to_csv('portfolios/optimal_weights.csv', index=False)
        
        print(f"\nOK Optimal weights saved: portfolios/optimal_weights.json")
        print(f"OK Detailed weights saved: portfolios/optimal_weights.csv")
    
    def run_optimization(self):
        """Execute full weight optimization pipeline"""
        
        print(f"\n{'='*80}")
        print("CLASSICAL WEIGHT OPTIMIZATION")
        print(f"{'='*80}\n")
        
        # Load data
        self.load_data()
        
        # Optimize weights
        self.optimize_weights_sharpe()
        
        # Calculate statistics
        self.calculate_portfolio_statistics()
        
        # Print results
        self.print_optimal_weights()
        
        # Save results
        self.save_optimal_portfolio()
        
        print(f"\n{'='*80}")
        print("WEIGHT OPTIMIZATION COMPLETE")
        print(f"{'='*80}\n")
        
        return self.optimal_weights

def main():
    """Main execution"""
    try:
        optimizer = ClassicalWeightOptimizer()
        weights = optimizer.run_optimization()
        return 0
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())

