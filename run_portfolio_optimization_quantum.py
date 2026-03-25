"""
Enhanced Quantum Portfolio - Paper's Methodology Pipeline
==========================================================
Implements Morapakula et al. (2025) methodology:

1. Data Preparation (NIFTY 100, Train/Test Split)
1b. Two-Step Cardinality Determination (Convex Sharpe → K)
2. QUBO Formulation (Paper's MVO - Equation 8)
3. Quantum Selection (Simulated Annealing)
4. Classical Weight Optimization (SLSQP Sharpe maximization)
5. Strategy Comparison with Quarterly Rebalancing

Reference: "End-to-End Portfolio Optimization with Hybrid Quantum Annealing"
           Morapakula et al., Advanced Quantum Technologies, 2025

Author: Enhanced Portfolio System  
Date: March 2026
"""

import sys
import time
from pathlib import Path
import json
from datetime import datetime
import numpy as np
import importlib.util

def import_module_from_file(module_name, filepath):
    """Dynamic module import"""
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Get current directory
current_dir = Path(__file__).parent

# Import weight optimizer
sys.path.insert(0, str(current_dir / 'quantum'))
from weight_optimizer import optimize_sharpe_slsqp, create_full_weight_vector, get_dynamic_risk_free_rate
current_dir = Path(__file__).parent

# Import modules in phase order
mod1 = import_module_from_file("data_prep", current_dir / "phase_01_data_preparation.py")
mod1b = import_module_from_file("cardinality", current_dir / "phase_02_cardinality_determination.py")
mod2 = import_module_from_file("qubo_form", current_dir / "phase_03_qubo_formulation.py")
mod3 = import_module_from_file("quantum_sel", current_dir / "phase_04_quantum_selection.py")
mod4b = import_module_from_file("quarterly_rebal", current_dir / "phase_05_rebalancing.py")
mod5 = import_module_from_file("comparison", current_dir / "phase_07_strategy_comparison.py")
mod6 = import_module_from_file("classical", current_dir / "phase_06_weight_optimization.py")

# Extract classes
QUBOFormulator = mod2.QUBOFormulator
QuantumStockSelector = mod3.QuantumStockSelector
ClassicalWeightOptimizer = mod6.ClassicalWeightOptimizer
QuarterlyRebalancer = mod4b.QuarterlyRebalancer


