"""
Autonomous Scheduler for the AI Trading System.
Runs the full 3-phase paper trading cycle hourly during ART trading hours.
This version is designed to run as the entrypoint on any cloud environment
(GitHub Actions, Oracle Cloud, Railway, PythonAnywhere, etc.)

Trading Window: 11:00 - 17:00 ART (UTC-3) = 14:00 - 20:00 UTC
US Market open: 09:30 ET = 13:30 UTC (EDT) / 14:30 UTC (EST)
"""
import sys
import time
import schedule
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.paper_runner import PaperTradingRunner

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Path(__file__).parent.parent / "live_output.txt", mode='a')
    ]
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
ART = timezone(timedelta(hours=-3))  # ART = UTC-3

# Trading window in ART local time
START_HOUR_ART = 11  # 11:00 ART = 14:00 UTC
END_HOUR_ART = 17   # 17:00 ART = 20:00 UTC

# Run every N minutes within the trading window
RUN_INTERVAL_MINUTES = 60

# Tickers universe (centralized here)
UNIVERSE = [
    # --- Megacap Tech ---
    "AAPL", "NVDA", "TSLA", "MSFT", "AMZN", "META", "GOOGL", "AMD", "NFLX",
    # --- Banking & Finance ---
    "JPM", "GS", "BAC", "MS", "V", "MA",
    # --- Energy & Industrials ---
    "XOM", "CVX", "SLB", "BA", "CAT",
    # --- Crypto-Linked & Fintech ---
    "COIN", "MARA", "PYPL", "SQ",
    # --- Macro ETFs ---
    "SPY", "QQQ", "IWM", "GLD"
]


def is_within_trading_window() -> bool:
    """Returns True if current ART time is within the trading window, on a weekday."""
    now_art = datetime.now(tz=ART)
    
    # Skip weekends (0=Monday, 6=Sunday)
    if now_art.weekday() >= 5:
        return False
    
    return START_HOUR_ART <= now_art.hour < END_HOUR_ART


def run_trading_sweep():
    """Executes one full multi-sector analysis cycle if within trading window."""
    now_art = datetime.now(tz=ART)
    
    if not is_within_trading_window():
        day_name = now_art.strftime("%A")
        logger.info(
            f"[SCHEDULER] Outside trading window "
            f"({day_name} {now_art.strftime('%H:%M')} ART). Sleeping..."
        )
        return

    logger.info("=" * 60)
    logger.info(f"[SCHEDULER] TRADING WINDOW ACTIVE — {now_art.strftime('%A %Y-%m-%d %H:%M')} ART")
    logger.info("=" * 60)

    try:
        runner = PaperTradingRunner()
        runner.run_full_cycle(universe=UNIVERSE)
        logger.info("[SCHEDULER] Sweep complete. Next run in ~60 min.")
    except Exception as e:
        logger.error(f"[SCHEDULER] CRITICAL SWEEP ERROR: {e}", exc_info=True)


def main():
    """Main entry point. Runs once immediately, then schedules recurring runs."""
    logger.info("╔═══════════════════════════════════════╗")
    logger.info("║  AI TRADING SCHEDULER — STARTING UP   ║")
    logger.info(f"║  Window: {START_HOUR_ART}:00 – {END_HOUR_ART}:00 ART (UTC-3)     ║")
    logger.info(f"║  Frequency: Every {RUN_INTERVAL_MINUTES} minutes            ║")
    logger.info("╚═══════════════════════════════════════╝")

    # Immediate run on startup if in window
    run_trading_sweep()

    # Schedule recurring runs at the top of every hour
    schedule.every(RUN_INTERVAL_MINUTES).minutes.do(run_trading_sweep)

    while True:
        schedule.run_pending()
        time.sleep(30)  # Low-CPU idle loop


if __name__ == "__main__":
    main()
