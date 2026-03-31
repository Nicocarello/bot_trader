"""
Concrete Strategy Agents (Trend, Mean Reversion, VCP)
Generates deterministic TradeProposals based strictly on math and regime.
"""
from typing import Dict, Any
from agents.base_agent import BaseAgent
from schemas.models import TradeProposal, MarketRegimeClassification, AgentProbability

class StrategyAgent(BaseAgent):
    """Base class for alpha generation strategies."""
    def __init__(self, name: str):
        super().__init__(name)

    def process(self, market_data: Dict[str, Any], regime: MarketRegimeClassification) -> TradeProposal:
        raise NotImplementedError("Strategies must implement process()")

class MomentumTrendFollower(StrategyAgent):
    def __init__(self):
        super().__init__("MomentumTrendFollower")

    def process(self, market_data: Dict[str, Any], regime: MarketRegimeClassification) -> TradeProposal:
        decision = "hold"
        prob = 0.50
        reason = "Regime out of bounds for Momentum."
        
        # PLAYBOOK RULE: Momentum Entry: Price > 20 SMA AND Z-Score > 1.0
        if regime.regime in ["bull_volatile", "bull_quiet", "ranging_choppy"]:
            close = market_data.get('close', 0.0)
            sma = market_data.get('sma_20', close)
            z_score = market_data.get('z_score', 0.0)
            
            if close > sma and z_score > 1.0:
                decision = "long"
                prob = 0.65
                reason = "Trend Momentum: Price > SMA20 AND Z-Score > 1.0"
            else:
                reason = "Price lack momentum strength (Z-Score <= 1.0)."
                
        return TradeProposal(
            strategy_name=self.name, asset=market_data.get("symbol", "AAPL"), decision=decision,
            probabilities=AgentProbability(probability_of_success=prob, expected_upside_pct=0.04, expected_downside_pct=0.02),
            confidence_score=0.1, market_regime=regime, reasoning=reason
        )

class MeanReversionAgent(StrategyAgent):
    def __init__(self):
        super().__init__("MeanReversionAgent")

    def process(self, market_data: Dict[str, Any], regime: MarketRegimeClassification) -> TradeProposal:
        decision = "hold"
        prob = 0.50
        reason = "Regime prohibits Mean Reversion."
        
        # PLAYBOOK RULE: Mean Reversion: Outside Bollinger Bands AND Z-Score < -2.0 (for longs)
        if regime.regime in ["ranging_choppy", "bull_quiet", "bear_quiet", "bull_volatile", "bear_volatile"]:
            z_score = market_data.get('z_score', 0.0)
            close = market_data.get('close', 0.0)
            bb_lower = market_data.get('bb_lower', 0.0)
            bb_upper = market_data.get('bb_upper', 99999.0)
            
            if z_score <= -2.0 and close < bb_lower:
                decision = "long"
                prob = 0.70
                reason = "Extremely Oversold: Z-Score < -2.0 AND Price < BB Lower."
            elif z_score >= 2.0 and close > bb_upper:
                decision = "short"
                prob = 0.70
                reason = "Extremely Overbought: Z-Score > 2.0 AND Price > BB Upper."
            else:
                reason = "Price inside normal mean band."
                
        return TradeProposal(
            strategy_name=self.name, asset=market_data.get("symbol", "AAPL"), decision=decision,
            probabilities=AgentProbability(probability_of_success=prob, expected_upside_pct=0.015, expected_downside_pct=0.015),
            confidence_score=0.15, market_regime=regime, reasoning=reason
        )

