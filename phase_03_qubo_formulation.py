"""
QUBO Formulation with Sector Diversification
=============================================
Converts portfolio selection to QUBO form with sector constraints

QUBO: Minimize  x^T Q x
where x_i ∈ {0,1} indicates if stock i is selected

Objective: Maximize diversification while ensuring sector balance

Author: Enhanced Portfolio System
Date: March 2026
"""

import numpy as np
import pandas as pd
import json
from pathlib import Path

class QUBOFormulator:
    
    def __init__(self, config_path='config/config.json'):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.K = self.config['portfolio']['K']
        self.q = self.config['portfolio']['q']
        
        # Sector constraints
        self.min_sectors = self.config['sector_constraints']['min_sectors']
        self.max_sector_weight = self.config['sector_constraints']['max_sector_weight']
        
        # Load sector mappings
        with open('config/nifty100_sectors.json', 'r') as f:
            self.sector_map = json.load(f)
    
    def load_prepared_data(self):
        """Load prepared data from step 1"""
        
        # Load universe data from step 1 output
        self.mean_returns = np.load('data/mean_returns.npy')
        self.cov_matrix = np.load('data/covariance_matrix.npy')
        self.sharpe_ratios = np.load('data/sharpe_ratios.npy')
        
        # Load returns data for downside risk calculation
        self.returns_data = np.load('data/returns_matrix.npy')
        
        # Load metadata
        with open('data/universe_metadata.json', 'r') as f:
            self.metadata = json.load(f)
        
        self.stocks = np.array(self.metadata['stocks'])
        
        print(f"Loaded {len(self.stocks)} stocks for QUBO formulation")
        print(f"Target portfolio size: K = {self.K}")
    
    def map_stocks_to_sectors(self):
        """Create mapping from stocks to sectors"""
        self.stock_to_sector = {}

        # Support both flat and nested structures in sector config.
        sector_source = self.sector_map
        if 'NIFTY_100_STOCKS' in sector_source and isinstance(sector_source['NIFTY_100_STOCKS'], dict):
            sector_source = sector_source['NIFTY_100_STOCKS']

        for sector, stocks_list in sector_source.items():
            for stock in stocks_list:
                if stock in self.stocks:
                    self.stock_to_sector[stock] = sector
        
        # Count stocks per sector
        sector_counts = {}
        for stock in self.stocks:
            sector = self.stock_to_sector.get(stock, 'Others')
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
        
        print(f"\nSector distribution in universe:")
        for sector, count in sorted(sector_counts.items(), key=lambda x: -x[1]):
            print(f"  {sector:<20}: {count:>3} stocks")
    
    def calculate_downside_deviation(self):
        """
        Calculate downside deviation for each stock.
        
        Downside deviation = std dev of negative returns only
        This penalizes stocks that crash during downturns.
        
        Returns:
            np.ndarray: Annualized downside deviation for each stock
        """
        N = len(self.stocks)
        downside_devs = np.zeros(N)
        
        for i in range(N):
            stock_returns = self.returns_data[:, i]
            # Only consider negative returns (losses)
            downside_returns = stock_returns[stock_returns < 0]
            
            if len(downside_returns) > 0:
                # Calculate standard deviation of downside
                downside_devs[i] = np.std(downside_returns) * np.sqrt(252)
            else:
                # No losses observed (very rare) - use overall volatility
                downside_devs[i] = np.std(stock_returns) * np.sqrt(252)
        
        return downside_devs

    def save_qubo_inputs_csv(self, downside_devs, lambda_penalty, sector_penalty):
        """Save all QUBO inputs as human-readable CSV files in data/ folder."""
        data_dir = Path('data')
        data_dir.mkdir(parents=True, exist_ok=True)

        def _safe_to_csv(df, filename: str):
            path = data_dir / filename
            try:
                df.to_csv(path, index=False)
                return path.name
            except PermissionError:
                alt = data_dir / f"{path.stem}_new{path.suffix}"
                df.to_csv(alt, index=False)
                print(f"  [WARN] {path.name} is locked; wrote {alt.name} instead")
                return alt.name

        # Mean returns vector (annualized)
        mean_df = pd.DataFrame({
            'stock': self.stocks,
            'mean_return_annual': self.mean_returns,
        })
        mean_name = _safe_to_csv(mean_df, 'qubo_input_mean_returns.csv')

        # Covariance matrix (annualized)
        cov_df = pd.DataFrame(self.cov_matrix, index=self.stocks, columns=self.stocks)
        cov_path = data_dir / 'qubo_input_covariance_matrix.csv'
        try:
            cov_df.to_csv(cov_path)
            cov_name = cov_path.name
        except PermissionError:
            cov_alt = data_dir / 'qubo_input_covariance_matrix_new.csv'
            cov_df.to_csv(cov_alt)
            print(f"  [WARN] {cov_path.name} is locked; wrote {cov_alt.name} instead")
            cov_name = cov_alt.name

        # Returns matrix used by QUBO (daily returns)
        returns_df = pd.DataFrame(self.returns_data, columns=self.stocks)
        returns_name = _safe_to_csv(returns_df, 'qubo_input_returns_matrix.csv')

        # Downside matrix: keep only negative returns, set others to 0
        downside_matrix = np.where(self.returns_data < 0, self.returns_data, 0.0)
        downside_df = pd.DataFrame(downside_matrix, columns=self.stocks)
        downside_name = _safe_to_csv(downside_df, 'qubo_input_downside_matrix.csv')

        # Downside deviation vector (annualized)
        downside_dev_df = pd.DataFrame({
            'stock': self.stocks,
            'downside_deviation_annual': downside_devs,
        })
        downside_dev_name = _safe_to_csv(downside_dev_df, 'qubo_input_downside_deviation.csv')

        # Stock-sector mapping used in sector penalty
        sector_df = pd.DataFrame({
            'stock': self.stocks,
            'sector': [self.stock_to_sector.get(s, 'Others') for s in self.stocks],
        })
        sector_name = _safe_to_csv(sector_df, 'qubo_input_stock_sector_map.csv')

        # Scalar inputs/knobs used in formula
        params_df = pd.DataFrame([
            {
                'N_variables': len(self.stocks),
                'target_K': self.K,
                'q_risk_aversion': self.q,
                'beta_downside': self.config['portfolio_optimization'].get('downside_risk_beta', 0.3),
                'lambda_penalty': lambda_penalty,
                'sector_penalty': sector_penalty,
                'min_sectors': self.min_sectors,
                'max_sector_weight': self.max_sector_weight,
            }
        ])
        params_name = _safe_to_csv(params_df, 'qubo_input_parameters.csv')

        print("\nSaved readable QUBO input CSVs in data/:")
        print(f"  - {mean_name}")
        print(f"  - {cov_name}")
        print(f"  - {returns_name}")
        print(f"  - {downside_name}")
        print(f"  - {downside_dev_name}")
        print(f"  - {sector_name}")
        print(f"  - {params_name}")
    
    def calculate_adaptive_lambda(self):
        """
        Calculate adaptive lambda penalty.
        
        Lambda should scale with:
        - Problem size (N stocks, K target)
        - Magnitude of returns and covariances
        - Ensure constraint dominates when violated
        
        Returns:
            float: Adaptive lambda penalty
        """
        N = len(self.stocks)
        
        # Scale based on problem characteristics
        avg_covariance = np.mean(np.abs(self.cov_matrix))
        avg_return = np.mean(np.abs(self.mean_returns))
        max_diag_q = np.max(np.abs(np.diag(self.cov_matrix)))
        
        # Lambda should dominate when constraint violated
        # But not overwhelm the return/risk signal
        scale_factor = max(avg_covariance, avg_return, max_diag_q)
        
        # Adaptive formula: λ = 10 × scale × (N/K)
        # This ensures proper constraint enforcement regardless of universe size
        lambda_penalty = 10.0 * scale_factor * (N / self.K)
        
        # Add minimum and maximum bounds for stability
        lambda_min = 50.0
        lambda_max = 500.0
        lambda_penalty = np.clip(lambda_penalty, lambda_min, lambda_max)
        
        return lambda_penalty
    
    def compute_qubo_matrix_paper_method(self):
        """
        Compute QUBO matrix using paper's MVO formulation (Equation 8) with robustness extensions.
        
        Paper's formulation:
        min q*x'Cx - μ'x + λ(1'x - B)²
        
        Extensions:
        - Downside risk penalty (β * downside_deviation)
        - Adaptive lambda scaling
        
        Where:
        - x: binary selection vector (x_i ∈ {0,1})
        - C: covariance matrix (Σ)
        - μ: expected returns vector
        - q: risk aversion coefficient (q > 0)
        - λ: Lagrange multiplier for cardinality constraint
        - B: target number of stocks (K)
        
        Reference: Morapakula et al. (2025) - Equation 8
        """
        
        N = len(self.stocks)
        Q = np.zeros((N, N))
        
        print(f"\n{'='*60}")
        print("QUBO FORMULATION (Paper + Robustness Extensions)")
        print(f"{'='*60}")
        
        # === Part 1: Risk Term (q * x'Cx) ===
        # This is the portfolio variance (covariance quadratic form)
        risk_weight = self.q
        Q += risk_weight * self.cov_matrix
        
        print(f"[1/4] Risk term: q * x'Cx")
        print(f"      Risk aversion q = {risk_weight}")
        print(f"      Covariance contribution: [{self.cov_matrix.min():.4f}, {self.cov_matrix.max():.4f}]")
        
        # === Part 2: Return Term (-μ'x) ===
        # Diagonal elements get the negative expected returns
        for i in range(N):
            Q[i, i] -= self.mean_returns[i]
        
        print(f"[2/4] Return term: -μ'x")
        print(f"      Mean returns: [{self.mean_returns.min():.4f}, {self.mean_returns.max():.4f}]")
        
        # === Part 2.5: Downside Risk Penalty ===
        # Penalize stocks with high downside volatility
        # This helps select stocks that perform better in bear markets
        beta = self.config['portfolio_optimization'].get('downside_risk_beta', 0.3)
        
        downside_devs = np.zeros(N)
        if beta > 0:
            downside_devs = self.calculate_downside_deviation()
            
            # Add downside penalty to diagonal (penalize high downside risk)
            for i in range(N):
                Q[i, i] += beta * downside_devs[i]
            
            print(f"[2.5/4] Downside risk penalty: β * downside_deviation")
            print(f"      Beta coefficient = {beta}")
            print(f"      Downside dev range: [{downside_devs.min():.4f}, {downside_devs.max():.4f}]")
        
        # === Part 3: Cardinality Constraint (λ(1'x - K)²) with Adaptive Lambda ===
        # Expanding: λ * (Σx_i - K)²
        #          = λ * (Σ_i Σ_j x_i*x_j - 2K*Σ_i x_i + K²)
        #          = λ * (Σ_i x_i² + Σ_i≠j x_i*x_j - 2K*Σ_i x_i + K²)
        # Since x_i² = x_i for binary variables:
        #          = λ * (Σ_i x_i + Σ_i<j 2*x_i*x_j - 2K*Σ_i x_i + K²)
        #
        # Adaptive lambda scaling
        if self.config['portfolio_optimization'].get('lambda_penalty_adaptive', True):
            lambda_penalty = self.calculate_adaptive_lambda()
        else:
            lambda_penalty = self.config['portfolio_optimization']['lambda_initial']
        
        # Diagonal terms: λ * (1 - 2K)
        for i in range(N):
            Q[i, i] += lambda_penalty * (1 - 2 * self.K)
        
        # Off-diagonal terms: 2λ
        for i in range(N):
            for j in range(i+1, N):
                Q[i, j] += 2 * lambda_penalty
        
        print(f"[3/4] Cardinality constraint: λ(1'x - K)²")
        print(f"      Target K = {self.K}")
        print(f"      Penalty λ = {lambda_penalty:.2f} (adaptive)")
        
        # === Part 4: Sector Diversification (extension to paper) ===
        # Add moderate penalty for sector concentration
        sector_penalty = lambda_penalty * 0.1  # 10% of cardinality penalty
        
        sector_stocks = {}
        for idx, stock in enumerate(self.stocks):
            sector = self.stock_to_sector.get(stock, 'Others')
            if sector not in sector_stocks:
                sector_stocks[sector] = []
            sector_stocks[sector].append(idx)
        
        # Penalize same-sector pairs slightly
        for sector, stock_indices in sector_stocks.items():
            if len(stock_indices) > 1:
                for i in stock_indices:
                    for j in stock_indices:
                        if i < j:
                            Q[i, j] += sector_penalty
        
        print(f"[4/4] Sector diversification penalty")
        print(f"      Sector penalty = {sector_penalty:.2f} (10% of λ)")

        # Export all QUBO inputs as readable CSV files.
        self.save_qubo_inputs_csv(
            downside_devs=downside_devs,
            lambda_penalty=lambda_penalty,
            sector_penalty=sector_penalty,
        )
        
        # === Make symmetric ===
        # QUBO should be symmetric: Q_symmetric = Q + Q^T - diag(Q)
        Q_symmetric = Q + Q.T - np.diag(np.diag(Q))
        
        self.Q = Q_symmetric
        self.lambda_penalty = lambda_penalty
        
        print(f"\nQUBO Matrix Statistics:")
        print(f"  Dimension: {N} x {N}")
        print(f"  Min value: {Q_symmetric.min():.2f}")
        print(f"  Max value: {Q_symmetric.max():.2f}")
        print(f"  Diagonal range: [{np.diag(Q_symmetric).min():.2f}, {np.diag(Q_symmetric).max():.2f}]")
        print(f"  Off-diagonal avg: {(Q_symmetric - np.diag(np.diag(Q_symmetric))).mean():.4f}")
        print(f"{'='*60}\n")
        
        return Q_symmetric
    
    def compute_qubo_matrix(self):
        """Wrapper that calls paper's method"""
        return self.compute_qubo_matrix_paper_method()
        
        return Q_symmetric
    
    def save_qubo(self):
        """Save QUBO matrix and metadata"""
        
        # Save QUBO matrix
        np.save('quantum/qubo_matrix.npy', self.Q)
        
        # Save QUBO metadata
        qubo_metadata = {
            'n_variables': len(self.stocks),
            'target_K': self.K,
            'q_parameter': self.q,
            'min_sectors': self.min_sectors,
            'max_sector_weight': self.max_sector_weight,
            'stocks': self.stocks.tolist(),
            'stock_to_sector': self.stock_to_sector,
            'matrix_stats': {
                'min': float(self.Q.min()),
                'max': float(self.Q.max()),
                'mean': float(self.Q.mean()),
                'std': float(self.Q.std())
            }
        }
        
        with open('quantum/qubo_metadata.json', 'w') as f:
            json.dump(qubo_metadata, f, indent=2)
        
        print(f"\nSaved QUBO matrix: quantum/qubo_matrix.npy")
        print(f"Saved QUBO metadata: quantum/qubo_metadata.json")
    
    def run_formulation(self):
        """Execute full QUBO formulation pipeline"""
        
        print(f"\n{'='*80}")
        print("QUBO FORMULATION WITH SECTOR DIVERSIFICATION")
        print(f"{'='*80}\n")
        
        # Load data
        self.load_prepared_data()
        
        # Map stocks to sectors
        self.map_stocks_to_sectors()
        
        # Compute QUBO matrix
        self.compute_qubo_matrix()
        
        # Save results
        self.save_qubo()
        
        print(f"\n{'='*80}")
        print("QUBO FORMULATION COMPLETE")
        print(f"{'='*80}\n")

def main():
    """Main execution"""
    try:
        formulator = QUBOFormulator()
        formulator.run_formulation()
        return 0
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())

