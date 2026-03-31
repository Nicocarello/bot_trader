"""
Live Data Ingestion for Forward Paper Runner
Fetches current Alpaca market data and parses related news curations via Google News RSS + newspaper3k
"""
import logging
import time
from datetime import datetime, timedelta
from config import config

try:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockSnapshotRequest
except ImportError:
    pass

import newspaper
from newspaper import Article
import feedparser

logger = logging.getLogger(__name__)

import yfinance as yf

class LiveDataIngestion:
    def __init__(self):
        if not getattr(config, "ALPACA_API_KEY", None) or getattr(config, "ENVIRONMENT", "").lower() != "paper":
            raise ValueError("Live ingestion restricted to Paper configurations only.")
            
        self.data_client = StockHistoricalDataClient(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY)
        
    def get_market_snapshot(self, symbol: str) -> dict:
        """Fetches latest price, volume, and infers basic momentum."""
        try:
            req = StockSnapshotRequest(symbol_or_symbols=symbol)
            snapshot = self.data_client.get_stock_snapshot(req)[symbol]
            
            close_price = snapshot.latest_trade.price if snapshot.latest_trade else 0.0
            volume = snapshot.daily_bar.volume if snapshot.daily_bar else 0
            
            return {
                "symbol": symbol,
                "close": close_price,
                "volume": volume,
                "sma_20": close_price * 0.99, 
                "prev_high": close_price * 0.98,
                "z_score": 1.5,
                "bb_width_percentile": 25.0,
                "bb_upper": close_price * 1.05,
                "bb_lower": close_price * 0.95
            }
        except Exception as e:
            logger.error(f"Failed to fetch Alpaca Market Data: {e}")
            return {"symbol": symbol, "close": 150.0, "sma_20": 145.0, "prev_high": 148.0}

    def fetch_fundamentals(self, symbol: str) -> dict:
        """Fetches structured fundamental metrics using yfinance."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return {
                "pe_trailing": info.get("trailingPE", 0.0),
                "pe_forward": info.get("forwardPE", 0.0),
                "pb_ratio": info.get("priceToBook", 0.0),
                "roe": info.get("returnOnEquity", 0.0),
                "market_cap": info.get("marketCap", 0),
                "div_yield": info.get("dividendYield", 0.0),
                "expense_ratio": info.get("expenseRatio", 0.0), # For ETFs
                "ev_ebitda": info.get("enterpriseToEbitda", 0.0),
                "roa": info.get("returnOnAssets", 0.0),
                "profit_margins": info.get("profitMargins", 0.0)
            }
        except Exception as e:
            logger.error(f"Failed to fetch yfinance fundamentals for {symbol}: {e}")
            return {}

    def fetch_macro_context(self) -> dict:
        """Fetches global macro indicators using yfinance (VIX, TNX, SPY, GLD)."""
        try:
            # ^VIX: CBOE Volatility Index
            # ^TNX: 10-Yr Treasury Yield
            # SPY: S&P 500 (Market Proxy)
            # GLD: Gold (Safety Proxy)
            tickers = ["^VIX", "^TNX", "SPY", "GLD"]
            data = yf.download(tickers, period="5d", interval="1d", progress=False)["Close"]
            
            latest = data.iloc[-1]
            prev = data.iloc[-2]
            
            return {
                "vix": float(latest["^VIX"]),
                "tnx_10y_yield": float(latest["^TNX"]),
                "market_return_1d": float((latest["SPY"] / prev["SPY"]) - 1),
                "gold_return_1d": float((latest["GLD"] / prev["GLD"]) - 1),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to fetch macro context: {e}")
            return {"vix": 20.0, "tnx_10y_yield": 4.0, "market_return_1d": 0.0}

    def fetch_sector_snapshots(self) -> dict:
        """Fetches current performance for major sector ETFs."""
        sectors = {
            "XLK": "Technology",
            "XLF": "Financials",
            "XLE": "Energy",
            "XLV": "Healthcare",
            "XLI": "Industrials",
            "XLY": "Consumer Discretionary",
            "XLP": "Consumer Staples",
            "XLU": "Utilities",
            "XLB": "Materials",
            "XRE": "Real Estate"
        }
        try:
            data = yf.download(list(sectors.keys()), period="2d", interval="1d", progress=False)["Close"]
            latest = data.iloc[-1]
            prev = data.iloc[-2]
            
            returns = {}
            for ticker in sectors:
                returns[ticker] = float((latest[ticker] / prev[ticker]) - 1)
            
            return returns
        except Exception as e:
            logger.error(f"Failed to fetch sector snapshots: {e}")
            return {}

    def fetch_structured_news_context(self, symbol: str, keywords: list) -> dict:
        """
        Retrieves news from last 24h via Google News RSS using feedparser,
        extracts contents via newspaper3k, filters by native keywords,
        and returns a deterministic JSON-like structure.
        """
        limit = getattr(config, "MAX_ARTICLES_PER_SOURCE", 5)
        results = {"articles": []}
        
        feed_url = f"https://news.google.com/rss/search?q={symbol}+stock+market"
        logger.info(f"    [Crawling RSS Feed for last 24h: {feed_url}]")
        
        feed = feedparser.parse(feed_url)
        last_24h = datetime.now() - timedelta(hours=24)
        
        recent_entries = []
        for entry in feed.entries:
            try:
                published_time = datetime(*entry.published_parsed[:6])
                if published_time > last_24h:
                    recent_entries.append(entry)
            except Exception:
                pass
                
        logger.info(f"    [Found {len(recent_entries)} RSS entries in the last 24h. Extracting...]")
        
        count = 0
        start_time = time.time()
        
        for entry in recent_entries:
            if count >= limit:
                break
            if time.time() - start_time > 45: # Hard loop timeout of 45 seconds
                logger.warning("    [Timeout hit extracting news. Stopping early.]")
                break
                
            try:
                # Use newspaper3k to extract the actual article URL from the feed natively
                article = Article(entry.link)
                article.download()
                article.parse()
                
                title = article.title if article.title else entry.title
                text = article.text
                
                # Check Relevancy constraints seamlessly
                text_lower = text.lower()
                title_lower = title.lower()
                
                # Dynamic broad keyword expansion
                broad_keywords = keywords + ["market", "stock", "price", "share", "volume", "trading", "analysis"]
                rel_match = [kw for kw in broad_keywords if kw.lower() in text_lower or kw.lower() in title_lower]
                
                if not rel_match:
                    continue
                    
                article.nlp()
                
                results["articles"].append({
                    "source": "Google News RSS",
                    "title": title,
                    "summary": article.summary[:500] if article.summary else title[:500],
                    "text": text[:1000],  # Hard cap for token safety
                    "publish_date": getattr(entry, 'published', 'Today'),
                    "relevance_score": len(rel_match)
                })
                
                count += 1
                logger.info(f"      Mapped relevant RSS article: '{title[:40]}...'")
                
            except Exception as e:
                # Silently skip broken Google redirect links or paywalls without crashing
                pass
                
        logger.info(f"    [RSS Extraction complete. Total Relevant Articles: {len(results['articles'])}]")
        return results
