"""
mf_screener_dashboard.py

A new page/tab for your Sectorial-RRG Streamlit app. Reads the weekly
mutual fund rankings straight from Claudeown's public repo (raw GitHub
URL) - no new secrets or infrastructure needed, since Claudeown is
already public.

How to wire it in: same pattern as sector_breadth_treemap.py - import
render() and call it in a new tab, or drop as a new page file.
"""
import requests
import streamlit as st
import plotly.express as px
import pandas as pd

RANKINGS_URL = "https://raw.githubusercontent.com/Sayed632/Claudeown/main/mf_rankings.json"


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_rankings():
    resp = requests.get(RANKINGS_URL, timeout=15)
    resp.raise_for_status()
    return resp.json()


def render():
    st.header("📈 Mutual Fund Screener")

    try:
        data = fetch_rankings()
    except Exception as e:
        st.error(f"Could not fetch rankings from Claudeown repo: {e}")
        return

    st.caption(f"Last updated: {data.get('generated_at', 'unknown')}")
    st.info(data.get("methodology", ""))

    categories = data.get("categories", {})
    tabs = st.tabs(list(categories.keys()))

    for tab, (category, funds) in zip(tabs, categories.items()):
        with tab:
            if not funds:
                st.warning("No funds with full 5-year history found in this category.")
                continue

            df = pd.DataFrame(funds)
            df.index = df.index + 1  # rank starting at 1

            display_df = df[["name", "cagr_1y", "cagr_3y", "cagr_5y", "blend_score"]].rename(
                columns={
                    "name": "Fund",
                    "cagr_1y": "1Y CAGR %",
                    "cagr_3y": "3Y CAGR %",
                    "cagr_5y": "5Y CAGR %",
                    "blend_score": "Blend Score",
                }
            )
            st.dataframe(display_df, use_container_width=True)

            fig = px.bar(
                df.sort_values("blend_score"),
                x="blend_score",
                y="name",
                orientation="h",
                title=f"{category} - Blend Score",
                labels={"blend_score": "Blend Score", "name": ""},
            )
            fig.update_layout(height=400 + len(df) * 20)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        "⚠️ Past performance does not guarantee future returns. This ranks "
        "funds by our own calculated CAGR blend, not a Value Research / "
        "Morningstar rating - verify expense ratios and exit loads before "
        "investing. Not financial advice."
    )


if __name__ == "__main__":
    st.set_page_config(page_title="MF Screener", layout="wide")
    render()
