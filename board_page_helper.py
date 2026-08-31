"""
board_page_helper.py — shared renderer used by each single-board page
(pages/7_BISE_Abbottabad.py, pages/8_BISE_Bahawalpur.py, ...).

Kept in its own module (not common.py) because views_board.py already does
`from common import *`, and common.py importing views_board back would be
a circular import.
"""
import pandas as pd
import streamlit as st

from common import (
    inject_css,
    render_hero_banner,
    render_sidebar_brand,
    render_currently_viewing,
    load_boards,
    show_missing_workbook_error,
    aggregate_demo_rows,
    extract_board_totals,
    extract_district_data,
    extract_gender_type_rows,
    extract_grade_distribution,
    extract_stream_summary,
    extract_subject_data,
    extract_subject_group_data,
    extract_type_from_pass_percentage,
    extract_type_from_yoy,
    extract_yearly_trend,
    summarize_gender,
    summarize_type,
    split_matches_total,
    extract_groupwise_type,
    build_subject_year_trend,
    get_master_summary,
)
from views_board import render_board_page


def render_single_board_page(display_name: str):
    """Everything a single board's page needs: sidebar year filter, hero
    banner, and the full board detail view — with no Quick Jump grid and
    no other boards' expanders above it, so results are visible immediately
    on load with no scrolling required."""
    st.set_page_config(page_title=f"{display_name} — BISE Dashboard", page_icon="🏫", layout="wide")
    inject_css()

    try:
        boards, board_prefixes, board_map, ALL_BOARD_NAMES = load_boards()
    except FileNotFoundError:
        show_missing_workbook_error()
        return

    prefix = board_map[display_name]
    board_sheets = boards[prefix]

    master = get_master_summary(boards)
    available_years = sorted({int(y) for y in master["Year"].dropna().unique()}, reverse=True)
    year_options = [str(y) for y in available_years] + ["All Years"]

    with st.sidebar:
        render_sidebar_brand()
        st.markdown("---")
        st.markdown("**Filters**")
        year_choice = st.selectbox("Year", year_options, key=f"year_{prefix}")
        st.markdown("---")
        render_currently_viewing(f"{display_name}<br>{year_choice}")

    year = None if year_choice == "All Years" else int(year_choice)
    year_label = "All Years" if year is None else str(year)

    st.markdown(render_hero_banner(len(board_prefixes)), unsafe_allow_html=True)
    st.subheader(f"🏫 {display_name} — {year_label}")

    if st.button("← Back to Board Explorer", key=f"back_{prefix}"):
        st.switch_page("pages/1_Board_Explorer.py")

    demo_df = extract_gender_type_rows(board_sheets, year)
    if year is None and not demo_df.empty:
        demo_df = aggregate_demo_rows(demo_df)

    totals = extract_board_totals(board_sheets, year, board_prefix=prefix)
    gender_df = summarize_gender(demo_df)
    type_df = summarize_type(demo_df)

    if type_df.empty:
        type_df = extract_type_from_yoy(board_sheets, year)
    if type_df.empty:
        type_df = extract_type_from_pass_percentage(board_sheets, year)
    if type_df.empty:
        type_df = extract_groupwise_type(board_sheets, year)

    if not split_matches_total(gender_df, totals["appeared"]):
        gender_df = pd.DataFrame(columns=["Gender", "Appeared", "Passed", "Failed", "Pass %"])
    if not split_matches_total(type_df, totals["appeared"]):
        type_df = pd.DataFrame(columns=["Candidate Type", "Appeared", "Passed", "Failed", "Pass %"])

    subj_trend_raw = build_subject_year_trend(board_sheets)
    if not subj_trend_raw.empty:
        subj_trend_raw = subj_trend_raw.copy()
        subj_trend_raw["Board"] = display_name

    render_board_page(
        display_name, board_sheets, year, year_label,
        demo_df, gender_df, type_df, totals,
        extract_subject_group_data(board_sheets, year),
        extract_subject_data(board_sheets, year),
        extract_district_data(board_sheets, year),
        extract_yearly_trend(board_sheets, board_prefix=prefix),
        extract_grade_distribution(board_sheets, year),
        extract_stream_summary(demo_df),
        boards=boards,
        board_map=board_map,
        filter_gender_list=["Male", "Female"],
        filter_type_list=["Regular", "Private"],
        min_pass_pct=0,
        top_n_subjects=1000,
        top_n_districts=1000,
        subj_trend_df=subj_trend_raw,
        trend_boards=[display_name],
    )

    st.markdown("---")
    st.caption("Data source: BISE SSC master workbooks only · no estimated values")
