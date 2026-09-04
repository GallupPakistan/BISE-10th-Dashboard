"""views_compare.py -- Compare Boards page rendering logic."""
import pandas as pd
import numpy as np
import streamlit as st
from common import *

def render_compare_page(boards, board_map, selected_names, year):
    if len(selected_names) < 2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("**Select at least 2 boards** from the sidebar to compare them side by side.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    master = get_master_summary(boards)
    board_df = master[master["Board"].isin(selected_names)].copy()
    if board_df.empty:
        st.warning("No data available for the selected boards.")
        return

    scope_df = board_df if year is None else board_df[board_df["Year"] == year]
    if scope_df.empty:
        scope_df = board_df
    agg = scope_df.groupby("Board", as_index=False).agg(Appeared=("Appeared", "sum"), Passed=("Passed", "sum"))
    agg["Failed"] = (agg["Appeared"] - agg["Passed"]).clip(lower=0)
    agg["Pass %"] = (100 * agg["Passed"] / agg["Appeared"].replace(0, float("nan"))).round(1)
    agg["Board"] = pd.Categorical(agg["Board"], categories=selected_names, ordered=True)
    agg = agg.sort_values("Board").reset_index(drop=True)
    agg["Board"] = agg["Board"].astype(str)

    year_label = "All Years" if year is None else str(year)
    st.markdown(
        f"""<div class="board-header">
        <div class="board-header-title">🆚 Comparing {len(selected_names)} Boards</div>
        <div class="board-header-sub">{year_label} · {' · '.join(selected_names)}</div>
        </div>""",
        unsafe_allow_html=True,
    )

    # Cards are rendered in one flex-wrap grid (not st.columns) so they stay
    # readable no matter how many boards are selected — with st.columns,
    # comparing 10+ boards squeezes each column so narrow that board names
    # wrap one letter per line. The grid instead keeps a minimum card width
    # and lets extra cards flow onto additional rows.
    cards_html = ['<div class="kpi-grid">']
    for i, (_, row) in enumerate(agg.iterrows()):
        accent = PALETTE[i % len(PALETTE)]
        pass_val = f"{row['Pass %']:.1f}%" if pd.notna(row["Pass %"]) else "—"
        cards_html.append(kpi_card(row["Board"], pass_val, f"{fmt_k(int(row['Appeared']))} appeared", accent))
    cards_html.append("</div>")
    st.markdown("".join(cards_html), unsafe_allow_html=True)

    st.write("")
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("📈 Pass % Trend Comparison")
    trend_fig = go.Figure()
    for i, b in enumerate(selected_names):
        bd = board_df[board_df["Board"] == b].sort_values("Year")
        trend_fig.add_trace(go.Scatter(x=bd["Year"], y=bd["Pass %"], mode="lines+markers", name=b,
                                        line=dict(width=3, shape="spline", smoothing=0.8, color=PALETTE[i % len(PALETTE)]),
                                        marker=dict(size=8)))
    trend_fig.update_layout(height=420,
                             xaxis=dict(dtick=1, title="Year", showgrid=True, gridcolor="rgba(0,0,0,0.06)", griddash="dot"),
                             yaxis=dict(title="Pass %", showgrid=True, gridcolor="rgba(0,0,0,0.06)", griddash="dot"),
                             legend=legend_top_right(), margin=chart_margins(legend_pos="top"), hovermode="x unified")
    show_chart(style_fig(trend_fig))
    st.markdown("</div>", unsafe_allow_html=True)

    gc1, gc2 = st.columns(2)
    with gc1:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("🟦 Passed vs Failed")
        show_chart(grouped_bar_chart(agg["Board"].tolist(),
                                      {"Passed": agg["Passed"].tolist(), "Failed": agg["Failed"].tolist()},
                                      "Passed vs Failed by Board", colors=[PASS_COLOR, FAIL_COLOR]))
        st.markdown("</div>", unsafe_allow_html=True)
    with gc2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("🔵 Volume vs Performance")
        show_chart(bubble_scatter_chart(agg["Appeared"].tolist(), agg["Pass %"].tolist(),
                                        agg["Appeared"].tolist(), agg["Board"].tolist(),
                                        "Appeared vs Pass % (bubble size = Appeared)", x_title="Total Appeared"))
        st.markdown("</div>", unsafe_allow_html=True)

    gender_rows = []
    for b in selected_names:
        prefix = board_map[b]
        demo = extract_gender_type_rows(boards[prefix], year)
        if year is None and not demo.empty:
            demo = aggregate_demo_rows(demo)
        g = summarize_gender(demo)
        for _, r in g.iterrows():
            gender_rows.append({"Board": b, "Gender": gender_label(r["Gender"]), "Pass %": r["Pass %"]})
    if gender_rows:
        gdf = pd.DataFrame(gender_rows)
        pivot = gdf.pivot_table(index="Board", columns="Gender", values="Pass %", aggfunc="mean").reindex(selected_names)
        gender_colors = [GENDER_COLORS.get(c, NAVY) for c in pivot.columns]
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("👥 Gender Pass % Comparison")
        show_chart(grouped_bar_chart(pivot.index.tolist(), {col: pivot[col].round(1).tolist() for col in pivot.columns},
                                      "Pass % by Gender — Selected Boards", y_title="Pass %", colors=gender_colors,
                                      show_values=True, value_suffix="%"))
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("📋 Comparison Table")
    st.dataframe(agg, use_container_width=True, hide_index=True)
    csv_download_button(agg, "⬇️ Download comparison CSV", "board_comparison.csv")
    st.markdown("</div>", unsafe_allow_html=True)
