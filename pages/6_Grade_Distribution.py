"""
Grade Distribution — A1/A/B/C/D/E/Fail breakdown, combined across all boards and per-board, all years.
"""
import pandas as pd
import streamlit as st

from common import (
    inject_css, render_hero_banner, render_sidebar_brand, render_currently_viewing,
    render_global_filters,
    load_boards, show_missing_workbook_error,
    extract_grade_distribution, kpi_card, show_chart,
    pass_fail_hbar, grouped_bar_chart, board_rank_hbar, cumulative_grade_line_chart,
    PALETTE, csv_download_button, fmt_k, NAVY, TEAL,
)

FAIL_GRADES = {"Fail", "E", "E/No Grade"}
TOP_GRADES = {"A1", "A+", "A"}
BOTTOM_GRADES = {"D", "E", "E/No Grade", "Fail"}
# Best-to-worst grade order used for cumulative ranking
GRADE_RANK = ["A1", "A+", "A", "B", "C", "D", "E", "Fail", "E/No Grade"]

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
pass_count = int(combined.loc[~combined["Grade"].astype(str).isin(FAIL_GRADES), "Count"].sum())
fail_count = int(combined.loc[combined["Grade"].astype(str).isin(FAIL_GRADES), "Count"].sum())
pass_pct = (pass_count / total * 100) if total else 0

c1, c2 = st.columns(2)
with c1:
    st.markdown(kpi_card("TOTAL STUDENTS GRADED", fmt_k(total), "All boards combined", NAVY), unsafe_allow_html=True)
with c2:
    top_grade = combined.sort_values("Count", ascending=False).iloc[0]
    st.markdown(kpi_card("MOST COMMON GRADE", str(top_grade["Grade"]), f"{fmt_k(int(top_grade['Count']))} students", TEAL), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

if len(boards_sel) < 2:
    st.info("Select 2 or more boards from the sidebar Filters to see board-level comparison charts.")
    st.stop()

board_totals = all_grades.groupby("Board")["Count"].sum()
board_fail = all_grades[all_grades["Grade"].astype(str).isin(FAIL_GRADES)].groupby("Board")["Count"].sum().reindex(board_totals.index).fillna(0)
board_pass = board_totals - board_fail
board_pass_pct = (board_pass / board_totals * 100).round(1)

# 1. STACKED BAR — passed vs failed per board (scale + performance together)
st.markdown('<div class="section-card">', unsafe_allow_html=True)
pf_df = pd.DataFrame({
    "Board": board_totals.index, "Appeared": board_totals.values,
    "Passed": board_pass.values, "Pass %": board_pass_pct.values,
})
show_chart(pass_fail_hbar(pf_df, "Board", title="Passed vs Failed — per Board"))
st.markdown("</div>", unsafe_allow_html=True)

# 2. TOP vs BOTTOM GRADE RATIO — grouped bar per board
st.markdown('<div class="section-card">', unsafe_allow_html=True)
board_grade_pivot = all_grades.pivot_table(index="Board", columns="Grade", values="Count", aggfunc="sum").fillna(0)
top_cols = [g for g in board_grade_pivot.columns if g in TOP_GRADES]
bottom_cols = [g for g in board_grade_pivot.columns if g in BOTTOM_GRADES]
top_sum = board_grade_pivot[top_cols].sum(axis=1) if top_cols else pd.Series(0, index=board_grade_pivot.index)
bottom_sum = board_grade_pivot[bottom_cols].sum(axis=1) if bottom_cols else pd.Series(0, index=board_grade_pivot.index)
show_chart(grouped_bar_chart(
    board_grade_pivot.index.tolist(),
    {"Top Grades (A1+A++A)": top_sum.tolist(), "Bottom Grades (D+E+Fail)": bottom_sum.tolist()},
    title="Top vs Bottom Grade Counts — per Board", y_title="Students",
    colors=[TEAL, "#E74C3C"],
))
st.markdown("</div>", unsafe_allow_html=True)

# 3. CUMULATIVE % LINE — % of students at grade X or better, per board
st.markdown('<div class="section-card">', unsafe_allow_html=True)
grade_order_present = [g for g in GRADE_RANK if g in board_grade_pivot.columns]
cum_series = {}
for b in board_grade_pivot.index:
    row = board_grade_pivot.loc[b, grade_order_present]
    cum_pct = (row.cumsum() / board_totals[b] * 100).round(1)
    cum_series[b] = cum_pct.tolist()
show_chart(cumulative_grade_line_chart(grade_order_present, cum_series, title="Cumulative % of Students by Grade or Better — per Board"))
st.markdown("</div>", unsafe_allow_html=True)

# 4. RANKED BAR — boards sorted by overall pass rate, best to worst
st.markdown('<div class="section-card">', unsafe_allow_html=True)
show_chart(board_rank_hbar(board_pass_pct.index.tolist(), board_pass_pct.tolist(), title="Boards Ranked by Pass Rate"))
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
