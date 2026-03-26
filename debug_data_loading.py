
import json
import pandas as pd
import numpy as np

# Load data exactly as the script does
prices_df = pd.read_csv('Dataset/prices_timeseries_complete.csv', parse_dates=['Date'])
prices_df = prices_df.sort_values('Date').reset_index(drop=True)

# Load NIFTY 200
with open('config/nifty200_sectors.json', 'r') as f:
    sectors_data = json.load(f)

nifty200_stocks = set()
for sector_stocks in sectors_data['NIFTY_200_STOCKS'].values():
    nifty200_stocks.update(sector_stocks)

# Replicate load_scenario_data for COVID crash
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

# Filter to NIFTY 200 stocks - use case-insensitive matching
all_symbols = set(col for col in prices_df.columns if col != 'Date')
available_stocks = [col for col in all_symbols 
                   if col.upper() in {s.upper() for s in nifty200_stocks}]

print(f"Available NIFTY200 stocks in data: {len(available_stocks)}")

# Split data
train_mask = (prices_df['Date'] >= train_start) & (prices_df['Date'] <= train_end)
test_mask = (prices_df['Date'] >= test_start) & (prices_df['Date'] <= test_end)

print(f"Train mask matches: {train_mask.sum()} days")
print(f"Test mask matches: {test_mask.sum()} days")

train_data = prices_df[train_mask].copy()
test_data = prices_df[test_mask].copy()

print(f"Train data shape: {train_data.shape}")
print(f"Test data shape: {test_data.shape}")

# Select available columns
train_cols = ['Date'] + [col for col in available_stocks if col in train_data.columns]
test_cols = ['Date'] + [col for col in available_stocks if col in test_data.columns]

train_df = train_data[train_cols].copy()
test_df = test_data[test_cols].copy()

print(f"Final train_df shape: {train_df.shape}")
print(f"Final test_df shape: {test_df.shape}")

# Check data types and values
if len(train_df) > 0:
    print(f"Train date range: {train_df['Date'].min()} to {train_df['Date'].max()}")
    # Check if we can calculate returns
    train_returns = train_df.iloc[:, 1:].ffill().bfill().pct_change().dropna()
    print(f"Train returns shape: {train_returns.shape}")
    print(f"Train condition: len(train_returns) < 10 or len(train_df) < 100 = {len(train_returns) < 10 or len(train_df) < 100}")
else:
    print("Train_df is empty!")