class PaperMethodologyPipeline:
    """Pipeline implementing paper's exact methodology"""
    
    def __init__(self, config_path='config/config.json'):
        self.config_path = config_path
        
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.start_time = None
        self.step_times = {}
        self.K_optimal = None
    
    def print_header(self):
        """Print pipeline header"""
        print("\n" + "="*100)
        print(" " * 15 + "PAPER'S METHODOLOGY: HYBRID QUANTUM-CLASSICAL PORTFOLIO OPTIMIZATION")
        print("="*100)
        print(f"\nReference: Morapakula et al. (2025)")
        print(f"           'End-to-End Portfolio Optimization with Hybrid Quantum Annealing'")
        print(f"           Advanced Quantum Technologies")
        print(f"\nConfiguration:")
        print(f"  Universe: NIFTY 100")
        print(f"  Portfolio Size: K will be derived from convex Sharpe optimization")
        print(f"  Training Period: 2011-2022")
        print(f"  Testing Period: 2024-2026")
        print(f"  Rebalancing: Quarterly with underperformer removal (K_sell={self.config['rebalancing']['K_sell']})")
        print(f"  QUBO Formulation: Paper's MVO (min q*x'Cx - mu'x + lambda(1'x-K)^2)")
        print(f"  Weight Optimization: SLSQP solver")
        print(f"\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*100 + "\n")
    
    def run_step(self, step_num, step_name, runner_func):
        """Run a pipeline step with timing"""
        
        print("\n" + "=" * 80)
        print(f"STEP {step_num}: {step_name}")
        print("=" * 80 + "\n")
        
        step_start = time.time()
        
        try:
            result = runner_func()
            step_end = time.time()
            elapsed = step_end - step_start
            
            self.step_times[step_name] = elapsed
            
            print(f"\nStep {step_num} completed in {elapsed:.2f}s")
            
            return result
            
        except Exception as e:
            print(f"\nStep {step_num} failed")
            print(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def step1_data_preparation(self):
        """Step 1: Prepare and clean NIFTY 100 data"""
        print("Executing standard data preparation...")
        return mod1.main()
    
    def step1b_cardinality_determination(self):
        """Step 1b: Determine optimal K using convex Sharpe maximization (Paper's method)"""
        print("Determining optimal cardinality K from convex optimization...")
        
        # Load prepared data
        mean_returns = np.load('data/mean_returns.npy')
        cov_matrix = np.load('data/covariance_matrix.npy')
        
        # Determine K
        K_optimal, y_optimal = mod1b.determine_optimal_cardinality(
            mean_returns, cov_matrix,
            rf_rate=self.config['data']['risk_free_rate'],
            verbose=True
        )
        
        # Save analysis
        if y_optimal is not None:
            mod1b.save_cardinality_analysis(K_optimal, y_optimal, mean_returns, 
                                           cov_matrix, self.config)
        
        # Update config with optimal K
        self.K_optimal = K_optimal
        self.config['portfolio']['K'] = K_optimal
        
        # Save updated config
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
        
        print(f"\nOptimal K = {K_optimal} (saved to config)")
        
        return K_optimal
    
    def step2_qubo_formulation(self):
        """Step 2: Formulate QUBO using paper's MVO method (Equation 8)"""
        print("Formulating QUBO with paper's MVO formulation...")
        
        formulator = QUBOFormulator(self.config_path)
        formulator.run_formulation()
        
        return True
    
    def step3_quantum_selection(self):
        """Step 3: Select stocks using simulated annealing"""
        print("Running quantum-inspired stock selection...")
        
        selector = QuantumStockSelector(self.config_path)
        selected_stocks = selector.run_selection()
        
        return selected_stocks
    
    def step4_weight_optimization(self):
        """Step 4: Optimize weights using SLSQP"""
        print("Optimizing portfolio weights with SLSQP Sharpe maximization...")
        print("Note: This replaces equal weights with optimized allocation")
        
        # Load selected stocks
        with open('portfolios/selected_stocks.json', 'r') as f:
            portfolio_data = json.load(f)
        
        selected_stocks = portfolio_data['selected_stocks']
        
        # Load universe data
        mean_returns_all = np.load('data/mean_returns.npy')
        cov_matrix_all = np.load('data/covariance_matrix.npy')
        
        with open('data/universe_metadata.json', 'r') as f:
            metadata = json.load(f)
        all_stocks = metadata['stocks']
        
        # Get indices of selected stocks
        stock_indices = [all_stocks.index(s) for s in selected_stocks]
        
        # Use dynamic risk-free rate
        risk_free_rate = get_dynamic_risk_free_rate()
        
        # Optimize weights using SLSQP
        optimized_weights, info = optimize_sharpe_slsqp(
            stock_indices,
            mean_returns_all,
            cov_matrix_all,
            risk_free_rate=risk_free_rate,
            verbose=True
        )
        
        # Create full weight vector
        full_weights = create_full_weight_vector(
            stock_indices,
            optimized_weights,
            len(all_stocks)
        )
        
        # Save optimized weights
        weights_data = {
            'stocks': selected_stocks,
            'weights': optimized_weights.tolist(),
            'optimization_info': {
                'sharpe_ratio': float(info['sharpe_ratio']),
                'portfolio_return': float(info['portfolio_return']),
                'portfolio_volatility': float(info['portfolio_volatility']),
                'risk_free_rate': float(info['risk_free_rate']),
                'method': 'SLSQP_Sharpe_Maximization',
                'max_weight': float(info['max_weight']),
                'min_weight': float(info['min_weight'])
            }
        }
        
        with open('portfolios/optimized_weights.json', 'w') as f:
            json.dump(weights_data, f, indent=2)
        
        # Also save as numpy array
        np.save('portfolios/weights.npy', full_weights)
        
        print(f"\nOptimized weights saved to portfolios/optimized_weights.json")
        print(f"Expected Sharpe Ratio: {info['sharpe_ratio']:.3f}")
        print(f"Expected Return: {info['portfolio_return']:.2%}")
        print(f"Expected Volatility: {info['portfolio_volatility']:.2%}")
        
        return full_weights
    
    def step5_strategy_comparison(self):
        """Step 5: Compare strategies with quarterly rebalancing"""
        print("Comparing strategies with quarterly rebalancing...")
        
        return mod5.main()
    
    def run_pipeline(self):
        """Execute full paper methodology pipeline"""
        
        self.start_time = time.time()
        
        self.print_header()
        
        try:
            # Step 1: Data Preparation
            self.run_step(1, "Data Preparation (NIFTY 100, Train/Test Split)", 
                         self.step1_data_preparation)
            
            # Step 1b: Cardinality Determination (NEW - Paper's method)
            K_optimal = self.run_step("1b", "Two-Step Cardinality Determination (Convex Sharpe)", 
                                     self.step1b_cardinality_determination)
            
            # Step 2: QUBO Formulation (Paper's MVO)
            self.run_step(2, "QUBO Formulation (Paper's MVO - Equation 8)", 
                         self.step2_qubo_formulation)
            
            # Step 3: Quantum Selection
            selected_stocks = self.run_step(3, "Quantum Selection (Simulated Annealing)", 
                                           self.step3_quantum_selection)
            
            # Step 4: Weight Optimization (SLSQP)
            weights = self.run_step(4, "Weight Optimization (SLSQP Solver)", 
                                   self.step4_weight_optimization)
            
            # Step 5: Strategy Comparison (with quarterly rebalancing)
            metrics = self.run_step(5, "Strategy Comparison (Quarterly Rebalancing)", 
                                   self.step5_strategy_comparison)
            
            # Print summary
            self.print_summary()
            
            return 0
            
        except Exception as e:
            print(f"\n{'='*100}")
            print("PIPELINE FAILED")
            print(f"{'='*100}\n")
            print(f"Error: {str(e)}")
            return 1
    
    def print_summary(self):
        """Print pipeline summary"""
        
        total_time = time.time() - self.start_time
        
        print("\n" + "="*100)
        print(" " * 30 + "PIPELINE EXECUTION SUMMARY")
        print("="*100 + "\n")
        
        print("Key Results:")
        print("-" * 80)
        print(f"  Optimal Cardinality (K): {self.K_optimal}")
        
        # Load final results
        try:
            with open('results/strategy_comparison.json', 'r') as f:
                results = json.load(f)
            
            print(f"\n  Strategy Performance:")
            for strategy in results['metrics']:
                print(f"\n    {strategy['strategy']}:")
                print(f"      Total Return: {strategy['total_return']:.2f}%")
                print(f"      Annual Return: {strategy['annual_return']:.2f}%")
                print(f"      Sharpe Ratio: {strategy['sharpe_ratio']:.4f}")
                print(f"      Max Drawdown: {strategy['max_drawdown']:.2f}%")
        except:
            print("  (Results file not found)")
        
        print("\n" + "-" * 80)
        print("\nStep Timing:")
        print("-" * 80)
        for step_name, elapsed in self.step_times.items():
            print(f"  {step_name:<50}: {elapsed:>8.2f}s ({elapsed/total_time*100:>5.1f}%)")
        print("-" * 80)
        print(f"  {'Total Time':<50}: {total_time:>8.2f}s")
        
        print("\n" + "="*100)
        print(" " * 20 + "PAPER'S METHODOLOGY IMPLEMENTATION COMPLETE")
        print("="*100 + "\n")
        
        print("Improvements over baseline:")
        print("  - Two-step cardinality determination (data-driven K)")
        print("  - Paper's MVO QUBO formulation (Equation 8)")
        print("  - SLSQP solver (proper weight optimization)")
        print("  - Quarterly rebalancing (vs half-yearly)")
        print("  - Underperformer removal (vs drift-based)")
        print("  - Sector-matched replacement")
        print()


def main():
    """Main entry point"""
    
    # Check if config exists
    if not Path('config/config.json').exists():
        print("Error: config/config.json not found")
        print("Please ensure you are running from the Portfolio Optimization Quantum directory")
        return 1
    
    # Create required directories
    for directory in ['data', 'quantum', 'portfolios', 'results']:
        Path(directory).mkdir(exist_ok=True)
    
    # Run pipeline with paper's methodology
    pipeline = PaperMethodologyPipeline()
    return pipeline.run_pipeline()


if __name__ == "__main__":
    exit(main())

