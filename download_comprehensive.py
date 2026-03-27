"""
Download HDFC Nifty 50 ETF data - Multiple Methods
Method 1: NSEPy (correct syntax)
Method 2: yfinance fallback
"""

from datetime import datetime
import pandas as pd
import os

# Create datasets folder
os.makedirs("datasets", exist_ok=True)

print("HDFC Nifty 50 ETF Data Downloader")
print("=" * 70)

start_date = datetime(2011, 1, 1)
end_date = datetime.now()

# ============================================================================
# METHOD 1: Try NSEPy (National Stock Exchange data)
# ============================================================================
print("\nMETHOD 1: Using NSEPy (NSE India data)")
print("-" * 70)

try:
    from nsepy import get_history
    
    symbols_to_try = ["HDFC50", "HDFCNIFTY50", "HDFCNIFTYBEES", "HDFCETF"]
    
    for symbol in symbols_to_try:
        try:
            print(f"Attempting: {symbol}...", end=" ")
            data = get_history(symbol=symbol, 
                              start=start_date, 
                              end=end_date)
            
            if data is not None and len(data) > 10:
                output_file = "datasets/HDFC_Nifty50_ETF_2011_to_2026.csv"
                data.to_csv(output_file)
                print("✓ SUCCESS")
                print(f"✓ Saved to: {output_file}")
                print(f"  Shape: {data.shape}")
                print(f"  Dates: {data.index[0].date()} to {data.index[-1].date()}")
                exit(0)
            else:
                print("✗ No suitable data")
        except Exception as e:
            print(f"✗ {str(e)[:50]}")
            
except ImportError:
    print("✗ NSEPy not imported correctly")

# ============================================================================
# METHOD 2: yfinance with multiple ticker variations
# ============================================================================
print("\nMETHOD 2: Using yfinance")
print("-" * 70)

try:
    import yfinance as yf
    
    # Extended list of possible tickers
    tickers = [
        "HDFCNIFTY50.NS",
        "HDFCETF50.NS",
        "HDFC50.NS",
        "HDFCNIF50.NS",
        "HDFCNIFTY50ETF.NS",
        "HDFCNIFTYBEES.NS",
    ]
    
    for ticker in tickers:
        try:
            print(f"Attempting: {ticker}...", end=" ")
            data = yf.download(ticker, 
                              start=start_date.strftime("%Y-%m-%d"),
                              end=end_date.strftime("%Y-%m-%d"),
                              progress=False)
            
            if data is not None and len(data) > 10:
                output_file = "datasets/HDFC_Nifty50_ETF_2011_to_2026.csv"
                data.to_csv(output_file)
                print("✓ SUCCESS")
                print(f"✓ Saved to: {output_file}")
                exit(0)
            else:
                print("✗ No data")
        except:
            print("✗ Error")

except Exception as e:
    print(f"✗ yfinance error: {e}")

# ============================================================================
# FALLBACK: If HDFC Nifty 50 not available, suggest alternatives
# ============================================================================
print("\n" + "=" * 70)
print("⚠ HDFC NIFTY 50 ETF NOT FOUND IN AVAILABLE SOURCES")
print("=" * 70)

print("""
IMPORTANT NOTES:
================
1. HDFC Nifty 50 ETF may:
   - Have a different ticker symbol on NSE
   - Be delisted or inactive
   - Have limited yfinance/nsepy coverage

2. RECOMMENDED ALTERNATIVES:
   
   a) Use NIFTYBEES (popular Nifty 50 ETF):
      - Ticker: NIFTYBEES.NS (works with yfinance)
      - This is a liquid Nifty 50 tracking ETF
   
   b) Check the correct ticker:
      - Visit NSE website: https://www.nseindia.com
      - Search for HDFC ETF products
      - Look for ISIN code

3. TO PROCEED WITH NIFTYBEES:
   Run this command in Python:
   
   import yfinance as yf
   data = yf.download("NIFTYBEES.NS", 
                      start="2011-01-01",
                      end="2026-03-27")
   data.to_csv("datasets/NIFTYBEES_2011_to_2026.csv")

4. MANUAL DOWNLOAD:
   - Visit NSE website directly
   - Download historical data CSV
   - Save to datasets/ folder
""")

print("\nFor more help, provide the exact HDFC Nifty 50 ETF ticker symbol.")
