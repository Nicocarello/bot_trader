"""
Integration Test proving RiskDecision schemas route universally through both
Backtest Broker and Alpaca Paper Adapter natively via the ExecutionVenue interface.
"""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env variables correctly before test
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / '.env')
except ImportError:
    pass

from schemas.models import RiskDecision, MarketRegimeClassification
from execution.paper_broker import SimulatedBroker
from execution.alpaca_paper_adapter import AlpacaPaperAdapter
from config import config

class TestExecutionVenues(unittest.TestCase):
    def setUp(self):
        # 1. Setup Local Simulated Broker
        self.sim_broker = SimulatedBroker()
        
        # 2. Setup External Adapter safely
        try:
            self.alpaca_broker = AlpacaPaperAdapter()
            self.alpaca_enabled = True
        except Exception:
            self.alpaca_enabled = False
            
        # 3. Build identical universal input Schema payload
        self.dummy_decision = RiskDecision(
            asset="AAPL",
            approved=True,
            net_expected_value_pct=0.05,
            kelly_fraction_suggested=0.05,
            uncertainty_penalty_applied=0.1,
            final_capital_allocation_usd=2.00, # Tiny test exposure mapping accurately to fractions
            market_regime=MarketRegimeClassification(
                regime="bull_quiet", confidence=0.9, volatility_index=15.0, key_drivers=[]
            )
        )

    def test_simulated_broker_schemas(self):
        """Proof that Backtest environment processes RiskDecision seamlessly."""
        report = self.sim_broker.route_order(self.dummy_decision, current_market_price=150.00)
        self.assertEqual(report.asset, "AAPL")
        self.assertEqual(report.status, "filled")
        self.assertTrue(hasattr(report, "slippage_pct"))
        self.assertGreater(report.fill_price, 0.0)

    def test_alpaca_adapter_schemas(self):
        """Proof that Forward Paper Trading processes the SAME RiskDecision format seamlessly."""
        if not self.alpaca_enabled:
            self.skipTest("Alpaca Paper Keys not configured or .env missing. Skipping network test.")
            
        report = self.alpaca_broker.route_order(self.dummy_decision, current_market_price=150.00)
        
        self.assertEqual(report.asset, "AAPL")
        # Ensure status matches correct schema map from Alpaca
        self.assertIn(report.status, ["filled", "accepted", "new"])
        self.assertGreater(report.quantity, 0.0)

if __name__ == '__main__':
    unittest.main()