class VolatilityBreakoutAgent(StrategyAgent):
    def __init__(self):
        super().__init__("VolatilityBreakoutAgent")

    def process(self, market_data: Dict[str, Any], regime: MarketRegimeClassification) -> TradeProposal:
        decision = "hold"
        prob = 0.50
        reason = "Vol expression already active or regime blocked."
        
        # PLAYBOOK RULE: Vol Breakout: BB Width < 20% AND Close > BB Upper
        if regime.regime in ["bear_quiet", "bull_quiet", "ranging_choppy"]:
            bb_width_percentile = market_data.get('bb_width_percentile', 100.0)
            close = market_data.get('close', 0.0)
            bb_upper = market_data.get('bb_upper', 99999.0)
            volume_ratio = market_data.get('volume_ratio', 1.0)  # NEW: real volume confirmation
            
            if bb_width_percentile < 20.0 and close > bb_upper:
                decision = "long"
                # Volume confirmation: breakout on high volume is a much stronger signal
                if volume_ratio >= 1.5:
                    prob = 0.68
                    reason = (f"HIGH-CONVICTION Squeeze Release: BB Width < 20% AND Close > BB Upper "
                              f"WITH volume confirmation ({volume_ratio:.1f}x avg).")
                else:
                    prob = 0.55
                    reason = (f"Squeeze Release: BB Width < 20% AND Close > BB Upper "
                              f"(low volume confirmation: {volume_ratio:.1f}x avg).")
                
        return TradeProposal(
            strategy_name=self.name, asset=market_data.get("symbol", "AAPL"), decision=decision,
            probabilities=AgentProbability(probability_of_success=prob, expected_upside_pct=0.06, expected_downside_pct=0.02),
            confidence_score=0.25, market_regime=regime, reasoning=reason
        )


class FundamentalAnalystAgent(StrategyAgent):
    """
    Evaluates 10 core fundamental metrics to provide a stability and 'Value' score.
    Metrics: P/E Trailing/Forward, P/B, ROE, Market Cap, Dividend Yield, Expense Ratio, EV/EBITDA, ROA, Profit Margins.
    """
    def __init__(self):
        super().__init__("FundamentalAnalystAgent")

    def process(self, market_data: Dict[str, Any], regime: MarketRegimeClassification) -> TradeProposal:
        fundamentals = market_data.get("fundamentals", {})
        if not fundamentals:
            return TradeProposal(
                strategy_name=self.name, asset=market_data.get("symbol", ""), decision="hold",
                probabilities=AgentProbability(probability_of_success=0.0, expected_upside_pct=0.0, expected_downside_pct=0.0),
                confidence_score=0.0, market_regime=regime, reasoning="No fundamental data provided."
            )

        # Scored Criteria Logic
        score_points = 0
        reasons = []

        # 1. P/E Trailing (< 25 = 1 pt)
        if 0 < fundamentals.get("pe_trailing", 999) < 25:
            score_points += 1
            reasons.append("Low P/E Trailing")

        # 2. ROE (> 15% = 1 pt)
        if fundamentals.get("roe", 0) > 0.15:
            score_points += 1
            reasons.append("High ROE")

        # 3. Profit Margins (> 10% = 1 pt)
        if fundamentals.get("profit_margins", 0) > 0.10:
            score_points += 1
            reasons.append("Healthy Margins")

        # 4. EV/EBITDA (< 15 = 1 pt)
        if 0 < fundamentals.get("ev_ebitda", 999) < 15:
            score_points += 1
            reasons.append("Attractive EV/EBITDA")

        # 5. ROA (> 5% = 1 pt)
        if fundamentals.get("roa", 0) > 0.05:
            score_points += 1
            reasons.append("Efficient ROA")

        decision = "long" if score_points >= 3 else "hold"
        # Scale probability based on fundamental strength (points 0-5)
        prob = 0.5 + (score_points * 0.05) if decision == "long" else 0.5
        
        return TradeProposal(
            strategy_name=self.name, 
            asset=market_data.get("symbol", ""), 
            decision=decision,
            probabilities=AgentProbability(probability_of_success=prob, expected_upside_pct=0.02, expected_downside_pct=0.01),
            confidence_score=0.1, 
            market_regime=regime, 
            reasoning=f"Fundamental Score: {score_points}/5. Keys: {', '.join(reasons)}" if reasons else "No fundamental edge found."
        )
