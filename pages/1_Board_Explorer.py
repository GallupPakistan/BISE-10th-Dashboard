"""
Board Explorer — full results for any BISE board(s) / year, filterable.
"""
import re

import pandas as pd
import streamlit as st

from common import (
    inject_css,
    render_hero_banner,
    render_sidebar_brand,
    render_currently_viewing,
    render_global_filters,
    GLOBAL_BOARDS_KEY,
    PENDING_YEAR_KEY,
    PENDING_BOARDS_KEY,
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
    BOARD_PROVINCE,
)
from views_board import render_board_page

st.set_page_config(page_title="Board Explorer — BISE Dashboard", page_icon="🏫", layout="wide")
inject_css()

try:
    boards, board_prefixes, board_map, ALL_BOARD_NAMES = load_boards()
except FileNotFoundError:
    show_missing_workbook_error()

with st.sidebar:
    render_sidebar_brand()
    st.markdown("---")
    year, selected_boards, year_choice = render_global_filters(boards, ALL_BOARD_NAMES)
    st.markdown("---")
    year_label_sb = "All Years" if year_choice == "All Years" else year_choice
    render_currently_viewing(f"Board Explorer<br>{len(selected_boards)} board(s) · {year_label_sb}")

year_label = "All Years" if year is None else str(year)

# Each board now has its own dedicated page (pages/10_BISE_Abbottabad.py,
# etc.) — "View results →" switches straight there instead of filtering
# this page, so results are on-screen immediately with nothing to scroll
# past.
def _board_page_path(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    board_order = sorted(board_map.keys())
    page_num = 10 + board_order.index(name)
    return f"pages/{page_num}_{slug}.py"

# Has the user actually picked a specific board (sidebar filter or a Quick
# Jump card)? If not, `selected_boards` defaults to *every* board — we only
# want to show detailed results once it's a real, explicit pick.
explicit_boards = st.session_state.get(GLOBAL_BOARDS_KEY, [])

st.markdown(render_hero_banner(len(board_prefixes)), unsafe_allow_html=True)
st.subheader(f"🏫 Board Explorer — {len(selected_boards)} board(s), {year_label}")

# ── Quick Jump — icon cards to jump straight to a board or year ────────────
# (Merged in from the old standalone Browse page — same cards, same behaviour,
# just living inline here instead of on a separate page.)
# Only shown while nothing is picked yet: once a board is selected, results
# start immediately below the header instead of you having to scroll past
# this whole grid to reach them.
if not explicit_boards:
    with st.expander("🧭 Quick Jump — Browse by Board / Year", expanded=True):
        all_names_sorted = sorted(board_map.keys())

        with st.container(border=True):
            cc1, cc2 = st.columns([3, 1])
            with cc1:
                st.markdown('<div class="navcard-title" style="font-size:16px;">🆚 Compare Boards Side-by-Side</div>', unsafe_allow_html=True)
                st.markdown('<div class="navcard-sub">Pick any two (or more) boards and compare pass %, appeared, gender & trends.</div>', unsafe_allow_html=True)
            with cc2:
                if st.button("Compare now →", key="explorer_compare_btn", use_container_width=True):
                    st.session_state[PENDING_BOARDS_KEY] = all_names_sorted[:2]
                    st.switch_page("pages/2_Compare_Boards.py")

        st.write("")
        st.markdown("**🏫 Browse by Board**")
        per_row = 4
        for i in range(0, len(all_names_sorted), per_row):
            row = all_names_sorted[i:i + per_row]
            cols = st.columns(per_row)
            for col, name in zip(cols, row):
                with col:
                    with st.container(border=True):
                        st.markdown(f'<div class="navcard-title">🏫 {name}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="navcard-sub">{BOARD_PROVINCE.get(name, "")}</div>', unsafe_allow_html=True)
                        if st.button("View results →", key=f"qj_board_{name}", use_container_width=True):
                            st.switch_page(_board_page_path(name))

        st.write("")
        master_qj = get_master_summary(boards)
        years_qj = sorted(master_qj["Year"].dropna().astype(int).unique().tolist()) if not master_qj.empty else []
        if years_qj:
            st.markdown("**📅 Browse by Year**")
            ycols = st.columns(min(len(years_qj), 6))
            for col, yr in zip(ycols, years_qj):
                with col:
                    with st.container(border=True):
                        st.markdown(f'<div class="navcard-title">📅 {int(yr)}</div>', unsafe_allow_html=True)
                        st.markdown('<div class="navcard-sub">All boards</div>', unsafe_allow_html=True)
                        if st.button("View results →", key=f"qj_year_{int(yr)}", use_container_width=True):
                            st.session_state[PENDING_YEAR_KEY] = str(int(yr))
                            st.rerun()
else:
    if st.button("← Back to Browse", key="back_to_browse"):
        st.session_state[PENDING_BOARDS_KEY] = []
        st.rerun()

filter_gender_list = ["Male", "Female"]
filter_type_list = ["Regular", "Private"]

if not explicit_boards:
    st.info("Pick a board above (Quick Jump) or from the sidebar Filters to see its results.")
    st.stop()

# Auto-expand the first card when the view is narrowed to a single board —
# otherwise keep every card collapsed.
auto_expand = len(selected_boards) == 1

for selected_board_name in selected_boards:
    prefix = board_map[selected_board_name]
    board_sheets = boards[prefix]

    with st.expander(f"📍 {selected_board_name}", expanded=auto_expand):
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
            subj_trend_raw["Board"] = selected_board_name

        render_board_page(
            selected_board_name, board_sheets, year, year_label,
            demo_df, gender_df, type_df, totals,
            extract_subject_group_data(board_sheets, year),
            extract_subject_data(board_sheets, year),
            extract_district_data(board_sheets, year),
            extract_yearly_trend(board_sheets, board_prefix=prefix),
            extract_grade_distribution(board_sheets, year),
            extract_stream_summary(demo_df),
            boards=boards,
            board_map=board_map,
            filter_gender_list=filter_gender_list,
            filter_type_list=filter_type_list,
            min_pass_pct=0,
            top_n_subjects=1000,
            top_n_districts=1000,
            subj_trend_df=subj_trend_raw,
            trend_boards=[selected_board_name],
        )

st.markdown("---")
st.caption("Data source: BISE SSC master workbooks only · no estimated values")
