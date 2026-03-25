"""
Real Quantum Portfolio - Crash Analysis
========================================
Uses REAL quantum QUBO formulation to test portfolio performance during crashes.

Author: Real Crash Analysis System
Date: March 2026
"""

import numpy as np
import pandas as pd
import json
from pathlib import Path
import sys
import matplotlib.pyplot as plt
import seaborn as sns

# Import modules
sys.path.insert(0, str(Path(__file__).parent))
from quantum.weight_optimizer import optimize_sharpe_slsqp, get_dynamic_risk_free_rate
from qubo_selector import select_quantum_stocks

def _load_runtime_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _profile_dataset(path: Path):
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, parse_dates=["Date"])
    except Exception:
        return None
    if "Date" not in df.columns or len(df.columns) < 3 or len(df) == 0:
        return None
    return {
        "path": str(path.resolve()),
        "rows": int(len(df)),
        "assets": int(len(df.columns) - 1),
        "end_ts": pd.to_datetime(df["Date"].max()),
    }


def _choose_best_dataset(base_dir: Path, candidates: list[str]) -> str:
    profs = []
    for rel in candidates:
        prof = _profile_dataset((base_dir / rel).resolve())
        if prof:
            profs.append(prof)
    if not profs:
        raise FileNotFoundError("No valid dataset found in configured candidates")
    profs.sort(key=lambda x: (x["end_ts"], x["rows"], x["assets"]), reverse=True)
    return profs[0]["path"]

def load_complete_data(data_path: str):
    """Load complete historical data from configured path."""
    data_path = Path(data_path)
    
    if not data_path.exists():
        raise FileNotFoundError(f"Complete data not found at {data_path}")
    
    print(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path, parse_dates=['Date'])
    df = df.sort_values('Date')
    
    print(f"Loaded {len(df)} rows, Date range: {df['Date'].min()} to {df['Date'].max()}")
    
    return df

def get_stock_universe(prices_df, train_start, train_end, test_start, test_end,
                       min_coverage=0.8, min_test_points=20,
                       min_train_points=0, min_return_points=0):
    """Get stocks with strong train coverage and minimum test availability."""
    train_mask = (prices_df['Date'] >= train_start) & (prices_df['Date'] <= train_end)
    test_mask = (prices_df['Date'] >= test_start) & (prices_df['Date'] <= test_end)

    train_df = prices_df[train_mask]
    test_df = prices_df[test_mask]

    total_train_days = len(train_df)
    min_required = int(total_train_days * min_coverage)

    eligible_stocks = []
    for col in train_df.columns:
        if col == 'Date':
            continue

        train_non_null = train_df[col].notna().sum()
        test_non_null = test_df[col].notna().sum()
        if train_non_null < min_required or test_non_null < min_test_points:
            continue

        if int(min_train_points) > 0 and train_non_null < int(min_train_points):
            continue

        series_train = train_df[col].ffill().bfill()
        returns_train = series_train.pct_change().replace([np.inf, -np.inf], np.nan).dropna()

        if int(min_return_points) > 0 and len(returns_train) < int(min_return_points):
            continue

        if returns_train.empty:
            continue

        variance = float(np.var(returns_train.values))
        if not np.isfinite(variance) or variance <= 0:
            continue

        eligible_stocks.append(col)

    return eligible_stocks

def validate_no_data_leakage(train_start, train_end, test_start, test_end):
    """Validate that train and test periods don't overlap."""
    train_start_dt = pd.to_datetime(train_start)
    train_end_dt = pd.to_datetime(train_end)
    test_start_dt = pd.to_datetime(test_start)
    test_end_dt = pd.to_datetime(test_end)
    
    if train_end_dt >= test_start_dt:
        raise ValueError(f"DATA LEAKAGE! Train ends {train_end_dt} but test starts {test_start_dt}")
    
    gap_days = (test_start_dt - train_end_dt).days
    
    print(f"\nDATA LEAKAGE CHECK PASSED")
    print(f"  Train: {train_start_dt.date()} to {train_end_dt.date()}")
    print(f"  Gap: {gap_days} days")
    print(f"  Test: {test_start_dt.date()} to {test_end_dt.date()}")
    
    return True


def _auto_shrinkage_alpha(returns_matrix: np.ndarray) -> float:
    """Heuristic shrinkage level based on dimensionality ratio (assets/observations)."""
    n_obs, n_assets = returns_matrix.shape
    if n_obs <= 1:
        return 0.30
    ratio = n_assets / max(float(n_obs), 1.0)
    alpha = 0.05 + 0.30 * (ratio / (1.0 + ratio))
    return float(np.clip(alpha, 0.05, 0.35))


def _shrink_covariance(cov_matrix: np.ndarray, returns_matrix: np.ndarray, alpha_cfg, diag_floor_eps: float = 1e-8):
    """Shrink sample covariance toward diagonal target for better OOS stability."""
    if alpha_cfg == "auto":
        alpha = _auto_shrinkage_alpha(returns_matrix)
    else:
        alpha = float(alpha_cfg)
    alpha = float(np.clip(alpha, 0.0, 1.0))

    target = np.diag(np.diag(cov_matrix))
    shrunk = (1.0 - alpha) * cov_matrix + alpha * target
    shrunk = shrunk + float(diag_floor_eps) * np.eye(shrunk.shape[0])

    return shrunk, alpha

