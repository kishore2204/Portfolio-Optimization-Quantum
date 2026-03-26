"""
Portfolio Value Analysis - Snake Graphs & Train/Test Splits
Generates monthly and yearly portfolio value comparisons with NIFTY 50
"""

import pandas as pd
import numpy as np
import os
import json
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.dates import DateFormatter, MonthLocator

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['font.size'] = 10

def load_nifty_data():
    """Load NIFTY 50 data with custom date parser"""
    def parse_nifty_date(date_str):
        try:
            # Parse format: 'Tue Jul 03 1990 00:00:00 GMT+0530 (India Standard Time)'
            parts = date_str.split()
            day = int(parts[1])
            month_str = parts[2]
            year = int(parts[3])
            months = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                     'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
            month = months.get(month_str, 1)
            return pd.Timestamp(year=year, month=month, day=day)
        except:
            return pd.NaT
    
    nifty_file = 'Dataset/NIFTY 50.csv.xls'
    if os.path.exists(nifty_file):
        nifty_df = pd.read_csv(nifty_file)
        nifty_df['Date'] = nifty_df['Date'].apply(parse_nifty_date)
        nifty_df = nifty_df.dropna(subset=['Date'])
        nifty_df['Date'] = pd.to_datetime(nifty_df['Date'])
        nifty_df = nifty_df.sort_values('Date')
        nifty_df.set_index('Date', inplace=True)
        return nifty_df
    return None

def calculate_portfolio_values(returns_df):
    """Calculate portfolio value from daily returns (starting with $100,000)"""
    portfolio_values = {}
    initial_investment = 100000
    
    for strategy in returns_df.columns:
        values = [initial_investment]
        for ret in returns_df[strategy]:
            values.append(values[-1] * (1 + ret))
        portfolio_values[strategy] = np.array(values[:-1])  # Remove last value
    
    return portfolio_values

def calculate_nifty_values(nifty_df, returns_df_dates):
    """Calculate NIFTY 50 portfolio value aligned with strategy dates"""
    # Filter NIFTY to match strategy dates
    nifty_filtered = nifty_df.loc[nifty_df.index.intersection(returns_df_dates)]
    
    if 'Close' in nifty_filtered.columns:
        # Calculate daily returns from NIFTY Close prices
        nifty_returns = nifty_filtered['Close'].pct_change().fillna(0)
        
        initial_investment = 100000
        values = [initial_investment]
        for ret in nifty_returns:
            values.append(values[-1] * (1 + ret))
        
        return nifty_returns, np.array(values[:-1])
    return None, None

