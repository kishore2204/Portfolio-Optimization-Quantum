"""
Quantum-Inspired Stock Selection using Simulated Annealing
===========================================================
Solves QUBO problem to select optimal K stocks with sector diversity

Uses D-Wave Ocean SDK's SimulatedAnnealingSampler

Author: Enhanced Portfolio System
Date: March 2026
"""

import numpy as np
import json
from pathlib import Path
from dimod import BinaryQuadraticModel
from neal import SimulatedAnnealingSampler

class QuantumStockSelector:
    
    def __init__(self, config_path='config/config.json'):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.K = self.config['portfolio']['K']
        self.num_reads = self.config['quantum']['num_reads']
        self.num_sweeps = self.config['quantum']['num_sweeps']
        
        # Sector constraints
        self.min_sectors = self.config['sector_constraints']['min_sectors']
        self.max_sector_weight = self.config['sector_constraints']['max_sector_weight']
    
    def load_qubo(self):
        """Load QUBO matrix and metadata"""
        
        # Load QUBO matrix
        self.Q = np.load('quantum/qubo_matrix.npy')
        
        # Load metadata
        with open('quantum/qubo_metadata.json', 'r') as f:
            self.metadata = json.load(f)
        
        self.stocks = np.array(self.metadata['stocks'])
        self.stock_to_sector = self.metadata['stock_to_sector']
        
        print(f"Loaded QUBO matrix: {self.Q.shape}")
        print(f"Target portfolio: K = {self.K} stocks")
    
    def convert_to_bqm(self):
        """Convert QUBO matrix to Binary Quadratic Model"""
        
        N = len(self.stocks)
        
        # Extract linear and quadratic terms
        linear = {}
        quadratic = {}
        
        for i in range(N):
            linear[i] = self.Q[i, i]
            for j in range(i+1, N):
                if self.Q[i, j] != 0:
                    quadratic[(i, j)] = self.Q[i, j]
        
        # Create BQM
        self.bqm = BinaryQuadraticModel(linear, quadratic, 0.0, 'BINARY')
        
        print(f"\nBQM created:")
        print(f"  Variables: {len(linear)}")
        print(f"  Quadratic terms: {len(quadratic)}")
    
    def solve_with_simulated_annealing(self):
        """Solve QUBO using simulated annealing"""
        
        print(f"\nRunning Simulated Annealing...")
        print(f"  Num reads: {self.num_reads}")
        print(f"  Num sweeps per read: {self.num_sweeps}")
        
        # Initialize sampler
        sampler = SimulatedAnnealingSampler()
        
        # Sample
        sampleset = sampler.sample(
            self.bqm,
            num_reads=self.num_reads,
            num_sweeps=self.num_sweeps,
            beta_range=None,  # Auto-detect temperature range
            beta_schedule_type='geometric'
        )
        
        print(f"  OK Completed {len(sampleset)} samples")
        
        # Get best solutions
        self.sampleset = sampleset
        
        return sampleset
    
    def validate_solution(self, solution):
        """
        Validate solution meets constraints:
        1. Exactly K stocks selected
        2. Minimum sector diversity
        3. No sector overconcentration
        """
        
        # Get selected stocks
        selected_indices = [i for i, val in solution.items() if val == 1]
        selected_stocks = [self.stocks[i] for i in selected_indices]
        
        # Check cardinality
        num_selected = len(selected_stocks)
        
        # Check sector diversity
        selected_sectors = set()
        sector_counts = {}
        for stock in selected_stocks:
            sector = self.stock_to_sector.get(stock, 'Others')
            selected_sectors.add(sector)
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
        
        num_sectors = len(selected_sectors)
        max_sector_count = max(sector_counts.values()) if sector_counts else 0
        
        # Calculate sector concentration
        max_concentration = max_sector_count / num_selected if num_selected > 0 else 0
        
        valid = (
            num_selected == self.K and
            num_sectors >= self.min_sectors and
            max_concentration <= self.max_sector_weight
        )
        
        return {
            'valid': valid,
            'num_selected': num_selected,
            'num_sectors': num_sectors,
            'max_concentration': max_concentration,
            'selected_stocks': selected_stocks,
            'selected_sectors': selected_sectors,
            'sector_counts': sector_counts
        }
    
    def select_best_valid_solution(self):
        """Select best solution that satisfies all constraints"""
        
        print(f"\nEvaluating solutions...")
        
        valid_solutions = []
        
        for i, (sample, energy) in enumerate(self.sampleset.data(['sample', 'energy'])):
            validation = self.validate_solution(sample)
            
            if validation['valid']:
                valid_solutions.append({
                    'sample': sample,
                    'energy': energy,
                    'validation': validation
                })
        
        print(f"  Valid solutions: {len(valid_solutions)}/{len(self.sampleset)}")
        
        if not valid_solutions:
            print(f"\n[INFO] Relaxing constraints to find best approximate solution")
            
            # Find solutions close to K stocks (K-3 to K+3)
            k_range = range(max(self.K - 3, 5), min(self.K + 3, len(self.stocks)))
            for k_target in k_range:
                for sample, energy in self.sampleset.data(['sample', 'energy']):
                    validation = self.validate_solution(sample)
                    if validation['num_selected'] == k_target:
                        valid_solutions.append({
                            'sample': sample,
                            'energy': energy,
                            'validation': validation
                        })
                if valid_solutions:
                    print(f"  Found {len(valid_solutions)} solutions with {k_target} stocks")
                    break
        
        if not valid_solutions:
            # Just take the best solution regardless
            print(f"  Taking best solution regardless of K constraint")
            best_sample, best_energy = list(self.sampleset.data(['sample', 'energy']))[0]
            validation = self.validate_solution(best_sample)
            valid_solutions.append({
                'sample': best_sample,
                'energy': best_energy,
                'validation': validation
            })
        
        # Select best valid solution (lowest energy)
        best_solution = min(valid_solutions, key=lambda x: x['energy'])
        
        self.selected_solution = best_solution
        self.selected_stocks = best_solution['validation']['selected_stocks']
        
        # Print results
        print(f"\n{'='*80}")
        print("SELECTED PORTFOLIO")
        print(f"{'='*80}")
        print(f"\nEnergy: {best_solution['energy']:.6f}")
        print(f"Stocks selected: {len(self.selected_stocks)}")
        print(f"Sectors: {best_solution['validation']['num_sectors']}")
        print(f"Max sector concentration: {best_solution['validation']['max_concentration']:.1%}")
        
        print(f"\nSelected Stocks:")
        print(f"{'Stock':<15} {'Sector':<25}")
        print("-" * 45)
        for stock in sorted(self.selected_stocks):
            sector = self.stock_to_sector.get(stock, 'Others')
            print(f"{stock:<15} {sector:<25}")
        
        print(f"\nSector Distribution:")
        for sector, count in sorted(best_solution['validation']['sector_counts'].items(), 
                                    key=lambda x: -x[1]):
            pct = count / len(self.selected_stocks) * 100
            print(f"  {sector:<25}: {count:>2} stocks ({pct:>5.1f}%)")
        
        return self.selected_stocks
    
    def save_selected_portfolio(self):
        """Save selected stocks portfolio"""
        
        # Save stock list
        portfolio_data = {
            'selected_stocks': self.selected_stocks,
            'num_stocks': len(self.selected_stocks),
            'energy': float(self.selected_solution['energy']),
            'num_sectors': self.selected_solution['validation']['num_sectors'],
            'max_concentration': self.selected_solution['validation']['max_concentration'],
            'sector_counts': self.selected_solution['validation']['sector_counts'],
            'stock_to_sector': {
                stock: self.stock_to_sector.get(stock, 'Others') 
                for stock in self.selected_stocks
            }
        }
        
        with open('portfolios/selected_stocks.json', 'w') as f:
            json.dump(portfolio_data, f, indent=2)
        
        print(f"\nOK Selected portfolio saved: portfolios/selected_stocks.json")
    
    def run_selection(self):
        """Execute full quantum selection pipeline"""
        
        print(f"\n{'='*80}")
        print("QUANTUM-INSPIRED STOCK SELECTION")
        print(f"{'='*80}\n")
        
        # Load QUBO
        self.load_qubo()
        
        # Convert to BQM
        self.convert_to_bqm()
        
        # Solve with simulated annealing
        self.solve_with_simulated_annealing()
        
        # Select best valid solution
        self.select_best_valid_solution()
        
        # Save results
        self.save_selected_portfolio()
        
        print(f"\n{'='*80}")
        print("QUANTUM SELECTION COMPLETE")
        print(f"{'='*80}\n")
        
        return self.selected_stocks

def main():
    """Main execution"""
    try:
        selector = QuantumStockSelector()
        selected_stocks = selector.run_selection()
        return 0
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())

