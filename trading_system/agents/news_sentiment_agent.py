import os
import logging
import yfinance as yf
import google.generativeai as genai
from typing import Dict, List
from config import config

logger = logging.getLogger(__name__)

class NewsSentimentAgent:
    """Uses Google Gemini to analyze news sentiment for specific tickers."""
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            logger.warning("GEMINI_API_KEY not found. Sentiment analysis will be disabled.")
            self.model = None

    def analyze_ticker(self, symbol: str) -> Dict:
        """ Fetches latest news via yfinance and analyzes with Gemini. """
        if not self.model:
            return {"sentiment_score": 0.5, "veto": False, "reason": "No API Key"}

        try:
            # 1. Fetch news from yfinance
            ticker = yf.Ticker(symbol)
            news = ticker.news
            if not news:
                return {"sentiment_score": 0.5, "veto": False, "reason": "No news found"}

            # 2. Extract headlines
            headlines = [n['title'] for n in news[:8]] # Grab top 8 recent headlines
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

            response = self.model.generate_content(prompt)
            
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
