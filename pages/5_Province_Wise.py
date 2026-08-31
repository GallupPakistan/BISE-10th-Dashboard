"""
Province-wise Analysis — aggregates BISE boards by province (KPK, Punjab, Federal).
"""
import pandas as pd
import streamlit as st

from common import (
    inject_css, render_hero_banner, render_sidebar_brand, render_currently_viewing,
    render_global_filters,
    load_boards, show_missing_workbook_error, get_master_summary,
    extract_board_totals, extract_yearly_trend, get_available_years,
    kpi_card, show_chart, style_fig, fmt_k, csv_download_button,
    donut_pie, trend_line_chart, BOARD_PROVINCE, PROVINCE_COLORS, NAVY, TEAL,
)
import plotly.graph_objects as go

st.set_page_config(page_title="Province-wise Analysis — BISE Dashboard", page_icon="🗺️", layout="wide")
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
    render_currently_viewing(f"Province-wise — {len(boards_sel)} board(s)<br>{year_label_sb}")

if not boards_sel:
    st.info("Select at least one board from the sidebar Filters to see results.")
    st.stop()

year_label_hdr = "All Years" if year is None else str(year)
st.markdown(render_hero_banner(len(board_prefixes)), unsafe_allow_html=True)
st.subheader(f"🗺️ Province-wise Analysis — {year_label_hdr}")

rows = []
for name in boards_sel:
    prefix = board_map[name]
    totals = extract_board_totals(boards[prefix], year, board_prefix=prefix)
    if totals["appeared"] <= 0:
        continue
    province = BOARD_PROVINCE.get(name, "Other")
    rows.append({
        "Board": name, "Province": province,
        "Appeared": totals["appeared"], "Passed": totals["passed"],
        "Failed": totals["failed"],
    })

df = pd.DataFrame(rows)
if df.empty:
    st.info("No board totals available for the selected year.")
    st.stop()

prov = df.groupby("Province", as_index=False)[["Appeared", "Passed", "Failed"]].sum()
prov["Pass %"] = (100 * prov["Passed"] / prov["Appeared"].replace(0, float('nan'))).round(2)
prov = prov.sort_values("Pass %", ascending=False)

cols = st.columns(len(prov)) if len(prov) <= 4 else st.columns(4)
for i, (_, r) in enumerate(prov.iterrows()):
    with cols[i % len(cols)]:
        st.markdown(
            kpi_card(r["Province"].upper(), f"{r['Pass %']:.1f}%", f"{fmt_k(int(r['Appeared']))} appeared",
                      PROVINCE_COLORS.get(r["Province"], NAVY)),
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])
with col1:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    fig = donut_pie(
        prov["Province"].tolist(), prov["Appeared"].tolist(),
        [PROVINCE_COLORS.get(p, NAVY) for p in prov["Province"]],
        title="Appeared Share by Province", height=400,
    )
    show_chart(fig)
    st.markdown("</div>", unsafe_allow_html=True)
with col2:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    fig2 = go.Figure(go.Bar(
        x=prov["Province"], y=prov["Pass %"],
        marker_color=[PROVINCE_COLORS.get(p, NAVY) for p in prov["Province"]],
        text=[f"{v:.1f}%" for v in prov["Pass %"]], textposition="outside",
    ))
    fig2.update_layout(title="Pass % by Province", yaxis_range=[0, 100])
    show_chart(style_fig(fig2))
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown("**Boards within each province**")
st.dataframe(
    df.assign(**{"Pass %": (100 * df["Passed"] / df["Appeared"].replace(0, float('nan'))).round(2)})
      .sort_values(["Province", "Pass %"], ascending=[True, False]),
    use_container_width=True, hide_index=True,
)
csv_download_button(df, "⬇️ Download board-level CSV", "province_wise_boards.csv")
st.markdown("</div>", unsafe_allow_html=True)

# ── Province trend across years ───────────────────────────────────────────────
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown("**Province pass % trend across years**")
trend_rows = []
for name in boards_sel:
    prefix = board_map[name]
    province = BOARD_PROVINCE.get(name, "Other")
    t = extract_yearly_trend(boards[prefix], board_prefix=prefix)
    if t.empty:
        continue
    t = t.copy()
    t["Province"] = province
    trend_rows.append(t[["Year", "Appeared", "Passed", "Province"]])

if trend_rows:
    trend_all = pd.concat(trend_rows, ignore_index=True)
    trend_prov = trend_all.groupby(["Year", "Province"], as_index=False)[["Appeared", "Passed"]].sum()
    trend_prov["Pass %"] = (100 * trend_prov["Passed"] / trend_prov["Appeared"].replace(0, float('nan'))).round(2)

    fig3 = go.Figure()
    for p in trend_prov["Province"].unique():
        sub = trend_prov[trend_prov["Province"] == p].sort_values("Year")
        fig3.add_trace(go.Scatter(
            x=sub["Year"].astype(str), y=sub["Pass %"], mode="lines+markers", name=p,
            line=dict(color=PROVINCE_COLORS.get(p, NAVY), width=3),
        ))
    fig3.update_layout(title="Pass % Trend by Province", yaxis=dict(title="Pass %"),
                        xaxis=dict(type="category", title="Year"))
    show_chart(style_fig(fig3))
else:
    st.caption("ℹ️ No multi-year trend data available.")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")
st.caption("Data source: BISE SSC master workbooks only · no estimated values")
