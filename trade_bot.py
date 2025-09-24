# local_test.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local Test Script for OKX Trading Bot
-------------------------------------
Purpose:
- To safely test the OKX API connection and trade execution on your local machine.
- Reads API keys from a local .env file.
- Executes a real market buy order with a very small, predefined test amount.

"""

import os
import datetime as dt
from dotenv import load_dotenv
import ccxt

# ==============================================================================
# SECTION 1: TEST CONFIGURATION
# ==============================================================================

# Set the amount for this one-time test. Must be slightly > 1 for most exchanges.
TEST_AMOUNT_USD = 1.01

# The trading pair on OKX
OKX_SYMBOL = "BTC/USDT"

# ==============================================================================
# SECTION 2: TEST EXECUTION LOGIC
# ==============================================================================

def run_local_test():
    """Connects to OKX and places a small test order."""
    
    # 1. Load API Keys from .env file
    print("Attempting to load API credentials from .env file...")
    load_dotenv()
    
    api_key = os.getenv("OKX_API_KEY")
    secret_key = os.getenv("OKX_SECRET_KEY")
    password = os.getenv("OKX_PASSWORD")

    if not all([api_key, secret_key, password]):
        print("\n" + "="*50)
        print("🔴 ERROR: Could not find API credentials in .env file.")
        print("Please ensure you have a .env file in the same directory with:")
        print("OKX_API_KEY=\"your_api_key\"")
        print("OKX_SECRET_KEY=\"your_secret_key\"")
        print("OKX_PASSWORD=\"your_passphrase\"")
        print("="*50 + "\n")
        return

    print("✅ API credentials loaded successfully.")

    # 2. Initialize CCXT Exchange
    print("Initializing connection to OKX...")
    exchange = ccxt.okx({
        'apiKey': api_key,
        'secret': secret_key,
        'password': password,
        'options': {
            'defaultType': 'spot',
        },
    })
    
    print(f"✅ Connection initialized.")

    # 3. Display Test Plan
    print("\n" + "="*50)
    print("             ⚡️ LIVE TEST WARNING ⚡️")
    print("This script will attempt to place a REAL trade on your OKX account.")
    print(f"  - Symbol: {OKX_SYMBOL}")
    print(f"  - Order Type: Market Buy")
    print(f"  - Amount: ${TEST_AMOUNT_USD}")
    print("="*50 + "\n")
    
    # Simple countdown to prevent accidental execution
    try:
        input("Press Enter to proceed, or Ctrl+C to cancel...")
    except KeyboardInterrupt:
        print("\nTest cancelled by user.")
        return

    # 4. Execute the test trade
    print(f"\nPlacing live market buy order for {OKX_SYMBOL} with amount ${TEST_AMOUNT_USD}...")
    try:
        order = exchange.create_market_buy_order(OKX_SYMBOL, TEST_AMOUNT_USD)
        
        print("\n" + "#"*50)
        print("      ✅✅✅ TEST TRADE SUCCESSFUL! ✅✅✅")
        print("#"*50)
        print(f"   Order ID: {order.get('id', 'N/A')}")
        print(f"   Timestamp: {dt.datetime.fromtimestamp(order.get('timestamp') / 1000) if order.get('timestamp') else 'N/A'}")
        print(f"   Filled Amount (BTC): {order.get('filled', 'N/A')}")
        print(f"   Average Price: {order.get('average', 'N/A')}")
        print(f"\nPlease log in to your OKX account to verify this transaction.")
        
    except Exception as e:
        print("\n" + "!"*50)
        print("      🔴🔴🔴 TEST TRADE FAILED! 🔴🔴🔴")
        print("!"*50)
        print(f"   Error Type: {type(e).__name__}")
        print(f"   Error Details: {e}")
        print("\n   Common reasons for failure:")
        print("   - Incorrect API Key, Secret, or Passphrase in .env file.")
        print("   - API Key does not have 'Trade' permission.")
        print("   - Insufficient USDT balance in your spot account.")

if __name__ == "__main__":
    run_local_test()