def select_quantum_portfolio(
    prices_df,
    stocks,
    train_start,
    train_end,
    K=10,
    seed=None,
    qubo_params=None,
    current_holdings=None,
    return_details=False,
    include_matrices=False,
    verbose=True,
):
    """Select portfolio using REAL quantum QUBO formulation."""
    if verbose:
        print("\n[QUANTUM] Selection")
    
    mask = (prices_df['Date'] >= train_start) & (prices_df['Date'] <= train_end)
    train_df = prices_df[mask]
    
    if verbose:
        print(f"  Training window: {train_df['Date'].min().date()} to {train_df['Date'].max().date()} ({len(train_df)} days)")
    
    stock_prices = train_df[stocks].ffill().bfill()
    returns = stock_prices.pct_change().dropna()
    
    mean_returns = returns.mean().values * 252
    cov_matrix = returns.cov().values * 252
    returns_matrix = returns.values

    qubo_params = qubo_params or {}
    lambda_penalty = qubo_params.get('lambda_penalty')
    lambda_base = float(qubo_params.get('lambda_base', 50.0))
    lambda_scale = float(qubo_params.get('lambda_scale', 10.0))
    downside_beta = float(qubo_params.get('downside_beta', 0.3))
    risk_aversion = float(qubo_params.get('risk_aversion', 1.0))
    max_iter = int(qubo_params.get('max_iter', 2000))
    cov_shrink_enabled = bool(qubo_params.get('covariance_shrinkage_enabled', False))
    cov_shrink_alpha_cfg = qubo_params.get('covariance_shrinkage_alpha', 'auto')
    cov_shrink_diag_eps = float(qubo_params.get('covariance_shrinkage_diag_eps', 1e-8))
    uncertainty_aware_enabled = bool(qubo_params.get('uncertainty_aware_enabled', False))
    instability_gamma = float(qubo_params.get('instability_gamma', 0.0))
    mean_shrinkage = float(qubo_params.get('mean_shrinkage', 0.0))
    ensemble_enabled = bool(qubo_params.get('ensemble_enabled', False))
    ensemble_num_seeds = max(1, int(qubo_params.get('ensemble_num_seeds', 1)))
    ensemble_seed_step = int(qubo_params.get('ensemble_seed_step', 101))
    ensemble_confidence_threshold = float(qubo_params.get('ensemble_confidence_threshold', 0.0))
    turnover_aware_enabled = bool(qubo_params.get('turnover_aware_enabled', False))
    turnover_penalty = float(qubo_params.get('turnover_penalty', 0.0))
    warm_start_enabled = bool(qubo_params.get('warm_start_enabled', False))
    path_relinking_enabled = bool(qubo_params.get('path_relinking_enabled', False))
    path_relinking_passes = int(qubo_params.get('path_relinking_passes', 1))
    regime_conditional_enabled = bool(qubo_params.get('regime_conditional_enabled', False))
    solver_backend = str(qubo_params.get('solver_backend', 'simulated_annealing'))
    solver_num_reads = int(qubo_params.get('solver_num_reads', 100))
    solver_annealing_time = int(qubo_params.get('solver_annealing_time', 20))
    solver_chain_strength = qubo_params.get('solver_chain_strength')
    solver_strict = bool(qubo_params.get('solver_strict', False))

    if cov_shrink_enabled:
        cov_matrix, alpha_used = _shrink_covariance(
            cov_matrix,
            returns_matrix,
            cov_shrink_alpha_cfg,
            diag_floor_eps=cov_shrink_diag_eps,
        )
        if verbose:
            print(f"  Covariance shrinkage applied (alpha={alpha_used:.3f})")

    # Regime-conditioned QUBO coefficients based on train-window market behavior.
    regime_label = "neutral"
    if len(returns) > 5:
        market = returns.mean(axis=1)
        ann_ret = float(market.mean() * 252)
        ann_vol = float(market.std() * np.sqrt(252))
        if ann_ret >= float(qubo_params.get('trend_return_threshold', 0.12)) and ann_vol <= float(qubo_params.get('trend_vol_threshold', 0.24)):
            regime_label = "trend"
        elif ann_vol >= float(qubo_params.get('unstable_vol_threshold', 0.32)):
            regime_label = "unstable"

    if regime_conditional_enabled:
        if regime_label == "trend":
            risk_aversion *= float(qubo_params.get('trend_risk_aversion_mult', 0.9))
            downside_beta *= float(qubo_params.get('trend_downside_beta_mult', 0.8))
            lambda_scale *= float(qubo_params.get('trend_lambda_scale_mult', 0.9))
        elif regime_label == "unstable":
            risk_aversion *= float(qubo_params.get('unstable_risk_aversion_mult', 1.2))
            downside_beta *= float(qubo_params.get('unstable_downside_beta_mult', 1.3))
            lambda_scale *= float(qubo_params.get('unstable_lambda_scale_mult', 1.1))

    # Robust-QUBO: shrink means and penalize unstable assets on diagonal.
    uncertainty_penalty_vector = None
    if uncertainty_aware_enabled and len(returns) > 5:
        mu = returns.mean().values * 252
        if 0.0 < mean_shrinkage < 1.0:
            cross_mean = float(np.nanmean(mu))
            mu = (1.0 - mean_shrinkage) * mu + mean_shrinkage * cross_mean
        mean_returns = mu

        vol = returns.std().values * np.sqrt(252)
        downside_freq = (returns < 0).mean().values
        instability = np.nan_to_num(vol, nan=0.0, posinf=0.0, neginf=0.0) * np.nan_to_num(downside_freq, nan=0.0)
        if np.max(instability) > 0:
            instability = instability / float(np.max(instability))
        uncertainty_penalty_vector = instability_gamma * instability

    hold_preference_vector = None
    if turnover_aware_enabled and current_holdings:
        cur = set(current_holdings)
        hold_preference_vector = np.array([1.0 if s in cur else 0.0 for s in stocks], dtype=float)

    # Use REAL QUBO formulation (optionally as multi-seed consensus ensemble)
    if ensemble_enabled and ensemble_num_seeds > 1:
        if verbose:
            print(f"  Ensemble selection enabled ({ensemble_num_seeds} seeds)")
        freq = {s: 0 for s in stocks}
        details_list = []

        for i in range(ensemble_num_seeds):
            run_seed = None if seed is None else int(seed) + i * ensemble_seed_step
            selected_i, details_i = select_quantum_stocks(
                mean_returns=mean_returns,
                cov_matrix=cov_matrix,
                returns_data=returns_matrix,
                stock_symbols=stocks,
                K=K,
                seed=run_seed,
                max_iter=max_iter,
                lambda_penalty=lambda_penalty,
                lambda_base=lambda_base,
                lambda_scale=lambda_scale,
                downside_beta=downside_beta,
                risk_aversion=risk_aversion,
                uncertainty_penalty_vector=uncertainty_penalty_vector,
                turnover_penalty=turnover_penalty,
                hold_preference_vector=hold_preference_vector,
                use_warm_start=warm_start_enabled,
                warm_start_symbols=current_holdings,
                path_relinking_enabled=path_relinking_enabled,
                path_relinking_passes=path_relinking_passes,
                solver_backend=solver_backend,
                solver_num_reads=solver_num_reads,
                solver_annealing_time=solver_annealing_time,
                solver_chain_strength=solver_chain_strength,
                solver_strict=solver_strict,
                return_details=True,
                include_qubo_matrix=False,
                verbose=verbose,
            )
            details_list.append(details_i)
            for s in selected_i:
                freq[s] = freq.get(s, 0) + 1

        sharpes = {}
        for i, stock in enumerate(stocks):
            sigma = np.sqrt(cov_matrix[i, i])
            sharpes[stock] = mean_returns[i] / sigma if sigma > 0 else -1e9

        ranked = sorted(stocks, key=lambda s: (freq.get(s, 0), sharpes.get(s, -1e9)), reverse=True)
        selected = []
        min_hits = int(np.ceil(ensemble_confidence_threshold * ensemble_num_seeds)) if ensemble_confidence_threshold > 0 else 0
        if min_hits > 0:
            selected = [s for s in ranked if freq.get(s, 0) >= min_hits][:K]
        if len(selected) < K:
            fill = [s for s in ranked if s not in set(selected)]
            selected.extend(fill[: max(0, K - len(selected))])

        qubo_details = {
            "ensemble": {
                "enabled": True,
                "num_seeds": ensemble_num_seeds,
                "seed_step": ensemble_seed_step,
                "frequency": freq,
                "confidence_threshold": float(ensemble_confidence_threshold),
                "min_hits": int(min_hits),
            },
            "regime": {
                "label": regime_label,
                "risk_aversion": float(risk_aversion),
                "downside_beta": float(downside_beta),
                "lambda_scale": float(lambda_scale),
            },
            "runs": details_list,
        }
    else:
        if return_details:
            selected, qubo_details = select_quantum_stocks(
                mean_returns=mean_returns,
                cov_matrix=cov_matrix,
                returns_data=returns_matrix,
                stock_symbols=stocks,
                K=K,
                seed=seed,
                max_iter=max_iter,
                lambda_penalty=lambda_penalty,
                lambda_base=lambda_base,
                lambda_scale=lambda_scale,
                downside_beta=downside_beta,
                risk_aversion=risk_aversion,
                uncertainty_penalty_vector=uncertainty_penalty_vector,
                turnover_penalty=turnover_penalty,
                hold_preference_vector=hold_preference_vector,
                use_warm_start=warm_start_enabled,
                warm_start_symbols=current_holdings,
                path_relinking_enabled=path_relinking_enabled,
                path_relinking_passes=path_relinking_passes,
                solver_backend=solver_backend,
                solver_num_reads=solver_num_reads,
                solver_annealing_time=solver_annealing_time,
                solver_chain_strength=solver_chain_strength,
                solver_strict=solver_strict,
                return_details=True,
                include_qubo_matrix=include_matrices,
                verbose=verbose,
            )
        else:
            selected = select_quantum_stocks(
                mean_returns=mean_returns,
                cov_matrix=cov_matrix,
                returns_data=returns_matrix,
                stock_symbols=stocks,
                K=K,
                seed=seed,
                max_iter=max_iter,
                lambda_penalty=lambda_penalty,
                lambda_base=lambda_base,
                lambda_scale=lambda_scale,
                downside_beta=downside_beta,
                risk_aversion=risk_aversion,
                uncertainty_penalty_vector=uncertainty_penalty_vector,
                turnover_penalty=turnover_penalty,
                hold_preference_vector=hold_preference_vector,
                use_warm_start=warm_start_enabled,
                warm_start_symbols=current_holdings,
                path_relinking_enabled=path_relinking_enabled,
                path_relinking_passes=path_relinking_passes,
                solver_backend=solver_backend,
                solver_num_reads=solver_num_reads,
                solver_annealing_time=solver_annealing_time,
                solver_chain_strength=solver_chain_strength,
                solver_strict=solver_strict,
                verbose=verbose,
            )
    
    # Show Sharpe ratios
    sharpes = {}
    for i, stock in enumerate(stocks):
        mu = mean_returns[i]
        sigma = np.sqrt(cov_matrix[i, i])
        if sigma > 0:
            sharpes[stock] = mu / sigma
    
    if verbose:
        print("\n  Selected stocks:")
        for i, stock in enumerate(selected[:5], 1):
            print(f"  {i}. {stock:12s} - Sharpe: {sharpes.get(stock, 0):.3f}")
        if len(selected) > 5:
            print(f"  ... and {len(selected)-5} more")
    
    if return_details:
        if isinstance(qubo_details, dict):
            qubo_details.setdefault("regime", {
                "label": regime_label,
                "risk_aversion": float(risk_aversion),
                "downside_beta": float(downside_beta),
                "lambda_scale": float(lambda_scale),
            })
        details = {
            "train_start": str(train_df['Date'].min().date()),
            "train_end": str(train_df['Date'].max().date()),
            "train_rows": int(len(train_df)),
            "returns_rows": int(len(returns)),
            "stock_symbols": list(stocks),
            "mean_returns_full": mean_returns,
            "covariance_full": cov_matrix,
            "qubo": qubo_details,
        }
        return selected, details

    return selected

