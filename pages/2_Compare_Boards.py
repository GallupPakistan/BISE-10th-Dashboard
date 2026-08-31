"""
Compare Boards — side-by-side comparison across BISE boards, filterable by year.
"""
import streamlit as st

from common import (
    inject_css,
    render_hero_banner,
    render_sidebar_brand,
    render_currently_viewing,
    render_global_filters,
    load_boards,
    show_missing_workbook_error,
)
from views_compare import render_compare_page

st.set_page_config(page_title="Compare Boards — BISE Dashboard", page_icon="🆚", layout="wide")
inject_css()

try:
    boards, board_prefixes, board_map, ALL_BOARD_NAMES = load_boards()
except FileNotFoundError:
    show_missing_workbook_error()

with st.sidebar:
    render_sidebar_brand()
    st.markdown("---")
    selected_year, selected_boards, year_choice = render_global_filters(boards, ALL_BOARD_NAMES)
    st.markdown("---")
    year_label = "All Years" if year_choice == "All Years" else year_choice
    render_currently_viewing(f"Comparing {len(selected_boards)} board(s)<br>{year_label}")

st.markdown(render_hero_banner(len(board_prefixes)), unsafe_allow_html=True)
render_compare_page(boards, board_map, selected_boards, selected_year)

st.markdown("---")
st.caption("Data source: BISE SSC master workbooks only · no estimated values")
