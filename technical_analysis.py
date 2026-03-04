# technical_analysis.py
"""
Core technical analysis engine
Pattern recognition and setup detection
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
from config import *

@dataclass
class ImpulseLeg:
    start_idx: int
    end_idx: int
    start_price: float
    end_price: float
    direction: str  # 'up' or 'down'
    size_pips: float
    duration_bars: int
    
@dataclass
class RetracementZone:
    level_50: float
    level_618: float
    level_786: float
    current_price: float
    in_zone: bool
    distance_to_618: float

@dataclass
class WickRejection:
    direction: str  # 'bullish' or 'bearish'
    price: float
    wick_size: float
    body_size: float
    ratio: float
    strength: str  # 'weak', 'medium', 'strong'

@dataclass
class Setup:
    instrument: str
    setup_type: SetupType
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    risk_reward: float
    confidence: float
    timeframe: str
    timestamp: datetime
    reasoning: Dict

class TechnicalAnalyzer:
    def __init__(self):
        self.impulse_history: Dict[str, List[ImpulseLeg]] = {}
        
    def analyze_trend(self, df: pd.DataFrame) -> Dict[str, Trend]:
        """Multi-timeframe trend analysis"""
        trends = {}
        
        # M5 Trend
        trends['M5'] = self._calculate_trend(df.tail(20), short_term=True)
        
        # M15 Trend  
        trends['M15'] = self._calculate_trend(df.tail(48), short_term=True)
        
        # H1 Trend
        trends['H1'] = self._calculate_trend(df.tail(100), short_term=False)
        
        # H4 Trend (aggregated)
        h4_df = self._aggregate_to_h4(df)
        trends['H4'] = self._calculate_trend(h4_df, short_term=False)
        
        return trends
    
    def _calculate_trend(self, df: pd.DataFrame, short_term: bool = True) -> Trend:
        """Calculate trend strength and direction"""
        if len(df) < 20:
            return Trend.NEUTRAL
        
        ema_fast = df['Close'].ewm(span=8 if short_term else 20).mean().iloc[-1]
        ema_slow = df['Close'].ewm(span=21 if short_term else 50).mean().iloc[-1]
        price = df['Close'].iloc[-1]
        
        # Trend strength based on alignment
        bullish_score = 0
        if price > ema_fast:
            bullish_score += 1
        if ema_fast > ema_slow:
            bullish_score += 1
        if df['Close'].iloc[-1] > df['Close'].iloc[-5]:
            bullish_score += 1
            
        bearish_score = 0
        if price < ema_fast:
            bearish_score += 1
        if ema_fast < ema_slow:
            bearish_score += 1
        if df['Close'].iloc[-1] < df['Close'].iloc[-5]:
            bearish_score += 1
        
        # ADX for trend strength
        adx = self._calculate_adx(df)
        
        if bullish_score >= 2 and adx > 25:
            return Trend.STRONG_BULLISH if adx > 40 else Trend.BULLISH
        elif bearish_score >= 2 and adx > 25:
            return Trend.STRONG_BEARISH if adx > 40 else Trend.BEARISH
        else:
            return Trend.NEUTRAL
    
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average Directional Index"""
        plus_dm = df['High'].diff()
        minus_dm = df['Low'].diff().abs()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        tr = pd.concat([
            df['High'] - df['Low'],
            abs(df['High'] - df['Close'].shift()),
            abs(df['Low'] - df['Close'].shift())
        ], axis=1).max(axis=1)
        
        atr = tr.rolling(period).mean()
        
        plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
        
        dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
        adx = dx.rolling(period).mean()
        
        return adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 0
    
    def detect_impulse_legs(self, df: pd.DataFrame, instrument: str) -> List[ImpulseLeg]:
        """Detect significant impulse legs in price action"""
        impulses = []
        min_move = IMPULSE_THRESHOLD
        
        # Find swing highs and lows
        highs = df['High'].values
        lows = df['Low'].values
        closes = df['Close'].values
        
        i = 0
        while i < len(df) - 5:
            # Look for impulse start
            start_price = closes[i]
            
            # Check forward for significant move
            for j in range(i+3, min(i+50, len(df))):
                end_price = closes[j]
                move_pct = (end_price - start_price) / start_price
                
                if abs(move_pct) > min_move:
                    direction = 'up' if move_pct > 0 else 'down'
                    
                    # Validate impulse structure (higher highs/lows or lower highs/lows)
                    valid = self._validate_impulse_structure(df.iloc[i:j+1], direction)
                    
                    if valid:
                        impulse = ImpulseLeg(
                            start_idx=i,
                            end_idx=j,
                            start_price=start_price,
                            end_price=end_price,
                            direction=direction,
                            size_pips=abs(end_price - start_price) / INSTRUMENTS[instrument]['pip_size'],
                            duration_bars=j-i
                        )
                        impulses.append(impulse)
                        i = j  # Skip to end of this impulse
                        break
            i += 1
        
        return impulses[-3:]  # Return last 3 impulses
    
    def _validate_impulse_structure(self, df: pd.DataFrame, direction: str) -> bool:
        """Validate that price action follows impulse structure"""
        if len(df) < 5:
            return False
            
        if direction == 'up':
            # Check for higher highs and higher lows
            highs = df['High'].values
            lows = df['Low'].values
            
            higher_highs = sum(1 for i in range(1, len(highs)) if highs[i] > highs[i-1])
            higher_lows = sum(1 for i in range(1, len(lows)) if lows[i] > lows[i-1])
            
            return higher_highs >= len(highs) * 0.6 and higher_lows >= len(lows) * 0.5
        else:
            # Check for lower highs and lower lows
            highs = df['High'].values
            lows = df['Low'].values
            
            lower_highs = sum(1 for i in range(1, len(highs)) if highs[i] < highs[i-1])
            lower_lows = sum(1 for i in range(1, len(lows)) if lows[i] < lows[i-1])
            
            return lower_highs >= len(highs) * 0.6 and lower_lows >= len(lows) * 0.5
    
    def calculate_retracement_zones(self, impulse: ImpulseLeg, current_price: float) -> RetracementZone:
        """Calculate Fibonacci retracement zones"""
        if impulse.direction == 'up':
            diff = impulse.end_price - impulse.start_price
            level_50 = impulse.end_price - (diff * 0.50)
            level_618 = impulse.end_price - (diff * 0.618)
            level_786 = impulse.end_price - (diff * 0.786)
        else:
            diff = impulse.start_price - impulse.end_price
            level_50 = impulse.end_price + (diff * 0.50)
            level_618 = impulse.end_price + (diff * 0.618)
            level_786 = impulse.end_price + (diff * 0.786)
        
        # Check if price is in retracement zone
        zone_high = max(level_50, level_618)
        zone_low = min(level_50, level_618)
        in_zone = zone_low <= current_price <= zone_high
        
        distance = abs(current_price - level_618)
        
        return RetracementZone(
            level_50=level_50,
            level_618=level_618,
            level_786=level_786,
            current_price=current_price,
            in_zone=in_zone,
            distance_to_618=distance
        )
    
    def detect_wick_rejections(self, df: pd.DataFrame) -> List[WickRejection]:
        """Detect significant wick rejections"""
        rejections = []
        
        for i in range(-5, 0):  # Last 5 candles
            if i < -len(df):
                continue
                
            candle = df.iloc[i]
            range_size = candle['range']
            
            if range_size == 0:
                continue
            
            upper_wick_pct = candle['upper_wick'] / range_size
            lower_wick_pct = candle['lower_wick'] / range_size
            body_pct = candle['body'] / range_size
            
            # Bullish rejection (long lower wick)
            if lower_wick_pct > WICK_RATIO_THRESHOLD and candle['Close'] > candle['Open']:
                strength = 'strong' if lower_wick_pct > 0.7 and body_pct > 0.2 else 'medium'
                rejections.append(WickRejection(
                    direction='bullish',
                    price=candle['Low'],
                    wick_size=candle['lower_wick'],
                    body_size=candle['body'],
                    ratio=lower_wick_pct,
                    strength=strength
                ))
            
            # Bearish rejection (long upper wick)
            elif upper_wick_pct > WICK_RATIO_THRESHOLD and candle['Close'] < candle['Open']:
                strength = 'strong' if upper_wick_pct > 0.7 and body_pct > 0.2 else 'medium'
                rejections.append(WickRejection(
                    direction='bearish',
                    price=candle['High'],
                    wick_size=candle['upper_wick'],
                    body_size=candle['body'],
                    ratio=upper_wick_pct,
                    strength=strength
                ))
        
        return rejections
    
    def detect_compression(self, df: pd.DataFrame, lookback: int = 20) -> Dict:
        """Detect market compression/consolidation"""
        recent = df.tail(lookback)
        
        current_atr = recent['atr_14'].iloc[-1]
        historical_atr = df['atr_14'].rolling(lookback*3).mean().iloc[-1]
        
        compression_ratio = current_atr / historical_atr if historical_atr > 0 else 1
        
        # Bollinger Band squeeze
        bb_width = (recent['High'].rolling(20).std() * 2).iloc[-1]
        price_range = recent['High'].max() - recent['Low'].min()
        
        is_compressed = compression_ratio < COMPRESSION_ATR_THRESHOLD
        is_squeeze = bb_width < price_range * 0.1
        
        return {
            'is_compressed': is_compressed,
            'compression_ratio': compression_ratio,
            'is_squeeze': is_squeeze,
            'atr_current': current_atr,
            'atr_historical': historical_atr,
            'range_bound': price_range < historical_atr * 2
        }
    
    def analyze_volume(self, df: pd.DataFrame) -> Dict:
        """Volume analysis for confirmation"""
        recent = df.tail(20)
        
        avg_volume = recent['volume_sma'].iloc[-1]
        current_volume = recent['Volume'].iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # Volume trend
        volume_trend = 'increasing' if recent['Volume'].iloc[-1] > recent['Volume'].iloc[-5] else 'decreasing'
        
        # Check for abnormal spikes
        is_spike = volume_ratio > VOLUME_SPIKE_THRESHOLD
        
        return {
            'current_volume': current_volume,
            'average_volume': avg_volume,
            'volume_ratio': volume_ratio,
            'volume_trend': volume_trend,
            'is_spike': is_spike,
            'confirmation': volume_ratio > 1.0 and volume_trend == 'increasing'
        }
    
    def generate_setup(self, 
                      instrument: str,
                      df: pd.DataFrame,
                      trends: Dict[str, Trend],
                      impulses: List[ImpulseLeg],
                      wicks: List[WickRejection],
                      compression: Dict,
                      volume: Dict) -> Optional[Setup]:
        """Generate trading setup based on all confirmations"""
        
        if not impulses or not wicks:
            return None
        
        current_price = df['Close'].iloc[-1]
        latest_impulse = impulses[-1]
        
        # Calculate retracement
        retracement = self.calculate_retracement_zones(latest_impulse, current_price)
        
        # Determine setup direction
        setup_type = SetupType.NO_SETUP
        
        # Bullish setup conditions
        bullish_conditions = [
            latest_impulse.direction == 'up',
            any(w.direction == 'bullish' and w.strength in ['medium', 'strong'] for w in wicks),
            retracement.in_zone or retracement.distance_to_618 < current_price * 0.002,
            trends['M15'] in [Trend.BULLISH, Trend.STRONG_BULLISH],
            trends['H1'] in [Trend.BULLISH, Trend.STRONG_BULLISH, Trend.NEUTRAL],
            volume['confirmation'],
            not compression['is_compressed']  # Want expansion, not compression
        ]
        
        # Bearish setup conditions
        bearish_conditions = [
            latest_impulse.direction == 'down',
            any(w.direction == 'bearish' and w.strength in ['medium', 'strong'] for w in wicks),
            retracement.in_zone or retracement.distance_to_618 < current_price * 0.002,
            trends['M15'] in [Trend.BEARISH, Trend.STRONG_BEARISH],
            trends['H1'] in [Trend.BEARISH, Trend.STRONG_BEARISH, Trend.NEUTRAL],
            volume['confirmation'],
            not compression['is_compressed']
        ]
        
        bullish_score = sum(bullish_conditions)
        bearish_score = sum(bearish_conditions)
        
        if bullish_score >= 5:
            setup_type = SetupType.LONG
            entry_price = retracement.level_618
            stop_loss = min([w.price for w in wicks if w.direction == 'bullish'] + [retracement.level_786])
            # Projections
            impulse_size = latest_impulse.end_price - latest_impulse.start_price
            take_profit_1 = latest_impulse.end_price + (impulse_size * 0.5)
            take_profit_2 = latest_impulse.end_price + impulse_size
            take_profit_3 = latest_impulse.end_price + (impulse_size * 1.618)
            
        elif bearish_score >= 5:
            setup_type = SetupType.SHORT
            entry_price = retracement.level_618
            stop_loss = max([w.price for w in wicks if w.direction == 'bearish'] + [retracement.level_786])
            # Projections
            impulse_size = latest_impulse.start_price - latest_impulse.end_price
            take_profit_1 = latest_impulse.end_price - (impulse_size * 0.5)
            take_profit_2 = latest_impulse.end_price - impulse_size
            take_profit_3 = latest_impulse.end_price - (impulse_size * 1.618)
        else:
            return None
        
        # Calculate risk/reward
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit_1 - entry_price)
        risk_reward = reward / risk if risk > 0 else 0
        
        if risk_reward < MIN_RISK_REWARD:
            return None
        
        confidence = (bullish_score if setup_type == SetupType.LONG else bearish_score) / 7 * 100
        
        return Setup(
            instrument=instrument,
            setup_type=setup_type,
            entry_price=round(entry_price, 2),
            stop_loss=round(stop_loss, 2),
            take_profit_1=round(take_profit_1, 2),
            take_profit_2=round(take_profit_2, 2),
            take_profit_3=round(take_profit_3, 2),
            risk_reward=round(risk_reward, 2),
            confidence=round(confidence, 1),
            timeframe='M15',
            timestamp=datetime.now(),
            reasoning={
                'trend_score': trends,
                'impulse_valid': True,
                'retracement_zone': retracement.in_zone,
                'wick_rejection': True,
                'volume_confirmed': volume['confirmation'],
                'compression': compression['is_compressed']
            }
        )
    
    def _aggregate_to_h4(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate 1H data to 4H"""
        return df.resample('4H').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
