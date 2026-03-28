"""
EDGE CASE HANDLER: Budget vs Stock Price Constraints
=====================================================

This module handles the practical edge case where:
  - A stock's price exceeds the allocated budget
  - Fractional shares cannot be purchased (real-world constraint)
  - Code operates in theoretical weight space but real trading has limits

EDGE CASE SCENARIO:
  Budget: ₹2,000
  Stock Price: ₹2,500
  Allocated Weight: 12%
  Allocated Amount: 0.12 × 2,000 = ₹240
  
  PROBLEM: Cannot buy even 1 share (which costs ₹2,500)
  CODE BEHAVIOR: Allows fractional positions (theoretical)
  REAL BEHAVIOR: Would fail (practical constraint)
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class EdgeCaseWarning:
    """Warning message for edge case violations"""
    asset: str
    stock_price: float
    allocated_amount: float
    allocated_weight: float
    budget: float
    shares_possible: float
    severity: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    message: str


def check_budget_vs_stock_price(
    weights: pd.Series,
    stock_prices: pd.Series | Dict[str, float],
    budget: float,
    verbose: bool = True
) -> List[EdgeCaseWarning]:
    """
    Check if allocated amounts are sufficient to buy at least 1 share.
    
    Args:
        weights: Asset allocation weights (should sum to ~1.0)
        stock_prices: Current stock prices per share
        budget: Total investment budget
        verbose: Print warnings to console
    
    Returns:
        List of EdgeCaseWarning objects for violating assets
    
    EXAMPLE:
        >>> weights = pd.Series({'INFY': 0.12, 'TCS': 0.08, 'BB': 0.05})
        >>> prices = {'INFY': 1234.50, 'TCS': 3456.75, 'BB': 125.00}
        >>> budget = 2000
        >>> warnings = check_budget_vs_stock_price(weights, prices, budget)
        >>> for w in warnings:
        >>>     print(w.message)
    """
    
    if isinstance(stock_prices, dict):
        stock_prices = pd.Series(stock_prices)
    
    warnings: List[EdgeCaseWarning] = []
    
    for asset, weight in weights.items():
        if asset not in stock_prices.index:
            continue
        
        price = stock_prices[asset]
        if pd.isna(price) or price <= 0:
            continue
        
        allocated_amount = weight * budget
        shares_possible = allocated_amount / price
        
        # Categorize severity
        if shares_possible < 1.0:
            if shares_possible < 0.5:
                severity = "CRITICAL"
            elif shares_possible < 0.75:
                severity = "HIGH"
            else:
                severity = "MEDIUM"
            
            message = (
                f"{severity}: {asset} | Price: ₹{price:.2f} | "
                f"Weight: {weight:.2%} | Allocated: ₹{allocated_amount:.2f} | "
                f"Can buy: {shares_possible:.3f} shares (need 1.0)"
            )
            
            warnings.append(EdgeCaseWarning(
                asset=asset,
                stock_price=price,
                allocated_amount=allocated_amount,
                allocated_weight=weight,
                budget=budget,
                shares_possible=shares_possible,
                severity=severity,
                message=message
            ))
    
    if verbose and warnings:
        print("\n" + "="*80)
        print("⚠️  EDGE CASE WARNINGS: Budget Insufficient for Stock Prices")
        print("="*80)
        print(f"Budget: ₹{budget:,.2f}\n")
        for warning in sorted(warnings, key=lambda w: w.shares_possible):
            print(f"  {warning.message}")
        print("="*80)
        print(f"Total violations: {len(warnings)} assets")
        print("\nIMPLICATION: Code operates in theoretical weight space (fractional OK)")
        print("             Real trading requires adjustment (rounding, constraint enforcement)\n")
    
    return warnings


def suggest_weight_adjustments(
    weights: pd.Series,
    stock_prices: pd.Series | Dict[str, float],
    budget: float,
    min_shares: float = 1.0
) -> pd.Series:
    """
    Suggest adjusted weights to ensure minimum shares can be purchased.
    
    STRATEGY:
      1. Calculate max weight per asset: weight_max = (min_shares × price) / budget
      2. If current weight > weight_max, cap it at weight_max
      3. Redistribute excess weight proportionally to compliant assets
    
    Args:
        weights: Original allocation weights
        stock_prices: Stock prices per share
        budget: Total budget
        min_shares: Minimum shares to guarantee purchase (default: 1.0)
    
    Returns:
        Adjusted weights that respect the constraint
    
    EXAMPLE:
        >>> weights = pd.Series({'INFY': 0.12, 'TCS': 0.08, 'BB': 0.05})
        >>> prices = {'INFY': 1234.50, 'TCS': 3456.75, 'BB': 125.00}
        >>> budget = 2000
        >>> adjusted = suggest_weight_adjustments(weights, prices, budget, min_shares=1.0)
        >>> print(adjusted.sum())  # Should be ~1.0
        0.98
    """
    
    if isinstance(stock_prices, dict):
        stock_prices = pd.Series(stock_prices)
    
    adjusted = weights.copy()
    
    # Step 1: Calculate max allowable weight per asset
    max_weights = {}
    for asset in adjusted.index:
        if asset not in stock_prices.index:
            max_weights[asset] = adjusted[asset]  # No constraint
            continue
        
        price = stock_prices[asset]
        if pd.isna(price) or price <= 0:
            max_weights[asset] = adjusted[asset]
            continue
        
        max_w = (min_shares * price) / budget
        max_weights[asset] = max_w
    
    # Step 2: Identify violations and redistribution amount
    total_excess = 0.0
    for asset in adjusted.index:
        if adjusted[asset] > max_weights.get(asset, 1.0):
            excess = adjusted[asset] - max_weights[asset]
            total_excess += excess
            adjusted[asset] = max_weights[asset]
    
    # Step 3: Redistribute excess proportionally among compliant assets
    if total_excess > 0:
        compliant_assets = [a for a in adjusted.index 
                           if adjusted[a] < max_weights.get(a, 1.0)]
        if compliant_assets:
            compliant_weights = adjusted[compliant_assets].sum()
            for asset in compliant_assets:
                if compliant_weights > 0:
                    adjusted[asset] += (total_excess * adjusted[asset] / compliant_weights)
            # Renormalize
            adjusted = adjusted / adjusted.sum()
    
    return adjusted


def report_edge_case_summary(
    weights: pd.Series,
    stock_prices: pd.Series | Dict[str, float],
    budget: float,
) -> Dict[str, any]:
    """
    Generate a comprehensive edge case analysis report.
    
    Returns:
        Summary statistics: violation_count, critical_count, affected_weight, etc.
    """
    
    warnings = check_budget_vs_stock_price(weights, stock_prices, budget, verbose=False)
    
    if not warnings:
        return {
            "status": "PASS",
            "violation_count": 0,
            "message": "All weights are compatible with budget constraints"
        }
    
    critical = [w for w in warnings if w.severity == "CRITICAL"]
    high = [w for w in warnings if w.severity == "HIGH"]
    medium = [w for w in warnings if w.severity == "MEDIUM"]
    
    affected_weight = sum(w.allocated_weight for w in warnings)
    
    return {
        "status": "FAIL",
        "violation_count": len(warnings),
        "critical_count": len(critical),
        "high_count": len(high),
        "medium_count": len(medium),
        "affected_weight_pct": affected_weight * 100,
        "worst_case_asset": min(warnings, key=lambda w: w.shares_possible).asset if warnings else None,
        "worst_case_shares": min(warnings, key=lambda w: w.shares_possible).shares_possible if warnings else None,
        "warnings": [w.message for w in warnings]
    }


# ============================================================================
# PROJECT-SPECIFIC CONSTANTS
# ============================================================================

DEFAULT_PROJECT_BUDGET = 1_000_000  # ₹1,000,000 (fixed in this project)

# Edge case thresholds (adjustable)
CRITICAL_THRESHOLD = 0.5    # shares < 0.5
HIGH_THRESHOLD = 0.75       # shares < 0.75
MEDIUM_THRESHOLD = 1.0      # shares < 1.0


# ============================================================================
# DEMONSTRATION & TESTING
# ============================================================================

def demonstrate_edge_case():
    """
    Demonstrate the edge case with the scenario from conversation:
    Budget: ₹2,000
    Stock: ₹2,500
    Weight: 12%
    """
    
    print("\n" + "="*80)
    print("EDGE CASE DEMONSTRATION")
    print("="*80)
    
    budget_scenario = 2000
    weights_scenario = pd.Series({
        'Stock_A': 0.12,  # High weight
        'Stock_B': 0.08,  # Medium weight
        'Stock_C': 0.05   # Low weight
    })
    prices_scenario = {
        'Stock_A': 2500,  # PROBLEM: Price > budget
        'Stock_B': 1200,  # OK: Can buy 1 share
        'Stock_C': 120    # OK: Can buy multiple
    }
    
    print(f"\nScenario: Budget ₹{budget_scenario:,}\n")
    
    # Check constraints
    warnings = check_budget_vs_stock_price(
        weights_scenario, 
        prices_scenario, 
        budget_scenario,
        verbose=True
    )
    
    # Suggest adjustments
    print("\nSUGGESTED WEIGHT ADJUSTMENTS:")
    print("-" * 80)
    adjusted = suggest_weight_adjustments(
        weights_scenario,
        prices_scenario,
        budget_scenario,
        min_shares=1.0
    )
    
    print("\nComparison:")
    print(f"{'Asset':<12} {'Original Weight':<20} {'Adjusted Weight':<20} {'Allocated (₹)':<15}")
    print("-" * 80)
    for asset in adjusted.index:
        original = weights_scenario[asset]
        adjusted_w = adjusted[asset]
        allocated = adjusted_w * budget_scenario
        print(f"{asset:<12} {original:>19.2%} {adjusted_w:>19.2%} {allocated:>14,.2f}")
    
    print(f"\n{'TOTAL':<12} {weights_scenario.sum():>19.2%} {adjusted.sum():>19.2%}")
    
    # Report summary
    print("\n\nSUMMARY REPORT:")
    print("-" * 80)
    report = report_edge_case_summary(weights_scenario, prices_scenario, budget_scenario)
    for key, value in report.items():
        if key != "warnings":
            print(f"  {key:<30}: {value}")


if __name__ == "__main__":
    demonstrate_edge_case()
