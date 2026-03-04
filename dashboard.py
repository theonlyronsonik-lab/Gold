# dashboard.py
"""
Interactive Dashboard using Dash/Plotly
Real-time visualization with WebSocket updates
"""

import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from datetime import datetime
import asyncio
import threading
from typing import Dict

# Import our modules
from data_feed import DataFeedManager, PriceTick
from technical_analysis import TechnicalAnalyzer, Setup
from session_manager import SessionManager
from macro_monitor import MacroMonitor
from config import *

# Initialize components
data_feed = DataFeedManager()
analyzer = TechnicalAnalyzer()
session_mgr = SessionManager()
macro_monitor = MacroMonitor()

# Global state
app_state = {
    'current_setups': {},
    'price_history': {},
    'confirmations': {},
    'last_update': datetime.now()
}

# Create Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
app.title = "Live Market Analysis Dashboard"

# Layout
app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.H1("🔴 LIVE Market Analysis Dashboard", className="text-primary"),
            html.P("Educational Tool - Not Financial Advice", className="text-warning"),
            html.Small(f"Last Update: {datetime.now().strftime('%H:%M:%S')}", id='last-update')
        ], width=12)
    ], className="mb-4"),
    
    # Navigation
    dbc.Tabs([
        # Tab 1: Market Overview
        dbc.Tab(label="📊 Market Overview", children=[
            dbc.Row([
                dbc.Col([
                    html.H3("XAUUSD (Gold)", className="mt-3"),
                    html.Div(id='xau-trend-cards'),
                    dcc.Graph(id='xau-chart', style={'height': '600px'})
                ], width=6),
                dbc.Col([
                    html.H3("BTCUSD (Bitcoin)", className="mt-3"),
                    html.Div(id='btc-trend-cards'),
                    dcc.Graph(id='btc-chart', style={'height': '600px'})
                ], width=6)
            ]),
            dbc.Row([
                dbc.Col([
                    html.H4("Session Status"),
                    html.Div(id='session-status')
                ], width=12)
            ])
        ]),
        
        # Tab 2: Confirmation Panel
        dbc.Tab(label="✅ Confirmation Panel", children=[
            dbc.Row([
                dbc.Col([
                    html.H3("XAUUSD Setup Confirmations", className="mt-3"),
                    html.Div(id='xau-confirmations')
                ], width=6),
                dbc.Col([
                    html.H3("BTCUSD Setup Confirmations", className="mt-3"),
                    html.Div(id='btc-confirmations')
                ], width=6)
            ]),
            dbc.Row([
                dbc.Col([
                    html.H4("Live Checklist", className="mt-4"),
                    html.Div(id='live-checklist')
                ], width=12)
            ])
        ]),
        
        # Tab 3: Trade Suggestions
        dbc.Tab(label="🎯 Trade Suggestions", children=[
            dbc.Row([
                dbc.Col([
                    html.H3("Active Setups", className="mt-3"),
                    html.Div(id='active-setups')
                ], width=8),
                dbc.Col([
                    html.H4("Risk Calculator", className="mt-3"),
                    html.Div(id='risk-calculator'),
                    html.Hr(),
                    html.H4("Macro Environment"),
                    html.Div(id='macro-panel')
                ], width=4)
            ])
        ])
    ]),
    
    # Update interval
    dcc.Interval(id='interval-component', interval=5000, n_intervals=0),
    
    # Store for data
    dcc.Store(id='price-store')
], fluid=True)

def create_trend_card(timeframe: str, trend: str) -> dbc.Card:
    """Create trend indicator card"""
    colors = {
        'STRONG_BULLISH': 'success',
        'BULLISH': 'success',
        'NEUTRAL': 'warning',
        'BEARISH': 'danger',
        'STRONG_BEARISH': 'danger'
    }
    
    return dbc.Card([
        dbc.CardBody([
            html.H5(timeframe, className="card-title"),
            html.P(trend.replace('_', ' ').title(), 
                   className=f"text-{colors.get(trend, 'secondary')}")
        ])
    ], className="mb-2")

def create_confirmation_badge(label: str, status: bool) -> html.Div:
    """Create confirmation badge"""
    return html.Div([
        html.Span("✅ " if status else "❌ ", 
                 style={'color': 'green' if status else 'red', 'fontSize': '20px'}),
        html.Span(label, className="ml-2")
    ], className="mb-2")

