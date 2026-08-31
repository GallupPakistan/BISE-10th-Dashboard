"""
Grade Distribution — A1/A/B/C/D/E/Fail breakdown, combined across all boards and per-board, all years.
"""
import pandas as pd
import streamlit as st

from common import (
    inject_css, render_hero_banner, render_sidebar_brand, render_currently_viewing,
    render_global_filters,
    load_boards, show_missing_workbook_error,
    extract_grade_distribution, kpi_card, show_chart, grade_hbar,
    donut_pie, treemap_chart, grouped_bar_chart, PALETTE,
    csv_download_button, fmt_k, NAVY, TEAL,
)

st.set_page_config(page_title="Grade Distribution — BISE Dashboard", page_icon="🎯", layout="wide")
inject_css()

try:
    boards, board_prefixes, board_map, ALL_BOARD_NAMES = load_boards()
except FileNotFoundError:
    show_missing_workbook_error()

with st.sidebar:
    render_sidebar_brand()
    st.markdown("---")
    year, boards_sel, year_choice = render_global_filters(boards, ALL_BOARD_NAMES)
    st.markdown("---")
    year_label_sb = "All Years" if year_choice == "All Years" else year_choice
    render_currently_viewing(f"Grade Distribution — {len(boards_sel)} board(s)<br>{year_label_sb}")

if not boards_sel:
    st.info("Select at least one board from the sidebar Filters to see results.")
    st.stop()

year_label = "All Years" if year is None else str(year)
st.markdown(render_hero_banner(len(board_prefixes)), unsafe_allow_html=True)
st.subheader(f"🎯 Grade Distribution — {len(boards_sel)} board(s), {year_label}")

frames = []
for name in boards_sel:
    g = extract_grade_distribution(boards[board_map[name]], year)
    if not g.empty:
        gg = g.copy()
        gg["Board"] = name
        frames.append(gg)

if not frames:
    st.info("No grade distribution data available.")
    st.stop()

all_grades = pd.concat(frames, ignore_index=True)
combined = all_grades.groupby("Grade", as_index=False)["Count"].sum()

total = int(combined["Count"].sum())
c1, c2 = st.columns(2)
with c1:
    st.markdown(kpi_card("TOTAL STUDENTS GRADED", fmt_k(total), "All boards combined", NAVY), unsafe_allow_html=True)
with c2:
    top_grade = combined.sort_values("Count", ascending=False).iloc[0]
    st.markdown(kpi_card("MOST COMMON GRADE", str(top_grade["Grade"]), f"{fmt_k(int(top_grade['Count']))} students", TEAL), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

gc1, gc2 = st.columns([1, 1])
with gc1:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    show_chart(grade_hbar(combined, title="Grade Distribution — All Boards Combined"))
    st.markdown("</div>", unsafe_allow_html=True)
with gc2:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    grades_sorted = combined.sort_values("Count", ascending=False)
    show_chart(donut_pie(
        grades_sorted["Grade"].astype(str).tolist(), grades_sorted["Count"].tolist(),
        PALETTE[: len(grades_sorted)], title="Grade Share — All Boards Combined",
    ))
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="section-card">', unsafe_allow_html=True)
show_chart(treemap_chart(combined["Grade"].astype(str).tolist(), combined["Count"].tolist(), title="Grade Distribution — Treemap"))
st.markdown("</div>", unsafe_allow_html=True)

if len(boards_sel) <= 8:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("📊 Grade Distribution — per Board")
    board_grade_pivot = all_grades.pivot_table(index="Board", columns="Grade", values="Count", aggfunc="sum").fillna(0)
    grade_order = combined.sort_values("Count", ascending=False)["Grade"].astype(str).tolist()
    grade_cols = [g for g in grade_order if g in board_grade_pivot.columns]
    series_grade = {str(g): board_grade_pivot[g].astype(int).tolist() for g in grade_cols}
    show_chart(grouped_bar_chart(
        board_grade_pivot.index.tolist(), series_grade, title="Grade Counts by Board", y_title="Students",
        colors=PALETTE,
    ))
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown("**Combined grade table**")
st.dataframe(combined.sort_values("Count", ascending=False), use_container_width=True, hide_index=True)
csv_download_button(combined, "⬇️ Download combined CSV", "grade_distribution_combined.csv")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown("**Per-board grade breakdown**")
st.dataframe(all_grades.sort_values(["Board", "Count"], ascending=[True, False]), use_container_width=True, hide_index=True)
csv_download_button(all_grades, "⬇️ Download per-board CSV", "grade_distribution_per_board.csv")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")
st.caption("Data source: BISE SSC master workbooks only · no estimated values")
