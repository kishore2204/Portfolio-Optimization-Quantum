# Rebalance Comparison Summary

Methods compared per scenario:
1. Quantum_NoRebalance
2. Quantum_Rebalanced
3. Markowitz (or Greedy if selected)

| Group | Scenario | Quantum NoRebal | Quantum Rebal | Baseline | Winner Return | Winner Sharpe | Rebalances |
|---|---|---:|---:|---:|---|---|---:|
| horizon | Horizon_6M_Train_60M | -2.83 | -2.82 | 3.34 | Markowitz | Markowitz | 1 |
| horizon | Horizon_12M_Train_60M | 35.07 | 36.94 | 26.14 | Quantum_Rebalanced | Quantum_Rebalanced | 3 |
| horizon | Horizon_24M_Train_60M | -1.86 | 5.19 | -8.16 | Quantum_Rebalanced | Quantum_Rebalanced | 7 |
| horizon | Horizon_36M_Train_60M | 25.78 | 79.98 | 28.40 | Quantum_Rebalanced | Quantum_Rebalanced | 11 |
| crash | COVID Peak Crash | -18.95 | -18.95 | -18.62 | Markowitz | Quantum_NoRebalance | 0 |
| crash | China Bubble Burst Peak | 52.99 | 40.97 | 3.98 | Quantum_NoRebalance | Quantum_NoRebalance | 1 |
| crash | European Debt Stress | 21.17 | 14.09 | 10.10 | Quantum_NoRebalance | Quantum_NoRebalance | 2 |
| crash | 2022 Global Bear Phase | -13.18 | -17.05 | -13.57 | Quantum_NoRebalance | Quantum_NoRebalance | 1 |