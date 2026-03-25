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


def _qubo_to_bqm(Q):
    """Convert dense Q matrix into a binary quadratic model matching x^T Q x energy."""
    from dimod import BinaryQuadraticModel

    n = int(Q.shape[0])
    linear = {i: float(Q[i, i]) for i in range(n)}
    quadratic = {}
    for i in range(n):
        for j in range(i + 1, n):
            coeff = float(Q[i, j] + Q[j, i])
            if coeff != 0.0:
                quadratic[(i, j)] = coeff

    return BinaryQuadraticModel(linear, quadratic, 0.0, "BINARY")


def _pick_best_cardinality_sample(sampleset, n_assets, K):
    """Prefer exact-cardinality sample; otherwise choose closest cardinality then lowest energy."""
    best_exact = None
    best_fallback = None

    for sample, energy in sampleset.data(["sample", "energy"]):
        vec = np.array([int(sample[i]) for i in range(n_assets)], dtype=float)
        selected = int(np.sum(vec))
        e = float(energy)

        if selected == int(K):
            if best_exact is None or e < best_exact[1]:
                best_exact = (vec, e, selected)

        gap = abs(selected - int(K))
        cand = (gap, e, vec, selected)
        if best_fallback is None or cand < best_fallback:
            best_fallback = cand

    if best_exact is not None:
        return best_exact[0], best_exact[1], best_exact[2], True

    if best_fallback is None:
        raise RuntimeError("No samples returned by sampler")

    _, e, vec, selected = best_fallback
    return vec, e, selected, False


def solve_qubo_with_dwave_qpu(
    Q,
    K,
    num_reads=100,
    annealing_time=20,
    chain_strength=None,
    label=None,
):
    """Submit QUBO to D-Wave QPU via Ocean SDK."""
    try:
        from dwave.system import DWaveSampler, EmbeddingComposite
    except Exception as exc:
        raise RuntimeError("D-Wave Ocean runtime unavailable for QPU sampling") from exc

    bqm = _qubo_to_bqm(Q)
    sampler = EmbeddingComposite(DWaveSampler())

    sample_kwargs = {
        "num_reads": int(num_reads),
        "annealing_time": int(annealing_time),
    }
    if chain_strength is not None:
        sample_kwargs["chain_strength"] = float(chain_strength)
    if label:
        sample_kwargs["label"] = str(label)

    sampleset = sampler.sample(bqm, **sample_kwargs)
    solution, energy, selected_count, exact_k = _pick_best_cardinality_sample(sampleset, Q.shape[0], K)

    timing = {}
    info = getattr(sampleset, "info", {})
    if isinstance(info, dict):
        timing = info.get("timing", {}) if isinstance(info.get("timing", {}), dict) else {}

    meta = {
        "backend_requested": "dwave_qpu",
        "backend_used": "dwave_qpu",
        "num_reads": int(num_reads),
        "annealing_time": int(annealing_time),
        "selected_count": int(selected_count),
        "target_k": int(K),
        "exact_cardinality": bool(exact_k),
        "samples_returned": int(len(sampleset)),
        "timing": timing,
    }
    return solution, energy, meta

def build_qubo_matrix(mean_returns, cov_matrix, returns_data,
                      K, lambda_penalty=100, downside_beta=0.3,
                      risk_aversion=1.0, uncertainty_penalty_vector=None):
    """
    Build QUBO matrix for portfolio selection.

    Args:
        mean_returns: Expected returns (N x 1)
        cov_matrix: Covariance matrix (N x N)
        returns_data: Historical returns for downside calculation (T x N)
        K: Target portfolio size
        lambda_penalty: Cardinality constraint penalty
        downside_beta: Weight for downside risk penalty
        risk_aversion: Multiplier on covariance risk term
        uncertainty_penalty_vector: Optional per-asset non-negative penalty vector

    Returns:
        Q: QUBO matrix (N x N)
    """
    N = len(mean_returns)
    Q = np.zeros((N, N))

    # Part 1: Maximize expected returns (negative because we minimize)
    for i in range(N):
        Q[i, i] -= mean_returns[i]

    # Part 2: Minimize variance (risk)
    Q += float(risk_aversion) * cov_matrix
    
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

    # Part 5: Uncertainty/stability penalty (optional)
    if uncertainty_penalty_vector is not None:
        pen = np.asarray(uncertainty_penalty_vector, dtype=float).reshape(-1)
        if pen.size == N:
            for i in range(N):
                if np.isfinite(pen[i]) and pen[i] > 0:
                    Q[i, i] += float(pen[i])

    # Make symmetric
    Q_symmetric = Q + Q.T - np.diag(np.diag(Q))
    
    return Q_symmetric