def create_candlestick_chart(df, instrument: str, setup: Setup = None) -> go.Figure:
    """Create interactive candlestick chart with indicators"""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                       vertical_spacing=0.03, row_heights=[0.7, 0.3])
    
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name=instrument
    ), row=1, col=1)
    
    # Add EMAs
    fig.add_trace(go.Scatter(x=df.index, y=df['ema_20'], 
                            line=dict(color='orange', width=1), name='EMA 20'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['ema_50'], 
                            line=dict(color='blue', width=1), name='EMA 50'), row=1, col=1)
    
    # Volume
    colors = ['red' if df['Open'].iloc[i] > df['Close'].iloc[i] else 'green' 
              for i in range(len(df))]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='Volume'), 
                 row=2, col=1)
    
    # Add setup levels if available
    if setup:
        fig.add_hline(y=setup.entry_price, line_dash="dash", line_color="yellow", 
                     annotation_text="Entry", row=1, col=1)
        fig.add_hline(y=setup.stop_loss, line_dash="dash", line_color="red", 
                     annotation_text="SL", row=1, col=1)
        fig.add_hline(y=setup.take_profit_1, line_dash="dash", line_color="green", 
                     annotation_text="TP1", row=1, col=1)
    
    fig.update_layout(
        title=f'{instrument} Analysis',
        yaxis_title='Price',
        xaxis_rangeslider_visible=False,
        template='plotly_dark',
        height=600
    )
    
    return fig

