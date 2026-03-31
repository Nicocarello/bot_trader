"""
Forward Life-Simulation Engine (Paper Trading Runner).
Strictly decoupled from Backtest Engine.
Runs live Alpaca Paper trades over the network.

Architecture:
  - Macro Layer (once per cycle): Fetches VIX, Yields, Gold for global context.
  - Sector Layer (once per cycle): Fetches all sector ETF returns for rotation analysis.
  - Regime Layer (per symbol): Classifies market regime using price + macro.
  - Strategy Fleet (per symbol): Generates trade proposals.
  - Coordinator: Synthesizes debate from all proposals.
  - Risk Gate: Validates EV and position sizing.
  - Execution Router: Routes approved orders to Alpaca Paper.
"""
import sys
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / '.env')
except ImportError:
    pass

from schemas.models import TradeProposal, PortfolioState, MarketRegimeClassification, RAGContext
from risk.risk_manager import RiskManager
from execution.alpaca_paper_adapter import AlpacaPaperAdapter
from agents.strategy_agents import MomentumTrendFollower, MeanReversionAgent, VolatilityBreakoutAgent, FundamentalAnalystAgent
from agents.analytical_agents import MarketRegimeAgent, MacroEconomicsAgent
from agents.sector_agent import SectorFlowAgent
from agents.calendar_agent import CalendarAgent
from agents.risk_guard_agent import RiskGuardAgent
from agents.coordinator import StrategyCoordinator
from data.live_ingestion import LiveDataIngestion
from config import config

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# --- DRY RUN FLAG ---
# Set to False ONLY to allow live paper ordering over the actual Alpaca REST hook
DRY_RUN = False


