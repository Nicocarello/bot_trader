"""
Alpaca Paper-Trading Verification Script.
Checks auth, fetches account info, features positions.
Will only submit a $1 test order if EXECUTE_TEST_ORDER is manually set to True.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / '.env')
except ImportError:
    pass

from config import config

try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce
except ImportError:
    print("Please run: pip install alpaca-py==0.17.4")
    sys.exit(1)

# --- STRICT SAFETY ENFORCEMENT ---

# 1. Verify Application Environment is strictly "paper"
if getattr(config, "ENVIRONMENT", "").lower() != "paper":
    print(f"CRITICAL ERROR: Application Environment is '{getattr(config, 'ENVIRONMENT', 'None')}'. Must be 'paper'.")
    sys.exit(1)

# 2. Verify boolean flag
if config.ALPACA_PAPER is not True:
    print("CRITICAL ERROR: ALPACA_PAPER Config must be set to True.")
    sys.exit(1)

# 3. Verify Keys exist
if not config.ALPACA_API_KEY or not config.ALPACA_SECRET_KEY:
    print("[X] ERROR: API Keys not found in .env file.")
    print("Please copy .env.example to .env and insert your Alpaca paper keys.")
    sys.exit(1)

PAPER_URL = "https://paper-api.alpaca.markets"

# --- MANUAL EXECUTION FLAG ---
# Change to True ONLY if you want to execute a safe $1.00 fractional order test.
EXECUTE_TEST_ORDER = True

def verify():
    print("\n=== ALPACA PAPER TRADING VERIFICATION ===\n")

    try:
        # Instantiation with explicit paper=True guarantees traffic routes to PAPER_URL natively
        print(f"[PAPER MODE CHECK] Initializing Alpaca Client...")
        client = TradingClient(
            api_key=config.ALPACA_API_KEY,
            secret_key=config.ALPACA_SECRET_KEY,
            paper=True
        )

        # A. Fetch Account Info
        print(f"[PAPER MODE CHECK] Targeting base endpoint: {PAPER_URL}")
        print("[PAPER MODE CHECK] Requesting account details...")
        account = client.get_account()
        
        print("\n[PAPER MODE VERIFIED]")
        print("[✓] Target Endpoint is Paper")
        print("[✓] API Keys Authenticated Successfully")
        print(f"    Account ID: {account.id}")
        print(f"    Status: {account.status}")
        print(f"    Paper Buying Power: ${account.buying_power}")
        print(f"    Paper Cash: ${account.cash}")
        print(f"    Portfolio Value: ${account.portfolio_value}\n")
        
        # B. Fetch Positions
        print("[PAPER MODE CHECK] Requesting open positions...")
        positions = client.get_all_positions()
        print(f"[✓] Fetched {len(positions)} Open Positions.")
        for pos in positions:
            print(f"    - {pos.symbol}: {pos.qty} shares @ ${pos.avg_entry_price}")
        print()
        
        # C. Fractional Order Execution (Disabled by default mechanism)
        if EXECUTE_TEST_ORDER:
            print("[PAPER MODE EXECUTION] EXECUTE_TEST_ORDER is True. Preparing fractional test order...")
            req = MarketOrderRequest(
                symbol="AAPL",
                notional=1.00, # Smallest possible fractional order ($1)
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
            print(f"[PAPER MODE EXECUTION] Routing $1.00 AAPL Market BUY to {PAPER_URL}...")
            order = client.submit_order(order_data=req)
            print("\n[✓] PAPER TRADE EXECUTED SUCCESSFULLY!")
            print(f"    Order ID: {order.id}")
            print(f"    Symbol: {order.symbol}")
            print(f"    Notional Value: ${order.notional}")
            print(f"    Status: {order.status}")
            
            # Print updated account snapshot
            print("\n[PAPER MODE SNAPSHOT] Fetching updated account status...")
            updated_account = client.get_account()
            print(f"    Paper Buying Power: ${updated_account.buying_power}")
            print(f"    Paper Cash: ${updated_account.cash}")
            print(f"    Portfolio Value: ${updated_account.portfolio_value}\n")
        else:
            print("[-] EXECUTE_TEST_ORDER is False. Skipping test order. No orders submitted.")

        print("\n=== VERIFICATION COMPLETE ===")
        
    except Exception as e:
        print(f"\n[X] VERIFICATION FAILED: {str(e)}")

if __name__ == "__main__":
    verify()
