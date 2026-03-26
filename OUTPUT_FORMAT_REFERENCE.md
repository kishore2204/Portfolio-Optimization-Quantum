# NIFTY 200 Analysis Output Format Reference

## 1. Scenario Metrics Output (`scenario_metrics_nifty200.json`)

### Structure
```json
{
  "scenario_1": {
    "scenario_name": "Present_Present to Mar-11-2026",
    "metadata": {
      "scenario_name": "Train 1Y before present period, test until latest available date",
      "train_period": "2024-03-11 to 2025-03-10",
      "test_period": "2025-03-11 to 2026-03-11",
      "train_days": 252,
      "test_days": 365,
      "available_stocks": 156,
      "nifty200_used": true
    },
    "selected_stocks": {
      "count": 8,
      "symbols": ["INFY", "TCS", "HCLTECH", "WIPRO", "AXISBANK", "HDFCBANK", "RELIANCE", "HINDUNILVR"],
      "metrics": {
        "INFY": {
          "train_return": 0.2345,  // 23.45% annualized train return
          "train_sharpe": 1.8521,  // Sharpe ratio during training
          "test_return": 0.1856,   // 18.56% annualized test return
          "test_sharpe": 1.4235    // Sharpe ratio during testing
        },
        // ... more stocks ...
      }
    },
    "weights": {
      "INFY": 0.125,      // 12.5% weight (1/8 in equal-weight)
      "TCS": 0.125,
      // ... more weights ...
    },
    "portfolio_metrics": {
      "test_return": 0.2104,    // Portfolio 21.04% annualized return
      "test_volatility": 0.1556, // Portfolio 15.56% volatility
      "test_sharpe": 1.3495      // Portfolio Sharpe of 1.3495
    }
  }
  // ... more scenarios ...
}
```

### Key Metrics Explained
- **train_return, test_return:** Annualized returns (multiply by 100 for %)
- **train_sharpe, test_sharpe:** (return - 6%) / volatility (risk-free rate = 6%)
- **weights:** Portfolio allocation (sum to 1.0 for full weight)
- **test_volatility:** Annualized standard deviation of portfolio returns

### Use Cases
- Performance attribution by stock
- Scenario-specific allocation decisions
- Historical performance analysis
- Risk/return tradeoffs by scenario

---

## 2. Adaptive K Report (`adaptive_k_report_nifty200.json`)

### Structure
```json
{
  "generated_at": "2026-03-26T12:34:06.123456",
  "methodology": "Adaptive K_sell based on scenario performance",
  "scenarios": {
    "Present_Present to Mar-11-2026": {
      "base_k_sell": 4,           // Default quarterly replacement count
      "adaptive_k_sell": 4,       // Adjusted count for this scenario
      "test_sharpe": 1.3495,      // Performance in this scenario
      "reason": "Normal regime. Standard replacement rate."
    },
    "2022 Global Bear Phase": {
      "base_k_sell": 4,
      "adaptive_k_sell": 6,       // More aggressive in crashes
      "test_sharpe": 1.4436,
      "reason": "Crash regime detected (Sharpe=1.4436). Increase replacement rate."
    },
    "Post-COVID Recovery": {
      "base_k_sell": 4,
      "adaptive_k_sell": 2,       // Conservative in bull markets
      "test_sharpe": 4.5299,
      "reason": "Bull regime detected (Sharpe=4.5299). Reduce replacement rate."
    }
  }
}
```

### Decision Rules Implemented
```python
IF test_sharpe < 0.5:
    adaptive_k_sell = min(K_sell + 2, K - 1)  # Aggressive
    reason = "Crash regime"
ELIF test_sharpe > 1.0:
    adaptive_k_sell = max(2, K_sell - 2)  # Conservative
    reason = "Bull regime"
ELSE:
    adaptive_k_sell = K_sell  # Standard
    reason = "Normal regime"
```

### Use Cases
- Understanding when to rebalance more/less frequently
- Regime detection validation
- Rebalancing frequency optimization
- Risk management decisions

---

## 3. Strategy Comparison Report (`strategy_comparison_nifty200_comprehensive.json`)

