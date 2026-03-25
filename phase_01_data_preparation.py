"""
Enhanced Data Preparation for NIFTY 100
=======================================
- Loads complete NSE dataset (2011-2026)
- Filters to NIFTY 100 stocks with sector mapping
- Prepares data for training (2023+) and testing
- Computes returns, covariance, sector statistics

Author: Enhanced Portfolio System
Date: March 2026
"""

import sys
import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

def print_header(text):
    print(f"\n{'='*80}")
    print(f"{text.center(80)}")
    print(f"{'='*80}\n")

def load_config():
    """Load configuration"""
    with open('config/config.json', 'r') as f:
        config = json.load(f)
    with open('config/nifty100_sectors.json', 'r') as f:
        sectors = json.load(f)
    return config, sectors

def load_nifty100_data(config, sectors):
    """Load and filter NIFTY 100 stocks from complete dataset"""
    print_header("ENHANCED DATA PREPARATION - NIFTY 100")
    
    print("[1/8] Loading complete NSE dataset...")
    data_path = Path(config['data']['source_path'])
    
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")
    
    df = pd.read_csv(data_path, parse_dates=['Date'])
    print(f"   OK Loaded {len(df):,} rows")
    print(f"   OK Date range: {df['Date'].min()} to {df['Date'].max()}")
    print(f"   OK Total stocks: {len(df.columns)-1}")
    
    # Get NIFTY 100 stocks
    nifty100_stocks = []
    stock_sector_map = {}
    
    for sector, stocks in sectors['NIFTY_100_STOCKS'].items():
        for stock in stocks:
            if stock in df.columns:
                nifty100_stocks.append(stock)
                stock_sector_map[stock] = sector
    
    print(f"\n[2/8] Filtering to NIFTY 100 stocks...")
    print(f"   OK“ Found {len(nifty100_stocks)} NIFTY 100 stocks in dataset")
    print(f"   OK“ Sectors: {len(set(stock_sector_map.values()))}")
    
    # Filter columns
    df_nifty = df[['Date'] + nifty100_stocks].copy()
    
    return df_nifty, stock_sector_map

def clean_and_validate(df, config):
    """Clean data and validate quality"""
    print(f"\n[3/8] Cleaning and validating data...")
    
    # Remove rows with too many nulls
    null_threshold = len(df.columns) * 0.3
    df = df.dropna(thresh=len(df.columns) - null_threshold)
    
    # Forward fill remaining nulls (max 5 days)
    df = df.ffill(limit=5)
    
    # Drop stocks with insufficient data
    min_data_points = config['data']['min_history_days']
    valid_stocks = []
    
    stock_cols = [c for c in df.columns if c != 'Date']
    for col in stock_cols:
        # Count non-null values - ensure we get a scalar
        try:
            non_null_count = int(df[col].notna().sum())
            if non_null_count >= min_data_points:
                valid_stocks.append(col)
        except Exception as e:
            print(f"   [SKIP] {col}: {e}")
            continue
    
    df = df[['Date'] + valid_stocks].copy()
    
    print(f"   OK Cleaned dataset: {len(df)} trading days")
    print(f"   OK Valid stocks: {len(valid_stocks)}")
    
    # Calculate data completeness safely
    total_cells = df.shape[0] * (df.shape[1] - 1)  # Exclude Date column
    null_cells = df[valid_stocks].isnull().sum().sum()
    completeness = (1 - null_cells / total_cells) * 100 if total_cells > 0 else 0
    print(f"   OK Data completeness: {completeness:.2f}%")
    
    return df

def split_train_test(df, config):
    """Split data into training and testing periods"""
    print(f"\n[4/8] Splitting data for training and testing...")
    
    train_start = pd.to_datetime(config['data']['train_start_date'])
    
    # Use all data before test period for historical analysis
    df_train = df[df['Date'] < train_start].copy()
    df_test = df[df['Date'] >= train_start].copy()
    
    print(f"   OK“ Historical data: {df_train['Date'].min()} to {df_train['Date'].max()}")
    print(f"   OK“ Historical days: {len(df_train)}")
    print(f"   OK“ Test period: {df_test['Date'].min()} to {df_test['Date'].max()}")
    print(f"   OK“ Test days: {len(df_test)}")
    
    return df_train, df_test