def generate_monthly_annual_graphs(returns_df, nifty_df, end_date):
    """Generate monthly and annual value comparison graphs"""
    
    # Calculate portfolio values
    portfolio_values = calculate_portfolio_values(returns_df)
    nifty_returns, nifty_values = calculate_nifty_values(nifty_df, returns_df.index)
    
    # Create two figures: Monthly and Annual
    fig1, axes1 = plt.subplots(2, 2, figsize=(16, 10))
    fig1.suptitle('Portfolio Value Analysis - MONTHLY COMPARISON', fontsize=14, fontweight='bold')
    
    fig2, axes2 = plt.subplots(2, 2, figsize=(16, 10))
    fig2.suptitle('Portfolio Value Analysis - ANNUAL COMPARISON', fontsize=14, fontweight='bold')
    
    strategies = ['classical', 'quantum', 'quantum_rebalanced']
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    
    # ===== MONTHLY ANALYSIS =====
    monthly_data = {}
    for strategy, values in portfolio_values.items():
        monthly_df = pd.DataFrame({
            'Date': returns_df.index,
            'Value': values
        })
        monthly_df['YearMonth'] = monthly_df['Date'].dt.to_period('M')
        monthly_agg = monthly_df.groupby('YearMonth')['Value'].apply(lambda x: x.iloc[-1])
        monthly_data[strategy] = monthly_agg
    
    # Add NIFTY monthly (only if data is available and aligned)
    if nifty_values is not None and len(nifty_values) == len(returns_df):
        monthly_df_nifty = pd.DataFrame({
            'Date': returns_df.index,
            'Value': nifty_values
        })
        monthly_df_nifty['YearMonth'] = monthly_df_nifty['Date'].dt.to_period('M')
        monthly_agg_nifty = monthly_df_nifty.groupby('YearMonth')['Value'].apply(lambda x: x.iloc[-1])
        monthly_data['NIFTY 50'] = monthly_agg_nifty
    
    # Plot 1: Monthly Portfolio Values (Snake Graph)
    ax = axes1[0, 0]
    for strategy in strategies:
        if strategy in monthly_data:
            ax.plot(range(len(monthly_data[strategy])), monthly_data[strategy].values, 
                   marker='o', label=strategy, linewidth=2, markersize=4)
    if 'NIFTY 50' in monthly_data:
        ax.plot(range(len(monthly_data['NIFTY 50'])), monthly_data['NIFTY 50'].values, 
               marker='s', label='NIFTY 50', linewidth=2, markersize=4, linestyle='--')
    ax.set_title('Monthly Portfolio Values (Snake Graph)', fontweight='bold')
    ax.set_xlabel('Month')
    ax.set_ylabel('Portfolio Value ($)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Plot 2: Monthly Returns Comparison
    ax = axes1[0, 1]
    for strategy in strategies:
        if strategy in monthly_data:
            monthly_ret = monthly_data[strategy].pct_change() * 100
            ax.plot(range(len(monthly_ret)), monthly_ret.values, marker='o', label=strategy, linewidth=2)
    if 'NIFTY 50' in monthly_data:
        monthly_ret_nifty = monthly_data['NIFTY 50'].pct_change() * 100
        ax.plot(range(len(monthly_ret_nifty)), monthly_ret_nifty.values, marker='s', 
               label='NIFTY 50', linewidth=2, linestyle='--')
    ax.set_title('Monthly Returns Comparison (%)', fontweight='bold')
    ax.set_xlabel('Month')
    ax.set_ylabel('Return (%)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    
    # Plot 3: Monthly Cumulative Returns
    ax = axes1[1, 0]
    for strategy in strategies:
        if strategy in monthly_data:
            cum_ret = ((monthly_data[strategy] / monthly_data[strategy].iloc[0]) - 1) * 100
            ax.plot(range(len(cum_ret)), cum_ret.values, marker='o', label=strategy, linewidth=2)
    if 'NIFTY 50' in monthly_data:
        cum_ret_nifty = ((monthly_data['NIFTY 50'] / monthly_data['NIFTY 50'].iloc[0]) - 1) * 100
        ax.plot(range(len(cum_ret_nifty)), cum_ret_nifty.values, marker='s', 
               label='NIFTY 50', linewidth=2, linestyle='--')
    ax.set_title('Monthly Cumulative Returns (%)', fontweight='bold')
    ax.set_xlabel('Month')
    ax.set_ylabel('Cumulative Return (%)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Plot 4: Monthly Value Distribution (Box Plot)
    ax = axes1[1, 1]
    monthly_values_list = [monthly_data[s].values for s in strategies]
    if 'NIFTY 50' in monthly_data:
        monthly_values_list.append(monthly_data['NIFTY 50'].values)
        labels = strategies + ['NIFTY 50']
    else:
        labels = strategies
    bp = ax.boxplot(monthly_values_list, labels=labels, patch_artist=True)
    for patch, color in zip(bp['boxes'], colors + ['red']):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    ax.set_title('Monthly Value Distribution', fontweight='bold')
    ax.set_ylabel('Portfolio Value ($)')
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig('results/monthly_portfolio_analysis.png', dpi=300, bbox_inches='tight')
    print("Saved: results/monthly_portfolio_analysis.png")
    plt.close(fig1)
    
    # ===== ANNUAL ANALYSIS =====
    annual_data = {}
    for strategy, values in portfolio_values.items():
        annual_df = pd.DataFrame({
            'Date': returns_df.index,
            'Value': values
        })
        annual_df['Year'] = annual_df['Date'].dt.year
        annual_agg = annual_df.groupby('Year')['Value'].apply(lambda x: x.iloc[-1])
        annual_data[strategy] = annual_agg
    
    # Add NIFTY annual (only if data is available and aligned)
    if nifty_values is not None and len(nifty_values) == len(returns_df):
        annual_df_nifty = pd.DataFrame({
            'Date': returns_df.index,
            'Value': nifty_values
        })
        annual_df_nifty['Year'] = annual_df_nifty['Date'].dt.year
        annual_agg_nifty = annual_df_nifty.groupby('Year')['Value'].apply(lambda x: x.iloc[-1])
        annual_data['NIFTY 50'] = annual_agg_nifty
    
    # Plot 1: Annual Portfolio Values (Snake Graph)
    ax = axes2[0, 0]
    for strategy in strategies:
        if strategy in annual_data:
            ax.plot(annual_data[strategy].index, annual_data[strategy].values, 
                   marker='o', label=strategy, linewidth=2.5, markersize=8)
    if 'NIFTY 50' in annual_data:
        ax.plot(annual_data['NIFTY 50'].index, annual_data['NIFTY 50'].values, 
               marker='s', label='NIFTY 50', linewidth=2.5, markersize=8, linestyle='--')
    ax.set_title('Annual Portfolio Values (Snake Graph)', fontweight='bold')
    ax.set_xlabel('Year')
    ax.set_ylabel('Portfolio Value ($)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Plot 2: Annual Returns Comparison
    ax = axes2[0, 1]
    for strategy in strategies:
        if strategy in annual_data:
            annual_ret = annual_data[strategy].pct_change() * 100
            ax.bar(annual_ret.index - 0.15, annual_ret.values, width=0.15, label=strategy, alpha=0.8)
    if 'NIFTY 50' in annual_data:
        annual_ret_nifty = annual_data['NIFTY 50'].pct_change() * 100
        ax.bar(annual_ret_nifty.index + 0.15, annual_ret_nifty.values, width=0.15, 
              label='NIFTY 50', alpha=0.8)
    ax.set_title('Annual Returns Comparison (%)', fontweight='bold')
    ax.set_xlabel('Year')
    ax.set_ylabel('Return (%)')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    
    # Plot 3: Annual Cumulative Returns
    ax = axes2[1, 0]
    for strategy in strategies:
        if strategy in annual_data:
            cum_ret = ((annual_data[strategy] / annual_data[strategy].iloc[0]) - 1) * 100
            ax.plot(cum_ret.index, cum_ret.values, marker='o', label=strategy, linewidth=2.5, markersize=8)
    if 'NIFTY 50' in annual_data:
        cum_ret_nifty = ((annual_data['NIFTY 50'] / annual_data['NIFTY 50'].iloc[0]) - 1) * 100
        ax.plot(cum_ret_nifty.index, cum_ret_nifty.values, marker='s', 
               label='NIFTY 50', linewidth=2.5, markersize=8, linestyle='--')
    ax.set_title('Annual Cumulative Returns (%)', fontweight='bold')
    ax.set_xlabel('Year')
    ax.set_ylabel('Cumulative Return (%)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Plot 4: Year-over-Year Comparison (Bar Chart)
    ax = axes2[1, 1]
    years = annual_data[strategies[0]].index
    x = np.arange(len(years))
    width = 0.2
    for i, strategy in enumerate(strategies):
        if strategy in annual_data:
            ax.bar(x + i*width, annual_data[strategy].values, width, label=strategy, alpha=0.8)
    if 'NIFTY 50' in annual_data:
        ax.bar(x + len(strategies)*width, annual_data['NIFTY 50'].values, width, 
              label='NIFTY 50', alpha=0.8)
    ax.set_title('Year-over-Year Portfolio Values', fontweight='bold')
    ax.set_xlabel('Year')
    ax.set_ylabel('Portfolio Value ($)')
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels(years)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig('results/annual_portfolio_analysis.png', dpi=300, bbox_inches='tight')
    print("Saved: results/annual_portfolio_analysis.png")
    plt.close(fig2)
    
    return monthly_data, annual_data

def analyze_train_test_splits(returns_df, nifty_df, end_date):
    """Analyze train/test splits for 1Y, 5Y, 10Y horizons"""
    
    results = {}
    nifty_returns, _ = calculate_nifty_values(nifty_df, returns_df.index)
    
    horizons = {
        '10Y': (365*10, 365*2),  # 10Y data, 2Y test
        '5Y': (365*5, 365*1),     # 5Y data, 1Y test
        '1Y': (365*1, 252*0.25)   # 1Y data, 3M test
    }
    
    strategies = ['classical', 'quantum', 'quantum_rebalanced']
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    
    fig, axes = plt.subplots(3, 3, figsize=(18, 12))
    fig.suptitle('Train/Test Split Analysis - Portfolio Performance', fontsize=14, fontweight='bold')
    
    for idx, (horizon_name, (train_days, test_days)) in enumerate(horizons.items()):
        test_days = int(test_days)
        train_days = int(train_days)
        
        # Define train/test split
        test_start_idx = max(0, len(returns_df) - test_days)
        train_end_idx = test_start_idx
        
        train_returns = returns_df.iloc[:train_end_idx]
        test_returns = returns_df.iloc[train_end_idx:]
        
        # Calculate portfolio values for train/test
        train_vals = calculate_portfolio_values(train_returns)
        test_vals = calculate_portfolio_values(test_returns)
        
        # Calculate metrics
        split_data = {
            'horizon': horizon_name,
            'train_period': f"{train_returns.index[0].date()} to {train_returns.index[-1].date()}",
            'test_period': f"{test_returns.index[0].date()} to {test_returns.index[-1].date()}",
            'train_days': len(train_returns),
            'test_days': len(test_returns),
            'train_metrics': {},
            'test_metrics': {}
        }
        
        # Calculate train metrics
        for strategy in strategies:
            if strategy in train_vals:
                train_ret = (train_vals[strategy][-1] - train_vals[strategy][0]) / train_vals[strategy][0] * 100
                train_annual = train_ret / (len(train_returns) / 252)
                split_data['train_metrics'][strategy] = {
                    'total_return': round(train_ret, 2),
                    'annual_return': round(train_annual, 2)
                }
        
        # Calculate test metrics
        for strategy in strategies:
            if strategy in test_vals:
                test_ret = (test_vals[strategy][-1] - test_vals[strategy][0]) / test_vals[strategy][0] * 100
                test_annual = test_ret / (len(test_returns) / 252) if len(test_returns) > 0 else 0
                split_data['test_metrics'][strategy] = {
                    'total_return': round(test_ret, 2),
                    'annual_return': round(test_annual, 2)
                }
        
        results[horizon_name] = split_data
        
        # Plots
        # Plot 1: Train vs Test Cumulative Returns
        ax = axes[idx, 0]
        for strategy in strategies:
            if strategy in train_vals:
                ax.plot(range(len(train_vals[strategy])), train_vals[strategy], 
                       label=f'{strategy} (Train)', linewidth=2, color=colors[strategies.index(strategy)])
        for strategy in strategies:
            if strategy in test_vals:
                ax.plot(range(len(train_vals[strategies[0]]), len(train_vals[strategies[0]]) + len(test_vals[strategy])), 
                       test_vals[strategy], label=f'{strategy} (Test)', linewidth=2, 
                       color=colors[strategies.index(strategy)], linestyle='--')
        ax.axvline(x=len(train_vals[strategies[0]]), color='red', linestyle=':', linewidth=2, label='Train/Test Split')
        ax.set_title(f'{horizon_name} - Train/Test Portfolio Values', fontweight='bold')
        ax.set_xlabel('Days')
        ax.set_ylabel('Portfolio Value ($)')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        
        # Plot 2: Train/Test Return Comparison
        ax = axes[idx, 1]
        train_returns_list = [split_data['train_metrics'][s]['total_return'] for s in strategies]
        test_returns_list = [split_data['test_metrics'][s]['total_return'] for s in strategies]
        x = np.arange(len(strategies))
        width = 0.35
        ax.bar(x - width/2, train_returns_list, width, label='Train', alpha=0.8)
        ax.bar(x + width/2, test_returns_list, width, label='Test', alpha=0.8)
        ax.set_title(f'{horizon_name} - Total Return Comparison', fontweight='bold')
        ax.set_ylabel('Return (%)')
        ax.set_xticks(x)
        ax.set_xticklabels(strategies, rotation=15)
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        
        # Plot 3: Train/Test Annual Return
        ax = axes[idx, 2]
        train_annual_list = [split_data['train_metrics'][s]['annual_return'] for s in strategies]
        test_annual_list = [split_data['test_metrics'][s]['annual_return'] for s in strategies]
        x = np.arange(len(strategies))
        ax.bar(x - width/2, train_annual_list, width, label='Train Annualized', alpha=0.8)
        ax.bar(x + width/2, test_annual_list, width, label='Test Annualized', alpha=0.8)
        ax.set_title(f'{horizon_name} - Annualized Return', fontweight='bold')
        ax.set_ylabel('Annual Return (%)')
        ax.set_xticks(x)
        ax.set_xticklabels(strategies, rotation=15)
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig('results/train_test_split_analysis.png', dpi=300, bbox_inches='tight')
    print("Saved: results/train_test_split_analysis.png")
    plt.close(fig)
    
    return results

def compare_quantum_vs_nifty_horizons(returns_df, nifty_df, end_date):
    """Compare Quantum portfolio with NIFTY 50 across 1Y, 5Y, 10Y horizons"""
    
    nifty_returns, _ = calculate_nifty_values(nifty_df, returns_df.index)
    portfolio_values = calculate_portfolio_values(returns_df)
    
    horizons = {
        '10Y': end_date - timedelta(days=365*10),
        '5Y': end_date - timedelta(days=365*5),
        '1Y': end_date - timedelta(days=365*1)
    }
    
    comparison_data = {}
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle('Quantum Portfolio vs NIFTY 50 - Horizon Analysis', fontsize=14, fontweight='bold')
    
    strategies = ['classical', 'quantum', 'quantum_rebalanced']
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    
    for idx, (horizon_name, horizon_start) in enumerate(horizons.items()):
        # Filter data
        mask = (returns_df.index >= horizon_start) & (returns_df.index <= end_date)
        horizon_returns = returns_df[mask]
        
        if nifty_returns is not None:
            nifty_mask = nifty_returns.index.map(lambda x: horizon_start <= x <= end_date)
            horizon_nifty = nifty_returns[nifty_mask]
        
        # Calculate metrics
        comparison_data[horizon_name] = {}
        
        ax = axes[idx]
        
        for i, strategy in enumerate(strategies):
            if strategy in horizon_returns.columns:
                # Cumulative returns
                cum_ret = (1 + horizon_returns[strategy]).cumprod()
                ax.plot(cum_ret.index, cum_ret.values, label=strategy, linewidth=2.5, color=colors[i])
                
                # Metrics
                total_ret = (cum_ret.iloc[-1] - 1) * 100
                annual_ret = (cum_ret.iloc[-1] ** (252 / len(horizon_returns)) - 1) * 100
                
                comparison_data[horizon_name][strategy] = {
                    'total_return': round(total_ret, 2),
                    'annual_return': round(annual_ret, 2)
                }
        
        # Add NIFTY
        if nifty_returns is not None and len(horizon_nifty) > 0:
            nifty_cum = (1 + horizon_nifty).cumprod()
            ax.plot(nifty_cum.index, nifty_cum.values, label='NIFTY 50', 
                   linewidth=2.5, color='red', linestyle='--')
            
            nifty_total = (nifty_cum.iloc[-1] - 1) * 100
            nifty_annual = (nifty_cum.iloc[-1] ** (252 / len(horizon_nifty)) - 1) * 100
            comparison_data[horizon_name]['NIFTY 50'] = {
                'total_return': round(nifty_total, 2),
                'annual_return': round(nifty_annual, 2)
            }
        
        ax.set_title(f'{horizon_name} Horizon ({horizon_returns.index[0].date()} to {horizon_returns.index[-1].date()})', fontweight='bold')
        ax.set_xlabel('Date')
        ax.set_ylabel('Cumulative Value')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('results/quantum_vs_nifty_horizons.png', dpi=300, bbox_inches='tight')
    print("Saved: results/quantum_vs_nifty_horizons.png")
    plt.close(fig)
    
    return comparison_data

def main():
    # Load data
    returns_file = 'results/strategy_returns.csv'
    
    if not os.path.exists(returns_file):
        print(f"Error: {returns_file} not found")
        return
    
    # Load returns
    returns_df = pd.read_csv(returns_file, parse_dates=['Date'], index_col='Date')
    end_date = returns_df.index.max()
    start_date = returns_df.index.min()
    
    print(f"Dataset Range: {start_date.date()} to {end_date.date()}")
    print(f"Total Trading Days: {len(returns_df)}")
    
    # Load NIFTY data
    nifty_df = load_nifty_data()
    if nifty_df is None:
        print("Warning: NIFTY 50 data not found")
    else:
        print(f"NIFTY 50 Data Loaded: {len(nifty_df)} records")
    
    # Create output directory
    os.makedirs('results', exist_ok=True)
    
    print("\n=== Generating Monthly & Annual Portfolio Analysis ===")
    monthly_data, annual_data = generate_monthly_annual_graphs(returns_df, nifty_df, end_date)
    
    print("\n=== Analyzing Train/Test Splits ===")
    split_results = analyze_train_test_splits(returns_df, nifty_df, end_date)
    
    print("\n=== Comparing Quantum vs NIFTY 50 Across Horizons ===")
    comparison_results = compare_quantum_vs_nifty_horizons(returns_df, nifty_df, end_date)
    
    # Save all results to JSON
    summary = {
        'analysis_info': {
            'start_date': str(start_date.date()),
            'end_date': str(end_date.date()),
            'total_trading_days': len(returns_df)
        },
        'train_test_splits': split_results,
        'horizon_comparison': comparison_results
    }
    
    with open('results/portfolio_value_analysis_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print("\n=== Analysis Complete ===")
    print("Generated graphs:")
    print("  - results/monthly_portfolio_analysis.png")
    print("  - results/annual_portfolio_analysis.png")
    print("  - results/train_test_split_analysis.png")
    print("  - results/quantum_vs_nifty_horizons.png")
    print("  - results/portfolio_value_analysis_summary.json")
    
    # Print summary tables
    print("\n" + "="*100)
    print("TRAIN/TEST SPLIT RESULTS")
    print("="*100)
    for horizon, data in split_results.items():
        print(f"\n{horizon}:")
        print(f"  Train: {data['train_period']} ({data['train_days']} days)")
        print(f"  Test:  {data['test_period']} ({data['test_days']} days)")
        print(f"  {'Strategy':<20} {'Train Return %':<15} {'Test Return %':<15} {'Train Annual %':<15} {'Test Annual %':<15}")
        print(f"  {'-'*80}")
        for strategy in ['classical', 'quantum', 'quantum_rebalanced']:
            if strategy in data['train_metrics'] and strategy in data['test_metrics']:
                train_ret = data['train_metrics'][strategy]['total_return']
                test_ret = data['test_metrics'][strategy]['total_return']
                train_ann = data['train_metrics'][strategy]['annual_return']
                test_ann = data['test_metrics'][strategy]['annual_return']
                print(f"  {strategy:<20} {train_ret:>6.2f}% {test_ret:>11.2f}% {train_ann:>12.2f}% {test_ann:>12.2f}%")
    
    print("\n" + "="*100)
    print("QUANTUM vs NIFTY 50 HORIZON COMPARISON")
    print("="*100)
    for horizon, strategies in comparison_results.items():
        print(f"\n{horizon}:")
        print(f"  {'Strategy':<20} {'Total Return %':<20} {'Annual Return %':<20}")
        print(f"  {'-'*60}")
        for strategy, metrics in strategies.items():
            print(f"  {strategy:<20} {metrics['total_return']:>8.2f}% {metrics['annual_return']:>17.2f}%")

if __name__ == '__main__':
    main()