def select_greedy_portfolio(prices_df, stocks, train_start, train_end, K=10, verbose=True):
    """Select portfolio using pure greedy Sharpe (NO diversification)."""
    if verbose:
        print("\n[GREEDY] Selection")
    
    mask = (prices_df['Date'] >= train_start) & (prices_df['Date'] <= train_end)
    train_df = prices_df[mask]
    
    if verbose:
        print(f"  Training window: {train_df['Date'].min().date()} to {train_df['Date'].max().date()}")
    
    stock_prices = train_df[stocks].ffill().bfill()
    returns = stock_prices.pct_change().dropna()
    
    mean_returns = returns.mean() * 252
    cov_matrix = returns.cov() * 252
    
    sharpes = {}
    for stock in stocks:
        if stock in returns.columns:
            mu = mean_returns[stock]
            sigma = np.sqrt(cov_matrix.loc[stock, stock])
            if sigma > 0:
                sharpes[stock] = mu / sigma
    
    sorted_stocks = sorted(sharpes.items(), key=lambda x: x[1], reverse=True)
    selected = [s[0] for s in sorted_stocks[:K]]
    
    if verbose:
        print(f"  Selected {len(selected)} stocks")
        for i, stock in enumerate(selected[:5], 1):
            print(f"  {i}. {stock:12s} - Sharpe: {sharpes[stock]:.3f}")
    
    return selected

