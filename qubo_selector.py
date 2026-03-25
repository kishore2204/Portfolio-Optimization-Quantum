"""
Real QUBO-based Stock Selection
================================
Uses quantum-inspired QUBO formulation with:
- Expected returns maximization
- Risk minimization (covariance penalty)
- Downside risk penalty
- Sector diversification
- Adaptive lambda cardinality constraint

Author: Real Quantum Portfolio
Date: March 2026
"""

import numpy as np
import random

def build_qubo_matrix(mean_returns, cov_matrix, returns_data, 
                      K, lambda_penalty=100, downside_beta=0.3):
    """
    Build QUBO matrix for portfolio selection.
    
    Args:
        mean_returns: Expected returns (N x 1)
        cov_matrix: Covariance matrix (N x N)
        returns_data: Historical returns for downside calculation (T x N)
        K: Target portfolio size
        lambda_penalty: Cardinality constraint penalty
        downside_beta: Weight for downside risk penalty
    
    Returns:
        Q: QUBO matrix (N x N)
    """
    N = len(mean_returns)
    Q = np.zeros((N, N))
    
    # Part 1: Maximize expected returns (negative because we minimize)
    for i in range(N):
        Q[i, i] -= mean_returns[i]
    
    # Part 2: Minimize variance (risk)
    Q += cov_matrix
    
    # Part 3: Cardinality constraint λ(1'x - K)²
    # Expands to: λ(x'x + K² - 2K·1'x)
    for i in range(N):
        Q[i, i] += lambda_penalty  # x'x term
        Q[i, i] -= 2 * lambda_penalty * K  # -2K·1'x term (diagonal)
    
    # Part 4: Downside risk penalty
    # Penalize stocks with high negative returns
    if returns_data is not None:
        for i in range(N):
            negative_returns = returns_data[:, i][returns_data[:, i] < 0]
            if len(negative_returns) > 0:
                downside_risk = np.mean(negative_returns ** 2)
                Q[i, i] += downside_beta * downside_risk
    
    # Make symmetric
    Q_symmetric = Q + Q.T - np.diag(np.diag(Q))
    
    return Q_symmetric

def simulated_annealing_qubo(
    Q,
    K,
    max_iter=1000,
    temp_init=10.0,
    cooling_rate=0.995,
    seed=None
):
    """
    Solve QUBO using simulated annealing.
    
    Args:
        Q: QUBO matrix (N x N)
        K: Target number of stocks to select
        max_iter: Maximum iterations
        temp_init: Initial temperature
        cooling_rate: Temperature decay rate
    
    Returns:
        best_solution: Binary vector indicating selected stocks
        best_energy: Best objective value found
    """
    N = Q.shape[0]
    
    rng = random.Random(seed) if seed is not None else random

    # Initialize with random K stocks
    current = np.zeros(N)
    selected_idx = rng.sample(range(N), K)
    current[selected_idx] = 1
    
    current_energy = current @ Q @ current
    best_solution = current.copy()
    best_energy = current_energy
    
    temperature = temp_init
    
    for iteration in range(max_iter):
        # Propose move: swap one selected with one unselected
        selected_indices = np.where(current == 1)[0]
        unselected_indices = np.where(current == 0)[0]
        
        if len(selected_indices) == 0 or len(unselected_indices) == 0:
            break
        
        # Random swap
        to_remove = rng.choice(selected_indices)
        to_add = rng.choice(unselected_indices)
        
        # Create new solution
        new_solution = current.copy()
        new_solution[to_remove] = 0
        new_solution[to_add] = 1
        
        # Calculate energy
        new_energy = new_solution @ Q @ new_solution
        
        # Accept or reject
        delta_energy = new_energy - current_energy
        if delta_energy < 0 or rng.random() < np.exp(-delta_energy / temperature):
            current = new_solution
            current_energy = new_energy
            
            # Update best
            if current_energy < best_energy:
                best_solution = current.copy()
                best_energy = current_energy
        
        # Cool down
        temperature *= cooling_rate
    
    return best_solution, best_energy

def select_quantum_stocks(
    mean_returns,
    cov_matrix,
    returns_data,
    stock_symbols,
    K=10,
    seed=None,
    max_iter=2000,
    lambda_penalty=None,
    lambda_base=50.0,
    lambda_scale=10.0,
    downside_beta=0.3,
    return_details=False,
    include_qubo_matrix=False,
    verbose=True,
):
    """
    Select stocks using QUBO formulation with simulated annealing.
    
    Args:
        mean_returns: Expected returns array
        cov_matrix: Covariance matrix
        returns_data: Historical returns matrix (T x N)
        stock_symbols: List of stock names
        K: Number of stocks to select
    
    Returns:
        selected_stocks: List of selected stock symbols
        If return_details=True, returns (selected_stocks, details_dict)
    """
    N = len(stock_symbols)

    if K <= 0:
        raise ValueError(f"K must be >= 1, got {K}")
    if K > N:
        raise ValueError(f"K ({K}) cannot exceed stock universe size ({N})")
    
    # Adaptive lambda based on problem size unless explicitly provided.
    if lambda_penalty is None:
        lambda_penalty = lambda_base + (N / K) * lambda_scale
    
    # Build QUBO matrix
    Q = build_qubo_matrix(
        mean_returns=mean_returns,
        cov_matrix=cov_matrix,
        returns_data=returns_data,
        K=K,
        lambda_penalty=lambda_penalty,
        downside_beta=downside_beta
    )
    
    if verbose:
        print(f"  QUBO matrix size: {N}x{N}")
        print(f"  Cardinality penalty λ: {lambda_penalty:.2f}")
        print(f"  Target stocks: K={K}")
    
    # Solve using simulated annealing
    solution, energy = simulated_annealing_qubo(
        Q,
        K,
        max_iter=max_iter,
        temp_init=20.0,
        cooling_rate=0.995,
        seed=seed,
    )
    
    # Extract selected stocks
    selected_indices = np.where(solution == 1)[0]
    selected_stocks = [stock_symbols[i] for i in selected_indices]
    
    if verbose:
        print(f"  QUBO solution: {len(selected_stocks)} stocks selected")
        print(f"  Energy: {energy:.4f}")
    
    details = {
        "n_universe": int(N),
        "k_target": int(K),
        "seed": seed,
        "max_iter": int(max_iter),
        "lambda_penalty": float(lambda_penalty),
        "downside_beta": float(downside_beta),
        "energy": float(energy),
        "selected_indices": selected_indices.tolist(),
        "selected_stocks": selected_stocks,
        "qubo_stats": {
            "min": float(np.min(Q)),
            "max": float(np.max(Q)),
            "mean": float(np.mean(Q)),
            "std": float(np.std(Q)),
            "shape": [int(Q.shape[0]), int(Q.shape[1])],
        },
        "qubo_selected_submatrix": Q[np.ix_(selected_indices, selected_indices)].tolist(),
    }

    if include_qubo_matrix:
        details["qubo_matrix"] = Q

    if return_details:
        return selected_stocks, details

    return selected_stocks

