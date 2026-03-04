# config.py
"""
Configuration and constants for the Live Market Analysis Dashboard
Educational purposes only - Not financial advice
"""

import os
from datetime import time
from enum import Enum

# API Configuration (Free tiers)
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "YOUR_FINNHUB_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "YOUR_NEWSAPI_KEY")

# Trading Instruments
INSTRUMENTS = {
    'XAUUSD': {
        'symbol': 'GC=F',  # Gold Futures
        'name': 'Gold',
        'type': 'commodity',
        'pip_size': 0.01,
        'session_volatility': {
            'asia': 0.008,
            'london': 0.015,
            'ny': 0.012,
            'overlap': 0.020
        }
    },
    'BTCUSD': {
        'symbol': 'BTC-USD',
        'name': 'Bitcoin',
        'type': 'crypto',
        'pip_size': 1.0,
        'session_volatility': {
            'asia': 0.025,
            'london': 0.030,
            'ny': 0.035,
            'overlap': 0.040
        }
    }
}

# Timeframes for analysis
TIMEFRAMES = {
    'M5': {'interval': '5m', 'period': '5d', 'minutes': 5},
    'M15': {'interval': '15m', 'period': '15d', 'minutes': 15},
    'H1': {'interval': '1h', 'period': '30d', 'minutes': 60},
    'H4': {'interval': '4h', 'period': '120d', 'minutes': 240}
}

# Session Times (EAT - East Africa Time, UTC+3)
SESSIONS = {
    'asia': {'start': time(3, 0), 'end': time(11, 0)},
    'london': {'start': time(11, 0), 'end': time(20, 0)},
    'ny': {'start': time(16, 0), 'end': time(1, 0)},  # Next day
    'overlap': {'start': time(16, 0), 'end': time(20, 0)}  # London-NY
}

# High Probability Windows (EAT)
TRADING_WINDOWS = {
    'XAUUSD': [
        ('05:00', '06:30'),   # Asia mid-session
        ('10:00', '11:30'),   # London open
        ('15:00', '17:00'),   # London-NY overlap
    ],
    'BTCUSD': [
        ('11:00', '13:00'),   # London open
        ('16:00', '18:00'),   # NY open
        ('21:30', '23:00'),   # US equity open
    ]
}

# Technical Analysis Parameters
IMPULSE_THRESHOLD = 0.015  # 1.5% move for impulse detection
RETRACEMENT_ZONES = [0.50, 0.618, 0.786]
WICK_RATIO_THRESHOLD = 0.6  # Wick must be 60% of candle range
VOLUME_SPIKE_THRESHOLD = 2.0  # 2x average volume
COMPRESSION_ATR_THRESHOLD = 0.5  # ATR compression factor

# Risk Management
MAX_RISK_REWARD = 5.0
MIN_RISK_REWARD = 1.5
DEFAULT_RISK_PERCENT = 1.0

class Trend(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    STRONG_BULLISH = "strong_bullish"
    STRONG_BEARISH = "strong_bearish"

class SetupType(Enum):
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"
    NO_SETUP = "no_setup"
