"""
Analytical Agents (Market Regime, Sentiment, Macro)
These do not output Trade Proposals, but context that feeds the system.
"""

from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from schemas.models import MarketRegimeClassification

class MarketRegimeAgent(BaseAgent):
    """Determines the broad market configuration based on price action and macro stats."""
    def __init__(self):
        super().__init__("MarketRegimeAgent")

    def process(self, market_snapshot: Dict[str, Any], macro_results: Dict[str, Any]) -> MarketRegimeClassification:
        """Determines the broad market configuration based on price action and macro stats."""
        # 1. Technical Indicators from Snapshot
        close = market_snapshot.get('close', 0.0)
        sma_20 = market_snapshot.get('sma_20', close)
        vix = macro_results.get('vix', 20.0)
        
        # 2. Logic for Regime Classification
        # BULL: Price > SMA20
        # VOLATILE: VIX > 25
        
        is_bull = close >= sma_20
        is_volatile = vix > 25.0
        
        confidence = 0.7 # Base confidence
        drivers = ["SMA20 Cross", f"VIX: {vix:.2f}"]
        
        if is_bull:
            regime = "bull_volatile" if is_volatile else "bull_quiet"
            if not is_volatile:
                confidence = 0.9
        else:
            regime = "bear_volatile" if is_volatile else "bear_quiet"
            if is_volatile:
                confidence = 0.85
                
        # Handle "Ranging" case if VIX is extremely low or price is hugging SMA
        if 15.0 < vix < 20.0 and abs(close - sma_20) / close < 0.01:
            regime = "ranging_choppy"
            confidence = 0.6
            
        return MarketRegimeClassification(
            regime=regime, 
            confidence=confidence, 
            volatility_index=vix, 
            key_drivers=drivers
        )

class SentimentAgent(BaseAgent):
    """Parses news and social media to output sentiment grids."""
    def __init__(self):
        super().__init__("SentimentAgent")

    def process(self, news_articles: List[Dict[str, str]]) -> Dict[str, float]:
        # LLM Logic: evaluate bullish/bearish news scale
        raise NotImplementedError("Stub: paper trading MVPs only")

class MacroEconomicsAgent(BaseAgent):
    """Parses Federal Reserve announcements, yield curves, and inflation prints."""
    def __init__(self):
        super().__init__("MacroEconomicsAgent")

    def process(self, macro_data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluates macro indicators (yields, volatility, gold) for tailwinds/headwinds."""
        vix = macro_data.get('vix', 20.0)
        yield_10y = macro_data.get('tnx_10y_yield', 4.0)
        mkt_ret = macro_data.get('market_return_1d', 0.0)
        
        headwinds = []
        tailwinds = []
        
        # VIX Analysis
        if vix > 30:
            headwinds.append("Extreme Market Volatility (Fear)")
        elif vix < 15:
            tailwinds.append("Low Volatility Environment (Stability)")
            
        # Yield Analysis
        if yield_10y > 4.5:
            headwinds.append("High Treasury Yields (Tighter Financial Conditions)")
        elif yield_10y < 3.5:
            tailwinds.append("Supportive Interest Rate Environment")
            
        # Return Analysis
        if mkt_ret < -0.02:
            headwinds.append("Significant Broad Market Selling Pressure")
            
        bias = "neutral"
        if len(tailwinds) > len(headwinds):
            bias = "bullish_tailwinds"
        elif len(headwinds) > len(tailwinds):
            bias = "bearish_headwinds"
            
        return {
            "bias": bias,
            "headwinds": headwinds,
            "tailwinds": tailwinds,
            "vix_status": "high" if vix > 25 else "neutral",
            "yield_impact": "negative" if yield_10y > 4.2 else "neutral"
        }