def compute_returns_statistics(df, stock_sector_map, config):
    """Compute returns, mean returns, covariance, and sector stats"""
    print(f"\n[5/8] Computing returns and statistics...")
    
    # Set Date as index
    df_prices = df.set_index('Date')
    
    # Compute daily returns
    df_returns = df_prices.pct_change().dropna()
    
    # Annualized statistics
    trading_days = config['data']['trading_days_per_year']
    mean_returns_annual = df_returns.mean() * trading_days
    cov_matrix_annual = df_returns.cov() * trading_days
    
    # Compute Sharpe ratios
    rf_rate = config['data']['risk_free_rate']
    volatilities = np.sqrt(np.diag(cov_matrix_annual))
    sharpe_ratios = (mean_returns_annual - rf_rate) / volatilities
    
    print(f"   OK“ Mean annual return: {mean_returns_annual.mean()*100:.2f}%")
    print(f"   OK“ Mean volatility: {volatilities.mean()*100:.2f}%")
    print(f"   OK“ Mean Sharpe ratio: {sharpe_ratios.mean():.3f}")
    
    # Compute sector statistics
    sector_stats = {}
    for sector in set(stock_sector_map.values()):
        sector_stocks = [s for s, sec in stock_sector_map.items() if sec == sector and s in df_returns.columns]
        if sector_stocks:
            sector_returns = df_returns[sector_stocks].mean(axis=1)
            sector_stats[sector] = {
                'stocks': sector_stocks,
                'count': len(sector_stocks),
                'avg_return': sector_returns.mean() * trading_days,
                'volatility': sector_returns.std() * np.sqrt(trading_days),
                'sharpe': ((sector_returns.mean() * trading_days - rf_rate) / 
                          (sector_returns.std() * np.sqrt(trading_days)))
            }
    
    print(f"\n   Sector Performance:")
    for sector, stats in sorted(sector_stats.items(), key=lambda x: x[1]['sharpe'], reverse=True)[:10]:
        print(f"     {sector:20s}: Sharpe={stats['sharpe']:6.3f}, Return={stats['avg_return']*100:6.2f}%, Stocks={stats['count']}")
    
    return df_returns, mean_returns_annual, cov_matrix_annual, sharpe_ratios, sector_stats

def rank_and_select_universe(df_returns, mean_returns, sharpe_ratios, stock_sector_map, config):
    """Rank stocks and select top universe for optimization"""
    print(f"\n[6/8] Selecting investment universe...")
    
    universe_size = config['data']['universe_size']
    
    # Create ranking DataFrame
    ranking = pd.DataFrame({
        'stock': sharpe_ratios.index,
        'sharpe': sharpe_ratios.values,
        'return': mean_returns.values,
        'sector': [stock_sector_map.get(s, 'Unknown') for s in sharpe_ratios.index]
    })
    
    # Sort by Sharpe ratio
    ranking = ranking.sort_values('sharpe', ascending=False)
    
    # Select top universe_size stocks while ensuring minimum sector diversification.
    selected_stocks = []
    sectors_included = set()
    min_sectors = int(config['sector_diversification']['min_sectors'])

    # Pass 1: pick strongest stocks that introduce new sectors until min_sectors is met.
    if min_sectors > 0:
        for _, row in ranking.iterrows():
            sector = row['sector']
            stock = row['stock']
            if sector not in sectors_included:
                selected_stocks.append(stock)
                sectors_included.add(sector)
            if len(sectors_included) >= min_sectors:
                break

    # Pass 2: fill remaining slots by Sharpe rank regardless of sector.
    selected_set = set(selected_stocks)
    for _, row in ranking.iterrows():
        stock = row['stock']
        if stock in selected_set:
            continue
        selected_stocks.append(stock)
        selected_set.add(stock)
        if len(selected_stocks) >= universe_size:
            break

    selected_stocks = selected_stocks[:universe_size]
    sectors_included = {stock_sector_map.get(s, 'Unknown') for s in selected_stocks}
    
    print(f"   OK“ Selected {len(selected_stocks)} stocks for optimization")
    print(f"   OK“ Sectors represented: {len(sectors_included)}")
    print(f"   OK“ Top 10 stocks by Sharpe ratio:")
    for i, stock in enumerate(selected_stocks[:10], 1):
        sr = ranking[ranking['stock'] == stock]['sharpe'].values[0]
        ret = ranking[ranking['stock'] == stock]['return'].values[0]
        print(f"      {i:2d}. {stock:15s} - Sharpe: {sr:.3f}, Return: {ret*100:.2f}%")
    
    return selected_stocks, ranking

