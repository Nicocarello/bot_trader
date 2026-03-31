"""
Sector Flow Agent
Analyzes sector ETF relative performance to detect money rotation.
Determines if a target symbol's sector is leading, lagging, or neutral.
"""
from typing import Dict, Any
from agents.base_agent import BaseAgent

# Maps individual tickers to their corresponding Sector ETF
TICKER_TO_SECTOR = {
    # Tech
    "AAPL": "XLK", "NVDA": "XLK", "MSFT": "XLK", "AMD": "XLK", "GOOGL": "XLK",
    "META": "XLK", "NFLX": "XLK", "AMZN": "XLK", "TSLA": "XLK",
    # Financials
    "JPM": "XLF", "GS": "XLF", "BAC": "XLF", "MS": "XLF", "V": "XLF", "MA": "XLF",
    # Energy
    "XOM": "XLE", "CVX": "XLE", "SLB": "XLE",
    # Industrials
    "BA": "XLI", "CAT": "XLI",
    # Fintech / Crypto-linked
    "COIN": "XLF", "PYPL": "XLF", "SQ": "XLF", "MARA": "XLK",
    # ETFs - no specific sector mapping
    "SPY": "SPY", "QQQ": "XLK", "IWM": None, "VXX": None, "GLD": None,
}

class SectorFlowAgent(BaseAgent):
    """
    Analyzes sector ETF daily returns to determine where money is flowing.
    Outputs a 'sector_bias' for a given stock: 'tailwind', 'headwind', or 'neutral'.
    """
    def __init__(self):
        super().__init__("SectorFlowAgent")

    def process(self, symbol: str, sector_returns: Dict[str, float]) -> Dict[str, Any]:
        """
        Args:
            symbol: The ticker being evaluated (e.g. 'AAPL')
            sector_returns: Dict of sector ETF -> 1-day return (e.g. {'XLK': 0.012, 'XLF': -0.005})
        
        Returns:
            A dict with sector_bias, sector_ticker, sector_return,
            leading_sector, lagging_sector, and reasoning.
        """
        if not sector_returns:
            return {"sector_bias": "neutral", "reasoning": "No sector data available."}

        # Identify the sector for this symbol
        sector_ticker = TICKER_TO_SECTOR.get(symbol)

        # Find leading and lagging sectors
        sorted_sectors = sorted(sector_returns.items(), key=lambda x: x[1], reverse=True)
        leading_sector = sorted_sectors[0] if sorted_sectors else (None, 0)
        lagging_sector = sorted_sectors[-1] if sorted_sectors else (None, 0)

        if sector_ticker is None or sector_ticker not in sector_returns:
            return {
                "sector_bias": "neutral",
                "sector_ticker": sector_ticker,
                "sector_return": None,
                "leading_sector": leading_sector[0],
                "leading_return": leading_sector[1],
                "lagging_sector": lagging_sector[0],
                "lagging_return": lagging_sector[1],
                "reasoning": f"{symbol} has no mapped sector. Cannot assess rotation bias."
            }

        symbol_sector_return = sector_returns[sector_ticker]

        # Compute average sector return
        avg_return = sum(sector_returns.values()) / len(sector_returns)

        # Determine bias relative to broad market average
        outperformance = symbol_sector_return - avg_return

        if outperformance > 0.005:   # >0.5% above average
            bias = "tailwind"
            reasoning = (
                f"{symbol} ({sector_ticker}) is LEADING the market today "
                f"(ret: {symbol_sector_return:.2%} vs mkt avg: {avg_return:.2%})."
            )
        elif outperformance < -0.005:  # >0.5% below average
            bias = "headwind"
            reasoning = (
                f"{symbol} ({sector_ticker}) is LAGGING the market today "
                f"(ret: {symbol_sector_return:.2%} vs mkt avg: {avg_return:.2%}). "
                f"Money rotating OUT of this sector."
            )
        else:
            bias = "neutral"
            reasoning = (
                f"{symbol} ({sector_ticker}) is trading in-line with the broad market "
                f"(ret: {symbol_sector_return:.2%} vs mkt avg: {avg_return:.2%})."
            )

        return {
            "sector_bias": bias,
            "sector_ticker": sector_ticker,
            "sector_return": symbol_sector_return,
            "leading_sector": leading_sector[0],
            "leading_return": leading_sector[1],
            "lagging_sector": lagging_sector[0],
            "lagging_return": lagging_sector[1],
            "reasoning": reasoning
        }