def simulated_annealing_qubo(
    Q,
    K,
    max_iter=1000,
    temp_init=10.0,
    cooling_rate=0.995,
    seed=None,
    initial_solution=None,
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

    # Initialize either from warm-start hint or random K stocks.
    current = np.zeros(N)
    used_warm_start = False
    if initial_solution is not None:
        init = np.asarray(initial_solution, dtype=float).reshape(-1)
        if init.size == N:
            ones = np.where(init > 0.5)[0].tolist()
            if len(ones) > K:
                # Keep strongest K entries from init.
                ranked = sorted(range(N), key=lambda i: init[i], reverse=True)
                ones = ranked[:K]
            elif len(ones) < K:
                remainder = [i for i in range(N) if i not in set(ones)]
                if remainder:
                    fill = rng.sample(remainder, min(K - len(ones), len(remainder)))
                    ones.extend(fill)
            if len(ones) == K:
                current[ones] = 1
                used_warm_start = True

    if not used_warm_start:
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


def path_relink_local_search(Q, solution, max_passes=1):
    """Simple swap-based local refinement with fixed cardinality."""
    x = np.array(solution, dtype=float).copy()
    n = len(x)

    def energy(v):
        return float(v @ Q @ v)

    e = energy(x)
    for _ in range(max(1, int(max_passes))):
        improved = False
        sel = np.where(x == 1)[0]
        unsel = np.where(x == 0)[0]
        best_delta = 0.0
        best_swap = None

        for i in sel:
            for j in unsel:
                cand = x.copy()
                cand[i] = 0
                cand[j] = 1
                e2 = energy(cand)
                delta = e2 - e
                if delta < best_delta:
                    best_delta = delta
                    best_swap = (i, j, e2)

        if best_swap is None:
            break

        i, j, e2 = best_swap
        x[i] = 0
        x[j] = 1
        e = e2
        improved = True

        if not improved:
            break

    return x, e


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
    risk_aversion=1.0,
    uncertainty_penalty_vector=None,
    turnover_penalty=0.0,
    hold_preference_vector=None,
    ensemble_confidence_threshold=0.0,
    use_warm_start=False,
    warm_start_symbols=None,
    path_relinking_enabled=False,
    path_relinking_passes=1,
    solver_backend="simulated_annealing",
    solver_num_reads=100,
    solver_annealing_time=20,
    solver_chain_strength=None,
    solver_strict=False,
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
        downside_beta=downside_beta,
        risk_aversion=risk_aversion,
        uncertainty_penalty_vector=uncertainty_penalty_vector,
    )

    # Turnover-aware QUBO: penalize opening new names when current holdings are known.
    if hold_preference_vector is not None and float(turnover_penalty) > 0:
        pref = np.asarray(hold_preference_vector, dtype=float).reshape(-1)
        if pref.size == N:
            for i in range(N):
                if pref[i] <= 0:
                    Q[i, i] += float(turnover_penalty)
    
    if verbose:
        print(f"  QUBO matrix size: {N}x{N}")
        print(f"  Cardinality penalty λ: {lambda_penalty:.2f}")
        print(f"  Target stocks: K={K}")
    
    # Build optional warm-start vector from prior holdings.
    initial_solution = None
    if use_warm_start and warm_start_symbols:
        warm_set = set(str(s) for s in warm_start_symbols)
        initial_solution = np.array([1.0 if s in warm_set else 0.0 for s in stock_symbols], dtype=float)

    solver_backend = str(solver_backend or "simulated_annealing").lower()
    solver_meta = {
        "backend_requested": solver_backend,
        "backend_used": "simulated_annealing",
        "fallback_used": False,
    }

    if solver_backend == "dwave_qpu":
        try:
            solution, energy, qpu_meta = solve_qubo_with_dwave_qpu(
                Q,
                K,
                num_reads=solver_num_reads,
                annealing_time=solver_annealing_time,
                chain_strength=solver_chain_strength,
                label="portfolio_optimization_quantum",
            )
            solver_meta.update(qpu_meta)
        except Exception as exc:
            if bool(solver_strict):
                raise
            solver_meta["fallback_used"] = True
            solver_meta["fallback_reason"] = str(exc)
            solution, energy = simulated_annealing_qubo(
                Q,
                K,
                max_iter=max_iter,
                temp_init=20.0,
                cooling_rate=0.995,
                seed=seed,
                initial_solution=initial_solution,
            )
    else:
        solution, energy = simulated_annealing_qubo(
            Q,
            K,
            max_iter=max_iter,
            temp_init=20.0,
            cooling_rate=0.995,
            seed=seed,
            initial_solution=initial_solution,
        )

    if path_relinking_enabled:
        solution, energy = path_relink_local_search(Q, solution, max_passes=path_relinking_passes)
    
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
        "risk_aversion": float(risk_aversion),
        "turnover_penalty": float(turnover_penalty),
        "ensemble_confidence_threshold": float(ensemble_confidence_threshold),
        "path_relinking_enabled": bool(path_relinking_enabled),
        "solver": solver_meta,
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

