"""
Abstract Interface for all Execution Venues (Simulated and Forward).
Enforces exact matching schemas regardless of destination path.
"""
from abc import ABC, abstractmethod
from schemas.models import RiskDecision, ExecutionReport

class ExecutionVenue(ABC):
    @abstractmethod
    def route_order(self, decision: RiskDecision, current_market_price: float) -> ExecutionReport:
        """Takes an approved RiskDecision and returns a structured ExecutionReport."""
        pass
