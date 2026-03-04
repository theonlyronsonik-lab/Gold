# main.py
"""
Entry point for the Live Market Analysis Dashboard
"""

import sys
import argparse
from dashboard import app, data_feed, background_updates
import threading

def main():
    parser = argparse.ArgumentParser(description='Live Market Analysis Dashboard')
    parser.add_argument('--port', type=int, default=8050, help='Port to run on')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()
    
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║           LIVE MARKET ANALYSIS DASHBOARD                     ║
    ║                    Educational Tool Only                     ║
    ║              NOT FINANCIAL ADVICE                            ║
    ╚══════════════════════════════════════════════════════════════╝
    
    Features:
    - Real-time XAUUSD & BTCUSD analysis
    - Multi-timeframe trend detection
    - Impulse leg & retracement calculation
    - Wick rejection detection
    - Volume confirmation
    - Session-based timing
    - Macro risk assessment
    
    Access the dashboard at: http://localhost:{port}
    """.format(port=args.port))
    
    # Start background data feed
    feed_thread = threading.Thread(target=background_updates, daemon=True)
    feed_thread.start()
    
    # Run Dash app
    app.run_server(debug=args.debug, host='0.0.0.0', port=args.port)

if __name__ == '__main__':
    main()
