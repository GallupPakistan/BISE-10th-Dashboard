"""
Gender-wise Analysis — Boys vs Girls performance across BISE boards.
"""
import pandas as pd
import streamlit as st

from common import (
    inject_css, render_hero_banner, render_sidebar_brand, render_currently_viewing,
    render_global_filters,
    load_boards, show_missing_workbook_error, get_master_summary,
    extract_gender_type_rows, summarize_gender, extract_board_totals,
    aggregate_demo_rows, get_available_years, split_matches_total,
    kpi_card, style_fig, show_chart, fmt_k, csv_download_button,
    grouped_bar_chart, gender_split_pie, GENDER_COLORS, NAVY, TEAL, MUTED,
    BOARD_PROVINCE, PROVINCE_COLORS,
)
import plotly.graph_objects as go

st.set_page_config(page_title="Gender-wise Analysis — BISE Dashboard", page_icon="👥", layout="wide")
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
    render_currently_viewing(f"Gender-wise — {len(boards_sel)} board(s)<br>{year_label_sb}")

if not boards_sel:
    st.info("Select at least one board from the sidebar Filters to see results.")
    st.stop()

st.markdown(render_hero_banner(len(board_prefixes)), unsafe_allow_html=True)
st.subheader(f"👥 Gender-wise Analysis — Boys vs Girls ({'All Years' if year is None else year})")

rows = []
for name in boards_sel:
    prefix = board_map[name]
    sheets = boards[prefix]
    demo_df = extract_gender_type_rows(sheets, year)
    if year is None and not demo_df.empty:
        demo_df = aggregate_demo_rows(demo_df)
    totals = extract_board_totals(sheets, year, board_prefix=prefix)
    g_df = summarize_gender(demo_df)
    if not split_matches_total(g_df, totals["appeared"]):
        continue
    for _, r in g_df.iterrows():
        rows.append({"Board": name, "Gender": r["Gender"], "Appeared": r["Appeared"],
                     "Passed": r["Passed"], "Pass %": r["Pass %"]})

gdf_all = pd.DataFrame(rows)

if gdf_all.empty:
    st.info("No gender-split data available for the selected boards/year.")
    st.stop()

gdf_all["Province"] = gdf_all["Board"].map(BOARD_PROVINCE).fillna("Other")

overall = gdf_all.groupby("Gender", as_index=False)[["Appeared", "Passed"]].sum()
overall["Pass %"] = (100 * overall["Passed"] / overall["Appeared"].replace(0, float('nan'))).round(2)

boys = overall[overall["Gender"] == "Male"]
girls = overall[overall["Gender"] == "Female"]
boys_pct = float(boys["Pass %"].iloc[0]) if not boys.empty else 0
girls_pct = float(girls["Pass %"].iloc[0]) if not girls.empty else 0
total_appeared = int(overall["Appeared"].sum())

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(kpi_card("TOTAL APPEARED", fmt_k(total_appeared), f"{len(boards_sel)} boards", NAVY), unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card("BOYS PASS %", f"{boys_pct:.1f}%", fmt_k(int(boys['Appeared'].iloc[0])) + " appeared" if not boys.empty else "-", GENDER_COLORS["Male"]), unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card("GIRLS PASS %", f"{girls_pct:.1f}%", fmt_k(int(girls['Appeared'].iloc[0])) + " appeared" if not girls.empty else "-", GENDER_COLORS["Female"]), unsafe_allow_html=True)
with c4:
    gap = round(girls_pct - boys_pct, 1)
    st.markdown(kpi_card("GENDER GAP", f"{gap:+.1f} pts", "Girls minus Boys", TEAL if gap >= 0 else "#E11D48"), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])
with col1:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    fig = gender_split_pie(overall.rename(columns={"Gender": "Gender"}), "Overall Appeared Share")
    show_chart(fig)
    st.markdown("</div>", unsafe_allow_html=True)
with col2:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=["Boys", "Girls"], y=[boys_pct, girls_pct],
                           marker_color=[GENDER_COLORS["Male"], GENDER_COLORS["Female"]],
                           text=[f"{boys_pct:.1f}%", f"{girls_pct:.1f}%"], textposition="outside"))
    fig2.update_layout(title="Overall Pass % by Gender", yaxis_range=[0, 100])
    show_chart(style_fig(fig2))
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="section-card">', unsafe_allow_html=True)
board_pivot = gdf_all.pivot_table(index="Board", columns="Gender", values="Pass %", aggfunc="mean")
board_pivot = board_pivot.sort_values(board_pivot.columns[0], ascending=False) if not board_pivot.empty else board_pivot
series = {}
for g in ["Male", "Female"]:
    if g in board_pivot.columns:
        series["Boys" if g == "Male" else "Girls"] = board_pivot[g].fillna(0).round(1).tolist()
