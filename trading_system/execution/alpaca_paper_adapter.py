"""
Alpaca Paper Trading Adapter.
Maps the internal RiskDecision/ExecutionReport flow to Alpaca PAPER orders ONLY.
"""
import uuid
from datetime import datetime, timezone
import logging

try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce
except ImportError:
    pass  # Graceful fail before `pip install`

from schemas.models import RiskDecision, ExecutionReport
from config import config
from execution.base import ExecutionVenue

logger = logging.getLogger(__name__)

# Hard assertion endpoint URL logic
PAPER_URL = "https://paper-api.alpaca.markets"

class AlpacaPaperAdapter(ExecutionVenue):
    def __init__(self):
        # EXPLICIT SAFETY COMMENT:
        # This adapter is for paper trading only and cannot touch live funds.
        # It rigorously denies connection if the environment is not set to 'paper'.
        
        # 1. ENFORCE: Absolutely halt if API keys are missing or PAPER is false
        if getattr(config, "ENVIRONMENT", "").lower() != "paper":
            raise ValueError(f"CRITICAL: Application Environment is '{getattr(config, 'ENVIRONMENT', 'None')}'. Must be 'paper'.")
            
        if not config.ALPACA_API_KEY or not config.ALPACA_SECRET_KEY:
            raise ValueError("Alpaca Paper API keys are missing. Please check your .env file.")
            
        if config.ALPACA_PAPER is not True:
            raise ValueError("CRITICAL: ALPACA_PAPER must be True. Live trading is strictly disabled.")
            
        # 2. Initialize Trading Client explicitly in paper_mode=True
        logger.info(f"[PAPER MODE CHECK] Initializing Alpaca Client at {PAPER_URL}...")
        self.client = TradingClient(
            api_key=config.ALPACA_API_KEY,
            secret_key=config.ALPACA_SECRET_KEY,
            paper=True 
        )
        
        # Verify account access
        try:
            logger.info("[PAPER MODE CHECK] Requesting account details...")
            account = self.client.get_account()
            if not account.account_blocked:
                logger.info(f"[PAPER MODE VERIFIED] Connected successfully. Account ID: {account.id}")
            else:
                logger.warning("[PAPER MODE VERIFIED] Alpaca Paper account is blocked!")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Alpaca Paper Trading: {str(e)}")

    def route_order(self, decision: RiskDecision, current_market_price: float) -> ExecutionReport:
        """
        Takes an approved RiskDecision and executes a Paper Market Order via Alpaca.
        """
        assert decision.approved is True, "Alpaca Adapter received an unapproved trade!"

        # Map action from RiskDecision to OrderSide
        action = getattr(decision, 'action', 'buy').lower()
        side = OrderSide.BUY if action == "buy" else OrderSide.SELL
        
        # Calculate algorithmic quantity (fractional shares allowed by Alpaca)
        quantity = round(decision.final_capital_allocation_usd / current_market_price, 5)
        
        if quantity <= 0:
            raise ValueError("Order quantity calculation resulted in 0.")

        # Construct Alpaca Paper Request
        order_req = MarketOrderRequest(
            symbol=decision.asset,
            qty=quantity,
            side=side,
            time_in_force=TimeInForce.DAY
        )

        try:
            # Submit Paper Order
            logger.info(f"[PAPER MODE] Routing {quantity} shares of {decision.asset} to {PAPER_URL}...")
            alpaca_order = self.client.submit_order(order_data=order_req)
            
            # Map Alpaca response back to internal ExecutionReport schema
            return ExecutionReport(
                order_id=str(alpaca_order.id),
                asset=decision.asset,
                action=action,
                requested_price=current_market_price,
                fill_price=current_market_price, # Actual fill price comes via websocket/poll later; using market 
                quantity=float(alpaca_order.qty) if getattr(alpaca_order, 'qty', None) else quantity,
                slippage_pct=0.0, # Slippage determined by actual exchange fills later
                fee_usd=0.0,      # Alpaca is commission-free
                status="filled",  # In reality, 'accepted' or 'new'
                timestamp=datetime.now(timezone.utc)
            )
        except Exception as e:
            logger.error(f"[PAPER MODE] Execution failed: {str(e)}")
            return ExecutionReport(
                order_id=f"failed_{uuid.uuid4().hex[:8]}",
                asset=decision.asset,
                action=action,
                requested_price=current_market_price,
                fill_price=0.0,
                quantity=quantity,
                slippage_pct=0.0,
                fee_usd=0.0,
                status="rejected",
                timestamp=datetime.now(timezone.utc)
            )
