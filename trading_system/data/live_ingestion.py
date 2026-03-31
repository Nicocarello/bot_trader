"""
Live Data Ingestion for Forward Paper Runner
Fetches current Alpaca market data and parses related news curations via Google News RSS + newspaper3k
"""
import logging
import time
import pandas as pd
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
        """
        Fetches live price from Alpaca and computes REAL technical indicators
        from 60 days of yfinance daily history:
          - SMA-20 (20-day Simple Moving Average)
          - Bollinger Bands upper/lower (20-day, 2 std)
          - Z-Score (standard deviations from 20-day mean)
          - BB Width Percentile (squeeze detection vs last 50 bars)
          - Volume Ratio (today's volume vs 20-day avg)
        """
        # --- Step 1: Live price from Alpaca ---
        close_price = 0.0
        volume = 0
        try:
            req = StockSnapshotRequest(symbol_or_symbols=symbol)
            snapshot = self.data_client.get_stock_snapshot(req)[symbol]
            close_price = snapshot.latest_trade.price if snapshot.latest_trade else 0.0
            volume = snapshot.daily_bar.volume if snapshot.daily_bar else 0
        except Exception as e:
            logger.warning(f"  [Alpaca snapshot failed for {symbol}, using yfinance fallback]: {e}")

        # --- Step 2: Historical data from yfinance for real indicators ---
        try:
            hist = yf.download(symbol, period="60d", interval="1d", progress=False, auto_adjust=True)

            if hist.empty or len(hist) < 5:
                raise ValueError("Insufficient historical data.")

            # Use yfinance close as fallback if Alpaca failed
            # Ensure we have a Series for Close prices, handling potential multi-index
            if isinstance(hist["Close"], (float, int)):
                closes = hist["Close"]
            elif "Close" in hist.columns:
                # If multi-index (Ticker, Price), select current symbol if present
                if isinstance(hist.columns, pd.MultiIndex):
                    closes = hist["Close"][symbol].dropna()
                else:
                    closes = hist["Close"].dropna()
            else:
                raise ValueError("Close column missing from history.")

            closes = closes.squeeze().astype(float)
            if close_price == 0.0 and not closes.empty:
                close_price = float(closes.iloc[-1])

            if len(closes) >= 20:
                # --- SMA-20 ---
                sma_20 = float(closes.rolling(20).mean().iloc[-1])

                # --- Bollinger Bands (2 std) ---
                std_20 = float(closes.rolling(20).std().iloc[-1])
                bb_upper = sma_20 + 2.0 * std_20
                bb_lower = sma_20 - 2.0 * std_20
                bb_width = bb_upper - bb_lower

                # --- Z-Score: how many std devs is price from the SMA ---
                z_score = (close_price - sma_20) / std_20 if std_20 > 0 else 0.0

                # --- BB Width Percentile (squeeze detection) ---
                # Measures where current BB width falls vs its history (0=tightest, 100=widest)
                if len(closes) >= 30:
                    all_std = closes.rolling(20).std().dropna()
                    all_widths = all_std * 4.0  # factor for upper-lower spread
                    pct_below = float((all_widths < bb_width).mean() * 100)
                    bb_width_percentile = round(pct_below, 1)
                else:
                    bb_width_percentile = 50.0

                # --- Previous session high ---
                prev_high = float(hist["High"].iloc[-2]) if len(hist) >= 2 else close_price

                # --- Volume ratio: today vs 20-day average ---
                avg_volume_20 = float(hist["Volume"].rolling(20).mean().iloc[-1])
                volume_ratio = (volume / avg_volume_20) if avg_volume_20 > 0 else 1.0

            else:
                # Not enough history — use safe neutral defaults
                logger.warning(f"  [{symbol}] Only {len(closes)} bars available. Using neutral indicator defaults.")
                sma_20    = close_price * 0.99
                bb_upper  = close_price * 1.04
                bb_lower  = close_price * 0.96
                z_score   = 0.0
                bb_width_percentile = 50.0
                prev_high = close_price
                volume_ratio = 1.0

            logger.info(
                f"  [{symbol}] Price=${close_price:.2f} | SMA20=${sma_20:.2f} | "
                f"Z={z_score:.2f} | BB%={bb_width_percentile:.0f} | VolRatio={volume_ratio:.1f}x"
            )

            return {
                "symbol":               symbol,
                "close":                close_price,
                "volume":               volume,
                "volume_ratio":         round(volume_ratio, 2),
                "sma_20":               round(sma_20, 4),
                "prev_high":            round(prev_high, 4),
                "z_score":              round(z_score, 4),
                "bb_upper":             round(bb_upper, 4),
                "bb_lower":             round(bb_lower, 4),
                "bb_width_percentile":  bb_width_percentile,
            }

        except Exception as e:
            logger.error(f"  [{symbol}] Technical indicator calculation failed: {e}. Using fallback.")
            return {
                "symbol":               symbol,
                "close":                close_price or 150.0,
                "volume":               volume,
                "volume_ratio":         1.0,
                "sma_20":               (close_price or 150.0) * 0.99,
                "prev_high":            (close_price or 150.0) * 1.01,
                "z_score":              0.0,
                "bb_upper":             (close_price or 150.0) * 1.04,
                "bb_lower":             (close_price or 150.0) * 0.96,
                "bb_width_percentile":  50.0,
            }

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
            "XLRE": "Real Estate"
        }
        try:
            data = yf.download(list(sectors.keys()), period="2d", interval="1d", progress=False)["Close"]
            latest = data.iloc[-1]
            prev = data.iloc[-2]
            
            returns = {}
            for ticker in sectors:
                try:
                    t_latest = latest[ticker] if ticker in latest else latest
                    t_prev = prev[ticker] if ticker in prev else prev
                    
                    if hasattr(t_latest, "iloc"): t_latest = t_latest.iloc[0]
                    if hasattr(t_prev, "iloc"): t_prev = t_prev.iloc[0]
                    
                    val_latest = float(t_latest)
                    val_prev = float(t_prev)
                    
                    if val_prev > 0:
                        returns[ticker] = (val_latest / val_prev) - 1
                except Exception:
                    continue
            
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
