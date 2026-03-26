import json

with open('results/strategy_comparison_nifty200_comprehensive.json', 'r') as f:
    data = json.load(f)

print('COMPREHENSIVE STRATEGY COMPARISON RESULTS')
print('='*100)

for scenario_name, scenario_data in data['comparisons'].items():
    print(f'\n{scenario_name}')
    print('-' * 100)
    print(f'  Training Period: {scenario_data["metadata"]["train_period"]}')
    print(f'  Test Period:     {scenario_data["metadata"]["test_period"]}')
    print(f'  Available Stocks: {scenario_data["metadata"]["available_stocks"]}')
    print()
    
    for strategy_name in ['Classical', 'Quantum_NoRebalance', 'Quantum_WithRebalance']:
        strategy = scenario_data['strategies'][strategy_name]
        metrics = strategy['metrics']
        print(f'  {strategy_name:25s}: Sharpe={metrics["Sharpe Ratio"]:7.4f}, Return={metrics["Annual Return"]:7.2f}%, Volatility={metrics["Annual Volatility"]:7.2f}%')
    
    print(f'  Winner: {scenario_data["winner"]} (Sharpe={scenario_data["sharpe_scores"][scenario_data["winner"]]:.4f})')