class PaperTradingRunner:
    def __init__(self, initial_capital: float = 100000.0):
        if config.ALPACA_PAPER is not True or getattr(config, "ENVIRONMENT", "").lower() != "paper":
            raise ValueError("CRITICAL: PaperRunner instantiated outside of Paper conditions.")

        self.portfolio = PortfolioState(
            total_capital_usd=initial_capital,
            available_cash_usd=initial_capital,
            open_positions={},
            daily_realized_pnl_pct=0.0,
            current_drawdown_pct=0.0
        )
        self.risk_manager = RiskManager()
        self.adapter = AlpacaPaperAdapter()
        self.ingestion = LiveDataIngestion()
        self.coordinator = StrategyCoordinator()

        # Analytical agents (shared context, run once per full cycle)
        self.regime_agent = MarketRegimeAgent()
        self.macro_agent = MacroEconomicsAgent()
        self.sector_agent = SectorFlowAgent()
        self.risk_guard = RiskGuardAgent(stop_loss_pct=-0.05, take_profit_pct=0.10)
        self.calendar_agent = CalendarAgent(earnings_days_before=3, earnings_days_after=1)

        # Strategy fleet (per-symbol)
        self.strategies = [
            MomentumTrendFollower(),
            MeanReversionAgent(),
            VolatilityBreakoutAgent(),
            FundamentalAnalystAgent()
        ]

    def run_full_cycle(self, universe: list):
        """Runs one complete orchestration cycle over the full ticker universe."""

        logger.info("\n╔══════════════════════════════════════════════════════╗")
        logger.info("║     MULTI-SECTOR PAPER RUNNER — CYCLE START          ║")
        logger.info(f"║     Universe: {len(universe)} tickers                            ║")
        logger.info("╚══════════════════════════════════════════════════════╝")

        # ─────────────────────────────────────────────────────
        # PHASE 0: Economic Calendar Blackout Check (once per cycle)
        # ─────────────────────────────────────────────────────
        econ_check = self.calendar_agent.check_economic_blackout()
        if econ_check["blackout"]:
            logger.warning(f"\n🚫 [ECONOMIC BLACKOUT] {econ_check['reason']}")
            logger.warning("   No trades will be placed today. Bot shutting down cycle.")
            return

        # ─────────────────────────────────────────────────────
        # PHASE 1: Global Context (runs ONCE per cycle)
        # ─────────────────────────────────────────────────────
        logger.info("\n[PHASE 1] Fetching Global Macro Context...")
        macro_data = self.ingestion.fetch_macro_context()
        logger.info(f"  VIX:          {macro_data.get('vix', 'N/A'):.2f}")
        logger.info(f"  10Y Yield:    {macro_data.get('tnx_10y_yield', 'N/A'):.2f}%")
        logger.info(f"  Market Ret:   {macro_data.get('market_return_1d', 0) * 100:.2f}%")
        logger.info(f"  Gold Ret:     {macro_data.get('gold_return_1d', 0) * 100:.2f}%")

        macro_assessment = self.macro_agent.process(macro_data)
        logger.info(f"  Macro Bias:   {macro_assessment.get('bias', 'neutral').upper()}")
        if macro_assessment.get('headwinds'):
            logger.info(f"  ⚠ Headwinds: {', '.join(macro_assessment['headwinds'])}")
        if macro_assessment.get('tailwinds'):
            logger.info(f"  ✓ Tailwinds: {', '.join(macro_assessment['tailwinds'])}")

        # ─────────────────────────────────────────────────────
        # PHASE 2: Sector Rotation Analysis (runs ONCE per cycle)
        # ─────────────────────────────────────────────────────
        logger.info("\n[PHASE 2] Analyzing Sector Rotation...")
        sector_returns = self.ingestion.fetch_sector_snapshots()
        if sector_returns:
            sorted_sectors = sorted(sector_returns.items(), key=lambda x: x[1], reverse=True)
            logger.info(f"  Leading Sector: {sorted_sectors[0][0]} ({sorted_sectors[0][1]*100:.2f}%)")
            logger.info(f"  Lagging Sector: {sorted_sectors[-1][0]} ({sorted_sectors[-1][1]*100:.2f}%)")
        else:
            logger.warning("  [!] No sector data retrieved. Proceeding with 'neutral' rotation bias.")

        # ─────────────────────────────────────────────────────
        # PHASE 3: Risk Monitoring (Exits: Stop Loss / Take Profit)
        # ─────────────────────────────────────────────────────
        logger.info("\n[PHASE 3] Monitoring Open Positions for Exits...")
        try:
            # Fetch real positions from Alpaca for exit logic
            positions = self.execution.client.get_all_positions()
            
            # Map into a simplified dictionary list for the RiskGuardAgent
            pos_dicts = []
            for p in positions:
                pos_dicts.append({
                    'symbol': p.symbol,
                    'qty': float(p.qty),
                    'unrealized_plpc': float(p.unrealized_plpc),
                    'current_price': float(p.current_price)
                })
            
            # Request exit signals from RiskGuardAgent
            exits = self.risk_guard.evaluate_positions(pos_dicts)
            
            if not exits:
                logger.info("  No exit triggers hit. All positions within risk bounds.")
            else:
                for exit_sig in exits:
                    logger.warning(f"  🚨 [EXIT SIGNAL] {exit_sig.symbol}: {exit_sig.reason} @ ${exit_sig.current_price:.2f}")
                    
                    # Convert ExitSignal into a synthetic RiskDecision for the adapter
                    from schemas.models import RiskDecision
                    exit_decision = RiskDecision(
                        asset=exit_sig.symbol,
                        action="sell",
                        approved=True,
                        final_capital_allocation_usd=exit_sig.qty * exit_sig.current_price,
                        reasoning=exit_sig.reason
                    )
                    
                    # Execute the SELL order immediately
                    report = self.execution.route_order(exit_decision, exit_sig.current_price)
                    logger.info(f"  [EXECUTION] Sell order: {report.status} for {report.quantity} shares.")
                    
        except Exception as e:
            logger.error(f"  [ERROR] Position monitoring failed: {e}")

        # ─────────────────────────────────────────────────────
        # PHASE 4: Per-Symbol Analysis Loop
        # ─────────────────────────────────────────────────────
        logger.info(f"\n[PHASE 4] Starting per-symbol analysis loop ({len(universe)} tickers)...")

        for symbol in universe:
            logger.info(f"\n{'─'*60}")
            logger.info(f"  SYMBOL: {symbol}")
            logger.info(f"{'─'*60}")
            try:
                self._run_symbol_cycle(symbol, macro_data, macro_assessment, sector_returns)
            except Exception as e:
                logger.error(f"  [ERROR] Unhandled exception for {symbol}: {e}")
                continue

        logger.info("\n╔══════════════════════════════════════════════════════╗")
        logger.info("║     CYCLE COMPLETE                                   ║")
        logger.info("╚══════════════════════════════════════════════════════╝\n")


    def _run_symbol_cycle(
        self, symbol: str,
        macro_data: dict,
        macro_assessment: dict,
        sector_returns: dict
    ):
        """Runs the full analysis + execution pipeline for a single symbol."""

        # 1. Ingest Market Data
        market_data = self.ingestion.get_market_snapshot(symbol)
        current_price = market_data.get("close", 0.0)
        logger.info(f"  Price: ${current_price:.2f}")

        # 2. Sector Flow Assessment
        sector_context = self.sector_agent.process(symbol, sector_returns)
        sector_bias = sector_context.get("sector_bias", "neutral")
        logger.info(f"  Sector: {sector_context.get('sector_ticker', 'N/A')} | Bias: {sector_bias.upper()}")
        logger.info(f"  {sector_context.get('reasoning', '')}")

        # 3. Skip if strong sector headwind AND macro is also bearish
        if sector_bias == "headwind" and macro_assessment.get("bias") == "bearish_headwinds":
            logger.info(f"  [SKIP] Double headwind (Sector + Macro). Strong no-trade signal.")
            return

        # 4. Earnings Calendar Blackout check (per-symbol)
        calendar_check = self.calendar_agent.is_clear_to_trade(symbol)
        if not calendar_check["clear"]:
            logger.warning(f"  📅 {calendar_check['reason']}")
            return
        logger.info(f"  📅 {calendar_check['reason']}")

        # 5. Fetch Fundamentals
        fundamentals = self.ingestion.fetch_fundamentals(symbol)
        market_data["fundamentals"] = fundamentals


        # 5. Precise Regime Classification using Macro + Technical data
        regime: MarketRegimeClassification = self.regime_agent.process(market_data, macro_data)
        logger.info(f"  Regime: {regime.regime.upper()} (conf: {regime.confidence:.2f})")

        # 6. Ingest News Context
        keywords = [symbol, "stock", "market", "finance", "earnings"]
        news_payload = self.ingestion.fetch_structured_news_context(symbol, keywords)
        top_summaries = [a["summary"] for a in news_payload.get("articles", [])]
        sources = [a["source"] for a in news_payload.get("articles", [])]
        conf = 0.8 if top_summaries else 0.5
        rag_context = RAGContext(
            query=symbol,
            top_k_chunks=top_summaries,
            source_documents=sources,
            retrieval_confidence=conf
        )
        logger.info(f"  News Articles Found: {len(top_summaries)}")

        # 7. Adjust market_data with sector bias signal for strategies
        market_data["sector_bias"] = sector_bias
        market_data["macro_bias"] = macro_assessment.get("bias", "neutral")

        # 8. Generate Strategy Proposals
        proposals = []
        for strategy in self.strategies:
            prop = strategy.process(market_data, regime)
            proposals.append(prop)

        decisions_str = " | ".join(f"{s.name[:8]}:{p.decision.upper()}" for s, p in zip(self.strategies, proposals))
        logger.info(f"  Proposals: {decisions_str}")

        # 9. Coordinator Synthesis
        synth_decision = self.coordinator.process(
            asset=symbol, proposals=proposals, regime=regime, rag_context=rag_context
        )
        logger.info(f"  Synthesis: {synth_decision.final_decision.upper()} via {synth_decision.winning_strategy}")

        if synth_decision.final_decision in ["no_trade", "hold"]:
            logger.info(f"  [NO TRADE] {synth_decision.reasoning_summary}")
            return

        # 10. Risk Gate
        risk_decision = self.risk_manager.evaluate_decision(
            decision=synth_decision,
            portfolio=self.portfolio,
            expected_upside_pct=0.04,
            expected_downside_pct=0.02
        )

        if not risk_decision.approved:
            logger.info(f"  [REJECTED BY RISK] {risk_decision.rejection_reason}")
            return

        logger.info(f"  [✓ RISK APPROVED] Capital: ${risk_decision.final_capital_allocation_usd:.2f}")

        # 11. Execution Router
        if DRY_RUN:
            logger.info(f"  [DRY RUN] Would send {synth_decision.final_decision.upper()} "
                        f"${risk_decision.final_capital_allocation_usd:.2f} of {symbol} to Alpaca.")
            return

        try:
            report = self.adapter.route_order(risk_decision, current_price)
            logger.info(f"  [✅ FILLED] {report.status.upper()} | {report.quantity} shares @ ${report.fill_price:.2f}")
        except Exception as e:
            logger.error(f"  [❌ EXECUTION FAILED] {e}")


if __name__ == "__main__":
    UNIVERSE = [
        # --- Megacap Tech ---
        "AAPL", "NVDA", "TSLA", "MSFT", "AMZN", "META", "GOOGL", "AMD", "NFLX",
        # --- Banking & Finance ---
        "JPM", "GS", "BAC", "MS", "V", "MA",
        # --- Energy & Industrials ---
        "XOM", "CVX", "SLB", "BA", "CAT",
        # --- Crypto-Linked & Fintech ---
        "COIN", "MARA", "PYPL", "SQ",
        # --- Market Tracking / ETFs ---
        "SPY", "QQQ", "IWM", "GLD",
        # --- International (LatAm / Japan / Brazil) ---
        "MELI", "EWJ", "EWZ"
    ]


    try:
        runner = PaperTradingRunner()
        runner.run_full_cycle(universe=UNIVERSE)
    except Exception as e:
        logger.error(f"FATAL ORCHESTRATION ERROR: {e}")
