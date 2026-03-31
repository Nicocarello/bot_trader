"""
Risk Guard Agent
Monitors open positions for stop-loss and take-profit triggers.
"""
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ExitSignal(BaseModel):
    symbol: str
    action: str = "sell"
    reason: str
    qty: float
    current_price: float
    pnl_pct: float

class RiskGuardAgent:
    def __init__(self, stop_loss_pct: float = -0.05, take_profit_pct: float = 0.10):
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

    def evaluate_positions(self, positions_data: List[Dict[str, Any]]) -> List[ExitSignal]:
        """
        Takes a list of open positions and checks if any trigger an exit.
        """
        exits = []
        
        for pos in positions_data:
            symbol = pos.get('symbol')
            # Alpaca positions have 'unrealized_plpc' (decimal 0.05 = 5%)
            pnl_pct = float(pos.get('unrealized_plpc', 0.0))
            qty = float(pos.get('qty', 0.0))
            current_price = float(pos.get('current_price', 0.0))
            
            # --- Rule 1: Hard Stop Loss ---
            if pnl_pct <= self.stop_loss_pct:
                exits.append(ExitSignal(
                    symbol=symbol,
                    reason=f"STOP LOSS hit ({pnl_pct*100:.1f}%)",
                    qty=qty,
                    current_price=current_price,
                    pnl_pct=pnl_pct
                ))
            
            # --- Rule 2: Take Profit ---
            elif pnl_pct >= self.take_profit_pct:
                exits.append(ExitSignal(
                    symbol=symbol,
                    reason=f"TAKE PROFIT hit ({pnl_pct*100:.1f}%)",
                    qty=qty,
                    current_price=current_price,
                    pnl_pct=pnl_pct
                ))
                
        return exits
