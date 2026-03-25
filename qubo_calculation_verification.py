#!/usr/bin/env python3
"""
QUBO Calculation Verification Script

This script guides you through calculating QUBO matrix elements manually
and compares with the actual computed matrix.

Run with: python qubo_calculation_verification.py

Author: Educational Tool
"""

import pandas as pd
import numpy as np
from pathlib import Path

def print_section(title):
    """Pretty print section headers"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def load_inputs():
    """Load all necessary input files"""
    print_section("STEP 1: Loading Input Files")
    
    # Check if files exist
    data_dir = Path('data')
    files = {
        'mean_returns': data_dir / 'qubo_input_mean_returns.csv',
        'covariance': data_dir / 'qubo_input_covariance_matrix.csv',
        'downside_dev': data_dir / 'qubo_input_downside_deviation.csv',
        'params': data_dir / 'qubo_input_parameters_new.csv',
        'sector_map': data_dir / 'qubo_input_stock_sector_map_new.csv',
        'actual_matrix': data_dir / 'qubo_matrix.csv'
    }
    
    for name, filepath in files.items():
        if filepath.exists():
            print(f"✓ {name}: {filepath}")
        else:
            print(f"✗ {name}: NOT FOUND at {filepath}")
            return None
    
    # Load files
    mean_returns = pd.read_csv(files['mean_returns'], index_col=0)
    covariance = pd.read_csv(files['covariance'], index_col=0)
    downside_dev = pd.read_csv(files['downside_dev'], index_col=0)
    params = pd.read_csv(files['params'], index_col=0).iloc[:, 0].to_dict()
    sector_map = pd.read_csv(files['sector_map'], index_col=0)
    actual_matrix = pd.read_csv(files['actual_matrix'], index_col=0)
    
    return {
        'mean_returns': mean_returns,
        'covariance': covariance,
        'downside_dev': downside_dev,
        'params': params,
        'sector_map': sector_map,
        'actual_matrix': actual_matrix
    }

def print_input_summary(data):
    """Print summary of loaded inputs"""
    print_section("Input Data Summary")
    
    params = data['params']
    print(f"Parameters:")
    print(f"  N (stocks) = {int(params['N_variables'])}")
    print(f"  K (target portfolio size) = {int(params['target_K'])}")
    print(f"  q (risk aversion) = {params['q_risk_aversion']:.4f}")
    print(f"  β (downside weight) = {params['beta_downside']:.4f}")
    print(f"  λ (cardinality penalty) = {params['lambda_penalty']:.6f}")
    print(f"  Sector penalty = {params['sector_penalty']:.6f}")
    
    print(f"\nMean Returns (first 5 stocks):")
    for i in range(min(5, len(data['mean_returns']))):
        stock = data['mean_returns'].index[i]
        value = data['mean_returns'].iloc[i, 0]
        print(f"  {stock}: {value:.6f}")
    
    print(f"\nDownside Deviations (first 5 stocks):")
    for i in range(min(5, len(data['downside_dev']))):
        stock = data['downside_dev'].index[i]
        value = data['downside_dev'].iloc[i, 0]
        print(f"  {stock}: {value:.6f}")
    
    print(f"\nSectors (first 5 stocks):")
    for i in range(min(5, len(data['sector_map']))):
        stock = data['sector_map'].index[i]
        sector = data['sector_map'].iloc[i, 0]
        print(f"  {stock}: {sector}")

def build_qubo_manual(data):
    """Build QUBO matrix step by step (educational)"""
    print_section("STEP 2: Building QUBO Matrix (6-Step Process)")
    
    mean_returns = data['mean_returns']
    covariance = data['covariance']
    downside_dev = data['downside_dev']
    params = data['params']
    sector_map = data['sector_map']
    
    N = int(params['N_variables'])
    K = int(params['target_K'])
    q = params['q_risk_aversion']
    beta = params['beta_downside']
    lambda_pen = params['lambda_penalty']
    sector_pen = params['sector_penalty']
    
    stocks = list(covariance.index)
    sectors = dict(sector_map['sector'])
    
    # Initialize matrix
    Q = np.zeros((N, N))
    
    # Step 1: Risk term (covariance scaled by q)
    print("Step 1: Risk Term (add q × Covariance)")
    for i in range(N):
        for j in range(N):
            Q[i, j] = q * covariance.iloc[i, j]
    print(f"  Q[0,0] after step 1: {Q[0, 0]:.6f}")
    print(f"  Q[0,1] after step 1: {Q[0, 1]:.6f}")
    
    # Step 2: Return term (diagonal only, negative)
    print("\nStep 2: Return Term (subtract μ from diagonal)")
    for i in range(N):
        Q[i, i] -= mean_returns.iloc[i, 0]
    print(f"  Q[0,0] after step 2: {Q[0, 0]:.6f}")
    print(f"  (diagonal only, Q[0,1] unchanged: {Q[0, 1]:.6f})")
    
    # Step 3: Downside penalty (diagonal only)
    print("\nStep 3: Downside Penalty (add β × downside_deviation to diagonal)")
    for i in range(N):
        downside_val = downside_dev.iloc[i, 0]
        Q[i, i] += beta * downside_val
    print(f"  Q[0,0] after step 3: {Q[0, 0]:.6f}")
    
    # Step 4: Cardinality penalty
    print(f"\nStep 4: Cardinality Penalty")
    cardinality_factor = 1 - 2 * K
    print(f"  Cardinality factor = 1 - 2×K = 1 - 2×{K} = {cardinality_factor}")
    print(f"  λ = {lambda_pen:.6f}")
    
    # Diagonal
    for i in range(N):
        Q[i, i] += lambda_pen * cardinality_factor
    
    # Off-diagonal
    for i in range(N):
        for j in range(i+1, N):
            Q[i, j] += 2 * lambda_pen
    
    print(f"  Q[0,0] after step 4: {Q[0, 0]:.6f}")
    print(f"  Q[0,1] after step 4: {Q[0, 1]:.6f}")
    
    # Step 5: Sector penalty (same sector only, off-diagonal)
    print(f"\nStep 5: Sector Penalty (add 0.1×λ for same-sector pairs)")
    sector_penalty_applied = 0
    for i in range(N):
        for j in range(i+1, N):
            if sectors[stocks[i]] == sectors[stocks[j]]:
                Q[i, j] += sector_pen
                sector_penalty_applied += 1
    
    print(f"  Applied sector penalty to {sector_penalty_applied} pairs")
    print(f"  Q[0,1] unchanged (different sectors: {sectors[stocks[0]]} vs {sectors[stocks[1]]})")
    print(f"  Q[0,1] after step 5: {Q[0, 1]:.6f}")
    
    # Step 6: Symmetrize
    print("\nStep 6: Symmetrize Matrix")
    # Make symmetric: Q = Q + Q^T - diag(diag(Q))
    Q_sym = np.zeros((N, N))
    for i in range(N):
        for j in range(N):
            if i == j:
                Q_sym[i, j] = Q[i, j]  # Keep diagonal
            elif i < j:
                Q_sym[i, j] = Q[i, j]  # Use upper triangle
                Q_sym[j, i] = Q[i, j]  # Mirror to lower
            # else: already filled from i < j
    
    Q = Q_sym
    print(f"  Q[0,0] final: {Q[0, 0]:.6f}")
    print(f"  Q[0,1] final: {Q[0, 1]:.6f}")
    print(f"  Q[1,0] final: {Q[1, 0]:.6f} (should equal Q[0,1])")
    
    return Q, stocks, sectors

def compare_with_actual(Q_manual, data):
    """Compare manually calculated matrix with actual"""
    print_section("STEP 3: Comparing with Actual Matrix")
    
    Q_actual = data['actual_matrix'].values
    stocks = list(data['covariance'].index)
    
    # Element-wise comparison
    diff_matrix = np.abs(Q_manual - Q_actual)
    
    print(f"Matrix shape: {Q_manual.shape}")
    print(f"Max absolute difference: {diff_matrix.max():.2e}")
    print(f"Mean absolute difference: {diff_matrix.mean():.2e}")
    print(f"Median absolute difference: {np.median(diff_matrix):.2e}")
    
    # Show first 5x5 block
    print(f"\nElement-wise comparison (first 5×5 block):")
    print(f"{'Stock Pair':<35} {'Manual':<15} {'Actual':<15} {'Diff':<12}")
    print("-" * 80)
    
    for i in range(min(5, Q_manual.shape[0])):
        for j in range(min(5, Q_manual.shape[1])):
            pair = f"{stocks[i]}-{stocks[j]}"
            if len(pair) > 33:
                pair = pair[:30] + "..."
            manual = Q_manual[i, j]
            actual = Q_actual[i, j]
            diff = abs(manual - actual)
            print(f"{pair:<35} {manual:>14.8f} {actual:>14.8f} {diff:>11.2e}")
    
    # Highlight differences > 1e-10
    large_diffs = np.argwhere(diff_matrix > 1e-10)
    if len(large_diffs) > 0:
        print(f"\n⚠️  Found {len(large_diffs)} differences > 1e-10:")
        for idx in large_diffs[:10]:  # Show first 10
            i, j = idx
            print(f"  Q[{i},{j}] ({stocks[i]}-{stocks[j]}): Diff = {diff_matrix[i,j]:.2e}")
    else:
        print(f"\n✓ All differences < 1e-10 (excellent match!)")
    
    return diff_matrix

def explain_calculation(data):
    """Show detailed explanation for specific elements"""
    print_section("STEP 4: Detailed Calculation Explanation")
    
    mean_returns = data['mean_returns']
    covariance = data['covariance']
    downside_dev = data['downside_dev']
    params = data['params']
    sector_map = data['sector_map']
    stocks = list(covariance.index)
    sectors = dict(sector_map['sector'])
    
    q = params['q_risk_aversion']
    beta = params['beta_downside']
    lambda_pen = params['lambda_penalty']
    sector_pen = params['sector_penalty']
    K = int(params['target_K'])
    
    # Example: First two stocks
    print(f"Example 1: Diagonal Element Q[0,0] (Stock: {stocks[0]})")
    print(f"{'='*70}")
    
    # Calculate step by step
    i = 0
    c_ii = covariance.iloc[i, i]
    mu_i = mean_returns.iloc[i, 0]
    down_i = downside_dev.iloc[i, 0]
    
    step1 = q * c_ii
    print(f"  Step 1 (Risk): q × C[0,0] = {q} × {c_ii:.6f} = {step1:.6f}")
    
    step2 = step1 - mu_i
    print(f"  Step 2 (Return): - μ[0] = {step1:.6f} - {mu_i:.6f} = {step2:.6f}")
    
    step3 = step2 + beta * down_i
    print(f"  Step 3 (Downside): + β × downside[0] = {step2:.6f} + {beta} × {down_i:.6f} = {step3:.6f}")
    
    card_factor = 1 - 2*K
    step4 = step3 + lambda_pen * card_factor
    print(f"  Step 4 (Cardinality): + λ × (1-2K) = {step3:.6f} + {lambda_pen:.6f} × {card_factor} = {step4:.6f}")
    
    print(f"  Step 5 (Sector): No change (diagonal)")
    print(f"  Step 6 (Symmetry): No change (diagonal)")
    print(f"  Final Q[0,0] = {step4:.6f}")
    
    # Next example: off-diagonal different sectors
    print(f"\n\nExample 2: Off-diagonal Element Q[0,1] (Stocks: {stocks[0]} vs {stocks[1]})")
    print(f"{'='*70}")
    
    j = 1
    c_ij = covariance.iloc[i, j]
    
    step1 = q * c_ij
    print(f"  Step 1 (Risk): q × C[0,1] = {q} × {c_ij:.6f} = {step1:.6f}")
    
    print(f"  Step 2-3 (Return, Downside): No change (off-diagonal)")
    
    step4 = step1 + 2 * lambda_pen
    print(f"  Step 4 (Cardinality): + 2λ = {step1:.6f} + 2 × {lambda_pen:.6f} = {step4:.6f}")
    
    sector_i = sectors[stocks[i]]
    sector_j = sectors[stocks[j]]
    if sector_i == sector_j:
        step5 = step4 + sector_pen
        print(f"  Step 5 (Sector): + 0.1λ = {step4:.6f} + {sector_pen:.6f} = {step5:.6f}")
        print(f"    (Both in {sector_i} sector - sector penalty applies)")
    else:
        step5 = step4
        print(f"  Step 5 (Sector): No change")
        print(f"    ({sectors[stocks[i]]} ≠ {sectors[stocks[j]]})")
    
    print(f"  Step 6 (Symmetry): Final Q[0,1] = Q[1,0] = {step5:.6f}")
    
    return step4, step5

def find_sector_pairs(data):
    """Find and show sector penalty applications"""
    print_section("STEP 5: Sector Penalty Analysis")
    
    sector_map = data['sector_map']
    covariance = data['covariance']
    stocks = list(covariance.index)
    sectors = dict(sector_map['sector'])
    
    # Count by sector
    sector_counts = {}
    for stock in stocks:
        sector = sectors[stock]
        sector_counts[sector] = sector_counts.get(sector, 0) + 1
    
    print(f"Sector Distribution:")
    for sector in sorted(sector_counts.keys()):
        count = sector_counts[sector]
        print(f"  {sector}: {count} stocks")
    
    # Find first few sector-pair examples
    print(f"\nExample same-sector pairs (will have Q[i,j] + 6.17):")
    pair_count = 0
    for i in range(len(stocks)):
        if pair_count >= 5:
            break
        for j in range(i+1, len(stocks)):
            if pair_count >= 5:
                break
            if sectors[stocks[i]] == sectors[stocks[j]]:
                print(f"  {stocks[i]} - {stocks[j]}: {sectors[stocks[i]]}")
                pair_count += 1

def verify_user_calculation():
    """Interactive verification for user-provided calculations"""
    print_section("STEP 6: Verify Your Own Calculation")
    
    print("Enter a stock pair to verify your calculation.")
    print("Examples: 0,1 (TVSMOTOR-PERSISTENT) or 5,10 (NTPC-LT)")
    
    try:
        user_input = input("\nEnter pair as 'i,j' (or 'skip'): ").strip()
        
        if user_input.lower() == 'skip':
            return
        
        i, j = map(int, user_input.split(','))
        
        # Load fresh data
        data = load_inputs()
        if data is None:
            return
        
        covariance = data['covariance']
        Q_actual = data['actual_matrix'].values
        stocks = list(covariance.index)
        
        if i >= len(stocks) or j >= len(stocks):
            print(f"Invalid indices. Max: {len(stocks)-1}")
            return
        
        actual_value = Q_actual[i, j]
        stock_i = stocks[i]
        stock_j = stocks[j]
        
        print(f"\nQ[{i},{j}] ({stock_i} - {stock_j}):")
        print(f"Actual value: {actual_value:.10f}")
        
        user_calc = input(f"Enter your calculated value: ").strip()
        try:
            user_val = float(user_calc)
            diff = abs(user_val - actual_value)
            pct_error = 100 * diff / abs(actual_value) if actual_value != 0 else 0
            
            print(f"\nYour value: {user_val:.10f}")
            print(f"Difference: {diff:.2e}")
            print(f"Error: {pct_error:.4f}%")
            
            if diff < 1e-6:
                print(f"✓ Excellent match!")
            elif diff < 1e-3:
                print(f"✓ Good approximation")
            else:
                print(f"⚠️  Check your calculation steps")
        
        except ValueError:
            print("Invalid number format")
    
    except ValueError:
        print("Invalid input format. Use: i,j (e.g., 0,1)")


def main():
    """Main verification workflow"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "QUBO MATRIX CALCULATION VERIFIER" + " "*21 + "║")
    print("║" + " "*68 + "║")
    print("║" + " Educational Tool for Manual QUBO Calculation Learning" + " "*12 + "║")
    print("╚" + "="*68 + "╝\n")
    
    # Load inputs
    data = load_inputs()
    if data is None:
        print("ERROR: Could not load input files. Are you in the project root?")
        return
    
    # Print summary
    print_input_summary(data)
    
    # Build QUBO manually
    Q_manual, stocks, sectors = build_qubo_manual(data)
    
    # Compare with actual
    diff_matrix = compare_with_actual(Q_manual, data)
    
    # Explain calculations
    explain_calculation(data)
    
    # Sector analysis
    find_sector_pairs(data)
    
    # Optional: verify user calculation
    try:
        verify_user_calculation()
    except (KeyboardInterrupt, EOFError):
        pass
    
    print_section("Verification Complete!")
    print("✓ You have successfully:")
    print("  1. Loaded all QUBO input files")
    print("  2. Built the QUBO matrix from scratch (6-step process)")
    print("  3. Compared your calculation with the actual matrix")
    print("  4. Learned how each term contributes")
    print("  5. Understood sector penalty application")
    print("\nNext steps:")
    print("  - Read QUBO_CALCULATION_TUTORIAL.md for detailed explanations")
    print("  - Read QUBO_HORIZON_SPECIFIC_GUIDE.md for horizon-specific details")
    print("  - Check quantum/weight_optimizer.py to see SLSQP weight optimization")
    print("  - Run unified_train_test_compare.py to see backtest results")
    print()

if __name__ == "__main__":
    main()