### Structure
```json
{
  "generated_at": "2026-03-26T12:34:15.654321",
  "total_scenarios": 8,
  "comparisons": {
    "Present_Present to Mar-11-2026": {
      "scenario": "Present_Present to Mar-11-2026",
      "metadata": {
        "train_period": "2024-03-11 to 2025-03-10",
        "test_period": "2025-03-11 to 2026-03-11",
        "available_stocks": 156,
        "universe": "NIFTY200",
        "K_stocks": 8,
        "K_sell": 4
      },
      "strategies": {
        "Classical": {
          "strategy": "Classical_Markowitz",
          "selected_stocks": ["INFY", "TCS", "HCLTECH", ...],
          "weights": { "INFY": 0.125, ... },
          "metrics": {
            "Annual Return": 0.2104,
            "Annual Volatility": 0.1556,
            "Sharpe Ratio": 1.3495,
            "Max Drawdown": -0.2345,
            "Cumulative Return": 0.2545,
            "Win Rate": 0.6234  // 62.34% positive days
          }
        },
        "Quantum_NoRebalance": {
          "strategy": "Quantum_NoRebalance",
          // ... similar structure ...
        },
        "Quantum_WithRebalance": {
          "strategy": "Quantum_WithRebalance",
          "rebalancing_events": 4,  // Number of quarterly rebalances done
          "selected_stocks": ["INFY", "TCS", ...],  // After rebalancing
          "metrics": {
            "Annual Return": 0.1945,
            "Annual Volatility": 0.1345,
            "Sharpe Ratio": 1.3495,
            "Max Drawdown": -0.1856,
            "Cumulative Return": 0.2340,
            "Win Rate": 0.5890
          }
        }
      },
      "winner": "Classical",
      "sharpe_scores": {
        "Classical": 1.3495,
        "Quantum_NoRebalance": 1.3495,
        "Quantum_WithRebalance": 1.3495
      }
    }
    // ... more scenarios ...
  },
  "summary": {
    "strategy_wins": {
      "Classical": 5,
      "Quantum_NoRebalance": 0,
      "Quantum_WithRebalance": 3
    },
    "average_sharpe": {
      "Classical": 0.8283,
      "Quantum_NoRebalance": 0.8283,
      "Quantum_WithRebalance": 0.8512
    },
    "quantum_outperformance": {
      "vs_classical": -2,        // Negative = Classical won more
      "sharpe_improvement": 0.0230 // 2.3% improvement
    }
  }
}
```

### Performance Metrics Explained
- **Annual Return:** Total return per year (annualized if less than 1 year)
- **Annual Volatility:** Standard deviation of daily returns (annualized)
- **Sharpe Ratio:** (Return - 6%) / Volatility (higher is better)
- **Max Drawdown:** Maximum loss from peak (negative value)
- **Cumulative Return:** Total return over period
- **Win Rate:** Fraction of positive days (>50% is good)

### Strategy Comparison Logic
- **Winner:** Strategy with highest Sharpe ratio in that scenario
- **Aggregate:** Win count across all scenarios
- **Performance:** Average Sharpe ratio across scenarios

---

## 4. Final Analysis Report (`final_analysis_report_nifty200.json`)

### Structure
```json
{
  "generated_at": "2026-03-26T12:34:20.987654",
  "title": "NIFTY 200 Portfolio Optimization - Comprehensive Analysis",
  "sections": {
    "scenario_metrics": {
      "summary": {
        "total_scenarios": 8,
        "avg_portfolio_sharpe": 1.1234  // Average Sharpe across all scenarios
      },
      "count": 8
    },
    "adaptive_k_analysis": {
      "methodology": "Adaptive K_sell...",
      "scenarios": { ... }  // Full adaptive K report
    },
    "strategy_comparison": {
      "total_scenarios": 8,
      "comparisons": { ... },  // Full comparison report
      "summary": {
        "strategy_wins": { ... },
        "average_sharpe": { ... },
        "quantum_outperformance": { ... }
      }
    }
  },
  "summary": {
    "total_scenarios": 8,
    "system_performance": {
      "strategy_wins": {
        "Classical": 5,
        "Quantum_NoRebalance": 0,
        "Quantum_WithRebalance": 3
      },
      "average_sharpe": {
        "Classical": 0.8283,
        "Quantum_NoRebalance": 0.8283,
        "Quantum_WithRebalance": 0.8512
      },
      "quantum_outperformance": {
        "vs_classical": -2,
        "sharpe_improvement": 0.0230
      }
    },
    "recommendations": [
      "Average Sharpe ratio improved by 2.77% with quantum+rebalance"
    ]
  }
}
```

