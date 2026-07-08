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
            "Nifty Smallcap 250": "NMLCAP_250.NS"
        }
    }
}

# CONSTITUENT STOCK MAP (Categorized by Sector and Market Cap)
STOCK_MAP = {
    "Nifty Bank": {
        "Large-Cap": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS"],
        "Mid-Cap": ["FEDERALBNK.NS", "IDFCFIRSTB.NS", "AUBANK.NS"],
        "Small-Cap": ["CUB.NS", "KARURVYSYA.NS", "UCOBANK.NS"]
    },
    "Nifty IT": {
        "Large-Cap": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS"],
        "Mid-Cap": ["LTIM.NS", "PERSISTENT.NS", "COFORGE.NS"],
        "Small-Cap": ["KPITTECH.NS", "CYIENT.NS", "ZENSARTECH.NS"]
    },
    "Nifty FMCG": {
        "Large-Cap": ["HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS", "BRITANNIA.NS"],
        "Mid-Cap": ["GODREJCP.NS", "MARICO.NS", "DABUR.NS"],
        "Small-Cap": ["BALRAMCHIN.NS", "AWL.NS", "VBL.NS"]
    },
    "Nifty Pharma": {
        "Large-Cap": ["SUNPHARMA.NS", "CIPLA.NS", "DRREDDY.NS", "DIVISLAB.NS"],
        "Mid-Cap": ["LUPIN.NS", "AUROPHARMA.NS", "TORNTPHARM.NS"],
        "Small-Cap": ["BIOCON.NS", "GLENMARK.NS", "GRANULES.NS"]
    },
    "Nifty Auto": {
        "Large-Cap": ["MARUTI.NS", "TATAMOTORS.NS", "M&M.NS", "BAJAJ-AUTO.NS"],
        "Mid-Cap": ["TVSMOTOR.NS", "TIINDIA.NS", "BHARATFORG.NS"],
        "Small-Cap": ["EXIDEIND.NS", "AMARAJABAT.NS", "BALKRISHIND.NS"]
    },
    "Nifty Metal": {
        "Large-Cap": ["TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS"],
        "Mid-Cap": ["JINDALSTEL.NS", "SAIL.NS", "NMDC.NS"],
        "Small-Cap": ["NATIONALUM.NS", "WELCORP.NS", "APLAPOLLO.NS"]
    },
    "Nifty Infra": {
        "Large-Cap": ["LT.NS", "RELIANCE.NS", "BHARTIARTL.NS", "NTPC.NS"],
        "Mid-Cap": ["GMRINFRA.NS", "IRB.NS", "CONCOR.NS"],
        "Small-Cap": ["NCC.NS", "HFCL.NS", "ENGINERSIN.NS"]
    },
    "Nifty Realty": {
        "Large-Cap": ["DLF.NS", "LODHA.NS", "GODREJPROP.NS"],
        "Mid-Cap": ["OBEROIRLTY.NS", "PRESTIGE.NS", "PHOENIXLTD.NS"],
        "Small-Cap": ["SOBHA.NS", "BRIGADE.NS", "SUNTECK.NS"]
    },
    "Nifty Energy": {
        "Large-Cap": ["RELIANCE.NS", "NTPC.NS", "POWERGRID.NS", "ONGC.NS"],
        "Mid-Cap": ["BPCL.NS", "IOC.NS", "GAIL.NS", "TATAPOWER.NS"],
        "Small-Cap": ["SJVN.NS", "IREDA.NS", "NHPC.NS"]
    }
}

# Compile a flat master list of all available tickers for the search box filter
ALL_AVAILABLE_STOCKS = sorted(list(set([
    stock for sector in STOCK_MAP.values() for cap_group in sector.values() for stock in cap_group
])))

# 2. SIDEBAR - INDIVIDUAL STOCK TREND CHARTER (NEW MODULE)
st.sidebar.header("🔍 Individual Stock Trend Look-up")
st.sidebar.markdown("Pick a stock from your watchlists to verify its daily chart breakout profile before trading.")
selected_stock_ticker = st.sidebar.selectbox("Select Ticker Target:", ALL_AVAILABLE_STOCKS)
lookback_days = st.sidebar.slider("Historical Lookback Window (Days):", min_value=30, max_value=180, value=90)

@st.cache_data(ttl=1800)
def fetch_stock_trend(ticker, days):
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days)
    data = yf.download(ticker, start=start_date, end=end_date, interval="1d", auto_adjust=True)
    return data

