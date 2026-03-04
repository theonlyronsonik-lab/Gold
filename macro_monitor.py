# macro_monitor.py
"""
Macro-economic and news monitoring
"""

import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

class MacroMonitor:
    def __init__(self):
        self.news_cache: List[Dict] = []
        self.usd_index: float = 100.0
        self.yields: Dict[str, float] = {'10y': 4.0, '2y': 4.5}
        self.last_update = datetime.now()
        
    async def fetch_usd_index(self):
        """Fetch DXY from Yahoo Finance"""
        try:
            import yfinance as yf
            dxy = yf.Ticker("DX-Y.NYB")
            data = dxy.history(period="1d")
            if not data.empty:
                self.usd_index = data['Close'].iloc[-1]
        except Exception as e:
            print(f"USD Index fetch error: {e}")
    
    async def fetch_yields(self):
        """Fetch Treasury yields"""
        try:
            import yfinance as yf
            tnx = yf.Ticker("^TNX")  # 10-year
            data = tnx.history(period="1d")
            if not data.empty:
                self.yields['10y'] = data['Close'].iloc[-1]
        except Exception as e:
            print(f"Yields fetch error: {e}")
    
    async def fetch_news(self):
        """Fetch financial news from NewsAPI"""
        if NEWS_API_KEY == "YOUR_NEWSAPI_KEY":
            return
        
        try:
            url = f"https://newsapi.org/v2/everything?q=gold+OR+federal+reserve+OR+inflation&apiKey={NEWS_API_KEY}&sortBy=publishedAt&pageSize=10"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.news_cache = data.get('articles', [])
        except Exception as e:
            print(f"News fetch error: {e}")
    
    def assess_macro_risk(self, instrument: str) -> Dict:
        """Assess current macro environment risk"""
        risk_score = 0
        factors = []
        
        # USD strength impact
        if instrument == 'XAUUSD':
            if self.usd_index > 102:
                risk_score += 2
                factors.append("Strong USD headwind")
            elif self.usd_index < 98:
                risk_score -= 1
                factors.append("Weak USD tailwind")
        
        # Yield curve impact
        yield_spread = self.yields['10y'] - self.yields.get('2y', 4.0)
        if yield_spread < 0:  # Inverted
            risk_score += 1
            factors.append("Inverted yield curve (recession risk)")
        
        # Recent news sentiment
        high_impact_news = [n for n in self.news_cache if any(word in n.get('title', '').lower() for word in ['fed', 'nfp', 'cpi', 'war', 'crisis'])]
        if len(high_impact_news) > 3:
            risk_score += 2
            factors.append(f"High news volatility ({len(high_impact_news)} major events)")
        
        # Time-based risk (NFP week, FOMC)
        now = datetime.now()
        if now.day <= 7:  # First week of month
            risk_score += 1
            factors.append("NFP week volatility")
        
        risk_level = 'low' if risk_score <= 1 else 'medium' if risk_score <= 3 else 'high'
        
        return {
            'risk_score': risk_score,
            'risk_level': risk_level,
            'factors': factors,
            'usd_index': self.usd_index,
            'yields': self.yields,
            'recent_news': self.news_cache[:3],
            'trade_safe': risk_score <= 3
        }
    
    async def update(self):
        """Update all macro data"""
        await asyncio.gather(
            self.fetch_usd_index(),
            self.fetch_yields(),
            self.fetch_news()
        )
        self.last_update = datetime.now()
