# session_manager.py
"""
Session detection and timing logic
"""

from datetime import datetime, time
import pytz
from typing import Dict, List, Tuple
from config import SESSIONS, TRADING_WINDOWS

class SessionManager:
    def __init__(self):
        self.eat_tz = pytz.timezone('Africa/Nairobi')  # EAT
        
    def get_current_session(self) -> str:
        """Determine current trading session"""
        now = datetime.now(self.eat_tz)
        current_time = now.time()
        
        # Check overlap first
        overlap_start = SESSIONS['overlap']['start']
        overlap_end = SESSIONS['overlap']['end']
        
        if overlap_start <= current_time <= overlap_end:
            return 'overlap'
        
        # Check individual sessions
        for session_name, times in SESSIONS.items():
            if session_name == 'overlap':
                continue
            if times['start'] <= current_time <= times['end']:
                return session_name
        
        return 'off_hours'
    
    def is_trading_window(self, instrument: str) -> Tuple[bool, str]:
        """Check if current time is in high-probability window"""
        now = datetime.now(self.eat_tz)
        current_time = now.strftime('%H:%M')
        current_hour = now.hour
        current_minute = now.minute
        
        windows = TRADING_WINDOWS.get(instrument, [])
        
        for start, end in windows:
            start_h, start_m = map(int, start.split(':'))
            end_h, end_m = map(int, end.split(':'))
            
            start_minutes = start_h * 60 + start_m
            end_minutes = end_h * 60 + end_m
            current_minutes = current_hour * 60 + current_minute
            
            if start_minutes <= current_minutes <= end_minutes:
                session = self.get_current_session()
                return True, f"Active: {start}-{end} ({session})"
        
        return False, "Outside optimal window"
    
    def get_session_stats(self, instrument: str) -> Dict:
        """Get volatility and liquidity stats for current session"""
        session = self.get_current_session()
        volatility = INSTRUMENTS[instrument]['session_volatility'].get(session, 0.01)
        
        return {
            'session': session,
            'volatility_factor': volatility,
            'liquidity_score': 1.0 if session in ['london', 'overlap'] else 0.7,
            'spread_factor': 0.8 if session == 'overlap' else 1.0
        }
    
    def time_to_next_session(self) -> Dict[str, int]:
        """Calculate time until next major session"""
        now = datetime.now(self.eat_tz)
        current_minutes = now.hour * 60 + now.minute
        
        sessions = {
            'london_open': 11 * 60,  # 11:00 EAT
            'ny_open': 16 * 60,      # 16:00 EAT
            'asia_open': 3 * 60      # 03:00 EAT
        }
        
        times = {}
        for name, minutes in sessions.items():
            diff = minutes - current_minutes
            if diff < 0:
                diff += 24 * 60
            times[name] = diff
        
        return times