if selected_stock_ticker:
    stock_df = fetch_stock_trend(selected_stock_ticker, lookback_days)
    if not stock_df.empty:
        st.sidebar.subheader(f"📈 {selected_stock_ticker.replace('.NS', '')} Daily Trend")
        
        # Plotly chart definition inside the sidebar container
        trend_fig = go.Figure()
        trend_fig.add_trace(go.Scatter(
            x=stock_df.index, y=stock_df['Close'].iloc[:, 0] if isinstance(stock_df['Close'], pd.DataFrame) else stock_df['Close'],
            mode='lines', name='Close Price', line=dict(color='#2563eb', width=2)
        ))
        trend_fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=280, plot_bgcolor='white',
            xaxis=dict(showgrid=True, gridcolor='#f1f5f9'),
            yaxis=dict(showgrid=True, gridcolor='#f1f5f9')
        )
        st.sidebar.plotly_chart(trend_fig, use_container_width=True)
    else:
        st.sidebar.warning("Failed to download pricing data for this stock stream.")


# 3. MAIN DASHBOARD DISPLAY PANEL
st.title("📊 Relative Rotation Graph (RRG) Dashboard")
st.markdown("Track real-time sector velocity and institutional rotation trends across NSE indices.")

selected_universe_name = st.selectbox("Select Target Market Universe:", list(UNIVERSES.keys()))
universe_config = UNIVERSES[selected_universe_name]

# 4. LIVE RRG MARKET DATA PROCESSING
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
        rs = (close_data[ticker] / benchmark_series) * 100
        rs_ratio = 100 + ((rs - rs.rolling(10).mean()) / (rs.rolling(10).std() + 0.001)) * 10
        rs_momentum = 100 + ((rs_ratio - rs_ratio.rolling(10).mean()) / (rs_ratio.rolling(10).std() + 0.001)) * 10
        
        df = pd.DataFrame({"RS_Ratio": rs_ratio, "RS_Momentum": rs_momentum}).dropna()
        if not df.empty:
            rrg_results[name] = df.tail(5)
            
    return rrg_results

with st.spinner("Fetching live Yahoo Finance index streams..."):
    rrg_data = load_and_calculate_rrg(universe_config)

