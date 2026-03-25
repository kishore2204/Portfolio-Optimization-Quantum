# Final Validation and Comparison

Dataset: Dataset/prices_timeseries_complete.csv
Universe mode: full_universe
Total scenarios evaluated: 8

## Quantum Winner Counts

- Best Total Return: 5/8
- Best Sharpe: 4/8
- Best Max Drawdown (less negative): 5/8
- Best VaR95 (less negative): 2/8

## Scenario Comparison (Quantum vs Greedy vs Classical)

| Block | Scenario | K | Eligible | Q Return % | G Return % | C Return % | Q Sharpe | G Sharpe | C Sharpe | Q MaxDD % | G MaxDD % | C MaxDD % | Q VaR95 % | G VaR95 % | C VaR95 % |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| horizon | Horizon_6M_Train_6M | 15 | 2074 | -10.57 | -11.25 | -32.53 | -1.224 | -1.160 | -3.748 | -28.18 | -32.78 | -41.13 | -2.65 | -2.42 | -2.42 |
| horizon | Horizon_12M_Train_12M | 15 | 1931 | 36.08 | 38.25 | 43.76 | 1.595 | 1.649 | 1.797 | -20.95 | -21.95 | -22.93 | -1.75 | -1.71 | -1.80 |
| horizon | Horizon_24M_Train_24M | 15 | 1715 | -8.11 | -1.61 | 18.34 | -0.458 | -0.266 | 0.238 | -26.28 | -28.29 | -22.76 | -1.97 | -1.97 | -1.59 |
| horizon | Horizon_36M_Train_36M | 15 | 1037 | 179.10 | 142.85 | 130.83 | 1.608 | 1.239 | 1.144 | -36.58 | -29.60 | -31.01 | -1.83 | -1.98 | -2.09 |
| crash | COVID Peak Crash | 15 | 963 | -21.42 | -25.05 | -19.09 | -2.989 | -3.538 | -2.698 | -37.64 | -38.79 | -32.25 | -5.05 | -5.03 | -4.60 |
| crash | China Bubble Burst Peak | 15 | 942 | 24.06 | 20.01 | 3.17 | 2.257 | 1.698 | 0.298 | -13.14 | -15.72 | -16.79 | -3.01 | -3.56 | -2.64 |
| crash | European Debt Stress | 15 | 878 | 19.23 | 8.16 | 9.03 | 1.924 | 0.633 | 0.780 | -9.41 | -12.56 | -11.04 | -1.16 | -1.43 | -1.36 |
| crash | 2022 Global Bear Phase | 15 | 1491 | -22.98 | -27.24 | -24.78 | -2.595 | -3.038 | -3.000 | -34.35 | -37.46 | -35.02 | -2.52 | -2.53 | -2.32 |