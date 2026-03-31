"""
Global Configuration for the AI Trading System (MVP)
"""

import os
from pydantic import field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "AITradingSystem_MVP"
    ENVIRONMENT: str = "paper" # Strictly paper trading
    
    # Portfolio Settings
    INITIAL_CAPITAL_USD: float = 100000.0
    GLOBAL_DRAWDOWN_LIMIT_PCT: float = 0.10  # 10% kill-switch
    MAX_DAILY_LOSS_PCT: float = 0.02         # 2% daily loss limit
    BASE_KELLY_FRACTION: float = 0.25        # Quarter-Kelly logic applied globally
    MAX_RISK_PER_TRADE_PCT: float = 0.05     # Absolute cap on per-trade exposure (5% max)
    
    # Execution Assumptions (Slippage & Fees used in Backtest & Paper Broker)
    # All percentages in this system are represented as DECIMALS (e.g. 0.05 = 5%).
    ASSUMED_SLIPPAGE_PCT: float = 0.0005     # 0.05%
    ASSUMED_FEE_PCT: float = 0.001           # 0.1%
    
    # RAG Vector Store
    VECTOR_DB_PATH: str = "./storage/vector_db"
    
    # News Extraction Curation List
    TRUSTED_NEWS_SOURCES: list = [
        "https://www.reuters.com/markets",
        "https://www.bloomberg.com/markets",
        "https://www.cnbc.com/markets",
        "https://finance.yahoo.com"
    ]
    MAX_ARTICLES_PER_SOURCE: int = 5 

    # Alpaca Paper Trading Config
    ALPACA_API_KEY: str = ""
    ALPACA_SECRET_KEY: str = ""
    ALPACA_PAPER: bool = True # Hardcoded paper validation flag
    
    @field_validator('ALPACA_PAPER')
    @classmethod
    def ensure_paper_trading(cls, v):
        if not v:
            raise ValueError("LIVE TRADING IS strictly disabled. ALPACA_PAPER must be True.")
        return True
    
    class Config:
        env_file = ".env"

config = Settings()
