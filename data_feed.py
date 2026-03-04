# data_feed.py
"""
Real-time data acquisition module
Supports multiple free data sources with failover
"""

import asyncio
import aiohttp
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Callable
import websocket
import json
import threading
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PriceTick:
    symbol: str
    price: float
    volume: int
    timestamp: datetime
    bid: float
    ask: float
    spread: float

class DataFeedManager:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.price_cache: Dict[str, PriceTick] = {}
        self.historical_cache: Dict[str, pd.DataFrame] = {}
        self.ws_connections: Dict[str, websocket.WebSocketApp] = {}
        self.running = False
        
    async def start(self):
        """Initialize all data feeds"""
        self.running = True
        await asyncio.gather(
            self._start_yahoo_feed(),
            self._start_finnhub_feed(),
            self._poll_economic_calendar()
        )
    
    async def _start_yahoo_feed(self):
        """Real-time feed from Yahoo Finance"""
        while self.running:
            try:
                for instrument, config in INSTRUMENTS.items():
                    ticker = yf.Ticker(config['symbol'])
                    data = ticker.history(period="1d", interval="1m")
                    
                    if not data.empty:
                        latest = data.iloc[-1]
                        tick = PriceTick(
                            symbol=instrument,
                            price=latest['Close'],
                            volume=int(latest['Volume']),
                            timestamp=datetime.now(),
                            bid=latest['Close'] * 0.9995,
                            ask=latest['Close'] * 1.0005,
                            spread=latest['Close'] * 0.001
                        )
                        self.price_cache[instrument] = tick
                        await self._notify_subscribers(instrument, tick)
                
                await asyncio.sleep(5)  # 5-second update interval
                
            except Exception as e:
                logger.error(f"Yahoo feed error: {e}")
                await asyncio.sleep(10)
    
    async def _start_finnhub_feed(self):
        """WebSocket feed from Finnhub (free tier)"""
        if FINNHUB_API_KEY == "YOUR_FINNHUB_KEY":
            logger.warning("Finnhub API key not set, skipping")
            return
            
        def on_message(ws, message):
            data = json.loads(message)
            if 'p' in data:  # Price update
                tick = PriceTick(
                    symbol=data['s'],
                    price=data['p'],
                    volume=data.get('v', 0),
                    timestamp=datetime.fromtimestamp(data['t']/1000),
                    bid=data.get('b', data['p']),
                    ask=data.get('a', data['p']),
                    spread=data.get('a', data['p']) - data.get('b', data['p'])
                )
                self.price_cache[data['s']] = tick
                asyncio.create_task(self._notify_subscribers(data['s'], tick))
        
        def on_error(ws, error):
            logger.error(f"Finnhub WS error: {error}")
        
        def on_close(ws):
            logger.info("Finnhub WS closed")
        
        # Connect to Finnhub WebSocket
        ws = websocket.WebSocketApp(
            f"wss://ws.finnhub.io?token={FINNHUB_API_KEY}",
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        # Subscribe to symbols
        for instrument in INSTRUMENTS.keys():
            ws.on_open = lambda ws: ws.send(json.dumps({"type":"subscribe", "symbol": instrument}))
        
        wst = threading.Thread(target=ws.run_forever)
        wst.daemon = True
        wst.start()
    
    async def get_historical_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Fetch historical OHLCV data"""
        cache_key = f"{symbol}_{timeframe}"
        
        if cache_key in self.historical_cache:
            cache_time = datetime.now() - timedelta(minutes=TIMEFRAMES[timeframe]['minutes'])
            if self.historical_cache[cache_key].index[-1] > cache_time:
                return self.historical_cache[cache_key]
        
        try:
            config = TIMEFRAMES[timeframe]
            ticker = yf.Ticker(INSTRUMENTS[symbol]['symbol'])
            data = ticker.history(period=config['period'], interval=config['interval'])
            
            # Calculate additional metrics
            data = self._calculate_metrics(data)
            self.historical_cache[cache_key] = data
            
            return data
            
        except Exception as e:
            logger.error(f"Historical data error for {symbol}: {e}")
            return pd.DataFrame()
    
    def _calculate_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical metrics to OHLCV data"""
        df = df.copy()
        
        # Basic indicators
        df['returns'] = df['Close'].pct_change()
        df['range'] = df['High'] - df['Low']
        df['body'] = abs(df['Close'] - df['Open'])
        df['upper_wick'] = df['High'] - df[['Open', 'Close']].max(axis=1)
        df['lower_wick'] = df[['Open', 'Close']].min(axis=1) - df['Low']
        df['wick_ratio'] = (df['upper_wick'] + df['lower_wick']) / df['range']
        
        # Moving averages
        df['ema_20'] = df['Close'].ewm(span=20).mean()
        df['ema_50'] = df['Close'].ewm(span=50).mean()
        df['sma_200'] = df['Close'].rolling(200).mean()
        
        # ATR for volatility
        df['atr_14'] = self._calculate_atr(df, 14)
        
        # Volume metrics
        df['volume_sma'] = df['Volume'].rolling(20).mean()
        df['volume_ratio'] = df['Volume'] / df['volume_sma']
        
        return df
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Average True Range"""
        high_low = df['High'] - df['Low']
        high_close = abs(df['High'] - df['Close'].shift())
        low_close = abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return true_range.rolling(period).mean()
    
    async def _poll_economic_calendar(self):
        """Fetch economic events from ForexFactory or similar"""
        # Implementation would fetch from free calendar API
        while self.running:
            try:
                # Placeholder for economic calendar data
                await asyncio.sleep(300)  # Check every 5 minutes
            except Exception as e:
                logger.error(f"Calendar error: {e}")
    
    async def _notify_subscribers(self, symbol: str, tick: PriceTick):
        """Notify all subscribers of price update"""
        if symbol in self.subscribers:
            for callback in self.subscribers[symbol]:
                try:
                    await callback(tick)
                except Exception as e:
                    logger.error(f"Subscriber error: {e}")
    
    def subscribe(self, symbol: str, callback: Callable):
        """Subscribe to price updates for a symbol"""
        if symbol not in self.subscribers:
            self.subscribers[symbol] = []
        self.subscribers[symbol].append(callback)
    
    def get_current_price(self, symbol: str) -> Optional[PriceTick]:
        """Get latest cached price"""
        return self.price_cache.get(symbol)
    
    def stop(self):
        """Stop all feeds"""
        self.running = False
        for ws in self.ws_connections.values():
            ws.close()