---

## How to Extract Specific Information

### Get all stocks selected in "Present" scenario
```python
import json

with open('results/scenario_metrics_nifty200.json') as f:
    data = json.load(f)

# Find Present scenario
for scenario_name, scenario_data in data.items():
    if 'Present' in scenario_name and scenario_data:
        print(f"Scenario: {scenario_name}")
        print(f"Selected stocks: {scenario_data['selected_stocks']['symbols']}")
        print(f"Weights: {scenario_data['weights']}")
        print(f"Portfolio Sharpe: {scenario_data['portfolio_metrics']['test_sharpe']:.4f}")
```

### Compare strategies across scenarios
```python
with open('results/strategy_comparison_nifty200_comprehensive.json') as f:
    comp = json.load(f)

print("Strategy Performance")
print("=" * 60)
for scenario, details in comp['comparisons'].items():
    if details:
        print(f"\n{scenario}")
        print(f"  Winner: {details['winner']}")
        for strat, scores in details['sharpe_scores'].items():
            print(f"    {strat}: {scores:.4f}")

print("\nSummary")
print(f"  Total wins: {comp['summary']['strategy_wins']}")
print(f"  Avg Sharpe: {comp['summary']['average_sharpe']}")
```

### Get adaptive K adjustments
```python
with open('results/adaptive_k_report_nifty200.json') as f:
    adaptive = json.load(f)

print("Adaptive K_sell Adjustments")
print("=" * 60)
for scenario, adj in adaptive['scenarios'].items():
    if adj['adaptive_k_sell'] != adj['base_k_sell']:
        print(f"{scenario}:")
        print(f"  Base: {adj['base_k_sell']} → Adjusted: {adj['adaptive_k_sell']}")
        print(f"  Reason: {adj['reason']}")
```

---

## Interpreting Results

### Good Performance Indicators
- **Sharpe > 1.0:** Excellent (1% return per 1% risk)
- **Sharpe 0.5-1.0:** Good
- **Sharpe < 0.5:** Poor (beta-like performance)
- **Max Drawdown < -20%:** Reasonable maximum loss
- **Win Rate > 55%:** More positive than negative days

### Strategy Selection
- **High Sharpe (>1.0):** Use full allocation
- **Medium Sharpe (0.5-1.0):** Use partial allocation or complement
- **Low Sharpe (<0.5):** Avoid or use for diversification only

### Scenario Context
- **Crash Scenarios:** Quantum+Rebalance usually better (protect downside)
- **Bull Scenarios:** Classical often better (ride the trend)
- **Normal Markets:** Mixed results (depends on market state)
- **Recent Data:** Classical typically stronger (less regime change)

---

## Data Dictionary

| Field | Type | Range | Meaning |
|-------|------|-------|---------|
| train_return | float | [-1.0, 1.0] | Annualized return (1.0 = 100%) |
| test_sharpe | float | [-5, 5] typically | Risk-adjusted return (higher is better) |
| weights | float [0,1] | [0.0, 0.4] | Portfolio allocation per stock |
| annual_return | float | [-1.0, 1.0] | Annualized return |
| annual_volatility | float | [0.05, 0.5] | Annualized standard deviation |
| max_drawdown | float | [-1.0, 0.0] | Maximum loss from peak |
| win_rate | float | [0.0, 1.0] | Fraction of positive days |
| K_stocks | int | [2, 20] | Number of stocks in portfolio |
| K_sell | int | [1, 5] | Quarterly replacement count |

---

**Report Generated:** March 26, 2026  
**Format Version:** 1.0  
**Universe:** NIFTY 200
