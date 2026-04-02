import os
import logging
import yfinance as yf
from google import genai
from typing import Dict, List
from config import config

logger = logging.getLogger(__name__)

class NewsSentimentAgent:
    """Uses Google Gemini to analyze news sentiment for specific tickers."""
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
            self.model_id = 'gemini-2.5-flash'
        else:
            logger.warning("GEMINI_API_KEY not found. Sentiment analysis will be disabled.")
            self.client = None

    def analyze_ticker(self, symbol: str) -> Dict:
        """ Fetches latest news via yfinance and analyzes with Gemini. """
        if not self.client:
            return {"sentiment_score": 0.5, "veto": False, "reason": "No API Key"}

        try:
            # 1. Fetch news from yfinance
            ticker = yf.Ticker(symbol)
            news = ticker.news
            if not news:
                return {"sentiment_score": 0.5, "veto": False, "reason": "No news found"}

            # 2. Extract headlines safely
            headlines = []
            for n in news[:8]:
                if isinstance(n, dict):
                    # Check both 'title' and 'headline' as fallback, handle missing keys
                    title = n.get('title') or n.get('headline') or "No Title Available"
                    headlines.append(title)
                else:
                    headlines.append(str(n))

            news_text = "\n- ".join(headlines)

            # 3. Prompt Gemini
            prompt = f"""
            You are a senior financial analyst. Analyze the following news headlines for ${symbol} and provide a sentiment assessment.
            
            Headlines:
            - {news_text}
            
            Based on these headlines, answer with a JSON object in this exact format:
            {{
              "score": (float between 0.0 and 1.0, where 0.5 is neutral, >0.6 is positive, <0.4 is negative),
              "veto": (boolean, set to true ONLY if there is critical catastrophic news like lawsuits, fraud, or bankruptcy),
              "reason": "short 1-sentence summary"
            }}
            
            Only output the JSON.
            """

            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            
            # Simple cleanup for JSON parsing
            text = response.text.strip().replace("```json", "").replace("```", "")
            import json
            result = json.loads(text)

            logger.info(f"  [SENTIMENT] {symbol}: Score {result.get('score')} | Veto: {result.get('veto')} | {result.get('reason')}")
            
            return {
                "sentiment_score": result.get("score", 0.5),
                "veto": result.get("veto", False),
                "reason": result.get("reason", "N/A")
            }

        except Exception as e:
            logger.error(f"Error in sentiment analysis for {symbol}: {e}")
            return {"sentiment_score": 0.5, "veto": False, "reason": f"Analysis failed: {e}"}