# 5. MAIN RRG PLOTLY CHART DISPLAY
if rrg_data:
    fig = go.Figure()
    
    all_x, all_y = [], []
    for df in rrg_data.values():
        all_x.extend(df['RS_Ratio'].tolist())
        all_y.extend(df['RS_Momentum'].tolist())
    
    max_deviation = max(
        abs(max(all_x) - 100), abs(min(all_x) - 100),
        abs(max(all_y) - 100), abs(min(all_y) - 100)
    ) + 1.5
    
    min_x, max_x = 100 - max_deviation, 100 + max_deviation
    min_y, max_y = 100 - max_deviation, 100 + max_deviation

    fig.add_shape(type="rect", x0=100, y0=100, x1=max_x, y1=max_y, fillcolor="rgba(34, 197, 94, 0.05)", line_width=0)
    fig.add_shape(type="rect", x0=min_x, y0=100, x1=100, y1=max_y, fillcolor="rgba(59, 130, 246, 0.05)", line_width=0)
    fig.add_shape(type="rect", x0=min_x, y0=min_y, x1=100, y1=100, fillcolor="rgba(239, 68, 68, 0.05)", line_width=0)
    fig.add_shape(type="rect", x0=100, y0=min_y, x1=max_x, y1=100, fillcolor="rgba(245, 158, 11, 0.05)", line_width=0)

    for sector_name, df in rrg_data.items():
        x_vals = df['RS_Ratio'].tolist()
        y_vals = df['RS_Momentum'].tolist()
        fig.add_trace(go.Scatter(x=x_vals, y=y_vals, mode='lines', name=sector_name, line=dict(width=2.5), hoverinfo='name'))
        fig.add_trace(go.Scatter(x=[x_vals[-1]], y=[y_vals[-1]], mode='markers+text', name=sector_name, text=[sector_name], textposition="top center", marker=dict(size=10, line=dict(width=1, color='black')), showlegend=False))

    fig.update_layout(
        xaxis=dict(title="JDK RS-Ratio (Trend Strength)", range=[min_x, max_x], gridcolor='lightgray'),
        yaxis=dict(title="JDK RS-Momentum (Velocity)", range=[min_y, max_y], gridcolor='lightgray'),
        width=1000, height=650, plot_bgcolor='white',
        annotations=[
            dict(x=100 + max_deviation/2, y=100 + max_deviation/2, text="<b>LEADING (Strong Momentum)</b>", showarrow=False, font=dict(color="green", size=14)),
            dict(x=100 - max_deviation/2, y=100 + max_deviation/2, text="<b>IMPROVING (Recovering)</b>", showarrow=False, font=dict(color="blue", size=14)),
            dict(x=100 - max_deviation/2, y=100 - max_deviation/2, text="<b>LAGGING (Weak / Avoid)</b>", showarrow=False, font=dict(color="red", size=14)),
            dict(x=100 + max_deviation/2, y=100 - max_deviation/2, text="<b>WEAKENING (Cooling Down)</b>", showarrow=False, font=dict(color="orange", size=14))
        ]
    )
    fig.add_hline(y=100, line_dash="dash", line_color="gray")
    fig.add_vline(x=100, line_dash="dash", line_color="gray")

    st.plotly_chart(fig, use_container_width=True)

    # 6. DYNAMIC INTERPRETATION SECTION
    st.write("---")
    st.header("📋 Real-Time Sector Intelligence Matrix")
    
    quadrants = {"Leading": [], "Improving": [], "Weakening": [], "Lagging": []}
    
    for sector_name, df in rrg_data.items():
        latest_ratio = df['RS_Ratio'].iloc[-1]
        latest_momo = df['RS_Momentum'].iloc[-1]
        
        if latest_ratio >= 100 and latest_momo >= 100:
            quadrants["Leading"].append(sector_name)
        elif latest_ratio < 100 and latest_momo >= 100:
            quadrants["Improving"].append(sector_name)
        elif latest_ratio >= 100 and latest_momo < 100:
            quadrants["Weakening"].append(sector_name)
        else:
            quadrants["Lagging"].append(sector_name)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.success("🟢 LEADING")
        for s in quadrants["Leading"]: st.markdown(f"**• {s}**")
    with col2:
        st.info("🔵 IMPROVING")
        for s in quadrants["Improving"]: st.markdown(f"**• {s}**")
    with col3:
        st.warning("🟡 WEAKENING")
        for s in quadrants["Weakening"]: st.markdown(f"**• {s}**")
    with col4:
        st.error("🔴 LAGGING")
        for s in quadrants["Lagging"]: st.markdown(f"**• {s}**")

    # 7. STRATIFIED ACTIONABLE STOCK LOOKUP GRID
    st.write("---")
    st.header("🎯 Alpha Momentum Watchlist (Target Swing Opportunities)")
    st.markdown("This matrix populates stock tickers matching your active **Leading** and **Improving** sectors, categorized by risk and market cap size.")

    def render_watchlist_column(sectors, header_title):
        st.markdown(f"### {header_title}")
        if not sectors:
            st.write("*No active sectors in this phase.*")
            return
            
        l_caps, m_caps, s_caps = [], [], []
        for sector in sectors:
            if sector in STOCK_MAP:
                l_caps.extend([f"{stock.split('.')[0]} ({sector.replace('Nifty ', '')})" for stock in STOCK_MAP[sector]["Large-Cap"]])
                m_caps.extend([f"{stock.split('.')[0]} ({sector.replace('Nifty ', '')})" for stock in STOCK_MAP[sector]["Mid-Cap"]])
                s_caps.extend([f"{stock.split('.')[0]} ({sector.replace('Nifty ', '')})" for stock in STOCK_MAP[sector]["Small-Cap"]])
        
        st.markdown("**🏢 Large-Cap Bluechips**")
        if l_caps:
            for s in l_caps[:4]: st.markdown(f"`{s}`")
        else: st.write("-")
            
        st.markdown("**🚀 Mid-Cap Momentum**")
        if m_caps:
            for s in m_caps[:4]: st.markdown(f"`{s}`")
        else: st.write("-")
            
        st.markdown("**💎 Small-Cap Breakouts**")
        if s_caps:
            for s in s_caps[:4]: st.markdown(f"`{s}`")
        else: st.write("-")

    watch_col1, watch_col2 = st.columns(2)
    
    with watch_col1:
        render_watchlist_column(quadrants["Improving"], "🔵 Improving Sector Picks (Swing Trading Alerts)")
        st.caption("💡 *Swing Logic:* These stocks possess rising velocity. Look for trend-reversal entries or breakout structures on daily charts.")
        
    with watch_col2:
        render_watchlist_column(quadrants["Leading"], "🟢 Leading Sector Picks (Position & Trend)")
        st.caption("💡 *Trend Logic:* Strong structural alpha. Best utilized for buying high-conviction pullbacks to key moving averages.")

else:
    st.error("No pricing streams returned for this universe block from Yahoo Finance servers right now.")