def save_prepared_data(df_prices, df_returns, mean_returns, cov_matrix, sharpe_ratios, 
                      selected_stocks, stock_sector_map, sector_stats, config):
    """Save all prepared data"""
    print(f"\n[7/8] Saving prepared data...")
    
    # Filter to selected stocks
    selected_returns = mean_returns[selected_stocks]
    selected_cov = cov_matrix.loc[selected_stocks, selected_stocks]
    selected_sharpe = sharpe_ratios[selected_stocks]
    
    # Save arrays
    np.save('data/mean_returns.npy', selected_returns.values)
    np.save('data/covariance_matrix.npy', selected_cov.values)
    np.save('data/sharpe_ratios.npy', selected_sharpe.values)
    
    # Save returns matrix for downside risk calculation
    selected_returns_matrix = df_returns[selected_stocks].values
    np.save('data/returns_matrix.npy', selected_returns_matrix)
    
    # Save time series
    df_prices[selected_stocks].to_csv('data/prices_timeseries.csv')
    df_returns[selected_stocks].to_csv('data/returns_timeseries.csv')
    
    # Save metadata
    metadata = {
        'stocks': list(selected_stocks),
        'sectors': {stock: stock_sector_map.get(stock, 'Unknown') for stock in selected_stocks},
        'sector_stats': {k: {kk: vv for kk, vv in v.items() if kk != 'stocks'} 
                        for k, v in sector_stats.items()},
        'statistics': {
            'mean_return': float(selected_returns.mean()),
            'mean_volatility': float(np.sqrt(np.diag(selected_cov)).mean()),
            'mean_sharpe': float(selected_sharpe.mean()),
            'date_range': {
                'start': str(df_prices.index[0]),
                'end': str(df_prices.index[-1])
            },
            'trading_days': len(df_prices)
        },
        'config': config
    }
    
    with open('data/universe_metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"   OK Saved arrays: mean_returns.npy, covariance_matrix.npy, sharpe_ratios.npy, returns_matrix.npy")
    print(f"   OK“ Saved time series: prices_timeseries.csv, returns_timeseries.csv")
    print(f"   OK“ Saved metadata: universe_metadata.json")

def main():
    """Main execution"""
    try:
        # Load configuration
        config, sectors = load_config()
        
        # Load NIFTY 100 data
        df, stock_sector_map = load_nifty100_data(config, sectors)
        
        # Clean and validate
        df = clean_and_validate(df, config)
        
        # Split train/test
        df_train, df_test = split_train_test(df, config)
        
        # Save test data separately
        df_test.to_csv('data/test_data.csv', index=False)
        print(f"\n   OK“ Saved test data: data/test_data.csv")
        
        # Use training data for optimization
        df_returns, mean_returns, cov_matrix, sharpe_ratios, sector_stats = \
            compute_returns_statistics(df_train, stock_sector_map, config)
        
        # Select universe
        selected_stocks, ranking = rank_and_select_universe(
            df_returns, mean_returns, sharpe_ratios, stock_sector_map, config
        )
        
        # Save everything
        save_prepared_data(
            df_train.set_index('Date'), df_returns, mean_returns, cov_matrix, 
            sharpe_ratios, selected_stocks, stock_sector_map, sector_stats, config
        )
        
        print(f"\n[8/8] Data preparation complete!")
        print(f"\n{'='*80}\n")
        print("OK“ Ready for QUBO formulation and quantum selection")
        print("OK“ Run: python phase_03_qubo_formulation.py")
        
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())



