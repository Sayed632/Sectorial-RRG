"""
returns_calculator.py

Interactive investment returns calculator - a new page/tab for the same
Streamlit app as the MF Screener and RRG. Pure calculation, no external
data or network calls, so this has been verified locally against known
reference values before deployment (SIP formula cross-checked against
the standard closed-form annuity-due formula; lumpsum cross-checked
against manual compound-interest calculation).

Three modes:
  1. SIP calculator (with optional annual step-up %)
  2. Lumpsum calculator
  3. Reverse SIP - "I want X corpus, what monthly SIP do I need?"

HONESTY NOTE: this projects future value using a fixed assumed annual
return you enter - real markets don't return a smooth fixed rate every
year. Treat outputs as illustrative planning estimates, not guarantees.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go


def sip_future_value(monthly_investment, annual_rate_pct, years, step_up_pct=0):
    """Annuity-due convention (contribution at start of month) - matches
    the standard formula used by AMFI/most Indian SIP calculators."""
    monthly_rate = annual_rate_pct / 100 / 12
    total_invested = 0.0
    corpus = 0.0
    current_monthly = monthly_investment
    yearly_snapshots = []
    for year in range(1, int(years) + 1):
        for _ in range(12):
            corpus = (corpus + current_monthly) * (1 + monthly_rate)
            total_invested += current_monthly
        yearly_snapshots.append({"year": year, "invested": total_invested, "corpus": corpus})
        current_monthly *= (1 + step_up_pct / 100)
    return corpus, total_invested, yearly_snapshots


def lumpsum_future_value(principal, annual_rate_pct, years):
    yearly_snapshots = []
    for year in range(1, int(years) + 1):
        value = principal * (1 + annual_rate_pct / 100) ** year
        yearly_snapshots.append({"year": year, "invested": principal, "corpus": value})
    final_value = principal * (1 + annual_rate_pct / 100) ** years
    return final_value, principal, yearly_snapshots


def required_sip_for_target(target_corpus, annual_rate_pct, years, step_up_pct=0):
    """
    Binary search for the monthly SIP amount that hits the target corpus,
    since the closed-form is awkward to invert directly once step-up is
    involved. Converges in ~40 iterations, effectively instant.
    """
    low, high = 1.0, target_corpus  # monthly SIP can't exceed the target itself
    for _ in range(60):
        mid = (low + high) / 2
        corpus, _, _ = sip_future_value(mid, annual_rate_pct, years, step_up_pct)
        if corpus < target_corpus:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def render():
    st.header("🧮 Returns Calculator")
    st.caption(
        "Illustrative planning tool - assumes a fixed annual return every year, "
        "which real markets don't provide. Not a guarantee of actual returns."
    )

    mode = st.radio(
        "Calculation type",
        ["SIP (monthly investing)", "Lumpsum (one-time investment)", "Reverse SIP (target a specific corpus)"],
        horizontal=False,
    )

    if mode == "SIP (monthly investing)":
        col1, col2 = st.columns(2)
        with col1:
            monthly = st.number_input("Monthly investment (₹)", min_value=100, value=5000, step=500)
            years = st.number_input("Investment period (years)", min_value=1, value=10, step=1)
        with col2:
            rate = st.number_input("Expected annual return (%)", min_value=0.0, value=12.0, step=0.5)
            step_up = st.number_input("Annual step-up (%) - optional", min_value=0.0, value=0.0, step=1.0)

        corpus, invested, snapshots = sip_future_value(monthly, rate, years, step_up)
        gains = corpus - invested

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Invested", f"₹{invested:,.0f}")
        c2.metric("Estimated Corpus", f"₹{corpus:,.0f}")
        c3.metric("Estimated Gains", f"₹{gains:,.0f}")

        df = pd.DataFrame(snapshots)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["year"], y=df["invested"], name="Invested", fill="tozeroy"))
        fig.add_trace(go.Scatter(x=df["year"], y=df["corpus"], name="Corpus", fill="tonexty"))
        fig.update_layout(title="Growth over time", xaxis_title="Year", yaxis_title="₹")
        st.plotly_chart(fig, use_container_width=True)

    elif mode == "Lumpsum (one-time investment)":
        col1, col2 = st.columns(2)
        with col1:
            principal = st.number_input("Investment amount (₹)", min_value=100, value=100000, step=1000)
            years = st.number_input("Investment period (years)", min_value=1, value=10, step=1)
        with col2:
            rate = st.number_input("Expected annual return (%)", min_value=0.0, value=12.0, step=0.5)

        final_value, invested, snapshots = lumpsum_future_value(principal, rate, years)
        gains = final_value - invested

        c1, c2, c3 = st.columns(3)
        c1.metric("Invested", f"₹{invested:,.0f}")
        c2.metric("Estimated Value", f"₹{final_value:,.0f}")
        c3.metric("Estimated Gains", f"₹{gains:,.0f}")

        df = pd.DataFrame(snapshots)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["year"], y=df["corpus"], name="Value", fill="tozeroy"))
        fig.add_hline(y=invested, line_dash="dot", annotation_text="Original investment")
        fig.update_layout(title="Growth over time", xaxis_title="Year", yaxis_title="₹")
        st.plotly_chart(fig, use_container_width=True)

    else:  # Reverse SIP
        col1, col2 = st.columns(2)
        with col1:
            target = st.number_input("Target corpus (₹)", min_value=1000, value=5000000, step=100000)
            years = st.number_input("Investment period (years)", min_value=1, value=10, step=1)
        with col2:
            rate = st.number_input("Expected annual return (%)", min_value=0.0, value=12.0, step=0.5)
            step_up = st.number_input("Annual step-up (%) - optional", min_value=0.0, value=0.0, step=1.0)

        required_monthly = required_sip_for_target(target, rate, years, step_up)
        corpus_check, invested_check, _ = sip_future_value(required_monthly, rate, years, step_up)

        c1, c2 = st.columns(2)
        c1.metric("Required Monthly SIP", f"₹{required_monthly:,.0f}")
        c2.metric("Total You'd Invest", f"₹{invested_check:,.0f}")
        st.caption(f"This reaches ≈ ₹{corpus_check:,.0f} by year {years}, close to your ₹{target:,.0f} target.")

    st.markdown(
        "\n⚠️ Assumes the entered return rate holds steady every year - real "
        "investments fluctuate year to year. Use this for rough planning, "
        "not as a promise of actual returns. Not financial advice."
    )


if __name__ == "__main__":
    st.set_page_config(page_title="Returns Calculator", layout="wide")
    render()