# Callbacks
@app.callback(
    [Output('xau-chart', 'figure'),
     Output('btc-chart', 'figure'),
     Output('xau-trend-cards', 'children'),
     Output('btc-trend-cards', 'children'),
     Output('session-status', 'children'),
     Output('last-update', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_charts(n):
    """Update all charts and analysis"""
    updates = []
    
    for instrument in ['XAUUSD', 'BTCUSD']:
        try:
            # Get data
            df = asyncio.run(data_feed.get_historical_data(instrument, 'M15'))
            
            if df.empty:
                continue
            
            # Analyze
            trends = analyzer.analyze_trend(df)
            impulses = analyzer.detect_impulse_legs(df, instrument)
            wicks = analyzer.detect_wick_rejections(df)
            compression = analyzer.detect_compression(df)
            volume = analyzer.analyze_volume(df)
            setup = analyzer.generate_setup(instrument, df, trends, impulses, wicks, compression, volume)
            
            # Store state
            app_state['current_setups'][instrument] = setup
            app_state['confirmations'][instrument] = {
                'trends': trends,
                'impulses': impulses,
                'wicks': wicks,
                'compression': compression,
                'volume': volume
            }
            
            # Create chart
            fig = create_candlestick_chart(df, instrument, setup)
            updates.append(fig)
            
            # Create trend cards
            cards = [create_trend_card(tf, trend.value) for tf, trend in trends.items()]
            updates.append(html.Div(cards))
            
        except Exception as e:
            print(f"Error updating {instrument}: {e}")
            updates.append(go.Figure())
            updates.append(html.Div())
    
    # Session status
    session = session_mgr.get_current_session()
    is_window_xau, xau_msg = session_mgr.is_trading_window('XAUUSD')
    is_window_btc, btc_msg = session_mgr.is_trading_window('BTCUSD')
    
    session_div = html.Div([
        dbc.Alert(f"Current Session: {session.upper()}", color="info"),
        dbc.Row([
            dbc.Col([
                html.H5("XAUUSD"),
                dbc.Badge(xau_msg, color="success" if is_window_xau else "secondary")
            ], width=6),
            dbc.Col([
                html.H5("BTCUSD"),
                dbc.Badge(btc_msg, color="success" if is_window_btc else "secondary")
            ], width=6)
        ])
    ])
    
    updates.append(session_div)
    updates.append(f"Last Update: {datetime.now().strftime('%H:%M:%S')}")
    
    return tuple(updates)

@app.callback(
    [Output('xau-confirmations', 'children'),
     Output('btc-confirmations', 'children'),
     Output('live-checklist', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_confirmations(n):
    """Update confirmation panels"""
    xau_div = html.Div()
    btc_div = html.Div()
    checklist_div = html.Div()
    
    for instrument in ['XAUUSD', 'BTCUSD']:
        conf = app_state['confirmations'].get(instrument, {})
        setup = app_state['current_setups'].get(instrument)
        
        if not conf:
            continue
        
        # Create confirmation items
        items = []
        
        # Trend alignment
        trends = conf.get('trends', {})
        trend_aligned = all(t in [Trend.BULLISH, Trend.STRONG_BULLISH] for t in trends.values()) or \
                       all(t in [Trend.BEARISH, Trend.STRONG_BEARISH] for t in trends.values())
        items.append(create_confirmation_badge("Trend Alignment", trend_aligned))
        
        # Impulse leg
        impulses = conf.get('impulses', [])
        has_impulse = len(impulses) > 0
        items.append(create_confirmation_badge("Valid Impulse Leg", has_impulse))
        
        # Retracement
        in_zone = False
        if impulses and setup:
            retracement = analyzer.calculate_retracement_zones(impulses[-1], 
                         data_feed.get_current_price(instrument).price if data_feed.get_current_price(instrument) else 0)
            in_zone = retracement.in_zone
        items.append(create_confirmation_badge("In Retracement Zone", in_zone))
        
        # Compression
        compression = conf.get('compression', {})
        expanding = not compression.get('is_compressed', True)
        items.append(create_confirmation_badge("Expansion Phase", expanding))
        
        # Wick rejection
        wicks = conf.get('wicks', [])
        has_wick = len([w for w in wicks if w.strength in ['medium', 'strong']]) > 0
        items.append(create_confirmation_badge("Wick Rejection", has_wick))
        
        # Volume
        volume = conf.get('volume', {})
        vol_ok = volume.get('confirmation', False)
        items.append(create_confirmation_badge("Volume Confirmation", vol_ok))
        
        # Assign to correct div
        content = html.Div([
            html.H5(instrument),
            html.Div(items),
            html.Hr(),
            html.H6("Setup Status"),
            html.Div(f"Type: {setup.setup_type.value if setup else 'No Setup'}", 
                    className="text-info" if setup else "text-muted"),
            html.Div(f"Confidence: {setup.confidence}%" if setup else "N/A")
        ])
        
        if instrument == 'XAUUSD':
            xau_div = content
        else:
            btc_div = content
    
    # Combined checklist
    all_ready = all(app_state['current_setups'].values())
    checklist_div = dbc.Alert(
        "🟢 TRADE READY - All Confirmations Valid" if all_ready else "⏳ Waiting for Confirmations...",
        color="success" if all_ready else "warning",
        className="text-center"
    )
    
    return xau_div, btc_div, checklist_div

@app.callback(
    [Output('active-setups', 'children'),
     Output('risk-calculator', 'children'),
     Output('macro-panel', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_trade_suggestions(n):
    """Update trade suggestions and calculations"""
    setups_div = html.Div()
    risk_div = html.Div()
    macro_div = html.Div()
    
    # Active setups table
    setup_cards = []
    for instrument, setup in app_state['current_setups'].items():
        if not setup:
            continue
        
        direction_color = "success" if setup.setup_type == SetupType.LONG else "danger"
        
        card = dbc.Card([
            dbc.CardHeader([
                html.H4(f"{instrument} {setup.setup_type.value.upper()}", 
                       className=f"text-{direction_color}")
            ]),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.H5("Entry & Risk"),
                        html.Table([
                            html.Tr([html.Td("Entry:"), html.Td(f"{setup.entry_price}")]),
                            html.Tr([html.Td("Stop Loss:"), html.Td(f"{setup.stop_loss}")]),
                            html.Tr([html.Td("Risk:"), html.Td(f"{abs(setup.entry_price - setup.stop_loss):.2f}")])
                        ], className="table table-dark table-sm")
                    ], width=4),
                    dbc.Col([
                        html.H5("Targets"),
                        html.Table([
                            html.Tr([html.Td("TP1:"), html.Td(f"{setup.take_profit_1}")]),
                            html.Tr([html.Td("TP2:"), html.Td(f"{setup.take_profit_2}")]),
                            html.Tr([html.Td("TP3:"), html.Td(f"{setup.take_profit_3}")])
                        ], className="table table-dark table-sm")
                    ], width=4),
                    dbc.Col([
                        html.H5("Metrics"),
                        html.Table([
                            html.Tr([html.Td("R:R Ratio:"), html.Td(f"1:{setup.risk_reward}")]),
                            html.Tr([html.Td("Confidence:"), html.Td(f"{setup.confidence}%")]),
                            html.Tr([html.Td("Timeframe:"), html.Td(setup.timeframe)])
                        ], className="table table-dark table-sm")
                    ], width=4)
                ]),
                html.Hr(),
                html.H6("Reasoning"),
                html.Ul([html.Li(f"{k}: {v}") for k, v in setup.reasoning.items()])
            ])
        ], className="mb-3")
        
        setup_cards.append(card)
    
    setups_div = html.Div(setup_cards) if setup_cards else html.Div("No active setups", className="text-muted")
    
    # Risk calculator
    risk_div = html.Div([
        html.P("Position Size Calculator"),
        dbc.Input(id="account-size", type="number", placeholder="Account Size ($)", value=10000, className="mb-2"),
        dbc.Input(id="risk-percent", type="number", placeholder="Risk %", value=1.0, className="mb-2"),
        html.Div(id="position-calc-output")
    ])
    
    # Macro panel
    macro = macro_monitor.assess_macro_risk('XAUUSD')
    macro_div = html.Div([
        html.H6(f"USD Index: {macro['usd_index']:.2f}"),
        html.H6(f"10Y Yield: {macro['yields']['10y']:.2f}%"),
        dbc.Badge(f"Risk Level: {macro['risk_level'].upper()}", 
                 color="success" if macro['risk_level'] == 'low' else "warning" if macro['risk_level'] == 'medium' else "danger"),
        html.Ul([html.Li(factor) for factor in macro['factors']]),
        html.Small("Trade Safe: " + ("Yes" if macro['trade_safe'] else "No"), 
                  className="text-success" if macro['trade_safe'] else "text-danger")
    ])
    
    return setups_div, risk_div, macro_div

# Background data update thread
def background_updates():
    """Background thread for data updates"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def update_loop():
        await data_feed.start()
        while True:
            await macro_monitor.update()
            await asyncio.sleep(60)  # Update macro every minute
    
    loop.run_until_complete(update_loop())

# Start background thread
update_thread = threading.Thread(target=background_updates, daemon=True)
update_thread.start()

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8050)
