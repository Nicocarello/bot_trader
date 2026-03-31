import time
import random
import pandas as pd
from typing import List, Dict, Any
from schemas.models import TradeProposal, PortfolioState, SynthesizedDecision, AgentProbability, MarketRegimeClassification, RAGContext
from risk.risk_manager import RiskManager
from execution.paper_broker import SimulatedBroker
from backtest.metrics import BacktestMetrics

from agents.coordinator import StrategyCoordinator
from agents.strategy_agents import MomentumTrendFollower, MeanReversionAgent, VolatilityBreakoutAgent

class BacktestEngine:
    def __init__(self, initial_capital: float = 100000.0, seed: int = 42):
        self.portfolio = PortfolioState(
            total_capital_usd=initial_capital,
            available_cash_usd=initial_capital,
            open_positions={},
            daily_realized_pnl_pct=0.0,
            current_drawdown_pct=0.0
        )
        self.risk_manager = RiskManager()
        self.broker = SimulatedBroker()
        
        self.coordinator = StrategyCoordinator()
        self.strategies = [
            MomentumTrendFollower(),
            MeanReversionAgent(),
            VolatilityBreakoutAgent()
        ]
        
        self.trade_log = []
        random.seed(seed) # Strict deterministic replay
        self.equity_curve = []

    def _infer_regime(self, bar: pd.Series) -> MarketRegimeClassification:
        # Simple dynamic market regime classifier applied row-by-row
        current = bar.get('close', 100.0)
        sma = bar.get('sma_20', current)
        z = bar.get('z_score', 0.0)
        
        if current > sma and abs(z) < 1.0:
            regime = "bull_quiet"
        elif current > sma and z >= 1.0:
            regime = "bull_volatile"
        elif current < sma and z <= -1.0:
            regime = "bear_volatile"
        elif current < sma and abs(z) < 1.0:
            regime = "bear_quiet"
        else:
            regime = "ranging_choppy"
            
        return MarketRegimeClassification(
            regime=regime,
            confidence=0.8,
            volatility_index=15.0,
            key_drivers=["offline_synthetic_backtest"]
        )

    def run(self, historical_data: pd.DataFrame):
        """Iterates offline bar-by-bar, generates true proposals, delegates to coordinator, and executes simulated ticks."""
        
        for index, bar in historical_data.iterrows():
            current_price = float(bar['close'])
            symbol = bar.get('symbol', 'AAPL')
            
            # --- 1. Synthesize Bar State ---
            regime = self._infer_regime(bar)
            
            rag_context = RAGContext(
                query=str(symbol),
                top_k_chunks=["Historical data replay simulation block."],
                source_documents=["local_offline_data"],
                retrieval_confidence=0.9
            )
            
            market_data = bar.to_dict()
            market_data['symbol'] = symbol
            
            # --- 2. Alpha Generation via Native Strategy Fleet ---
            proposals = []
            for strategy in self.strategies:
                prop = strategy.process(market_data, regime)
                proposals.append(prop)
                
            # --- 3. Deterministic Debate & Synthesis ---
            synth_decision = self.coordinator.process(
                asset=str(symbol),
                proposals=proposals,
                regime=regime,
                rag_context=rag_context
            )
            
            if synth_decision.final_decision not in ["no_trade", "hold"]:
                # --- 4. Risk Scaling ---
                risk_decision = self.risk_manager.evaluate_decision(
                    decision=synth_decision,
                    portfolio=self.portfolio,
                    expected_upside_pct=0.04,
                    expected_downside_pct=0.02
                )

                if risk_decision.approved:
                    # --- 5. Forward Simulation Hook (100% Offline) ---
                    execution_report = self.broker.route_order(risk_decision, current_price)
                    self.trade_log.append(execution_report)
                    
                    self.portfolio.available_cash_usd -= execution_report.fee_usd
                    
                    if execution_report.action == "buy": 
                        self.portfolio.open_positions[str(symbol)] = self.portfolio.open_positions.get(str(symbol), 0.0) + execution_report.quantity
                        self.portfolio.available_cash_usd -= (execution_report.quantity * execution_report.fill_price)
                    elif execution_report.action == "sell":
                        current_qty = self.portfolio.open_positions.get(str(symbol), 0.0)
                        sold_qty = min(execution_report.quantity, current_qty) 
                        self.portfolio.open_positions[str(symbol)] = max(0.0, current_qty - sold_qty)
                        self.portfolio.available_cash_usd += (sold_qty * execution_report.fill_price)

            # --- 6. Tick-by-Tick Settlement / MTM Mapping ---
            asset_value = sum(qty * current_price for asset, qty in self.portfolio.open_positions.items())
            self.portfolio.total_capital_usd = self.portfolio.available_cash_usd + asset_value
            self.equity_curve.append(self.portfolio.total_capital_usd)

        # 7. Post-Run Statistical Metrics
        returns = [self.equity_curve[i] / self.equity_curve[i-1] - 1 for i in range(1, len(self.equity_curve))] if len(self.equity_curve) > 1 else [0.0]
        sharpe = BacktestMetrics.calculate_sharpe_ratio(returns)
        max_dd = BacktestMetrics.calculate_max_drawdown(self.equity_curve)
        
        return {
            "final_capital": self.portfolio.total_capital_usd,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd,
            "total_trades": len(self.trade_log)
        }
