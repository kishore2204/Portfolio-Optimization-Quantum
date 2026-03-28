"""
Generate detailed portfolio CSV files with stock-level metrics

Creates CSVs for Classical and Quantum portfolios showing:
- Stock name
- Weight allocated
- Individual stock returns
- Individual stock risk (volatility)
- Sharpe ratio
- Contribution to portfolio
"""

import pandas as pd
import numpy as np
from pathlib import Path
from data_loader import load_all_data
from preprocessing import clean_prices, time_series_split, annualize_stats

root = Path(__file__).resolve().parent
dataset_root = root / "datasets"
data_dir = root / "data"
output_dir = root / "outputs"

print("\n" + "="*80)
print("GENERATING DETAILED PORTFOLIO CSVS")
print("="*80)

# Load data
print("\n[STEP 1] Loading portfolio data...")
bundle = load_all_data(dataset_root)
prices = clean_prices(bundle.asset_prices)
split = time_series_split(prices, train_years=10, test_years=5)

train_r = split.train_returns
test_r = split.test_returns
test_dates = test_r.index

print(f"  Test period: {test_dates[0].date()} to {test_dates[-1].date()}")
print(f"  Test days: {len(test_r)}")

# Load weights
print("\n[STEP 2] Loading portfolio weights...")
weights_df = pd.read_csv(data_dir / "07_portfolio_weights.csv", index_col=0)

classical_w = weights_df['Classical'].dropna()
quantum_w = weights_df['Quantum'].dropna()

print(f"  Classical assets: {len(classical_w)}")
print(f"  Quantum assets: {len(quantum_w)}")

# Load portfolio values for metrics
print("\n[STEP 3] Loading portfolio values...")
pv_df = pd.read_csv(data_dir / "10_portfolio_values.csv", index_col='Date', parse_dates=True)

classical_value = pv_df['Classical']
quantum_value = pv_df['Quantum']

# Calculate overall portfolio metrics
def calc_metrics(value_series, rf=0.05):
    ret = np.log(value_series / value_series.shift(1)).dropna()
    total_return = float(value_series.iloc[-1] / value_series.iloc[0] - 1.0)
    ann_return = float(np.exp(ret.mean() * 252.0) - 1.0)
    vol = float(ret.std() * np.sqrt(252.0))
    sharpe = float((ann_return - rf) / vol) if vol > 0 else np.nan
    return {
        'Total Return': total_return,
        'Annualized Return': ann_return,
        'Volatility': vol,
        'Sharpe Ratio': sharpe
    }

classical_metrics = calc_metrics(classical_value)
quantum_metrics = calc_metrics(quantum_value)

print(f"\n  Classical Portfolio Metrics:")
for k, v in classical_metrics.items():
    print(f"    {k}: {v:.6f}")

print(f"\n  Quantum Portfolio Metrics:")
for k, v in quantum_metrics.items():
    print(f"    {k}: {v:.6f}")

