"""
Simulated Broker Execution Stub for Historical Backtesting.
Simulates realistic trade fills locally without touching any external networking.
"""
import uuid
import random
from datetime import datetime, timezone
from schemas.models import RiskDecision, ExecutionReport
from config import config
from execution.base import ExecutionVenue

class SimulatedBroker(ExecutionVenue):
    def __init__(self):
        self.base_slippage = config.ASSUMED_SLIPPAGE_PCT
        self.base_fee = config.ASSUMED_FEE_PCT

    def route_order(self, decision: RiskDecision, current_market_price: float) -> ExecutionReport:
        assert decision.approved is True, "SimulatedBroker received an unapproved trade!"
        
        # Local slippage math representing network latency matching logic
        actual_slippage = self.base_slippage * random.uniform(0.5, 1.5)
        if decision.market_regime.regime in ["bull_volatile", "bear_volatile"]:
            actual_slippage *= 2.0  
            
        action = "buy" 
        if action == "buy":
            fill_price = current_market_price * (1 + actual_slippage)
        else:
            fill_price = current_market_price * (1 - actual_slippage)
            
        quantity = decision.final_capital_allocation_usd / fill_price
        fee_usd = decision.final_capital_allocation_usd * self.base_fee
        
        return ExecutionReport(
            order_id=f"sim_{uuid.uuid4().hex[:8]}",
            asset=decision.asset,
            action=action,
            requested_price=current_market_price,
            fill_price=fill_price,
            quantity=quantity,
            slippage_pct=actual_slippage,
            fee_usd=fee_usd,
            status="filled",
            timestamp=datetime.now(timezone.utc)
        )
