"""
Download HDFC Nifty 50 ETF data using nsepy (NSE India)
nsepy has better support for Indian market instruments
"""

import nsepy
from datetime import datetime
import pandas as pd
import os

# Create datasets folder if it doesn't exist
os.makedirs("datasets", exist_ok=True)

print("HDFC Nifty 50 ETF Data Downloader (using NSEPy)")
print("=" * 60)

# Common HDFC ETF symbols on NSE
symbols_to_try = [
    "HDFC50",
    "HDFCNIFTY50", 
    "HDFCNIFTYBEES",
    "HDFCETF",
    "HDFCNIF50",
]

start_date = datetime(2011, 1, 1)
end_date = datetime.now()

downloaded = False

for symbol in symbols_to_try:
    try:
        print(f"\nAttempting: {symbol}...", end=" ")
        
        # NSEPy download
        data = nsepy.get_data(symbol, 
                              start=start_date, 
                              end=end_date)
        
        if data is not None and not data.empty and len(data) > 10:
            output_file = "datasets/HDFC_Nifty50_ETF_2011_to_2026.csv"
            data.to_csv(output_file)
            print("✓ SUCCESS")
            print(f"Saved to: {output_file}")
            print(f"Data shape: {data.shape}")
            print(f"Date range: {data.index[0].date()} to {data.index[-1].date()}")
            print(f"\nFirst few rows:\n{data.head()}")
            downloaded = True
            break
        else:
            print("✗ No data")
            
    except Exception as e:
        error_msg = str(e)[:60]
        print(f"✗ Error: {error_msg}")

if not downloaded:
    print("\n" + "=" * 60)
    print("HDFC Nifty 50 ETF NOT FOUND")
    print("=" * 60)
    print("\nPossible reasons:")
    print("1. Ticker may have different symbol on NSE")
    print("2. ETF may be recently delisted or inactive")
    print("3. nsepy may have limited coverage of that symbol")
    print("\nAlternatives:")
    print("• Use NIFTYBEES.NS (popular Nifty 50 ETF) - works with yfinance")
    print("• Search NSE website for HDFC-specific ETF products")
    print("• Check ISIN code on NSE and use that as reference")
    print("\nTo find correct info:")
    print("  Visit: https://www.nseindia.com/products/etf")
    print("  Search for HDFC ETF products")