# Function to create portfolio CSV
def create_portfolio_csv(weights, test_returns, portfolio_name, portfolio_metrics):
    """Create detailed portfolio CSV"""
    
    portfolio_data = []
    
    # Get returns for weighted assets
    test_r_weighted = test_returns[weights.index].fillna(0.0)
    
    for asset in weights.index:
        if weights[asset] == 0:
            continue
        
        asset_returns = test_r_weighted[asset]
        
        # Stock-level metrics
        total_return = np.exp(asset_returns.sum()) - 1.0
        ann_return = np.exp(asset_returns.mean() * 252.0) - 1.0
        volatility = asset_returns.std() * np.sqrt(252.0)
        sharpe = (ann_return - 0.05) / volatility if volatility > 0 else np.nan
        
        portfolio_data.append({
            'Stock': asset,
            'Weight': weights[asset],
            'Annual Return (%)': ann_return * 100,
            'Annual Risk (%)': volatility * 100,
            'Sharpe Ratio': sharpe,
            'Weight × Annual Return': weights[asset] * ann_return * 100,
        })
    
    # Create DataFrame
    df = pd.DataFrame(portfolio_data)
    
    # Calculate portfolio-level diversification metrics
    df = df.sort_values('Weight', ascending=False).reset_index(drop=True)
    
    # Calculate diversification ratio (sum of weights / portfolio volatility)
    port_vol = portfolio_metrics['Volatility']
    div_ratio = df['Weight'].sum() / port_vol if port_vol > 0 else np.nan
    
    # Create summary section
    summary_data = {
        'Metric': [
            'Total Number of Stocks',
            'Portfolio Size (Stock Count)',
            'Total Exposure',
            'Portfolio Annual Return (%)',
            'Portfolio Annual Risk (%)',
            'Portfolio Sharpe Ratio',
            'Diversification Ratio',
            'Top 3 Stock Exposure (%)',
            'HHI (Herfindahl Index)',
            'Max Weight (%)',
            'Min Weight (%)',
            'Average Weight (%)',
        ],
        'Value': [
            len(df),
            len(df),
            f"{df['Weight'].sum():.4f}",
            f"{portfolio_metrics['Annualized Return'] * 100:.4f}",
            f"{portfolio_metrics['Volatility'] * 100:.4f}",
            f"{portfolio_metrics['Sharpe Ratio']:.4f}",
            f"{div_ratio:.4f}",
            f"{df['Weight'].head(3).sum() * 100:.4f}",
            f"{(df['Weight'] ** 2).sum():.4f}",
            f"{df['Weight'].max() * 100:.4f}",
            f"{df['Weight'].min() * 100:.4f}",
            f"{df['Weight'].mean() * 100:.4f}",
        ]
    }
    
    return df, pd.DataFrame(summary_data)

# Create Classical portfolio CSV
print("\n[STEP 4] Creating Classical Portfolio CSV...")
classical_df, classical_summary = create_portfolio_csv(
    classical_w, test_r, "Classical", classical_metrics
)

classical_csv = output_dir / "Portfolio_Classical_Stocks.csv"
classical_df.to_csv(classical_csv, index=False)
print(f"  ✓ Saved: {classical_csv.name}")

# Create Quantum portfolio CSV
print("\n[STEP 5] Creating Quantum Portfolio CSV...")
quantum_df, quantum_summary = create_portfolio_csv(
    quantum_w, test_r, "Quantum", quantum_metrics
)

quantum_csv = output_dir / "Portfolio_Quantum_Stocks.csv"
quantum_df.to_csv(quantum_csv, index=False)
print(f"  ✓ Saved: {quantum_csv.name}")

# Save summaries
print("\n[STEP 6] Creating summary files...")

classical_summary_csv = output_dir / "Portfolio_Classical_Summary.csv"
classical_summary.to_csv(classical_summary_csv, index=False)
print(f"  ✓ Saved: {classical_summary_csv.name}")

quantum_summary_csv = output_dir / "Portfolio_Quantum_Summary.csv"
quantum_summary.to_csv(quantum_summary_csv, index=False)
print(f"  ✓ Saved: {quantum_summary_csv.name}")

# Print summaries
print("\n[CLASSICAL PORTFOLIO SUMMARY]")
print(classical_summary.to_string(index=False))

print("\n[QUANTUM PORTFOLIO SUMMARY]")
print(quantum_summary.to_string(index=False))

print("\n[CLASSICAL PORTFOLIO - TOP 10 STOCKS]")
print(classical_df.head(10).to_string(index=False))

print("\n[QUANTUM PORTFOLIO - TOP 10 STOCKS]")
print(quantum_df.head(10).to_string(index=False))

print("\n" + "="*80)
print("✅ PORTFOLIO CSVs GENERATED SUCCESSFULLY")
print("="*80)
print(f"\nFiles created in: {output_dir}")
print(f"  - Portfolio_Classical_Stocks.csv")
print(f"  - Portfolio_Quantum_Stocks.csv")
print(f"  - Portfolio_Classical_Summary.csv")
print(f"  - Portfolio_Quantum_Summary.csv")
print("\n")
