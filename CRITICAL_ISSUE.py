"""
CRITICAL ISSUE INVESTIGATION
Asset count mismatch in Quantum portfolio
"""

import pandas as pd
from pathlib import Path

data_dir = Path('data')
weights = pd.read_csv(data_dir / '07_portfolio_weights.csv', index_col=0)

print('[CRITICAL FINDING] PORTFOLIO ASSET COUNT MISMATCH')
print('='*80)

classical = weights[weights['Classical'] > 0.0001]
quantum = weights[weights['Quantum'] > 0.0001]

print(f'\nClassical Portfolio: {len(classical)} assets')
print(f'  Assets: {list(classical.index)}')
print(f'  Sum of weights: {classical["Classical"].sum():.6f}')
print(f'  Expected: 15')
print(f'  Status: PASS' if len(classical) == 15 else '  Status: FAIL')

print(f'\nQuantum Portfolio: {len(quantum)} assets')
print(f'  Assets: {list(quantum.index)}')
print(f'  Sum of weights: {quantum["Quantum"].sum():.6f}')
print(f'  Expected: 15')
print(f'  Status: FAIL - Only {len(quantum)} instead of 15')

print('\n' + '='*80)
print('ROOT CAUSE ANALYSIS:')
print('='*80)
print('''
The Quantum portfolio has only 12 assets instead of 15.
This could be due to:

1. Annealing algorithm selected fewer than K assets
2. Sharpe filter removed low-quality assets after annealing
3. Rebalancing logic reduced the portfolio size
4. Bug in asset selection or weight calculation

IMPACT:
- Quantum portfolio is suboptimal (missing 3 assets)
- Returns may be lower than theoretical maximum
- Rebalancing logic may not be respecting K constraint
- Performance metrics may not reflect intended 15-asset portfolio

ACTION REQUIRED:
- Investigate hybrid_optimizer.py and rebalancing.py
- Verify K is passed correctly to annealing
- Check if Sharpe filter is removing assets incorrectly
- Enable verbose logging to trace asset selection
''')
