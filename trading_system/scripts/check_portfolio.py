import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import config
from execution.alpaca_paper_adapter import AlpacaPaperAdapter

def check():
    print("=== ALPACA PAPER PORTFOLIO SNAPSHOT ===")
    try:
        adapter = AlpacaPaperAdapter()
        account = adapter.client.get_account()
        positions = adapter.client.get_all_positions()
        
        print(f"Account Balance: ${account.equity}")
        print(f"Cash Buying Power: ${account.buying_power}")
        print(f"\nOpen Positions: {len(positions)}")
        for pos in positions:
            print(f" - {pos.symbol}: {pos.qty} shares @ {pos.current_price} (Unrealized PnL: ${pos.unrealized_pl})")
    except Exception as e:
        print(f"Error checking portfolio: {e}")

if __name__ == "__main__":
    check()
