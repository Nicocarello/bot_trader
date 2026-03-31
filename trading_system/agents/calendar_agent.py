"""
Calendar Blackout Agent
Prevents the bot from trading around high-uncertainty scheduled events:

1. EARNINGS BLACKOUT: Skips individual stocks that have an earnings announcement
   within a configurable window (default: 3 days before / 1 day after).
   Source: yfinance ticker.calendar (live)

2. ECONOMIC BLACKOUT: Pauses ALL trading on days with major macro events:
   - FOMC Interest Rate Decisions
   - CPI / Core CPI releases
   - Non-Farm Payrolls (NFP / Jobs Report)
   - GDP Advance Estimates
   Source: Hardcoded official schedules (Fed + BLS publish annually in advance)

Rationale:
  Around these events, the market reacts to *surprises*, not fundamentals.
  No technical or fundamental model can reliably predict the surprise direction.
  The professional trader's rule: "If you don't know what the catalyst is, don't trade."
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional
import yfinance as yf

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# OFFICIAL ECONOMIC CALENDAR — 2025 & 2026
# Sources:
#   FOMC: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
#   CPI:  https://www.bls.gov/schedule/news_release/cpi.htm
#   NFP:  https://www.bls.gov/schedule/news_release/empsit.htm
# ─────────────────────────────────────────────────────────────────────────────

FOMC_DECISION_DATES = [
    # 2025 — Federal Reserve Interest Rate Decisions (day 2 of each meeting = announcement)
    date(2025, 1, 29),
    date(2025, 3, 19),
    date(2025, 5, 7),
    date(2025, 6, 18),
    date(2025, 7, 30),
    date(2025, 9, 17),
    date(2025, 10, 29),
    date(2025, 12, 10),
    # 2026
    date(2026, 1, 28),
    date(2026, 3, 18),
    date(2026, 4, 29),
    date(2026, 6, 17),
    date(2026, 7, 29),
    date(2026, 9, 16),
    date(2026, 10, 28),
    date(2026, 12, 9),
]

CPI_RELEASE_DATES = [
    # 2025 — Bureau of Labor Statistics CPI Release Dates
    date(2025, 1, 15),
    date(2025, 2, 12),
    date(2025, 3, 12),
    date(2025, 4, 10),
    date(2025, 5, 13),
    date(2025, 6, 11),
    date(2025, 7, 11),
    date(2025, 8, 12),
    date(2025, 9, 10),
    date(2025, 10, 15),
    date(2025, 11, 12),
    date(2025, 12, 10),
    # 2026
    date(2026, 1, 14),
    date(2026, 2, 11),
    date(2026, 3, 11),
    date(2026, 4, 9),
    date(2026, 5, 13),
    date(2026, 6, 10),
    date(2026, 7, 10),
    date(2026, 8, 12),
    date(2026, 9, 9),
    date(2026, 10, 14),
    date(2026, 11, 11),
    date(2026, 12, 9),
]

NFP_RELEASE_DATES = [
    # 2025 — Non-Farm Payrolls (first Friday of each month)
    date(2025, 1, 10),
    date(2025, 2, 7),
    date(2025, 3, 7),
    date(2025, 4, 4),
    date(2025, 5, 2),
    date(2025, 6, 6),
    date(2025, 7, 3),   # Usually moved when Friday is near holiday
    date(2025, 8, 1),
    date(2025, 9, 5),
    date(2025, 10, 3),
    date(2025, 11, 7),
    date(2025, 12, 5),
    # 2026
    date(2026, 1, 9),
    date(2026, 2, 6),
    date(2026, 3, 6),
    date(2026, 4, 3),
    date(2026, 5, 1),
    date(2026, 6, 5),
]

# All major economic events combined
ALL_ECONOMIC_BLACKOUT_DATES = (
    {d: "FOMC Interest Rate Decision" for d in FOMC_DECISION_DATES} |
    {d: "CPI Release (Inflation Print)" for d in CPI_RELEASE_DATES} |
    {d: "NFP Jobs Report" for d in NFP_RELEASE_DATES}
)


class CalendarAgent:
    """
    Checks whether trading should be blocked based on scheduled events.
    """

    def __init__(self, earnings_days_before: int = 3, earnings_days_after: int = 1):
        self.earnings_days_before = earnings_days_before
        self.earnings_days_after = earnings_days_after

    # ─────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────────────────────────────

    def check_economic_blackout(self, check_date: Optional[date] = None) -> dict:
        """
        Returns blackout info for economic macro events on a given date.
        Checks today and tomorrow (pre-event caution day).
        """
        today = check_date or date.today()
        tomorrow = today + timedelta(days=1)

        for event_date, event_name in ALL_ECONOMIC_BLACKOUT_DATES.items():
            if today == event_date:
                return {
                    "blackout": True,
                    "event": event_name,
                    "event_date": str(event_date),
                    "reason": f"[ECON BLACKOUT] {event_name} TODAY. Market direction unpredictable."
                }
            if tomorrow == event_date:
                return {
                    "blackout": True,
                    "event": event_name,
                    "event_date": str(event_date),
                    "reason": f"[ECON BLACKOUT] {event_name} TOMORROW. Pre-event positioning is noise."
                }

        return {"blackout": False, "event": None}

    def check_earnings_blackout(self, symbol: str) -> dict:
        """
        Returns blackout info for a stock's upcoming or recent earnings.
        Uses yfinance .calendar to get the next earnings date.
        """
        try:
            ticker = yf.Ticker(symbol)
            calendar = ticker.calendar

            # yfinance returns a dict with 'Earnings Date' key
            if not calendar or "Earnings Date" not in calendar:
                return {"blackout": False, "earnings_date": None}

            earnings_entry = calendar["Earnings Date"]

            # May be a list with [earliest, latest] estimate range, or a single date
            if isinstance(earnings_entry, list) and len(earnings_entry) > 0:
                earnings_dt = earnings_entry[0]
            else:
                earnings_dt = earnings_entry

            # Normalize to date object
            if hasattr(earnings_dt, "date"):
                earnings_date = earnings_dt.date()
            elif isinstance(earnings_dt, str):
                earnings_date = datetime.strptime(earnings_dt[:10], "%Y-%m-%d").date()
            else:
                earnings_date = earnings_dt

            today = date.today()
            days_delta = (earnings_date - today).days

            if -self.earnings_days_after <= days_delta <= self.earnings_days_before:
                direction = "in" if days_delta >= 0 else "ago"
                count = abs(days_delta)
                return {
                    "blackout": True,
                    "earnings_date": str(earnings_date),
                    "days_delta": days_delta,
                    "reason": (
                        f"[EARNINGS BLACKOUT] {symbol} reports "
                        f"{'in ' + str(count) + ' day(s)' if days_delta >= 0 else str(count) + ' day(s) ago'}. "
                        f"Window: {self.earnings_days_before}d before / {self.earnings_days_after}d after."
                    )
                }

            return {
                "blackout": False,
                "earnings_date": str(earnings_date),
                "days_until": days_delta
            }

        except Exception as e:
            logger.debug(f"  [{symbol}] Could not fetch earnings calendar: {e}")
            return {"blackout": False, "earnings_date": None}

    def is_clear_to_trade(self, symbol: str) -> dict:
        """
        Combined check: symbol-level earnings blackout + global economic blackout.
        Returns dict with 'clear' bool and 'reason' string.
        """
        # Check global economic events first (applies to all symbols)
        econ = self.check_economic_blackout()
        if econ["blackout"]:
            return {"clear": False, "reason": econ["reason"]}

        # Check symbol-specific earnings
        earnings = self.check_earnings_blackout(symbol)
        if earnings["blackout"]:
            return {"clear": False, "reason": earnings["reason"]}

        days_until = earnings.get("days_until", "N/A")
        return {
            "clear": True,
            "reason": f"Calendar clear. Next earnings: {earnings.get('earnings_date', 'N/A')} ({days_until}d away)."
        }
