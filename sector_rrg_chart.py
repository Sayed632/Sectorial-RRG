"""
sector_rrg_chart.py

Sectorial RRG (Relative Rotation Graph) - the third chart alongside
sector_breadth_treemap.py's breadth table and treemap. Add this as
render_rrg() in a third tab of your Streamlit dashboard.

Concept:
  - Build an equal-weighted composite price series per sector from the
    SECTOR_UNIVERSE (sector_universe_generated.py) stocks.
  - Compare each sector composite to a benchmark (NIFTY 50) to get a
    relative-strength ratio and its momentum (rate of change).
  - Plot sectors on a 4-quadrant scatter with recent "tails":
        Leading    (top-right)    RS-Ratio > 100, RS-Momentum > 100
        Weakening  (bottom-right) RS-Ratio > 100, RS-Momentum < 100
        Lagging    (bottom-left)  RS-Ratio < 100, RS-Momentum < 100
        Improving  (top-left)     RS-Ratio < 100, RS-Momentum > 100

Honest note: the JdK RS-Ratio/RS-Momentum formula used by commercial RRG
tools (StockCharts, OptumaJdK) is proprietary and not publicly documented
in exact form. This uses a standard open-source approximation (z-score
normalized relative strength + smoothed rate of change) that is
directionally equivalent - same quadrant behavior and rotation logic -
but won't produce pixel-identical numbers to a licensed JdK RRG.

Usage as a Streamlit tab:
    from sector_rrg_chart import render_rrg
    render_rrg()
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

BENCHMARK = "^NSEI"  # Nifty 50 index
RS_PERIOD = 10        # smoothing window for RS-Ratio
MOM_PERIOD = 10        # smoothing window for RS-Momentum
TAIL_LENGTH = 8         # number of recent points to show as the "tail"
MAX_STOCKS_PER_SECTOR = 10  # cap for composite calc speed - largest-weight names first


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_close_series(ticker: str, period="1y") -> pd.Series | None:
    try:
        df = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=True)
        if df is None or len(df) < 30:
            return None
        s = df["Close"]
        s.index = s.index.tz_localize(None)
        return s
    except Exception:
        return None


def build_sector_composite(tickers: list[str]) -> pd.Series | None:
    """Equal-weighted composite: normalize each stock to 100 at series start, average."""
    series_list = []
    for t in tickers[:MAX_STOCKS_PER_SECTOR]:
        s = fetch_close_series(t)
        if s is not None and len(s) > 0:
            series_list.append((s / s.iloc[0]) * 100)
    if not series_list:
        return None
    df = pd.concat(series_list, axis=1).ffill().dropna(how="all")
    return df.mean(axis=1)


def compute_rrg_metrics(sector_series: pd.Series, benchmark_series: pd.Series):
    """Approximate JdK-style RS-Ratio and RS-Momentum. See module docstring."""
    aligned = pd.concat([sector_series, benchmark_series], axis=1, join="inner").dropna()
    aligned.columns = ["sector", "benchmark"]
    if len(aligned) < RS_PERIOD + MOM_PERIOD:
        return None, None

    rs = (aligned["sector"] / aligned["benchmark"]) * 100
    rs_mean = rs.rolling(RS_PERIOD).mean()
    rs_std = rs.rolling(RS_PERIOD).std()
    rs_ratio = 100 + (rs - rs_mean) / rs_std.replace(0, np.nan)

    rm_mean = rs_ratio.rolling(MOM_PERIOD).mean()
    rm_std = rs_ratio.rolling(MOM_PERIOD).std()
    rs_momentum = 100 + (rs_ratio - rm_mean) / rm_std.replace(0, np.nan)

    return rs_ratio.dropna(), rs_momentum.dropna()


def quadrant_color(x, y):
    if x >= 100 and y >= 100:
        return "#2ecc71"   # Leading - green
    if x >= 100 and y < 100:
        return "#f39c12"   # Weakening - orange
    if x < 100 and y < 100:
        return "#e74c3c"   # Lagging - red
    return "#3498db"       # Improving - blue


def render_rrg(sector_universe: dict):
    st.header("🔄 Sectorial RRG (Relative Rotation Graph)")
    st.caption(
        "Benchmark: NIFTY 50. Approximation of JdK-style RS-Ratio/RS-Momentum - "
        "directionally accurate, not a licensed-formula exact match."
    )

    with st.spinner("Fetching benchmark and sector composites..."):
        benchmark = fetch_close_series(BENCHMARK)
        if benchmark is None:
            st.error("Could not fetch NIFTY 50 benchmark data.")
            return

        fig = go.Figure()

        # Quadrant background shading
        fig.add_shape(type="rect", x0=100, x1=115, y0=100, y1=115, fillcolor="#2ecc71", opacity=0.08, line_width=0)
        fig.add_shape(type="rect", x0=100, x1=115, y0=85, y1=100, fillcolor="#f39c12", opacity=0.08, line_width=0)
        fig.add_shape(type="rect", x0=85, x1=100, y0=85, y1=100, fillcolor="#e74c3c", opacity=0.08, line_width=0)
        fig.add_shape(type="rect", x0=85, x1=100, y0=100, y1=115, fillcolor="#3498db", opacity=0.08, line_width=0)
        fig.add_hline(y=100, line_dash="dot", line_color="gray")
        fig.add_vline(x=100, line_dash="dot", line_color="gray")

        plotted_any = False
        for sector, tickers in sector_universe.items():
            composite = build_sector_composite(tickers)
            if composite is None:
                continue
            rs_ratio, rs_momentum = compute_rrg_metrics(composite, benchmark)
            if rs_ratio is None or len(rs_ratio) < TAIL_LENGTH:
                continue

            x_tail = rs_ratio.iloc[-TAIL_LENGTH:].values
            y_tail = rs_momentum.reindex(rs_ratio.index).iloc[-TAIL_LENGTH:].values
            if np.isnan(x_tail).any() or np.isnan(y_tail).any():
                continue

            color = quadrant_color(x_tail[-1], y_tail[-1])

            # Tail line
            fig.add_trace(go.Scatter(
                x=x_tail, y=y_tail, mode="lines+markers",
                line=dict(color=color, width=1.5),
                marker=dict(size=5, color=color),
                opacity=0.6, showlegend=False,
                hoverinfo="skip",
            ))
            # Latest point, labeled
            fig.add_trace(go.Scatter(
                x=[x_tail[-1]], y=[y_tail[-1]], mode="markers+text",
                marker=dict(size=13, color=color, line=dict(width=1, color="black")),
                text=[sector], textposition="top center",
                name=sector,
                hovertemplate=f"<b>{sector}</b><br>RS-Ratio: %{{x:.1f}}<br>RS-Momentum: %{{y:.1f}}<extra></extra>",
            ))
            plotted_any = True

        if not plotted_any:
            st.warning("Not enough data to plot RRG yet - try again in a few minutes (rate limits) or check tickers.")
            return

        fig.update_layout(
            xaxis_title="RS-Ratio (Relative Strength vs NIFTY 50)",
            yaxis_title="RS-Momentum",
            height=650,
            annotations=[
                dict(x=112, y=112, text="LEADING", showarrow=False, font=dict(color="#2ecc71", size=12)),
                dict(x=112, y=88, text="WEAKENING", showarrow=False, font=dict(color="#f39c12", size=12)),
                dict(x=88, y=88, text="LAGGING", showarrow=False, font=dict(color="#e74c3c", size=12)),
                dict(x=88, y=112, text="IMPROVING", showarrow=False, font=dict(color="#3498db", size=12)),
            ],
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        "**Reading the chart:** the dot is each sector's current position, the tail shows its "
        f"last {TAIL_LENGTH} days of rotation. Sectors rotate clockwise through the quadrants over time "
        "(Improving → Leading → Weakening → Lagging → Improving) in a healthy market cycle."
    )


if __name__ == "__main__":
    st.set_page_config(page_title="Sectorial RRG", layout="wide")
    # Minimal standalone test with a few sectors - replace with full import in production
    from sector_universe_generated import SECTOR_UNIVERSE
    render_rrg(SECTOR_UNIVERSE)
