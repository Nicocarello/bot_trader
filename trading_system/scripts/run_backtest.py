"""
Historical Backtest Runner.
Loads local offline data, iterates the engine, and outputs deterministic performance.
NO EXTERNAL API CALLS PERMITTED.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.loader import DataLoader
from backtest.engine import BacktestEngine

def run():
    print("=== STARTING OFFLINE BACKTEST ===")
    
    # 1. Load Offline Data
    data_path = Path(__file__).parent.parent / "data" / "sample_data.csv"
    print(f"[1] Loading Historical Data from {data_path.name}...")
    
    loader = DataLoader(str(data_path))
    try:
        df = loader.load()
        print(f"    Loaded {len(df)} discrete chronological bars. Schema Validated.")
    except Exception as e:
        print(f"    [X] DataFrame Load Error: {e}")
        return

    # 2. Initialize Engine deterministically
    print("\n[2] Initializing Deterministic Backtest Engine (Seed=42)...")
    engine = BacktestEngine(initial_capital=100000.0, seed=42)
    
    # 3. Process the entire sequence
    print(f"\n[3] Engaging Tick-by-Tick Replay Sequence...")
    results = engine.run(df)
    
    # 4. Present Terminal Feedback
    print("\n=== OFFLINE BACKTEST COMPLETE ===")
    print(f"Final Capital:   ${results['final_capital']:.2f}")
    print(f"Max Drawdown:    {results['max_drawdown'] * 100:.2f}%")
    print(f"Annualized Sharpe:{results['sharpe_ratio']:.4f}")
    print(f"Total Trades:    {results['total_trades']}")
    
    print("\n[TRACE LOG] Detailed Audit Trail of Final Simulated Fill:")
    if engine.trade_log:
        last_trade = engine.trade_log[-1]
        print(f"    ID: {last_trade.order_id} | Asset: {last_trade.asset} | Qty: {last_trade.quantity:.4f} | Fill: ${last_trade.fill_price:.2f}")
    else:
        print("    No trades executed.")

if __name__ == "__main__":
    run()
