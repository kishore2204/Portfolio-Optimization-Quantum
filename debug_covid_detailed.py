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

# Filter to NIFTY 200 stocks
all_symbols = set(col for col in prices_df.columns if col != 'Date')
available_stocks = [col for col in all_symbols 
                   if col.upper() in {s.upper() for s in nifty200_stocks}]

# Split data
train_mask = (prices_df['Date'] >= train_start) & (prices_df['Date'] <= train_end)
train_data = prices_df[train_mask].copy()

# Select available columns
train_cols = ['Date'] + [col for col in available_stocks if col in train_data.columns]
train_df = train_data[train_cols].copy()

print(f"Train_df shape: {train_df.shape}")
print(f"Train_df columns (first 10): {train_df.columns[:10].tolist()}")
print(f"Train_df dtypes (first 5):")
print(train_df.dtypes[:5])

# Check for NaN values
print(f"\nNumber of NaN values per column (first 5):")
print(train_df.isna().sum()[:5])

print(f"\nTotal NaN values: {train_df.isna().sum().sum()}")

# Try pct_change step by step
print(f"\nChecking pct_change process:")
prices_only = train_df.iloc[:, 1:]
print(f"Prices only shape: {prices_only.shape}")

# Forward fill
prices_filled = prices_only.ffill()
print(f"After ffill, NaN count: {prices_filled.isna().sum().sum()}")

# Backward fill
prices_filled = prices_filled.bfill()  
print(f"After bfill, NaN count: {prices_filled.isna().sum().sum()}")

# Check for non-numeric data
print(f"\nData types in prices_only:")
print(prices_only.dtypes.value_counts())

# Manually convert to numeric
prices_numeric = prices_only.apply(pd.to_numeric, errors='coerce')
print(f"After converting to numeric, NaN count: {prices_numeric.isna().sum().sum()}")

# Try pct_change on numeric
pct_change_result = prices_numeric.ffill().bfill().pct_change().dropna()
print(f"\nPct change result shape: {pct_change_result.shape}")
print(f"Pct change result (first 5 rows):\n{pct_change_result.head()}")
