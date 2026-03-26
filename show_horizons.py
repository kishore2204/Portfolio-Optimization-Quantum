import json
from datetime import datetime

with open('results/strategy_comparison_nifty200_comprehensive.json', 'r') as f:
    data = json.load(f)

print('TIME HORIZONS TESTED - ALL 8 SCENARIOS')
print('='*100)

scenarios = data['comparisons']

for scenario_name, scenario_data in scenarios.items():
    metadata = scenario_data['metadata']
    train_period = metadata['train_period']
    test_period = metadata['test_period']
    
    # Parse dates
    train_start_str, train_end_str = train_period.split(' to ')
    test_start_str, test_end_str = test_period.split(' to ')
    
    train_start = datetime.strptime(train_start_str, '%Y-%m-%d')
    train_end = datetime.strptime(train_end_str, '%Y-%m-%d')
    test_start = datetime.strptime(test_start_str, '%Y-%m-%d')
    test_end = datetime.strptime(test_end_str, '%Y-%m-%d')
    
    train_days = (train_end - train_start).days
    test_days = (test_end - test_start).days
    
    print(f'\n{scenario_name}')
    print('-' * 100)
    print(f'  Training Period:  {train_period} ({train_days} calendar days / ~{int(train_days*252/365)} trading days)')
    print(f'  Test Period:      {test_period} ({test_days} calendar days / ~{int(test_days*252/365)} trading days)')
    print(f'  Metrics:          K={metadata["K_stocks"]}, K_sell={metadata["K_sell"]}, Stocks available={metadata["available_stocks"]}')