def select_classical_portfolio(prices_df, stocks, train_start, train_end, K=10, verbose=True):
    """Select portfolio using classical MVO (return/variance ratio)."""
    if verbose:
        print("\n[CLASSICAL] Selection")
    
    mask = (prices_df['Date'] >= train_start) & (prices_df['Date'] <= train_end)
    train_df = prices_df[mask]
    
    if verbose:
        print(f"  Training window: {train_df['Date'].min().date()} to {train_df['Date'].max().date()}")
    
    stock_prices = train_df[stocks].ffill().bfill()
    returns = stock_prices.pct_change().dropna()
    
    mean_returns = returns.mean() * 252
    cov_matrix = returns.cov() * 252
    
    # Risk-adjusted score: higher return / lower variance
    scores = {}
    for stock in stocks:
        if stock in returns.columns:
            mu = mean_returns[stock]
            variance = cov_matrix.loc[stock, stock]
            if variance > 0:
                scores[stock] = mu / variance
    
    sorted_stocks = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    selected = [s[0] for s in sorted_stocks[:K]]
    
    if verbose:
        print(f"  Selected {len(selected)} stocks")
        for i, stock in enumerate(selected[:5], 1):
            sharpe = mean_returns[stock] / np.sqrt(cov_matrix.loc[stock, stock])
            print(f"  {i}. {stock:12s} - Risk-adj: {scores[stock]:.2f}, Sharpe: {sharpe:.3f}")
    
    return selected

def optimize_weights(
    selected_stocks,
    prices_df,
    train_start,
    train_end,
    max_weight=0.40,
    min_weight=0.0,
    return_info=False,
    verbose=True,
):
    """Optimize portfolio weights using SLSQP (robust error handling)."""
    mask = (prices_df['Date'] >= train_start) & (prices_df['Date'] <= train_end)
    train_df = prices_df[mask]
    
    stock_prices = train_df[selected_stocks].ffill().bfill()
    returns = stock_prices.pct_change().dropna()
    
    if len(returns) < 20:
        if verbose:
            print(f"  Warning: Insufficient data ({len(returns)} days), using equal weights")
        n = len(selected_stocks)
        if return_info:
            return {stock: 1.0/n for stock in selected_stocks}, 0.0, {
                "optimization_success": False,
                "fallback": "insufficient_data",
                "n_returns": int(len(returns)),
            }
        return {stock: 1.0/n for stock in selected_stocks}, 0.0
    
    mean_returns = returns.mean() * 252
    cov_matrix = returns.cov() * 252
    
    if cov_matrix.isnull().any().any():
        if verbose:
            print("  Warning: Invalid covariance matrix, using equal weights")
        n = len(selected_stocks)
        if return_info:
            return {stock: 1.0/n for stock in selected_stocks}, 0.0, {
                "optimization_success": False,
                "fallback": "invalid_covariance",
            }
        return {stock: 1.0/n for stock in selected_stocks}, 0.0
    
    train_date = pd.to_datetime(train_end)
    rf_rate = get_dynamic_risk_free_rate(train_date)
    
    try:
        # Pass sequential indices since we're already working with filtered data
        stock_indices = list(range(len(selected_stocks)))
        weights, info = optimize_sharpe_slsqp(
            stock_indices,
            mean_returns.values,
            cov_matrix.values,
            risk_free_rate=rf_rate,
            max_weight=max_weight,
            min_weight=min_weight
        )
        sharpe = info.get('sharpe_ratio', 0.0)
        
        if np.any(np.isnan(weights)) or np.any(weights < 0):
            raise ValueError("Invalid weights")
        
        if verbose:
            print(f"  Optimized weights (Sharpe: {sharpe:.3f}, rf={rf_rate:.1%})")
        if return_info:
            return dict(zip(selected_stocks, weights)), sharpe, info
        return dict(zip(selected_stocks, weights)), sharpe
    except Exception as e:
        if verbose:
            print(f"  Warning: Optimization failed: {str(e)[:50]}, using equal weights")
        n = len(selected_stocks)
        if return_info:
            return {stock: 1.0/n for stock in selected_stocks}, 0.0, {
                "optimization_success": False,
                "fallback": "exception",
                "error": str(e),
            }
        return {stock: 1.0/n for stock in selected_stocks}, 0.0

def backtest_period(prices_df, portfolio_stocks, portfolio_weights, test_start, test_end, verbose=True):
    """Backtest portfolio on test period."""
    mask = (prices_df['Date'] >= test_start) & (prices_df['Date'] <= test_end)
    test_df = prices_df[mask]
    
    if len(test_df) == 0:
        return None
    
    if verbose:
        print(f"  Test window: {test_df['Date'].min().date()} to {test_df['Date'].max().date()} ({len(test_df)} days)")
    
    stock_prices = test_df.set_index('Date')[portfolio_stocks].ffill().bfill()
    daily_returns = stock_prices.pct_change()
    daily_returns = daily_returns.replace([np.inf, -np.inf], np.nan)
    daily_returns = daily_returns.iloc[1:]

    if daily_returns.empty:
        return None

    current_weight_map = {s: float(portfolio_weights.get(s, 0.0)) for s in portfolio_stocks}
    w_sum = float(sum(current_weight_map.values()))
    if w_sum <= 0:
        n = len(portfolio_stocks)
        current_weight_map = {s: 1.0 / n for s in portfolio_stocks}
    else:
        current_weight_map = {s: w / w_sum for s, w in current_weight_map.items()}
    
    portfolio_returns = []
    for date, row in daily_returns.iterrows():
        daily_ret = 0.0
        for stock, w in current_weight_map.items():
            r = row.get(stock, 0.0)
            r = 0.0 if pd.isna(r) else float(r)
            daily_ret += float(w) * r
        portfolio_returns.append(daily_ret)

        # Buy-and-hold drift (no reset) to match rebalanced path behavior between rebalance events.
        current_weight_map = _drift_weight_map(current_weight_map, row)
    
    portfolio_returns = np.array(portfolio_returns)
    cumulative_returns = (1 + portfolio_returns).cumprod()
    total_return = (cumulative_returns[-1] - 1) * 100
    
    volatility = portfolio_returns.std() * np.sqrt(252) * 100
    
    rolling_max = np.maximum.accumulate(cumulative_returns)
    drawdowns = (cumulative_returns - rolling_max) / rolling_max * 100
    max_drawdown = drawdowns.min()
    
    var_95 = np.percentile(portfolio_returns, 5) * 100
    
    rf_daily = get_dynamic_risk_free_rate(pd.to_datetime(test_start)) / 252
    excess_returns = portfolio_returns - rf_daily
    sharpe = np.mean(excess_returns) / np.std(portfolio_returns) * np.sqrt(252) if np.std(portfolio_returns) > 0 else 0
    
    return {
        'total_return': total_return,
        'volatility': volatility,
        'max_drawdown': max_drawdown,
        'var_95': var_95,
        'sharpe': sharpe,
        'cumulative_returns': cumulative_returns,
        'dates': daily_returns.index.tolist()
    }


