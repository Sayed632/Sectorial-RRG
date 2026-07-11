"""
sector_dashboard.py

Single entry point combining all three requested charts in tabs:
  1. Sectorial RRG        - sector_rrg_chart.py
  2. Sector Breadth Table - sector_breadth_treemap.py
  3. Clickable Treemap    - sector_breadth_treemap.py

Run with:
    streamlit run sector_dashboard.py

Requires, in the same folder:
    - sector_breadth_treemap.py
    - sector_rrg_chart.py
    - sector_universe_generated.py   (from csv_to_sector_universe.py output)

If you'd rather fold this into your existing Sectorial-RRG app instead of
running it standalone, just copy the st.tabs(...) block below into your
app's main script and import the two render functions the same way.
"""
import streamlit as st
from sector_universe_generated import SECTOR_UNIVERSE
import sector_breadth_treemap
import sector_rrg_chart

st.set_page_config(page_title="Sector Dashboard", layout="wide")
st.title("📈 Sector Dashboard")

# Use the full generated universe (493 stocks / 18 sectors) everywhere,
# instead of the 5-sector starter dict inside sector_breadth_treemap.py
sector_breadth_treemap.SECTOR_UNIVERSE = SECTOR_UNIVERSE

tab_rrg, tab_breadth = st.tabs(["🔄 Sectorial RRG", "📊 Breadth + Treemap"])

with tab_rrg:
    sector_rrg_chart.render_rrg(SECTOR_UNIVERSE)

with tab_breadth:
    sector_breadth_treemap.render()
