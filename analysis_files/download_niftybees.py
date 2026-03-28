"""
Download Nifty Bees ETF (Alternative to HDFC Nifty 50)
NIFTYBEES is a liquid ETF that tracks the Nifty 50 Index
"""

import yfinance as yf
import pandas as pd
from datetime import datetime
import os

os.makedirs("datasets", exist_ok=True)

print("Nifty Bees ETF Data Downloader")
print("=" * 70)
print("NIFTYBEES: An ETF that tracks Nifty 50 Index")
print("-" * 70)

try:
    start_date = "2011-01-01"
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    print(f"Downloading NIFTYBEES.NS from {start_date} to {end_date}...")
    
    data = yf.download("NIFTYBEES.NS", 
                      start=start_date, 
                      end=end_date,
                      progress=True)
    
    if data is not None and len(data) > 0:
        output_file = "datasets/NIFTYBEES_2011_to_2026.csv"
        data.to_csv(output_file)
        
        print("\n" + "=" * 70)
        print("✓ DOWNLOAD SUCCESSFUL")
        print("=" * 70)
        print(f"File: {output_file}")
        print(f"Rows: {len(data)}")
        print(f"Columns: {', '.join(data.columns.tolist())}")
        print(f"Date range: {data.index[0].date()} to {data.index[-1].date()}")
        print(f"\nFirst 5 rows:")
        print(data.head())
        print(f"\nLast 5 rows:")
        print(data.tail())
        print(f"\nBasic Statistics:")
        print(data['Close'].describe())
        
        # Calculate returns
        data['Daily_Return'] = data['Close'].pct_change()
        print(f"\nDaily return statistics:")
        print(data['Daily_Return'].describe())
        
    else:
        print("✗ No data retrieved")
        
except Exception as e:
    print(f"✗ Error: {e}")

print("\n" + "=" * 70)
print("ABOUT NIFTYBEES:")
print("=" * 70)
print("""
• Official name: Nippon India ETF Nifty 50
• Ticker: NIFTYBEES.NS (NSE symbol)
• Index tracked: Nifty 50 (Top 50 companies in India)
• Type: Open-ended ETF
• Highly liquid and widely traded
• Lower fees compared to mutual funds
• Perfect replacement for HDFC Nifty 50 tracking

Use this data for your portfolio optimization analysis.
""")
