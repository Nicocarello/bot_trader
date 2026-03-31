"""
Strategy Coordinator Agent
Responsible for adversarial debate and final synthesis of competing Trade Proposals.
"""

from typing import List, Optional
from agents.base_agent import BaseAgent
from schemas.models import TradeProposal, SynthesizedDecision, MarketRegimeClassification, RAGContext, CalibrationMetrics

class StrategyCoordinator(BaseAgent):
    """
    Evaluates conflicting Strategy Agent proposals.
    Assigns an overarching 'uncertainty_score'.
    Maps strategy relevance conditionally to specific market regimes.
    """
    def __init__(self):
        super().__init__("StrategyCoordinator")

    def process(
        self,
        asset: str,
        proposals: List[TradeProposal],
        regime: MarketRegimeClassification,
        sentiment_score: float = 0.5,
        rag_context: Optional[RAGContext] = None,
        calibrations: Optional[List[CalibrationMetrics]] = None
    ) -> SynthesizedDecision:

        
        active_props = [p for p in proposals if p.decision != "hold"]
        
        # Base No-Trade Condition 1: No active proposals
        if not active_props:
            return self._abort(asset, regime, "All strategies submitted 'hold'.")

        longs = [p for p in active_props if p.decision == "long"]
        shorts = [p for p in active_props if p.decision == "short"]
        
        conflict = len(longs) > 0 and len(shorts) > 0
        
        # Base No-Trade Condition 2: Strong Conflict
        if conflict:
            return self._abort(asset, regime, "Strong signal conflict detected (Longs vs Shorts). Bailing out.")
        
        # Base No-Trade Condition 3: Insufficient Regime Confidence
        if regime.confidence < 0.3:
            return self._abort(asset, regime, f"Regime confidence too low ({regime.confidence}). Requires > 0.3.")
            
        # Base No-Trade Condition 4: Insufficient News/RAG Context
        rag_conf = rag_context.retrieval_confidence if rag_context else 0.0
        if rag_conf < 0.0:
            return self._abort(asset, regime, f"Insufficient news/RAG context confidence ({rag_conf}). Requires > 0.0.")

        # Scoring Logic Framework:
        # Final Score = Base Algorithm Prob + Agreement Bonus + RAG Boost - Algorithmic Uncertainty (Confidence_score proxy) - Stale/Weak Calibration Penalty
        
        agreement_bonus = 0.05 * (len(active_props) - 1)  # Reward consensus logically
        best_proposal = active_props[0]
        max_score = -1.0
        
        for prop in active_props:
            base_prob = prop.probabilities.probability_of_success
            regime_bonus = 0.0
            
            # Map Regime Alignment Native Bonus & Strict Compatibility Blocks
            if prop.strategy_name == "MomentumTrendFollower":
                if regime.regime in ["bull_volatile", "bull_quiet", "bear_volatile", "ranging_choppy"]:
                    regime_bonus = 0.15
                else:
                    return self._abort(asset, regime, f"Momentum strategy mathematically incompatible with {regime.regime}.")

            elif prop.strategy_name == "MeanReversionAgent":
                if regime.regime in ["ranging_choppy", "bull_quiet", "bear_quiet", "bull_volatile", "bear_volatile"]:
                    regime_bonus = 0.15
                else:
                    return self._abort(asset, regime, f"MeanReversion strategy incompatible with {regime.regime}.")
                    
            elif prop.strategy_name == "VolatilityBreakoutAgent":
                if regime.regime in ["bear_quiet", "bull_quiet", "ranging_choppy"]:
                    regime_bonus = 0.15
                else:
                    return self._abort(asset, regime, f"VolatilityBreakout incompatible with {regime.regime}.")
            
            # Calibration/Memory Penalty (If memory agent fed history)
            calibration_penalty = 0.0
            if calibrations:
                for cal in calibrations:
                    if cal.strategy_name == prop.strategy_name:
                        calibration_penalty = cal.reliability_haircut
            
            # Sentiment Boost/Penalty
            sentiment_mod = 0.0
            if sentiment_score > 0.60:
                sentiment_mod = 0.10
            elif sentiment_score < 0.40:
                sentiment_mod = -0.10
            
            # Compute Final Synthesis Score
            score = base_prob + regime_bonus + agreement_bonus + (rag_conf * 0.1) + sentiment_mod - prop.confidence_score - calibration_penalty
            
            if score > max_score:
                max_score = score
                best_proposal = prop

        # Final No-Trade Condition 5: Probability/Score Threshold Minimums
        # We need the synthesis score to fundamentally beat internal uncertainty limits
        if max_score < 0.45:
            return self._abort(asset, regime, f"Winning strategy '{best_proposal.strategy_name}' failed minimum final synthesis score (Score: {max_score:.2f} < 0.45). Sentiment: {sentiment_score:.2f}")

        # PLAYBOOK RULE: News Uncertainty - If RAG Confidence is < 0.3, the trade must have a consensus score > 0.8 to proceed.
        # Consensus score proxy here is our synthetic score being extremely high despite no news.
        if rag_conf < 0.3 and max_score < 0.8:
            return self._abort(asset, regime, f"PLAYBOOK DISCIPLINE: Marginal signal ({max_score:.2f}) rejected due to news uncertainty loop (RAG < 0.3). Sentiment: {sentiment_score:.2f}")

        return SynthesizedDecision(
            asset=asset,
            final_decision=best_proposal.decision,
            winning_strategy=best_proposal.strategy_name,
            synthesized_probability=min(0.99, best_proposal.probabilities.probability_of_success + agreement_bonus + (sentiment_mod * 0.5)),
            uncertainty_score=max(0.0, 1.0 - max_score), 
            expected_value_raw=0.0, 
            market_regime=regime,
            reasoning_summary=f"PLAYBOOK APPROVED: {best_proposal.strategy_name} selected (Score: {max_score:.2f}, Sentiment: {sentiment_score:.2f})."
        )


    def _abort(self, asset: str, regime: MarketRegimeClassification, reason: str) -> SynthesizedDecision:
        return SynthesizedDecision(
            asset=asset,
            final_decision="no_trade",
            winning_strategy=None,
            synthesized_probability=0.0,
            uncertainty_score=1.0,  
            expected_value_raw=0.0,
            market_regime=regime,
            reasoning_summary=reason
        )
