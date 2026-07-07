import datetime
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import streamlit as st

# Set up clean browser tab layout
st.set_page_config(page_title="NSE Sectoral RRG Dashboard", layout="wide")

# 1. DEFINE MARKET SEGMENT DATA MAPS
UNIVERSES = {
    "Nifty 50 Sector Matrix": {
        "benchmark": "^NSEI",
        "sectors": {
            "Nifty Bank": "^NSEBANK", "Nifty IT": "^CNXIT", "Nifty FMCG": "^CNXFMCG",
            "Nifty Pharma": "^CNXPHARMA", "Nifty Auto": "^CNXAUTO", "Nifty Metal": "^CNXMETAL",
            "Nifty Infra": "^CNXINFRA", "Nifty Realty": "^CNXREALTY", "Nifty Energy": "^CNXENERGY"
        }
    },
    "Nifty Midcap 50": {
        "benchmark": "^NSEMDCP50",
        "sectors": {
            "Nifty Midcap 100": "NIFTY_MIDCAP_100.NS",
            "Nifty Smallcap 100": "NIFTY_SMALL_100.NS",
            "Nifty MidSmallcap 400": "NIFTY_MIDSML_400.NS",
            "Nifty Microcap 250": "NIFTY_MICRO_250.NS"
        }
    },
    "Nifty Total Market": {
        "benchmark": "^NSEI",
        "sectors": {
            "Nifty 100": "^CNX100",
            "Nifty 200": "^CNX200",
            "Nifty 500": "NIFTY_500.NS",
            "Nifty Smallcap 250": "NIFTY_SMLCAP_250.NS"
        }
    }
}

# 2. STREAMLIT USER INTERFACE CONTROL PANEL
st.title("📊 Relative Rotation Graph (RRG) Dashboard")
st.markdown("Track real-time sector velocity and institutional rotation trends across NSE indices.")

selected_universe_name = st.selectbox("Select Target Market Universe:", list(UNIVERSES.keys()))
universe_config = UNIVERSES[selected_universe_name]

# 3. LIVE MARKET DATA PROCESSING
@st.cache_data(ttl=3600)
def load_and_calculate_rrg(config):
    benchmark_ticker = config["benchmark"]
    sectors_dict = config["sectors"]
    all_tickers = [benchmark_ticker] + list(sectors_dict.values())
    
    raw_data = yf.download(all_tickers, period="1y", interval="1wk", auto_adjust=True)
    if raw_data.empty:
        return None
    
    close_data = raw_data['Close'].ffill()
    benchmark_series = close_data[benchmark_ticker]
    rrg_results = {}
    
    for name, ticker in sectors_dict.items():
        if ticker not in close_data.columns:
            continue
        # Core RRG Mathematical Engine (RS-Ratio & RS-Momentum)
        rs = (close_data[ticker] / benchmark_series) * 100
        rs_ratio = 100 + ((rs - rs.rolling(10).mean()) / (rs.rolling(10).std() + 0.001)) * 10
        rs_momentum = 100 + ((rs_ratio - rs_ratio.rolling(10).mean()) / (rs_ratio.rolling(10).std() + 0.001)) * 10
        
        df = pd.DataFrame({"RS_Ratio": rs_ratio, "RS_Momentum": rs_momentum}).dropna()
        if not df.empty:
            rrg_results[name] = df.tail(5)
            
    return rrg_results

with st.spinner("Fetching live Yahoo Finance index streams..."):
    rrg_data = load_and_calculate_rrg(universe_config)

# 4. PLOTLY GRAPH VISUALIZATION SETUP
if rrg_data:
    fig = go.Figure()
    
    # Calculate perfect square bounds around the center (100, 100)
    all_x = []
    all_y = []
    for df in rrg_data.values():
        all_x.extend(df['RS_Ratio'].tolist())
        all_y.extend(df['RS_Momentum'].tolist())
    
    max_deviation = max(
        abs(max(all_x) - 100), abs(min(all_x) - 100),
        abs(max(all_y) - 100), abs(min(all_y) - 100)
    ) + 1.5
    
    # Force a symmetric view grid window
    min_x, max_x = 100 - max_deviation, 100 + max_deviation
    min_y, max_y = 100 - max_deviation, 100 + max_deviation

    # Clean geometric quadrant background blocks
    fig.add_shape(type="rect", x0=100, y0=100, x1=max_x, y1=max_y, fillcolor="rgba(34, 197, 94, 0.05)", line_width=0)  # Leading
    fig.add_shape(type="rect", x0=min_x, y0=100, x1=100, y1=max_y, fillcolor="rgba(59, 130, 246, 0.05)", line_width=0)  # Improving
    fig.add_shape(type="rect", x0=min_x, y0=min_y, x1=100, y1=100, fillcolor="rgba(239, 68, 68, 0.05)", line_width=0)   # Lagging
    fig.add_shape(type="rect", x0=100, y0=min_y, x1=max_x, y1=100, fillcolor="rgba(245, 158, 11, 0.05)", line_width=0)  # Weakening

    # Plot lines and dots
    for sector_name, df in rrg_data.items():
        x_vals = df['RS_Ratio'].tolist()
        y_vals = df['RS_Momentum'].tolist()
        fig.add_trace(go.Scatter(x=x_vals, y=y_vals, mode='lines', name=sector_name, line=dict(width=2.5), hoverinfo='name'))
        fig.add_trace(go.Scatter(x=[x_vals[-1]], y=[y_vals[-1]], mode='markers+text', name=sector_name, text=[sector_name], textposition="top center", marker=dict(size=10, line=dict(width=1, color='black')), showlegend=False))

    # Grid line configurations layouts
    fig.update_layout(
        xaxis=dict(title="JDK RS-Ratio (Trend Strength)", range=[min_x, max_x], gridcolor='lightgray'),
        yaxis=dict(title="JDK RS-Momentum (Velocity)", range=[min_y, max_y], gridcolor='lightgray'),
        width=1000, height=650, plot_bgcolor='white',
        annotations=[
            dict(x=100 + max_deviation/2, y=100 + max_deviation/2, text="<b>LEADING (Strong Momentum)</b>", showarrow=False, font=dict(color="green", size=14)),
            dict(x=100 - max_deviation/2, y=100 + max_deviation/2, text="<b>IMPROVING (Recovering)</b>", showarrow=False, font=dict(color="blue", size=14)),
            dict(x=100 - max_deviation/2, y=100 - max_deviation/2, text="<b>LAGGING (Weak / Avoid)</b>", showarrow=False, font=dict(color="red", size=14)),
            dict(x=100 + max_deviation/
