"""
app.py — Entry point / router.
BISE 10th Grade 2024-26 Result -- Enhanced Results Dashboard

This file no longer renders the Home page directly. Instead it builds the
sidebar navigation with st.navigation(), grouped into sections:
    Dashboard   -> Overview (Home)
    Analysis    -> Board Explorer, Compare Boards, Gender Analysis,
                   Subject Analysis, Province Wise, Grade Distribution
    All Boards  -> the 15 individual BISE board pages

Grouping the 15 board pages under their own "All Boards" heading (instead
of them just trailing on flat, unlabeled, after Grade Distribution) is the
whole point of this file.

Run: streamlit run app.py
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
from views_overview import render_overview


def home_page():
    """Overview (Home) — kept as a function so it can be registered as a
    st.Page below, grouped under its own 'Dashboard' section heading."""
    st.set_page_config(
        page_title="Overview - BISE Dashboard",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_css()

    try:
        boards, board_prefixes, board_map, ALL_BOARD_NAMES = load_boards()
    except FileNotFoundError:
        show_missing_workbook_error()
        return

    with st.sidebar:
        render_sidebar_brand()
        st.markdown("---")
        year, boards_sel, year_choice = render_global_filters(boards, ALL_BOARD_NAMES)
        st.markdown("---")
        year_label_sb = "All Years" if year_choice == "All Years" else year_choice
        render_currently_viewing(f"Overview — {len(boards_sel)} board(s)<br>{year_label_sb}")

    if not boards_sel:
        st.info("Select at least one board from the sidebar Filters to see results.")
        st.stop()

    st.markdown(render_hero_banner(len(board_prefixes)), unsafe_allow_html=True)
    render_overview(boards, board_map, year, boards_sel)

    st.markdown("---")
    st.caption("Data source: BISE SSC master workbooks only · no estimated values")


# -- All Boards section: the 15 individual board pages -----------------------
BOARD_PAGES = [
    ("pages/10_BISE_Abbottabad.py", "BISE Abbottabad"),
    ("pages/11_BISE_Bahawalpur.py", "BISE Bahawalpur"),
    ("pages/12_BISE_Bannu.py", "BISE Bannu"),
    ("pages/13_BISE_Dera_Ghazi_Khan.py", "BISE Dera Ghazi Khan"),
    ("pages/14_BISE_Faisalabad.py", "BISE Faisalabad"),
    ("pages/15_BISE_Gujranwala.py", "BISE Gujranwala"),
    ("pages/16_BISE_Kohat.py", "BISE Kohat"),
    ("pages/17_BISE_Lahore.py", "BISE Lahore"),
    ("pages/18_BISE_Mardan.py", "BISE Mardan"),
    ("pages/19_BISE_Peshawar.py", "BISE Peshawar"),
    ("pages/20_BISE_Rawalpindi.py", "BISE Rawalpindi"),
    ("pages/21_BISE_Sahiwal.py", "BISE Sahiwal"),
    ("pages/22_BISE_Sargodha.py", "BISE Sargodha"),
    ("pages/23_BISE_Swat.py", "BISE Swat"),
    ("pages/24_FBISE.py", "FBISE"),
]

pg = st.navigation(
    {
        "Dashboard": [
            st.Page(home_page, title="Overview", icon="🎓", default=True),
        ],
        "Analysis": [
            st.Page("pages/1_Board_Explorer.py", title="Board Explorer", icon="🏫"),
            st.Page("pages/2_Compare_Boards.py", title="Compare Boards", icon="🆚"),
            st.Page("pages/3_Gender_Analysis.py", title="Gender Analysis", icon="👥"),
            st.Page("pages/4_Subject_Analysis.py", title="Subject Analysis", icon="📚"),
            st.Page("pages/5_Province_Wise.py", title="Province Wise", icon="🗺️"),
            st.Page("pages/6_Grade_Distribution.py", title="Grade Distribution", icon="🎯"),
        ],
        "All Boards": [
            st.Page(path, title=title, icon="🏫") for path, title in BOARD_PAGES
        ],
    }
)
pg.run()