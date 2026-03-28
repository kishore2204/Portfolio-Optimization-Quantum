"""
Discovery script to find available HDFC/Nifty ETF tickers on yfinance
"""

import yfinance as yf

print("HDFC & Nifty ETF Ticker Discovery")
print("=" * 50)

# Try to get info on HDFC company/ETF
search_terms = ["HDFC", "NIFTY50", "NIFTYBEES", "NIFTYHALF"]

for term in search_terms:
    print(f"\nSearching for: {term}")
    try:
        ticker_obj = yf.Ticker(term)
        info = ticker_obj.info
        if info:
            print(f"  ✓ Found: {term}")
            print(f"    Name: {info.get('shortName', 'N/A')}")
        else:
            print(f"  ✗ No info found")
    except Exception as e:
        print(f"  ✗ Error: {str(e)[:50]}")

print("\n" + "=" * 50)
print("RECOMMENDED APPROACH:")
print("=" * 50)
print("""
1. Most Indian ETFs may not have direct yfinance support
2. BETTER OPTION: Use NSE-Direct data sources:
   - NSE API (National Stock Exchange of India)
   - yfinance with BSE/NSE ticker codes for stocks
   - pandas_datareader with Yahoo Finance

3. Alternative Nifty ETFs that might work:
   - NIFTYBEES (popular Nifty 50 ETF)
   - Check NSE website for exact HDFC ETF ticker
   
4. For Indian data, consider:
   - nsepy library: https://pypi.org/project/nsepy/
   - yfinance with correct .NS/.BO suffixes
   - Direct NSE downloads
""")

# Try one more with Nifty Bees which is commonly available
print("\nAttempting NIFTYBEES.NS...")
try:
    data = yf.download("NIFTYBEES.NS", start="2023-01-01", end="2026-01-01", progress=False)
    if not data.empty:
        print("✓ SUCCESS with NIFTYBEES.NS!")
        print(f"  Data shape: {data.shape}")
    else:
        print("✗ NIFTYBEES.NS returned no data")
except Exception as e:
    print(f"✗ Error: {e}")
