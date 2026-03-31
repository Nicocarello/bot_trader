import sys
import unittest
from pathlib import Path
 # Fix import path so we don't need PYTHONPATH externally
sys.path.insert(0, str(Path(__file__).parent.parent))

from risk.risk_manager import RiskManager
from schemas.models import SynthesizedDecision, PortfolioState, MarketRegimeClassification
from datetime import datetime, timezone

class TestRiskManager(unittest.TestCase):
    def setUp(self):
        self.rm = RiskManager()
        self.portfolio = PortfolioState(
            total_capital_usd=100000.0,
            available_cash_usd=100000.0,
            open_positions={},
            daily_realized_pnl_pct=0.0,
            current_drawdown_pct=0.0
        )
        self.regime = MarketRegimeClassification(
            regime="bull_quiet",
            confidence=0.9,
            volatility_index=15.0,
            key_drivers=["Strong earnings"]
        )

    def test_negative_ev_rejection(self):
        """Test that negative EV trades are rejected mathematically."""
        decision = SynthesizedDecision(
            asset="BTC-USD", final_decision="long", winning_strategy="Trend",
            synthesized_probability=0.40,  # Only 40% win prob
            uncertainty_score=0.1, expected_value_raw=0.0,
            market_regime=self.regime, reasoning_summary="Testing negative EV"
        )
        # 1% upside, 5% downside => guarantees negative EV
        risk_check = self.rm.evaluate_decision(decision, self.portfolio, 0.01, 0.05)
        self.assertFalse(risk_check.approved)
        self.assertIn("NEGATIVE EV", risk_check.rejection_reason)
        
    def test_positive_ev_kelly_sizing(self):
        """Test Kelly sizing logic correctly sizes positive EV trades."""
        decision = SynthesizedDecision(
            asset="BTC-USD", final_decision="long", winning_strategy="Trend",
            synthesized_probability=0.70, # High 70% win rate
            uncertainty_score=0.1, expected_value_raw=0.0,
            market_regime=self.regime, reasoning_summary="Testing Kelly"
        )
        # Expected Profit 10% vs Loss 5% - high EV
        risk_check = self.rm.evaluate_decision(decision, self.portfolio, 0.10, 0.05)
        self.assertTrue(risk_check.approved)
        self.assertGreater(risk_check.kelly_fraction_suggested, 0.0)
        self.assertLessEqual(risk_check.kelly_fraction_suggested, self.rm.max_exposure_per_trade)

    def test_killswitch_drawdown(self):
        """Test that the 10% Global Drawdown kill-switch violently halts trading."""
        self.portfolio.current_drawdown_pct = 0.12 # 12% drawdown (above the 10% limit)
        decision = SynthesizedDecision(
            asset="ETH-USD", final_decision="long", winning_strategy="Trend",
            synthesized_probability=0.95, uncertainty_score=0.0, expected_value_raw=0.0,
            market_regime=self.regime, reasoning_summary="Test Killswitch"
        )
        risk_check = self.rm.evaluate_decision(decision, self.portfolio, 0.10, 0.05)
        self.assertFalse(risk_check.approved)
        self.assertIn("GLOBAL KILL-SWITCH", risk_check.rejection_reason)

if __name__ == '__main__':
    unittest.main()
