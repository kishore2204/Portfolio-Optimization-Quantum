"""
Download HDFC Nifty 50 ETF data using yfinance
Tests multiple ticker variations for HDFC Nifty 50 ETF on Indian exchanges
"""

import yfinance as yf
import pandas as pd
from datetime import datetime
import os

# Create datasets folder if it doesn't exist
os.makedirs("datasets", exist_ok=True)

start_date = "2011-01-01"
end_date = datetime.now().strftime("%Y-%m-%d")

# List of possible ticker variations for HDFC Nifty 50 ETF
tickers_to_try = [
    "HDFCNIFTY50.NS",
    "HDFCNIFTY50.BO",
    "HDFC50.NS",
    "HDFCETF50.NS",
    "HDFCNIFTY50ETF.NS",
    "0P000167VV.IN",  # ISIN approach
    "NIFTYHDFCETF.NS",
    "HDFCNIF50.NS",
]

print("HDFC Nifty 50 ETF Data Downloader")
print("=" * 50)
print(f"Attempting to download from {start_date} to {end_date}\n")

downloaded = False

for ticker in tickers_to_try:
    try:
        print(f"Attempting: {ticker}...", end=" ")
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        
        if not data.empty and len(data) > 0:
            output_file = "datasets/HDFC_Nifty50_ETF_2011_to_2026.csv"
            data.to_csv(output_file)
            print("✓ SUCCESS")
            print(f"\nData saved to {output_file}")
            print(f"Shape: {data.shape}")
            print(f"Date range: {data.index[0].date()} to {data.index[-1].date()}")
            print(f"\nFirst few rows:\n{data.head()}")
            print(f"\nLast few rows:\n{data.tail()}")
            downloaded = True
            break
        else:
            print("✗ No data")
            
    except Exception as e:
        print(f"✗ Error: {str(e)[:40]}...")

if not downloaded:
    print("\n" + "=" * 50)
    print("UNABLE TO DOWNLOAD - POSSIBLE SOLUTIONS:")
    print("=" * 50)
    print("\n1. The HDFC Nifty 50 ETF may not have a public yfinance ticker")
    print("2. Check the exact ticker on NSE (National Stock Exchange India)")
    print("3. Alternative: Download from NSE website directly")
    print("\n4. Common HDFC ETF tickers to research:")
    print("   - Search 'HDFC Nifty ETF' on NSE website")
    print("   - Try searching on yfinance.Ticker() for available symbols")
    print("\nTo manually check available symbols:")
    print("   import yfinance as yf")
    print("   yf.Ticker('HDFC').info  # Try this with correct ticker")
