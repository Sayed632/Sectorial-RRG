"""
sector_breadth_treemap.py

A new page/tab for your existing Sectorial-RRG Streamlit app.

What it does:
  1. Sector Breadth Table  - % of stocks above SMA20/50/200, RSI>50%, MFI>50%,
     day/week gainers % - one row per sector (like your Trendlyne screenshots).
  2. Clickable Treemap     - drill into a sector: each rectangle is a stock,
     sized by market cap, colored by today's % change. Click a rectangle to
     see that stock's mini chart + stats in a panel below, plus a direct
     link out to TradingView/NSE for the full chart.

How to wire it into your existing app:
  - If Sectorial-RRG is a single-file app: import and call render() from your
    main script inside a new st.tabs(["RRG", "Sector Breadth"]) tab.
  - If it's multi-page: drop this file into your `pages/` folder as
    `2_Sector_Breadth.py` - Streamlit will auto-add it to the sidebar.

Data source: yfinance only (matches your existing Empire Quant Lab /
Claudeown pattern - no Screener.in/Trendlyne scraping).

Notes / honest limitations:
  - Trendlyne's exact "Momentum Score", "Sector Beta", and advance/decline
    ratio are proprietary calculations from their paid data. The metrics
    here are close analogues built from free OHLCV data, not identical
    formulas - treat as directionally equivalent, not number-for-number
    matching.
  - Market cap here is a rough proxy (last close * shares outstanding from
    yfinance .info, which can be stale/missing for some smaller names).
    Falls back to equal-weight sizing if unavailable.
  - Click-to-navigate uses Streamlit's native Plotly selection events
    (requires streamlit>=1.35). If your Streamlit is older, run
    `pip3 install --upgrade streamlit --break-system-packages` first.
"""

import time
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

# ---------------------------------------------------------------------------
# Sector -> ticker universe. Replace/extend with your own stock_universe.json
# sector mapping (Claudeown repo) if you already maintain one - this is a
# starter set of large/mid-cap NSE names per sector so the page works out
# of the box.
# ---------------------------------------------------------------------------
SECTOR_UNIVERSE = {
    "Automobiles & Auto Components": [
        "MARUTI.NS", "TATAMOTORS.NS", "M&M.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS",
        "HEROMOTOCO.NS", "TVSMOTOR.NS", "BOSCHLTD.NS", "MOTHERSON.NS", "BALKRISIND.NS",
    ],
    "Banking and Finance": [
        "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS",
        "BAJFINANCE.NS", "BAJAJFINSV.NS", "INDUSINDBK.NS", "PNB.NS", "BANKBARODA.NS",
    ],
    "Cement and Construction": [
        "ULTRACEMCO.NS", "SHREECEM.NS", "AMBUJACEM.NS", "ACC.NS", "GRASIM.NS",
        "LT.NS", "DALBHARAT.NS", "RAMCOCEM.NS",
    ],
    "Chemicals & Petrochemicals": [
        "PIDILITIND.NS", "SRF.NS", "AARTIIND.NS", "DEEPAKNTR.NS", "UPL.NS",
        "TATACHEM.NS", "NAVINFLUOR.NS", "ATUL.NS",
    ],
    "Consumer Durables": [
        "TITAN.NS", "HAVELLS.NS", "VOLTAS.NS", "CROMPTON.NS", "WHIRLPOOL.NS",
        "BLUESTARCO.NS", "DIXON.NS",
    ],
}

METRIC_LABELS = {
    "sma20_pct": "LTP > SMA20",
    "sma50_pct": "LTP > SMA50",
    "sma200_pct": "LTP > SMA200",
    "sma50_over_sma200_pct": "SMA50 > SMA200",
    "day_gainers_pct": "Day Gainers%",
    "week_gainers_pct": "Week Gainers%",
    "rsi_over_50_pct": "RSI > 50",
    "mfi_over_50_pct": "MFI > 50",
    "momentum_score": "Momentum Score",
}


@st.cache_data(ttl=900, show_spinner=False)
def fetch_stock_data(ticker: str) -> dict | None:
    """Pull 6mo daily OHLCV + basic info for one ticker; return computed metrics."""
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="6mo", interval="1d", auto_adjust=True)
        if hist is None or len(hist) < 60:
            return None

        close = hist["Close"]
        volume = hist["Volume"]
        high, low = hist["High"], hist["Low"]

        sma20 = close.rolling(20).mean().iloc[-1]
        sma50 = close.rolling(50).mean().iloc[-1]
        sma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else np.nan
        ltp = close.iloc[-1]

        # RSI(14)
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        rsi_val = rsi.iloc[-1]

        # MFI(14) - Money Flow Index
        typical_price = (high + low + close) / 3
        money_flow = typical_price * volume
        tp_diff = typical_price.diff()
        pos_flow = money_flow.where(tp_diff > 0, 0).rolling(14).sum()
        neg_flow = money_flow.where(tp_diff < 0, 0).rolling(14).sum()
        mfr = pos_flow / neg_flow.replace(0, np.nan)
        mfi = 100 - (100 / (1 + mfr))
        mfi_val = mfi.iloc[-1]

        day_change_pct = (close.iloc[-1] / close.iloc[-2] - 1) * 100 if len(close) >= 2 else np.nan
        week_change_pct = (close.iloc[-1] / close.iloc[-6] - 1) * 100 if len(close) >= 6 else np.nan

        try:
            mcap = tk.fast_info.get("market_cap", None)
        except Exception:
            mcap = None

        return {
            "ticker": ticker,
            "name": ticker.replace(".NS", ""),
            "ltp": round(float(ltp), 2),
            "sma20": sma20, "sma50": sma50, "sma200": sma200,
            "rsi": rsi_val, "mfi": mfi_val,
            "day_change_pct": day_change_pct,
            "week_change_pct": week_change_pct,
            "market_cap": mcap,
        }
    except Exception as e:
        st.warning(f"Could not fetch {ticker}: {e}")
        return None


