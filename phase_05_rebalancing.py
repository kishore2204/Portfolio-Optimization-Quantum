"""
Quarterly Rebalancing with Underperformer Removal (Paper's Methodology)
=======================================================================
- Rebalance every 3 months (quarterly)
- Identify bottom K_sell stocks by expected return
- Remove underperformers
- Replace with sector-matched candidates
- Re-optimize portfolio weights

Reference: Morapakula et al. (2025) - Algorithm 1

Author: Enhanced Portfolio System
Date: March 2026
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class QuarterlyRebalancer:
    """Implements paper's quarterly rebalancing with underperformer removal"""
    
    def __init__(self, config_path='config/config.json'):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.K_sell = self.config['rebalancing']['K_sell']  # Number of stocks to replace
        self.transaction_cost_pct = self.config['rebalancing']['transaction_cost_pct']
        self.trading_days_per_year = self.config['data']['trading_days_per_year']
        
        # Load sector mappings
        with open('config/nifty100_sectors.json', 'r') as f:
            self.sector_map = json.load(f)
    
    def get_rebalance_dates(self, start_date, end_date):
        """
        Generate quarterly rebalance dates (end of each quarter)
        Quarters end: Mar 31, Jun 30, Sep 30, Dec 31
        """
        dates = []
        current = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        # Find next quarter-end
        quarter_ends = []
        year = current.year
        while True:
            for month in [3, 6, 9, 12]:
                if month == 3:
                    day = 31
                elif month == 6:
                    day = 30
                elif month == 9:
                    day = 30
                else:  # December
                    day = 31
                
                quarter_end = pd.Timestamp(year=year, month=month, day=day)
                if quarter_end >= current and quarter_end <= end:
                    quarter_ends.append(quarter_end)
            
            year += 1
            if pd.Timestamp(year=year, month=1, day=1) > end:
                break
        
        return quarter_ends
    
    def compute_quarterly_returns(self, prices_df, stocks):
        """
        Compute annualized returns for each stock over the quarter
        
        Uses rolling window of last ~63 trading days (quarter)
        """
        quarterly_window = min(63, len(prices_df))  # ~3 months of trading days
        
        # Get recent prices
        recent_prices = prices_df[stocks].tail(quarterly_window)
        
        # Compute log returns
        log_returns = np.log(recent_prices / recent_prices.shift(1)).dropna()
        
        # Annualize mean returns
        mean_daily_returns = log_returns.mean()
        mean_annual_returns = mean_daily_returns * self.trading_days_per_year
        
        return mean_annual_returns
    
    def identify_underperformers(self, current_holdings, quarterly_returns):
        """
        Identify bottom K_sell stocks by quarterly return performance
        
        Paper's method: Rank current holdings by μ(k), mark lowest as underperformers
        """
        # Get returns for current holdings only
        holdings_returns = quarterly_returns[current_holdings].sort_values()
        
        # Bottom K_sell stocks
        underperformers = holdings_returns.head(self.K_sell).index.tolist()
        
        print(f"\n  [UNDERPERFORMER IDENTIFICATION]")
        print(f"  Bottom {self.K_sell} stocks by quarterly return:")
        for i, stock in enumerate(underperformers, 1):
            ret = holdings_returns[stock]
            print(f"    {i}. {stock:15s}: {ret*100:>6.2f}% annual return")
        
        return underperformers
    
    def get_sector_matched_candidates(self, underperformers, universe, current_holdings):
        """
        Get replacement candidates from same sectors as sold stocks
        
        Paper's method: Collect replacements from same sectors as sold names
        """
        # Build reverse sector map (stock -> sector)
        stock_to_sector = {}
        sector_source = self.sector_map
        if isinstance(sector_source, dict) and 'NIFTY_100_STOCKS' in sector_source:
            sector_source = sector_source['NIFTY_100_STOCKS']

        for sector, stocks in sector_source.items():
            for stock in stocks:
                stock_to_sector[stock] = sector
        
        # Get sectors of underperformers
        underperformer_sectors = []
        for stock in underperformers:
            sector = stock_to_sector.get(stock, 'Others')
            underperformer_sectors.append(sector)
        
        print(f"\n  [SECTOR-MATCHED REPLACEMENT]")
        print(f"  Looking for candidates in sectors: {set(underperformer_sectors)}")
        
        # Find candidates from same sectors
        candidates = []
        for sector in underperformer_sectors:
            # Get all stocks in this sector
            sector_stocks = sector_source.get(sector, [])
            
            # Filter to universe and exclude current holdings
            available = [s for s in sector_stocks 
                        if s in universe and s not in current_holdings]
            
            candidates.extend(available)
        
        # Remove duplicates
        candidates = list(set(candidates))
        
        print(f"  Found {len(candidates)} sector-matched candidates")
        
        return candidates, stock_to_sector
    
    def rebalance_portfolio(self, current_holdings, prices_df, universe_data, 
                           rebalance_date, rebalance_number):
        """
        Execute quarterly rebalancing:
        1. Compute quarterly returns
        2. Identify underperformers
        3. Get sector-matched candidates
        4. Run quantum selection on candidates
        5. Re-optimize weights
        
        Returns:
            new_holdings: Updated stock list
            trades: Dict of trades executed
            cost: Total transaction cost
        """
        
        print(f"\n{'='*80}")
        print(f"QUARTERLY REBALANCE #{rebalance_number} - {rebalance_date.date()}")
        print(f"{'='*80}")
        
        # Get data up to rebalance date
        historical_data = prices_df[prices_df.index <= rebalance_date]
        
        # Compute quarterly returns for all universe stocks
        quarterly_returns = self.compute_quarterly_returns(historical_data, universe_data['stocks'])
        
        # Step 1: Identify underperformers in current holdings
        underperformers = self.identify_underperformers(current_holdings, quarterly_returns)
        
        # Step 2: Remove underperformers
        remaining_holdings = [s for s in current_holdings if s not in underperformers]
        
        print(f"\n  Remaining holdings after removal: {len(remaining_holdings)}")
        
        # Step 3: Get sector-matched candidates
        candidates, stock_to_sector = self.get_sector_matched_candidates(
            underperformers, universe_data['stocks'], remaining_holdings
        )
        
        if len(candidates) < self.K_sell:
            print(f"  [WARNING] Only {len(candidates)} candidates available, using all")
            # If not enough candidates, keep some underperformers
            need_more = self.K_sell - len(candidates)
            keep_best = sorted(underperformers, 
                             key=lambda s: quarterly_returns[s], 
                             reverse=True)[:need_more]
            remaining_holdings.extend(keep_best)
            candidates = [s for s in candidates if s not in remaining_holdings]
        
        # Step 4: Run quantum selection on candidates (simplified - top K_sell by Sharpe)
        # In full implementation, this would re-run QUBO optimization
        # For now, select top K_sell by Sharpe ratio from candidates
        
        candidate_sharpe = {}
        for stock in candidates:
            if stock in universe_data['stocks']:
                idx = universe_data['stocks'].index(stock)
                candidate_sharpe[stock] = universe_data['sharpe_ratios'][idx]
        
        # Select top K_sell
        sorted_candidates = sorted(candidate_sharpe.items(), key=lambda x: -x[1])
        new_stocks = [stock for stock, _ in sorted_candidates[:self.K_sell]]
        
        print(f"\n  [NEW STOCK SELECTION]")
        print(f"  Selected {len(new_stocks)} new stocks:")
        for i, stock in enumerate(new_stocks, 1):
            sharpe = candidate_sharpe[stock]
            sector = stock_to_sector.get(stock, 'Others')
            print(f"    {i}. {stock:15s} (Sharpe: {sharpe:.3f}, Sector: {sector})")
        
        # Updated holdings
        new_holdings = remaining_holdings + new_stocks
        
        # Calculate transaction costs
        trades = {
            'sold': underperformers,
            'bought': new_stocks
        }
        
        # Estimate transaction cost (simplified - assume average position value)
        num_trades = len(underperformers) + len(new_stocks)
        total_cost = num_trades * self.transaction_cost_pct  # As fraction of portfolio
        
        print(f"\n  [TRANSACTION SUMMARY]")
        print(f"  Stocks sold: {len(underperformers)}")
        print(f"  Stocks bought: {len(new_stocks)}")
        print(f"  Total trades: {num_trades}")
        print(f"  Transaction cost: {total_cost*100:.3f}% of portfolio value")
        
        return new_holdings, trades, total_cost
    
    def execute_rebalancing_strategy(self, initial_holdings, prices_df, universe_data, 
                                     start_date, end_date):
        """
        Execute full quarterly rebalancing strategy over test period
        
        Returns:
            rebalancing_record: List of all rebalancing events
            final_holdings: Portfolio composition at end
        """
        
        print(f"\n{'='*80}")
        print("QUARTERLY REBALANCING STRATEGY")
        print(f"{'='*80}")
        print(f"Period: {start_date} to {end_date}")
        print(f"Initial holdings: {len(initial_holdings)} stocks")
        print(f"Rebalancing frequency: Quarterly")
        print(f"Stocks to replace each quarter: {self.K_sell}")
        
        # Get rebalance dates
        rebalance_dates = self.get_rebalance_dates(start_date, end_date)
        
        print(f"\nScheduled rebalances: {len(rebalance_dates)}")
        for i, date in enumerate(rebalance_dates, 1):
            print(f"  {i}. {date.date()}")
        
        # Track rebalancing history
        rebalancing_record = []
        current_holdings = initial_holdings.copy()
        cumulative_cost = 0.0
        
        # Execute rebalancing at each date
        for i, rebalance_date in enumerate(rebalance_dates, 1):
            # Find closest trading date in prices_df
            closest_date = prices_df.index[prices_df.index <= rebalance_date][-1]
            
            # Rebalance
            new_holdings, trades, cost = self.rebalance_portfolio(
                current_holdings, prices_df, universe_data, 
                closest_date, i
            )
            
            # Record
            rebalancing_record.append({
                'date': str(closest_date),
                'rebalance_number': i,
                'holdings_before': current_holdings.copy(),
                'holdings_after': new_holdings.copy(),
                'stocks_sold': trades['sold'],
                'stocks_bought': trades['bought'],
                'transaction_cost': cost,
                'num_trades': len(trades['sold']) + len(trades['bought'])
            })
            
            # Update holdings
            current_holdings = new_holdings
            cumulative_cost += cost
        
        print(f"\n{'='*80}")
        print(f"REBALANCING COMPLETE")
        print(f"{'='*80}")
        print(f"Total rebalancing events: {len(rebalancing_record)}")
        print(f"Cumulative transaction cost: {cumulative_cost*100:.2f}% of portfolio")
        print(f"Final portfolio: {len(current_holdings)} stocks")
        
        return rebalancing_record, current_holdings


if __name__ == "__main__":
    # Test quarterly rebalancer
    rebalancer = QuarterlyRebalancer()
    
    # Load test data
    test_df = pd.read_csv('data/test_data.csv', parse_dates=['Date'], index_col='Date')
    
    with open('data/universe_metadata.json', 'r') as f:
        universe_data = json.load(f)
    
    # Get initial holdings
    initial_holdings = universe_data['stocks'][:12]  # Simulated initial portfolio
    
    # Get rebalance dates
    dates = rebalancer.get_rebalance_dates('2023-01-01', '2026-03-11')
    print(f"\nQuarterly rebalance dates ({len(dates)} total):")
    for date in dates:
        print(f"  - {date.date()}")
