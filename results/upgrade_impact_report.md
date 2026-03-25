# Upgrade Impact Report

Pre K: 8 | Post K: 8
Post dynamic_k: configured in config

## Average Total Return Delta (post - pre)

| Block | Quantum | Greedy | Classical |
|---|---:|---:|---:|
| Horizon | 1.90 | -3.80 | -3.61 |
| Crash | 12.12 | 8.38 | -0.56 |

## Winner Counts

### Pre
{'horizon': {'best_total_return': {'Greedy': 1, 'Classical': 2, 'Quantum': 1}, 'best_sharpe': {'Greedy': 1, 'Classical': 2, 'Quantum': 1}, 'best_max_drawdown': {'Greedy': 2, 'Classical': 2}, 'best_var_95': {'Quantum': 2, 'Classical': 2}}, 'crash': {'best_total_return': {'Classical': 3, 'Quantum': 1}, 'best_sharpe': {'Classical': 3, 'Quantum': 1}, 'best_max_drawdown': {'Classical': 4}, 'best_var_95': {'Greedy': 1, 'Classical': 3}}}

### Post
{'horizon': {'best_total_return': {'Quantum': 2, 'Classical': 2}, 'best_sharpe': {'Greedy': 1, 'Classical': 2, 'Quantum': 1}, 'best_max_drawdown': {'Quantum': 2, 'Classical': 1, 'Greedy': 1}, 'best_var_95': {'Classical': 2, 'Greedy': 1, 'Quantum': 1}}, 'crash': {'best_total_return': {'Classical': 1, 'Quantum': 3}, 'best_sharpe': {'Classical': 1, 'Quantum': 3}, 'best_max_drawdown': {'Classical': 1, 'Quantum': 3}, 'best_var_95': {'Classical': 3, 'Quantum': 1}}}