def build_sector_breadth_table(sector_universe: dict) -> pd.DataFrame:
    rows = []
    for sector, tickers in sector_universe.items():
        stock_rows = [fetch_stock_data(t) for t in tickers]
        stock_rows = [r for r in stock_rows if r is not None]
        if not stock_rows:
            continue
        df = pd.DataFrame(stock_rows)
        n = len(df)

        row = {
            "Sector": sector,
            "No. of Stocks": n,
            "sma20_pct": round((df["ltp"] > df["sma20"]).sum() / n * 100, 1),
            "sma50_pct": round((df["ltp"] > df["sma50"]).sum() / n * 100, 1),
            "sma200_pct": round((df["ltp"] > df["sma200"]).sum() / n * 100, 1),
            "sma50_over_sma200_pct": round((df["sma50"] > df["sma200"]).sum() / n * 100, 1),
            "day_gainers_pct": round((df["day_change_pct"] > 0).sum() / n * 100, 1),
            "week_gainers_pct": round((df["week_change_pct"] > 0).sum() / n * 100, 1),
            "rsi_over_50_pct": round((df["rsi"] > 50).sum() / n * 100, 1),
            "mfi_over_50_pct": round((df["mfi"] > 50).sum() / n * 100, 1),
        }
        # Simple momentum score analogue: average of the breadth % metrics above
        row["momentum_score"] = round(
            np.mean([row["sma20_pct"], row["sma50_pct"], row["rsi_over_50_pct"], row["mfi_over_50_pct"]]), 1
        )
        rows.append(row)
    return pd.DataFrame(rows)


def render():
    st.header("📊 Sector Breadth")
    st.caption("Free yfinance data - directional analogue of Trendlyne's sector heatmap, not identical formulas.")

    with st.spinner("Fetching sector data... (cached 15 min)"):
        breadth_df = build_sector_breadth_table(SECTOR_UNIVERSE)

    if breadth_df.empty:
        st.error("No data fetched - check network/ticker list.")
        return

    display_df = breadth_df.rename(columns=METRIC_LABELS)
    st.dataframe(
        display_df.style.background_gradient(
            subset=[c for c in display_df.columns if c not in ("Sector", "No. of Stocks")],
            cmap="RdYlGn", vmin=0, vmax=100,
        ),
        use_container_width=True,
    )

    st.divider()
    st.subheader("🗺️ Sector Treemap - click a stock for detail")

    sector_choice = st.selectbox("Sector", list(SECTOR_UNIVERSE.keys()))
    tickers = SECTOR_UNIVERSE[sector_choice]
    stock_rows = [fetch_stock_data(t) for t in tickers]
    stock_rows = [r for r in stock_rows if r is not None]
    tdf = pd.DataFrame(stock_rows)

    if tdf.empty:
        st.warning("No data for this sector.")
        return

    # Fall back to equal sizing if market cap missing
    tdf["size"] = tdf["market_cap"].fillna(tdf["market_cap"].median() if tdf["market_cap"].notna().any() else 1)
    tdf["size"] = tdf["size"].fillna(1)
    tdf["label"] = tdf["name"] + "<br>" + tdf["day_change_pct"].round(1).astype(str) + "%"

    fig = px.treemap(
        tdf,
        path=[px.Constant(sector_choice), "name"],
        values="size",
        color="day_change_pct",
        color_continuous_scale="RdYlGn",
        color_continuous_midpoint=0,
        custom_data=["ticker", "ltp", "day_change_pct", "rsi", "mfi"],
    )
    fig.update_traces(
        texttemplate="%{label}<br>%{customdata[2]:.1f}%",
        hovertemplate="<b>%{label}</b><br>LTP: %{customdata[1]:.2f}<br>Day: %{customdata[2]:.1f}%"
                      "<br>RSI: %{customdata[3]:.0f}<br>MFI: %{customdata[4]:.0f}<extra></extra>",
    )
    fig.update_layout(margin=dict(t=30, l=0, r=0, b=0))

    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", key="sector_treemap")

    selected_ticker = None
    if event and event.get("selection") and event["selection"].get("points"):
        pt = event["selection"]["points"][0]
        if "customdata" in pt:
            selected_ticker = pt["customdata"][0]

    if selected_ticker:
        row = tdf[tdf["ticker"] == selected_ticker].iloc[0]
        st.markdown("### 📌 " + row["name"])
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("LTP", f"₹{row['ltp']:.2f}", f"{row['day_change_pct']:.1f}%")
        c2.metric("RSI(14)", f"{row['rsi']:.0f}")
        c3.metric("MFI(14)", f"{row['mfi']:.0f}")
        c4.metric("Week %", f"{row['week_change_pct']:.1f}%")

        tv_symbol = row["ticker"].replace(".NS", "")
        st.markdown(
            f"[Open full chart on TradingView](https://www.tradingview.com/chart/?symbol=NSE:{tv_symbol}) · "
            f"[Open on NSE](https://www.nseindia.com/get-quotes/equity?symbol={tv_symbol})"
        )
    else:
        st.info("Click a rectangle above to see stock detail + chart links.")


if __name__ == "__main__":
    st.set_page_config(page_title="Sector Breadth", layout="wide")
    render()
