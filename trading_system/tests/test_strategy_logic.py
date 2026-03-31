"""
Deterministic Strategy Logic Tests.
Validates each strategy adheres strictly to Regime constraints and numeric Entry Triggers.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas.models import MarketRegimeClassification
from agents.strategy_agents import MomentumTrendFollower, MeanReversionAgent, VolatilityBreakoutAgent

class TestStrategyLogic(unittest.TestCase):
    def setUp(self):
        self.momentum = MomentumTrendFollower()
        self.mean_rev = MeanReversionAgent()
        self.vol_break = VolatilityBreakoutAgent()

        # Build Mock Regimes (matching strict schema literals)
        self.regime_bull_volatile = MarketRegimeClassification(regime="bull_volatile", confidence=0.8, volatility_index=25.0, key_drivers=[])
        self.regime_ranging_choppy = MarketRegimeClassification(regime="ranging_choppy", confidence=0.8, volatility_index=10.0, key_drivers=[])
        self.regime_bull_quiet = MarketRegimeClassification(regime="bull_quiet", confidence=0.8, volatility_index=8.0, key_drivers=[])

    def test_momentum_follower(self):
        # 1. Blocks on wrong regime
        data = {"symbol": "AAPL", "close": 160.0, "sma_20": 150.0, "prev_high": 155.0} # Perfect entry math
        prop = self.momentum.process(data, self.regime_ranging_choppy)
        self.assertEqual(prop.decision, "hold")
        
        # 2. Fires Long on correct regime + math
        prop2 = self.momentum.process(data, self.regime_bull_volatile)
        self.assertEqual(prop2.decision, "long")
        
        # 3. Blocks on bad math, correct regime
        data_bad = {"symbol": "AAPL", "close": 140.0, "sma_20": 150.0, "prev_high": 155.0}
        prop3 = self.momentum.process(data_bad, self.regime_bull_volatile)
        self.assertEqual(prop3.decision, "hold")

    def test_mean_reversion(self):
        # 1. Blocks on wrong regime (Bull Volatile)
        data = {"symbol": "AAPL", "z_score": -2.5} # Extreme oversold
        prop = self.mean_rev.process(data, self.regime_bull_volatile)
        self.assertEqual(prop.decision, "hold")
        
        # 2. Fires Long on extreme negative Z in Range
        prop2 = self.mean_rev.process(data, self.regime_ranging_choppy)
        self.assertEqual(prop2.decision, "long")
        
        # 3. Fires Short on extreme positive Z in Range
        data_short = {"symbol": "AAPL", "z_score": 2.1}
        prop3 = self.mean_rev.process(data_short, self.regime_ranging_choppy)
        self.assertEqual(prop3.decision, "short")

    def test_volatility_breakout(self):
        # 1. Fires only on tight squeeze + breakout
        data = {"symbol": "AAPL", "close": 155.0, "bb_width_percentile": 15.0, "bb_upper": 154.0}
        prop = self.vol_break.process(data, self.regime_bull_quiet)
        self.assertEqual(prop.decision, "long")
        
        # 2. Blocks if squeeze isn't tight
        data_loose = {"symbol": "AAPL", "close": 155.0, "bb_width_percentile": 50.0, "bb_upper": 154.0}
        prop2 = self.vol_break.process(data_loose, self.regime_bull_quiet)
        self.assertEqual(prop2.decision, "hold")

        # 3. Blocks on trend regime
        prop3 = self.vol_break.process(data, self.regime_bull_volatile)
        self.assertEqual(prop3.decision, "hold")

if __name__ == '__main__':
    unittest.main()