fig3 = grouped_bar_chart(
    board_pivot.index.tolist(), series, title="Pass % by Gender — per Board", y_title="Pass %",
    colors=[GENDER_COLORS["Male"], GENDER_COLORS["Female"]],
    show_values=True, value_suffix="%",
)
show_chart(fig3)
st.markdown("</div>", unsafe_allow_html=True)

# ── Raw headcount — Boys vs Girls Appeared, per board ───────────────────────
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.subheader("🧮 Appeared — Boys vs Girls (headcount, per board)")
board_pivot_app = gdf_all.pivot_table(index="Board", columns="Gender", values="Appeared", aggfunc="sum")
board_pivot_app = board_pivot_app.reindex(board_pivot.index) if not board_pivot.empty else board_pivot_app
series_app = {}
for g in ["Male", "Female"]:
    if g in board_pivot_app.columns:
        series_app["Boys" if g == "Male" else "Girls"] = board_pivot_app[g].fillna(0).astype(int).tolist()
fig_app = grouped_bar_chart(
    board_pivot_app.index.tolist(), series_app, title="Students Appeared — Boys vs Girls, per Board",
    y_title="Students Appeared", colors=[GENDER_COLORS["Male"], GENDER_COLORS["Female"]],
)
show_chart(fig_app)
st.markdown("</div>", unsafe_allow_html=True)

# ── Province × Gender ─────────────────────────────────────────────────────────
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.subheader("🗺️ Gender Split by Province")
st.caption("Same Boys/Girls figures rolled up one level — by province instead of by board — so you can see whether the gender gap varies regionally.")

prov_gender = gdf_all.groupby(["Province", "Gender"], as_index=False)[["Appeared", "Passed"]].sum()
prov_gender["Pass %"] = (100 * prov_gender["Passed"] / prov_gender["Appeared"].replace(0, float("nan"))).round(2)

prov_order = (
    gdf_all.groupby("Province")["Appeared"].sum().sort_values(ascending=False).index.tolist()
)

pc1, pc2 = st.columns(2)
with pc1:
    prov_pivot_app = prov_gender.pivot_table(index="Province", columns="Gender", values="Appeared", aggfunc="sum").reindex(prov_order)
    series_prov_app = {}
    for g in ["Male", "Female"]:
        if g in prov_pivot_app.columns:
            series_prov_app["Boys" if g == "Male" else "Girls"] = prov_pivot_app[g].fillna(0).astype(int).tolist()
    show_chart(grouped_bar_chart(
        prov_pivot_app.index.tolist(), series_prov_app, title="Appeared — Boys vs Girls, by Province",
        y_title="Students Appeared", colors=[GENDER_COLORS["Male"], GENDER_COLORS["Female"]],
    ))
with pc2:
    prov_pivot_pct = prov_gender.pivot_table(index="Province", columns="Gender", values="Pass %", aggfunc="mean").reindex(prov_order)
    series_prov_pct = {}
    for g in ["Male", "Female"]:
        if g in prov_pivot_pct.columns:
            series_prov_pct["Boys" if g == "Male" else "Girls"] = prov_pivot_pct[g].fillna(0).round(1).tolist()
    show_chart(grouped_bar_chart(
        prov_pivot_pct.index.tolist(), series_prov_pct, title="Pass % by Gender, by Province",
        y_title="Pass %", colors=[GENDER_COLORS["Male"], GENDER_COLORS["Female"]],
        show_values=True, value_suffix="%",
    ))

# Quick reading of the gender gap itself, per province — reuses the same
# "Girls minus Boys" framing as the top KPI, just sliced by province.
gap_rows = []
for p in prov_order:
    sub = prov_gender[prov_gender["Province"] == p].set_index("Gender")
    if "Male" in sub.index and "Female" in sub.index:
        gap_rows.append({
            "Province": p,
            "Boys Appeared": int(sub.loc["Male", "Appeared"]),
            "Girls Appeared": int(sub.loc["Female", "Appeared"]),
            "Boys Pass %": round(float(sub.loc["Male", "Pass %"]), 1),
            "Girls Pass %": round(float(sub.loc["Female", "Pass %"]), 1),
            "Gender Gap (pts, Girls-Boys)": round(float(sub.loc["Female", "Pass %"] - sub.loc["Male", "Pass %"]), 1),
        })
gap_df = pd.DataFrame(gap_rows)
if not gap_df.empty:
    st.markdown("**Province-wise gender breakdown**")
    st.dataframe(gap_df, use_container_width=True, hide_index=True)
    csv_download_button(gap_df, "⬇️ Download province-gender CSV", "gender_by_province.csv")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown("**Gender breakdown table**")
st.dataframe(gdf_all.sort_values(["Board", "Gender"]), use_container_width=True, hide_index=True)
csv_download_button(gdf_all, "⬇️ Download CSV", "gender_wise_breakdown.csv")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")
st.caption("Data source: BISE SSC master workbooks only · no estimated values")
