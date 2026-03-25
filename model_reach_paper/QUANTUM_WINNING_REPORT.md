# Quantum Method Winning Scenarios Report

**Baseline Configuration**: 5-Year Rolling Training Window | 7-Seed Ensemble | Full Universe  
**Dataset**: 2248 Assets | 2011-03-14 to 2026-03-11  
**Generation Date**: March 24, 2026

---

## Executive Summary

Quantum method (QUBO-based binary selection + continuous weight optimization) captures significant wins in **medium-to-long horizons** and **stress scenarios**, outperforming Greedy and Classical methods in **4 out of 8 total evaluation scenarios**.

- **Horizon Wins**: 2 of 4 (12M, 36M)
- **Crash Wins**: 2 of 4 (China Bubble, 2022 Bear Phase)
- **Combined**: 4 of 8 scenarios with quantum as leader

---

## Horizon Test Results (4 Rolling Windows)

### Win Summary
| Scenario | Winner | Quantum Return | Runner-Up | Gap |
|----------|--------|-----------------|-----------|-----|
| **6M Test** | Greedy | -15.00% | Greedy (-10.18%) | **5.0% worse** |
| **12M Test** | **QUANTUM** | **+16.95%** | Greedy (+3.63%) | **13.3% better** ✓ |
| **24M Test** | Classical | +7.77% | Classical (+19.51%) | **11.7% worse** |
| **36M Test** | **QUANTUM** | **+72.80%** | Greedy (+67.98%) | **4.8% better** ✓ |

### Detail: Where Quantum Wins

**Horizon_12M_Train_60M** (March 2025 - March 2026)
- Quantum Return: **+16.95%** (Sharpe: 0.576)
- Greedy Return: +3.63% (Sharpe: 0.037)
- Classical Return: -2.15% (Sharpe: -0.351)
- **Performance**: Quantum +13.3% vs Greedy, +19.1% vs Classical
- **Key Insight**: Medium term (12M) is Quantum's sweet spot; strong positive returns with positive Sharpe

**Horizon_36M_Train_60M** (March 2023 - March 2026)
- Quantum Return: **+72.80%** (Sharpe: 0.708)
- Greedy Return: +67.98% (Sharpe: 0.635)
- Classical Return: +56.24% (Sharpe: 0.567)
- **Performance**: Quantum dominates all return metrics over 36-month horizon
- **Key Insight**: Long-term accumulation; Quantum captures best upside trajectories

---

## Crash/Stress Test Results (4 Market Regimes)

### Win Summary
| Scenario | Winner | Quantum Performance | Context |
|----------|--------|---------------------|---------|
| **COVID Peak Crash** | Classical | -21.42% | Downside capture; Classical better |
| **China Bubble Burst** | **QUANTUM** | **+24.06%** ✓ | Contrarian strength; +3.9% vs Greedy |
| **European Debt Stress** | **QUANTUM** | **+19.23%** ✓ | Risk-on phase; +11.1% vs Greedy |
| **2022 Global Bear** | **QUANTUM** | **-22.98%** ✓ | Relative resilience; -5.3% vs Greedy |

### Detail: Where Quantum Wins in Crashes

**China_Bubble_Burst_Peak** (June 2015 Test Period)
- Quantum Return: **+24.06%** (Sharpe: 2.257)
- Greedy Return: +20.01% (Sharpe: 1.621)
- Classical Return: +3.17% (Sharpe: 0.210)
- **Performance**: Quantum +4.0% vs Greedy, +20.9% vs Classical
- **Key Insight**: Quantum's binary selection identifies contrarian alpha during market dislocations

**European_Debt_Stress** (August 2011 - August 2012 Period)
- Quantum Return: **+19.23%** (Sharpe: 3.051)
- Greedy Return: +8.16% (Sharpe: 0.833)
- Classical Return: +9.03% (Sharpe: 0.822)
- **Performance**: Quantum +11.1% vs Greedy, +10.2% vs Classical
- **Key Insight**: QUBO ensemble captures quality stocks insensitive to peripheral debt shocks

**2022_Global_Bear_Phase** (2022 Bear Market)
- Quantum Return: **-22.98%** (Sharpe: -4.124)
- Greedy Return: -27.24% (Sharpe: -4.732)
- Classical Return: -24.78% (Sharpe: -3.941)
- **Performance**: Quantum -4.3% better than Greedy, -1.8% better than Classical
- **Key Insight**: Defensive positioning; Quantum limits downside relative to Greedy

---

## Quantum Sharpe Ratio Wins

Quantum leads in risk-adjusted returns (Sharpe) in:
1. **12M Horizon** (0.576 vs Greedy 0.037)
2. **36M Horizon** (0.708 vs Greedy 0.635, Classical 0.567)
3. **China Crashes** (2.257 vs Greedy 1.621)
4. **European Debt** (3.051 vs Greedy 0.833)

---

## No Quantum Wins (Underperformance Cases)

**6M Horizon Test** - Short-term noise dominates
- Likely cause: 60-month training window too conservative for 6M rolling; market frictions and micro-cap noise overwhelm QUBO optimization
- Recommendation: Evaluate shorter train windows (12-24M) for 6M horizons if tactical rebalancing required

**24M Horizon & COVID Peak Crash** - Black swan tail risk
- Classical method's simpler diversification captures downside better during extreme volatility
- Quantum's concentrated positions (top 5 allocations ~60% of portfolio) amplified pandemic crash impact

---

## Recommendation Summary

**Use Quantum When:**
- Evaluating 12M+ holding periods
- Markets show structural dislocations (China bubble, debt crises, regime shifts)
- Seeking risk-adjusted returns (Sharpe ratio) in stressed environments
- Portfolio can tolerate moderate concentration (5-8 stocks) for strategy gains

**Use Classical When:**
- Holding periods < 12 months with noise-heavy data
- Extreme tail-risk protection is primary objective (e.g., pandemic crashes)
- Requiring maximum diversification and simplicity

**Use Greedy When:**
- Quick tactical rebalancing with minimal computation
- Baseline comparison benchmark needed

---

## Baseline Data Source

All metrics extracted from: `results/unified_train_test_compare_base.json`

Config: `config/unified_compare_config.json` (5Y rolling, 7-seed ensemble, full universe)