def _rebalance_period_key(dt, rebalance_freq: str):
    """Map a date to a rebalance bucket key."""
    if rebalance_freq == '6M':
        half = 1 if dt.month <= 6 else 2
        return (dt.year, half)
    if rebalance_freq == 'monthly':
        return (dt.year, dt.month)
    # default quarterly
    quarter = ((dt.month - 1) // 3) + 1
    return (dt.year, quarter)


def _rebalance_interval_months(rebalance_freq: str) -> int:
    """Return rebalance interval length in months."""
    if rebalance_freq == 'monthly':
        return 1
    if rebalance_freq == '6M':
        return 6
    return 3


def _normalize_symbol(symbol: str) -> str:
    return str(symbol).strip().upper()


def _load_sector_map(
    sector_file: str = 'config/nifty100_sectors.json',
    sector_template_file: str = 'config/all_stocks_sector_template.csv',
):
    """Load sector mapping as normalized stock->sector from json and csv fallback."""
    stock_to_sector = {}

    path = Path(sector_file)
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            groups = raw.get('NIFTY_100_STOCKS', raw if isinstance(raw, dict) else {})
            if isinstance(groups, dict):
                for sector, stocks in groups.items():
                    if isinstance(stocks, list):
                        for s in stocks:
                            key = _normalize_symbol(s)
                            if key:
                                stock_to_sector[key] = str(sector)
        except Exception:
            pass

    template_path = Path(sector_template_file)
    if template_path.exists():
        try:
            df = pd.read_csv(template_path)
            stock_col = 'stock' if 'stock' in df.columns else df.columns[0]
            sector_col = 'sector' if 'sector' in df.columns else (df.columns[1] if len(df.columns) > 1 else None)
            if sector_col is not None:
                for _, row in df.iterrows():
                    stock = _normalize_symbol(row.get(stock_col, ''))
                    sector = str(row.get(sector_col, '')).strip()
                    if stock and sector and sector.lower() != 'nan':
                        stock_to_sector[stock] = sector
        except Exception:
            pass

    return stock_to_sector


def _quarterly_mean_returns_for_holdings(prices_df, holdings, up_to_date, lookback_days: int = 63):
    """Estimate annualized mean returns over recent quarter window via log-returns."""
    if not holdings:
        return {}
    hist = prices_df[prices_df['Date'] <= up_to_date]
    if hist.empty:
        return {s: -np.inf for s in holdings}

    cols = [c for c in holdings if c in hist.columns]
    if not cols:
        return {s: -np.inf for s in holdings}

    recent = hist[cols].tail(max(2, lookback_days)).ffill().bfill()
    log_returns = np.log(recent / recent.shift(1)).dropna()
    if log_returns.empty:
        return {s: -np.inf for s in holdings}

    mu = (log_returns.mean() * 252).to_dict()
    return {s: float(mu.get(s, -np.inf)) for s in holdings}


def _select_replacement_candidates(universe, current_holdings, sold_names, stock_to_sector):
    """Build sector-matched candidate pool as described in the reference algorithm."""
    if not sold_names:
        return []

    sold_sectors = {stock_to_sector.get(_normalize_symbol(s), 'Others') for s in sold_names}
    current_set = set(current_holdings)

    sector_matched = [
        s for s in universe
        if s not in current_set and stock_to_sector.get(_normalize_symbol(s), 'Others') in sold_sectors
    ]

    # Fallback: if sector-matched set is too small, allow full-universe candidates.
    if len(sector_matched) >= len(sold_names):
        return sector_matched

    fallback = [s for s in universe if s not in current_set and s not in sector_matched]
    return sector_matched + fallback


def _drift_weight_map(weight_map: dict, row_returns: pd.Series):
    """Drift weights by one day of realized returns and renormalize."""
    gross = {}
    for s, w in weight_map.items():
        r = row_returns.get(s, 0.0)
        r = 0.0 if pd.isna(r) else float(r)
        gross[s] = float(w) * (1.0 + r)
    denom = float(sum(gross.values()))
    if denom <= 0:
        n = max(1, len(gross))
        return {s: 1.0 / n for s in gross}
    return {s: v / denom for s, v in gross.items()}


def backtest_period_with_rebalance(
    prices_df,
    portfolio_stocks,
    portfolio_weights,
    train_start,
    test_start,
    test_end,
    rebalance_freq='quarterly',
    max_weight=0.40,
    min_weight=0.0,
    sell_count=None,
    sector_file='config/nifty100_sectors.json',
    sector_template_file='config/all_stocks_sector_template.csv',
    qubo_params=None,
    transaction_cost_pct=0.0,
    underperformer_threshold_annualized=0.0,
    max_turnover_per_rebalance=0.35,
    replacement_min_annualized_return=0.0,
    eligible_universe=None,
    verbose=True,
):
    """Backtest with paper-style periodic rebalancing: sell underperformers, sector-matched quantum replacement, re-optimize weights."""
    mask = (prices_df['Date'] >= test_start) & (prices_df['Date'] <= test_end)
    test_df = prices_df[mask]

    if len(test_df) == 0:
        return None

    if verbose:
        print(
            f"  Test window (rebalanced): {test_df['Date'].min().date()} to "
            f"{test_df['Date'].max().date()} ({len(test_df)} days), freq={rebalance_freq}"
        )

    universe_all = [c for c in test_df.columns if c != 'Date']
    if eligible_universe is not None:
        eligible_set = set(eligible_universe)
        universe = [c for c in universe_all if c in eligible_set]
    else:
        universe = list(universe_all)
    stock_prices = test_df.set_index('Date')[universe].ffill().bfill()
    daily_returns = stock_prices.pct_change()
    daily_returns = daily_returns.replace([np.inf, -np.inf], np.nan)
    # Keep rows even if some assets are missing; missing values are treated as 0 for non-held assets.
    daily_returns = daily_returns.iloc[1:]

    if daily_returns.empty:
        return None

    current_holdings = [s for s in portfolio_stocks if s in universe]
    if not current_holdings:
        return None

    current_weight_map = {s: float(portfolio_weights.get(s, 0.0)) for s in current_holdings}
    w_sum = float(sum(current_weight_map.values()))
    if w_sum <= 0:
        n = len(current_holdings)
        current_weight_map = {s: 1.0 / n for s in current_holdings}
    else:
        current_weight_map = {s: w / w_sum for s, w in current_weight_map.items()}

    stock_to_sector = _load_sector_map(sector_file, sector_template_file)
    k_sell_default = max(1, min(4, max(1, len(current_holdings) // 4)))
    k_sell = int(sell_count) if sell_count is not None else k_sell_default

    qcfg = dict(qubo_params or {})
    qcfg.setdefault('ensemble_enabled', False)
    qcfg['max_iter'] = min(int(qcfg.get('max_iter', 800)), 800)

    adaptive_turnover_cap_enabled = bool(qcfg.get('adaptive_turnover_cap_enabled', False))
    turnover_cap_trend = float(qcfg.get('turnover_cap_trend', max_turnover_per_rebalance if max_turnover_per_rebalance is not None else 0.45))
    turnover_cap_neutral = float(qcfg.get('turnover_cap_neutral', max_turnover_per_rebalance if max_turnover_per_rebalance is not None else 0.35))
    turnover_cap_unstable = float(qcfg.get('turnover_cap_unstable', max_turnover_per_rebalance if max_turnover_per_rebalance is not None else 0.20))
    turnover_regime_lookback = int(qcfg.get('turnover_regime_lookback_days', 63))
    trend_return_threshold = float(qcfg.get('trend_return_threshold', 0.12))
    trend_vol_threshold = float(qcfg.get('trend_vol_threshold', 0.24))
    unstable_vol_threshold = float(qcfg.get('unstable_vol_threshold', 0.32))

    portfolio_returns = []
    turnover_history = []
    transaction_cost_history = []
    rebalance_count = 0
    pending_rebalance_cost = 0.0
    step_months = _rebalance_interval_months(rebalance_freq)
    first_dt = pd.to_datetime(daily_returns.index[0])
    next_rebalance_dt = first_dt + pd.DateOffset(months=step_months)

    for date, row in daily_returns.iterrows():
        current_dt = pd.to_datetime(date)

        # Rebalance only after a full interval has elapsed since test start.
        if current_dt >= next_rebalance_dt:
            # 1) Rank holdings by recent quarter annualized expected returns and sell underperformers.
            mu_holdings = _quarterly_mean_returns_for_holdings(prices_df, current_holdings, pd.to_datetime(date))
            underperformers = [
                s for s in current_holdings
                if float(mu_holdings.get(s, -np.inf)) < float(underperformer_threshold_annualized)
            ]
            sorted_holdings = sorted(underperformers, key=lambda s: mu_holdings.get(s, -np.inf))
            sell_n = max(0, min(k_sell, max(0, len(current_holdings) - 1)))
            sold = sorted_holdings[:sell_n] if sell_n > 0 else []
            remaining = [s for s in current_holdings if s not in sold]

            # 2) Sector-matched candidates from current universe, then QUBO pick replacements.
            candidate_pool = _select_replacement_candidates(universe, remaining, sold, stock_to_sector)
            if candidate_pool and replacement_min_annualized_return is not None:
                mu_candidates = _quarterly_mean_returns_for_holdings(prices_df, candidate_pool, pd.to_datetime(date))
                strong = [
                    s for s in candidate_pool
                    if float(mu_candidates.get(s, -np.inf)) >= float(replacement_min_annualized_return)
                ]
                if strong:
                    candidate_pool = strong
            need = len(sold)
            replacements = []
            if need > 0 and candidate_pool:
                k_pick = min(need, len(candidate_pool))
                try:
                    replacements = select_quantum_portfolio(
                        prices_df,
                        candidate_pool,
                        train_start,
                        str(pd.to_datetime(date).date()),
                        K=k_pick,
                        seed=None,
                        qubo_params=qcfg,
                        current_holdings=remaining,
                        return_details=False,
                        verbose=False,
                    )
                except Exception:
                    replacements = candidate_pool[:k_pick]

            current_holdings = remaining + list(replacements)
            if not current_holdings:
                current_holdings = [s for s in portfolio_stocks if s in universe]

            # 3) Re-optimize weights on updated holdings up to rebalance date.
            new_w_map, _ = optimize_weights(
                current_holdings,
                prices_df,
                train_start,
                str(pd.to_datetime(date).date()),
                max_weight=max_weight,
                min_weight=min_weight,
                verbose=False,
            )

            pre_rebalance_weights = dict(current_weight_map)
            ws = float(sum(new_w_map.values()))
            if ws <= 0:
                n = len(current_holdings)
                current_weight_map = {s: 1.0 / n for s in current_holdings}
            else:
                current_weight_map = {s: float(new_w_map.get(s, 0.0)) / ws for s in current_holdings}

            # Cap turnover to reduce churn from aggressive rebalance updates.
            overlap = set(pre_rebalance_weights.keys()) | set(current_weight_map.keys())
            old_weights = {k: float(pre_rebalance_weights.get(k, 0.0)) for k in overlap}
            new_weights = {k: float(current_weight_map.get(k, 0.0)) for k in overlap}
            turnover = float(sum(abs(new_weights[k] - old_weights[k]) for k in overlap))

            cap = None if max_turnover_per_rebalance is None else float(max_turnover_per_rebalance)
            if adaptive_turnover_cap_enabled:
                hist = prices_df[prices_df['Date'] <= current_dt]
                cols = [c for c in current_holdings if c in hist.columns]
                if cols:
                    recent = hist[cols].tail(max(10, turnover_regime_lookback)).ffill().bfill()
                    rets = recent.pct_change().dropna()
                    if not rets.empty:
                        market = rets.mean(axis=1)
                        ann_ret = float(market.mean() * 252)
                        ann_vol = float(market.std() * np.sqrt(252))
                        if ann_ret >= trend_return_threshold and ann_vol <= trend_vol_threshold:
                            cap = turnover_cap_trend
                        elif ann_vol >= unstable_vol_threshold:
                            cap = turnover_cap_unstable
                        else:
                            cap = turnover_cap_neutral

            if cap is not None and cap > 0 and turnover > cap:
                alpha = cap / turnover
                blended = {k: old_weights[k] + alpha * (new_weights[k] - old_weights[k]) for k in overlap}
                denom = float(sum(blended.values()))
                if denom > 0:
                    current_weight_map = {k: float(v) / denom for k, v in blended.items() if float(v) > 0}
                else:
                    current_weight_map = dict(pre_rebalance_weights)
                turnover = cap

            turnover_history.append(float(turnover))

            # Apply turnover-based transaction cost on rebalance date.
            if float(transaction_cost_pct) > 0:
                pending_rebalance_cost = turnover * float(transaction_cost_pct)
                transaction_cost_history.append(float(pending_rebalance_cost))
            else:
                transaction_cost_history.append(0.0)

            rebalance_count += 1
            while current_dt >= next_rebalance_dt:
                next_rebalance_dt = next_rebalance_dt + pd.DateOffset(months=step_months)

        daily_ret = 0.0
        for s, w in current_weight_map.items():
            r = row.get(s, 0.0)
            r = 0.0 if pd.isna(r) else float(r)
            daily_ret += float(w) * r
        if pending_rebalance_cost > 0:
            daily_ret -= pending_rebalance_cost
            pending_rebalance_cost = 0.0
        portfolio_returns.append(daily_ret)

        # Drift weights between rebalances.
        current_weight_map = _drift_weight_map(current_weight_map, row)

    portfolio_returns = np.array(portfolio_returns)
    cumulative_returns = (1 + portfolio_returns).cumprod()
    total_return = (cumulative_returns[-1] - 1) * 100

    volatility = portfolio_returns.std() * np.sqrt(252) * 100

    rolling_max = np.maximum.accumulate(cumulative_returns)
    drawdowns = (cumulative_returns - rolling_max) / rolling_max * 100
    max_drawdown = drawdowns.min()

    var_95 = np.percentile(portfolio_returns, 5) * 100

    rf_daily = get_dynamic_risk_free_rate(pd.to_datetime(test_start)) / 252
    excess_returns = portfolio_returns - rf_daily
    sharpe = np.mean(excess_returns) / np.std(portfolio_returns) * np.sqrt(252) if np.std(portfolio_returns) > 0 else 0

    return {
        'total_return': total_return,
        'volatility': volatility,
        'max_drawdown': max_drawdown,
        'var_95': var_95,
        'sharpe': sharpe,
        'rebalance_frequency': rebalance_freq,
        'rebalances_applied': int(rebalance_count),
        'avg_turnover_per_rebalance': float(np.mean(turnover_history)) if turnover_history else 0.0,
        'total_transaction_cost': float(np.sum(transaction_cost_history)) if transaction_cost_history else 0.0,
        'cumulative_returns': cumulative_returns,
        'dates': daily_returns.index.tolist(),
    }

def test_crash_scenario(
    scenario_name,
    config,
    prices_df,
    K=10,
    seed=None,
    min_train_coverage=0.8,
    min_test_points=20,
    weight_params=None,
    qubo_params=None,
):
    """Test one crash scenario."""
    if K <= 0:
        raise ValueError(f"K must be >= 1, got {K}")

    print(f"\n{'='*80}")
    print(f"SCENARIO: {scenario_name}")
    print(f"{'='*80}")
    print(f"{config['description']}")
    
    validate_no_data_leakage(
        config['train_start'], config['train_end'],
        config['test_start'], config['test_end']
    )
    
    eligible_stocks = get_stock_universe(
        prices_df,
        config['train_start'],
        config['train_end'],
        config['test_start'],
        config['test_end'],
        min_coverage=min_train_coverage,
        min_test_points=min_test_points,
    )
    print(f"\nStock universe: {len(eligible_stocks)} stocks (train>=80%, test>=20 points)")
    
    results = {}
    
    # === QUANTUM ===
    print(f"\n{'─'*80}")
    print("QUANTUM PORTFOLIO")
    print(f"{'─'*80}")
    quantum_stocks = select_quantum_portfolio(
        prices_df, eligible_stocks,
        config['train_start'], config['train_end'], K=K, seed=seed, qubo_params=qubo_params
    )
    weight_params = weight_params or {}
    quantum_weights, _ = optimize_weights(
        quantum_stocks, prices_df,
        config['train_start'], config['train_end'],
        max_weight=float(weight_params.get('max_weight', 0.40)),
        min_weight=float(weight_params.get('min_weight', 0.0)),
    )
    quantum_results = backtest_period(
        prices_df, quantum_stocks, quantum_weights,
        config['test_start'], config['test_end']
    )
    if quantum_results:
        results['Quantum'] = quantum_results
    
    # === GREEDY ===
    print(f"\n{'─'*80}")
    print("GREEDY PORTFOLIO")
    print(f"{'─'*80}")
    greedy_stocks = select_greedy_portfolio(
        prices_df, eligible_stocks,
        config['train_start'], config['train_end'], K=K
    )
    greedy_weights, _ = optimize_weights(
        greedy_stocks, prices_df,
        config['train_start'], config['train_end'],
        max_weight=float(weight_params.get('max_weight', 0.40)),
        min_weight=float(weight_params.get('min_weight', 0.0)),
    )
    greedy_results = backtest_period(
        prices_df, greedy_stocks, greedy_weights,
        config['test_start'], config['test_end']
    )
    if greedy_results:
        results['Greedy'] = greedy_results
    
    # === CLASSICAL ===
    print(f"\n{'─'*80}")
    print("CLASSICAL MVO PORTFOLIO")
    print(f"{'─'*80}")
    classical_stocks = select_classical_portfolio(
        prices_df, eligible_stocks,
        config['train_start'], config['train_end'], K=K
    )
    classical_weights, _ = optimize_weights(
        classical_stocks, prices_df,
        config['train_start'], config['train_end'],
        max_weight=float(weight_params.get('max_weight', 0.40)),
        min_weight=float(weight_params.get('min_weight', 0.0)),
    )
    classical_results = backtest_period(
        prices_df, classical_stocks, classical_weights,
        config['test_start'], config['test_end']
    )
    if classical_results:
        results['Classical MVO'] = classical_results
    
    # Print summary
    print(f"\n{'='*80}")
    print(f"TEST PERIOD RESULTS: {scenario_name}")
    print(f"{'='*80}")
    print(f"{'Strategy':<20} {'Return %':>12} {'Max DD %':>12} {'Sharpe':>10} {'VaR 95%':>10}")
    print(f"{'-'*80}")
    for strategy, metrics in results.items():
        print(f"{strategy:<20} {metrics['total_return']:>11.2f}% {metrics['max_drawdown']:>11.2f}% "
              f"{metrics['sharpe']:>10.3f} {metrics['var_95']:>9.2f}%")
    
    return results

def plot_comparison(all_results, output_dir: Path):
    """Plot comparison across crashes."""
    scenarios = list(all_results.keys())
    strategies = ['Quantum', 'Greedy', 'Classical MVO']
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Real Quantum Portfolio - Crash Analysis (QUBO vs Greedy vs Classical)', 
                 fontsize=16, fontweight='bold')
    
    x = np.arange(len(scenarios))
    width = 0.25
    
    # Total Return
    ax = axes[0, 0]
    for i, strategy in enumerate(strategies):
        returns = [all_results[sc][strategy]['total_return'] for sc in scenarios if strategy in all_results[sc]]
        ax.bar(x[:len(returns)] + i * width, returns, width, label=strategy, alpha=0.8)
    ax.set_ylabel('Total Return (%)', fontsize=12, fontweight='bold')
    ax.set_title('6-Month Test Period Returns', fontsize=13, fontweight='bold')
    ax.set_xticks(x + width)
    ax.set_xticklabels([s.replace(' ', '\n') for s in scenarios], fontsize=10)
    ax.axhline(0, color='black', linestyle='--', linewidth=0.8)
    ax.legend()
    ax.grid(alpha=0.3)
    
    # Max Drawdown
    ax = axes[0, 1]
    for i, strategy in enumerate(strategies):
        dd = [all_results[sc][strategy]['max_drawdown'] for sc in scenarios if strategy in all_results[sc]]
        ax.bar(x[:len(dd)] + i * width, dd, width, label=strategy, alpha=0.8)
    ax.set_ylabel('Max Drawdown (%)', fontsize=12, fontweight='bold')
    ax.set_title('Maximum Drawdown', fontsize=13, fontweight='bold')
    ax.set_xticks(x + width)
    ax.set_xticklabels([s.replace(' ', '\n') for s in scenarios], fontsize=10)
    ax.legend()
    ax.grid(alpha=0.3)
    
    # Sharpe Ratio
    ax = axes[1, 0]
    for i, strategy in enumerate(strategies):
        sharpe = [all_results[sc][strategy]['sharpe'] for sc in scenarios if strategy in all_results[sc]]
        ax.bar(x[:len(sharpe)] + i * width, sharpe, width, label=strategy, alpha=0.8)
    ax.set_ylabel('Sharpe Ratio', fontsize=12, fontweight='bold')
    ax.set_title('Risk-Adjusted Returns', fontsize=13, fontweight='bold')
    ax.set_xticks(x + width)
    ax.set_xticklabels([s.replace(' ', '\n') for s in scenarios], fontsize=10)
    ax.axhline(0, color='black', linestyle='--', linewidth=0.8)
    ax.legend()
    ax.grid(alpha=0.3)
    
    # VaR 95%
    ax = axes[1, 1]
    for i, strategy in enumerate(strategies):
        var = [all_results[sc][strategy]['var_95'] for sc in scenarios if strategy in all_results[sc]]
        ax.bar(x[:len(var)] + i * width, var, width, label=strategy, alpha=0.8)
    ax.set_ylabel('VaR 95% (%)', fontsize=12, fontweight='bold')
    ax.set_title('Value at Risk', fontsize=13, fontweight='bold')
    ax.set_xticks(x + width)
    ax.set_xticklabels([s.replace(' ', '\n') for s in scenarios], fontsize=10)
    ax.legend()
    ax.grid(alpha=0.3)
    
    plt.tight_layout()
    
    output_dir.mkdir(exist_ok=True)
    plt.savefig(output_dir / 'real_quantum_crash_analysis.png', dpi=300, bbox_inches='tight')
    print(f"\nSaved: {output_dir / 'real_quantum_crash_analysis.png'}")

def main(config_path: str = "config/enhanced_evaluation_config.json"):
    """Main execution."""
    cfg_path = Path(config_path)
    runtime_cfg = _load_runtime_config(cfg_path)

    base_dir = Path(__file__).parent
    data_candidates = runtime_cfg.get("dataset_candidates", [])
    if not data_candidates:
        raise ValueError("dataset_candidates must be configured")

    scenarios = runtime_cfg.get("crash_scenarios", {})
    if not scenarios:
        raise ValueError("crash_scenarios must be configured")

    required_keys = ["k_stocks", "base_seed", "min_train_coverage", "min_test_points"]
    missing = [k for k in required_keys if k not in runtime_cfg]
    if missing:
        raise ValueError(f"Missing required config keys: {missing}")

    K = int(runtime_cfg["k_stocks"])
    base_seed = int(runtime_cfg["base_seed"])
    min_train_coverage = float(runtime_cfg["min_train_coverage"])
    min_test_points = int(runtime_cfg["min_test_points"])
    qubo_params = runtime_cfg.get("qubo", {})
    weight_params = runtime_cfg.get("weight_optimization", {})
    artifacts_cfg = runtime_cfg.get("artifacts", {})
    output_dir = (base_dir / artifacts_cfg.get("output_dir", "results")).resolve()

    data_path = _choose_best_dataset(base_dir, data_candidates)
    
    print("="*80)
    print("REAL QUANTUM PORTFOLIO - CRASH ANALYSIS")
    print("="*80)
    print("\nMethodology:")
    print("  1. Train on historical data before each crash")
    print("  2. Test during defined crash period")
    print("  3. Compare Quantum, Greedy, and Classical")
    print("  4. Enforce train/test separation checks")
    print(f"  5. Portfolio size: K={K} stocks")
    
    prices_df = load_complete_data(data_path)
    
    all_results = {}
    for scenario_name, config in scenarios.items():
        try:
            results = test_crash_scenario(
                scenario_name,
                config,
                prices_df,
                K=K,
                seed=base_seed,
                min_train_coverage=min_train_coverage,
                min_test_points=min_test_points,
                weight_params=weight_params,
                qubo_params=qubo_params,
            )
            all_results[scenario_name] = results
        except Exception as e:
            print(f"\nWarning: Error in {scenario_name}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    if len(all_results) > 0:
        plot_comparison(all_results, output_dir=output_dir)
    
    # Save results
    output_dir.mkdir(exist_ok=True)
    
    json_results = {}
    for scenario, strategies in all_results.items():
        json_results[scenario] = {}
        for strategy, metrics in strategies.items():
            json_results[scenario][strategy] = {
                'total_return': metrics['total_return'],
                'volatility': metrics['volatility'],
                'max_drawdown': metrics['max_drawdown'],
                'var_95': metrics['var_95'],
                'sharpe': metrics['sharpe']
            }
    
    with open(output_dir / 'real_quantum_crash_results.json', 'w') as f:
        json.dump(json_results, f, indent=2)
    
    print(f"\nSaved: {output_dir / 'real_quantum_crash_results.json'}")
    
    print(f"\n{'='*80}")
    print("REAL QUANTUM CRASH ANALYSIS COMPLETE ")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()

