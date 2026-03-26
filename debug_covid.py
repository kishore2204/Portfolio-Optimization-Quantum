import pandas as pd
import numpy as np
import json

# Load data
prices_df = pd.read_csv('Dataset/prices_timeseries_complete.csv', parse_dates=['Date'])
prices_df = prices_df.sort_values('Date').reset_index(drop=True)

# Load NIFTY 200
with open('config/nifty200_sectors.json', 'r') as f:
    sectors_data = json.load(f)

nifty200_stocks = set()
for sector_stocks in sectors_data['NIFTY_200_STOCKS'].values():
    nifty200_stocks.update(sector_stocks)

# Test COVID scenario
scenario_config = {
    'train_start': '2019-02-20',
    'train_end': '2020-02-19',
    'test_start': '2020-02-20',
    'test_end': '2020-04-30',
}

train_start = pd.to_datetime(scenario_config['train_start'])
train_end = pd.to_datetime(scenario_config['train_end'])
test_start = pd.to_datetime(scenario_config['test_start'])
test_end = pd.to_datetime(scenario_config['test_end'])

# Filter to NIFTY 200 stocks
all_symbols = set(col for col in prices_df.columns if col != 'Date')
available_stocks = [col for col in all_symbols 
                   if col.upper() in {s.upper() for s in nifty200_stocks}]

print(f"Available NIFTY200 stocks in data: {len(available_stocks)}")

# Split data
train_mask = (prices_df['Date'] >= train_start) & (prices_df['Date'] <= train_end)
test_mask = (prices_df['Date'] >= test_start) & (prices_df['Date'] <= test_end)

train_data = prices_df[train_mask].copy()
test_data = prices_df[test_mask].copy()

print(f"Train data shape: {train_data.shape}")
print(f"Test data shape: {test_data.shape}")

# Select available columns
train_cols = ['Date'] + [col for col in available_stocks if col in train_data.columns]
test_cols = ['Date'] + [col for col in available_stocks if col in test_data.columns]

train_df = train_data[train_cols].copy()
test_df = test_data[test_cols].copy()

# Check if we have data
train_returns = train_df.iloc[:, 1:].ffill().bfill().pct_change().dropna()
test_returns_all = test_df.iloc[:, 1:].ffill().bfill().pct_change().dropna()

print(f"Train returns shape: {train_returns.shape}")
print(f"Test returns (all stocks) shape: {test_returns_all.shape}")

# Test with COVID selected stocks
selected_stocks = ['360ONE', 'ABB', 'ABCAPITAL', 'ACC', 'ADANIENSOL', 'ADANIENT', 'ADANIGREEN', 'ADANIPORTS']
print(f"\nTesting selected stocks: {selected_stocks}")

# Test returns for selected stocks
if len(test_returns_all) > 0:
    test_returns_selected = test_returns_all[selected_stocks]
    print(f"Test returns (selected stocks) shape: {test_returns_selected.shape}")
    print(f"Test returns selected (first 5 rows):\n{test_returns_selected.head()}")
    
    # Calculate portfolio returns
    weights = np.ones(len(selected_stocks)) / len(selected_stocks)
    portfolio_returns = test_returns_selected.dot(weights)
    print(f"\nPortfolio returns shape: {portfolio_returns.shape}")
    print(f"Portfolio returns (first 5): {portfolio_returns.head()}")
    
    # Calculate metrics
    annual_return = portfolio_returns.mean() * 252
    annual_vol = portfolio_returns.std() * np.sqrt(252)
    sharpe = (annual_return - 0.06) / (annual_vol + 1e-6)
    
    print(f"\nCalculated metrics:")
    print(f"  Annual Return: {annual_return:.6f}")
    print(f"  Annual Volatility: {annual_vol:.6f}")
    print(f"  Sharpe Ratio: {sharpe:.6f}")
else:
    print("Test returns empty!")
