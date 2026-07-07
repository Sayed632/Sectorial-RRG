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

# Native interactive dropdown menu component
selected_universe_name = st.selectbox("Select Target Market Universe:", list(UNIVERSES.keys()))
universe_config = UNIVERSES[selected_universe_name]

# 3. LIVE MARKET DATA PROCESSING
@st.cache_data(ttl=3600)  # Caches data for 1 hour to keep speeds blazing fast
def load_and_calculate_rrg(config):
    benchmark_ticker = config["benchmark"]
    sectors_dict = config["sectors"]
    all_tickers = [benchmark_ticker] + list(sectors_dict.values())
    
    # Download 1 year of weekly intervals via yfinance
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
            rrg_results[name] = df.tail(5)  # Extract trailing historical track lines
            
    return rrg_results

# Execute processing data stream
with st.spinner("Fetching live Yahoo Finance index streams..."):
    rrg_data = load_and_calculate_rrg(universe_config)

# 4. PLOTLY GRAPH VISUALIZATION SETUP
if rrg_data:
    fig = go.Figure()
    
    # Dynamically find min/max values to automatically adjust the chart viewport safely
    all_x = []
    all_y = []
    for df in rrg_data.values():
        all_x.extend(df['RS_Ratio'].tolist())
        min_x, max_x = min(all_x) - 1, max(all_x) + 1
        all_y.extend(df['RS_Momentum'].tolist())
        min_y, max_y = min(all_y) - 1, max(all_y) + 1
        
    # Ensure the chart includes the 100 baseline intersections cleanly
    min_x = min(min_x, 97.0)
    max_x = max(max_x, 103.0)
    min_y = min(min_y, 97.0)
    max_y = max(max_y, 103.0)

    # Generate quadrant color bounds dynamically stretching over calculated margins
    fig.add_shape(type="rect", x0=100, y0=100, x1=max_x, y1=max_y, fillcolor="rgba(34, 197, 94, 0.04)", line_width=0)  # Leading
    fig.add_shape(type="rect", x0=min_x, y0=100, x1=100, y1=max_y, fillcolor="rgba(59, 130, 246, 0.04)", line_width=0)  # Improving
    fig.add_shape(type="rect", x0=min_x, y0=min_y, x1=100, y1=100, fillcolor="rgba(239, 68, 68, 0.04)", line_width=0)   # Lagging
    fig.add_shape(type="rect", x0=100, y0=min_y, x1=max_x, y1=100, fillcolor="rgba(245, 158, 11, 0.04)", line_width=0)  # Weakening

    # Map each sector line and trailing endpoint pointer node
    for sector_name, df in rrg_data.items():
        x_vals = df['RS_Ratio'].tolist()
        y_vals = df['RS_Momentum'].tolist()
        
        # Trailing history line
        fig.add_trace(go.Scatter(x=x_vals, y=y_vals, mode='lines', name=sector_name, line=dict(width=2.5), hoverinfo='name'))
        # Live location marker dot
        fig.add_trace(go.Scatter(x=[x_vals[-1]], y=[y_vals[-1]], mode='markers+text', name=sector_name, text=[sector_name], textposition="top center", marker=dict(size=10, line=dict(width=1, color='black')), showlegend=False))

    # General axes and grid line configuration layouts
    fig.update_layout(
        xaxis=dict(title="JDK RS-Ratio (Trend Strength)", range=[min_x, max_x], gridcolor='lightgray'),
        yaxis=dict(title="JDK RS-Momentum (Velocity)", range=[min_y, max_y], gridcolor='lightgray'),
        width=1000, height=650, plot_bgcolor='white',
        annotations=[
            dict(x=100 + (max_x-100)/2, y=100 + (max_y-100)/2, text="<b>LEADING</b>", showarrow=False, font=dict(color="green", size=14)),
            dict(x=100 - (100-min_x)/2, y=100 + (max_y-100)/2, text="<b>IMPROVING</b>", showarrow=False, font=dict(color="blue", size=14)),
            dict(x=100 - (100-min_x)/2, y=100 - (100-min_y)/2, text="<b>LAGGING</b>", showarrow=False, font=dict(color="red", size=14)),
            dict(x=100 + (max_x-100)/2, y=100 - (100-min_y)/2, text="<b>WEAKENING</b>", showarrow=False, font=dict(color="orange", size=14))
        ]
    )
    fig.add_hline(y=100, line_dash="dash", line_color="gray")
    fig.add_vline(x=100, line_dash="dash", line_color="gray")

    # Render interactive figure natively onto webpage
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("No pricing streams returned for this universe block from Yahoo Finance servers right now.")
