"""views_overview.py -- Overview page rendering logic (used by app.py)."""
import pandas as pd
import numpy as np
import streamlit as st
from common import *

# ── Manual red→yellow→green gradient for the Pass % trend table's
#    "Change (pp)" column — avoids requiring matplotlib (pandas Styler's
#    background_gradient() needs it; many venvs don't have it installed).
_RDYLGN_STOPS = [
    (0.0, (215, 48, 39)),    # red    — big decline
    (0.5, (255, 255, 191)),  # yellow — flat
    (1.0, (26, 152, 80)),    # green  — improvement
]


def _interp_rdylgn(t):
    t = max(0.0, min(1.0, t))
    for (t0, c0), (t1, c1) in zip(_RDYLGN_STOPS, _RDYLGN_STOPS[1:]):
        if t0 <= t <= t1:
            f = (t - t0) / (t1 - t0) if t1 != t0 else 0.0
            return tuple(int(c0[i] + f * (c1[i] - c0[i])) for i in range(3))
    return _RDYLGN_STOPS[-1][1]


def _pp_change_css(v, vmin=-40.0, vmax=10.0):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return ""
    t = (max(min(v, vmax), vmin) - vmin) / (vmax - vmin) if vmax != vmin else 0.5
    r, g, b = _interp_rdylgn(t)
    text_color = "#111827" if (0.299 * r + 0.587 * g + 0.114 * b) > 140 else "#FFFFFF"
    return f"background-color: rgb({r},{g},{b}); color:{text_color};"


def render_overview(boards, board_map, year, boards_sel=None):
    master = get_master_summary(boards)
    rankings = get_all_board_rankings(boards, year)
    if master.empty:
        st.warning("Master summary not found in workbook.")
        return

    # ── Apply the shared sidebar Boards filter (same one used on every page) ──
    if boards_sel:
        master = master[master["Board"].isin(boards_sel)].copy()
        rankings = rankings[rankings["Board"].isin(boards_sel)].copy()

    board_iter_names = sorted(boards_sel) if boards_sel else sorted(board_map.keys())

    master["Province"] = master["Board"].map(BOARD_PROVINCE).fillna("Other")
    rankings["Province"] = rankings["Board"].map(BOARD_PROVINCE).fillna("Other")
    master_all_provinces = master.copy()  # kept unfiltered for the province trend chart below

    st.info("🧭 Want to jump straight to a board or year? Use the **Quick Jump** cards at the top of the **Board Explorer** page.", icon="🧭")

    # ── Compare Boards — quick-access card on the front page ───────────────────
    all_names_sorted = sorted(board_map.keys())
    with st.container(border=True):
        cc1, cc2 = st.columns([3, 1])
        with cc1:
            st.markdown('<div class="navcard-title" style="font-size:16px;">🆚 Compare Boards Side-by-Side</div>', unsafe_allow_html=True)
            st.markdown('<div class="navcard-sub">Pick any two (or more) boards and compare pass %, appeared, gender & trends.</div>', unsafe_allow_html=True)
        with cc2:
            if st.button("Compare now →", key="frontpage_compare_btn", use_container_width=True):
                st.session_state["global_boards_filter"] = all_names_sorted[:2]
                st.switch_page("pages/2_Compare_Boards.py")

    st.write("")

    # ── Province filter (applies to every chart/KPI below, on top of the
    #     shared Boards filter from the sidebar) ────────────────────────────────
    fcol1, fcol2 = st.columns([1, 3])
    with fcol1:
        province_options = ["All Provinces"] + sorted(master["Province"].unique().tolist())
        selected_province = st.selectbox("🏛️ Province", province_options, index=0, key="overview_province_filter")
    if selected_province != "All Provinces":
        master = master[master["Province"] == selected_province].copy()
        rankings = rankings[rankings["Province"] == selected_province].copy()

    df = master if year is None else master[master["Year"] == year]
    total_app = int(df["Appeared"].sum())
    total_pass = int(df["Passed"].sum())
    total_fail = max(total_app - total_pass, 0)
    pass_pct = round(100 * total_pass / max(total_app, 1), 2)

    year_label = "All Years (2024–2026 combined)" if year is None else str(year)
    if year is None:
        st.info(
            "📌 Showing **cumulative totals across 2024–2026**. Cumulative figures can be misleading "
            "(a board with 3 years of data looks bigger than one with 2) — pick a specific year above "
            "for an apples-to-apples snapshot.",
            icon="⚠️",
        )

    appeared_sub = f"Appeared in {year_label}" if year is not None else "Appeared, 2024–2026 combined"
    kpi = [("Boards", f"{df['Board'].nunique()}", f"{selected_province if selected_province != 'All Provinces' else 'All BISE boards'}"),
           ("Total Appeared", fmt_k(total_app), appeared_sub),
           ("Total Passed", fmt_k(total_pass), f"{pass_pct:.1f}% pass rate"),
           ("Total Failed", fmt_k(total_fail), f"{100-pass_pct:.1f}% fail rate")]
    cols = st.columns(4)
    for col, accent, (label, val, sub) in zip(cols, [NAVY, ACCENT, PASS_COLOR, FAIL_COLOR], kpi):
        col.markdown(kpi_card(label, val, sub, accent), unsafe_allow_html=True)

    # ── Result Flow — aggregated across every board (Overall) ──────────────────
    overall_gender_rows, overall_type_rows = [], []
    for name in board_iter_names:
        if selected_province != "All Provinces" and BOARD_PROVINCE.get(name, "Other") != selected_province:
            continue
        demo = extract_gender_type_rows(boards[board_map[name]], year)
        if year is None and not demo.empty:
            demo = aggregate_demo_rows(demo)
        g = summarize_gender(demo)
        t = summarize_type(demo)
        if t.empty:
            t = extract_type_from_yoy(boards[board_map[name]], year)
        if t.empty:
            t = extract_type_from_pass_percentage(boards[board_map[name]], year)
        if t.empty:
            t = extract_groupwise_type(boards[board_map[name]], year)
        if not g.empty:
            overall_gender_rows.append(g)
        if not t.empty:
            overall_type_rows.append(t)

    def _combine(rows, key_col):
        if not rows:
            return pd.DataFrame(columns=[key_col, "Appeared", "Passed", "Failed", "Pass %"])
        cat = pd.concat(rows, ignore_index=True)
        cat["Appeared"] = pd.to_numeric(cat["Appeared"], errors="coerce")
        cat["Passed"] = pd.to_numeric(cat["Passed"], errors="coerce")
        out = cat.groupby(key_col, as_index=False)[["Appeared", "Passed"]].sum()
        out["Failed"] = (out["Appeared"] - out["Passed"]).clip(lower=0)
        out["Pass %"] = (100 * out["Passed"] / out["Appeared"].replace(0, np.nan)).round(2)
        return out

    overall_gender_df = _combine(overall_gender_rows, "Gender")
    overall_type_df = _combine(overall_type_rows, "Candidate Type")
    overall_totals = {"appeared": total_app, "passed": total_pass, "failed": total_fail, "pass_pct": pass_pct}
    render_gender_type_flow(
        f"Overall — {selected_province if selected_province != 'All Provinces' else 'All Boards'}",
        year_label, overall_totals, overall_gender_df, overall_type_df,
    )

    st.write("")
    c1, c2 = st.columns([1.3, 1])
    with c1:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Board Ranking by Pass %")
        rank = rankings.sort_values("Pass %", ascending=True)
        fig = go.Figure(go.Bar(x=rank["Pass %"], y=rank["Board"], orientation="h", marker_color=NAVY, text=rank["Pass %"]))
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(height=max(380, 40 * len(rank)), xaxis_range=[0, 105], showlegend=False, margin=chart_margins())
        show_chart(style_fig(fig))
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Share of Total Appeared")
        show_chart(donut_pie(rankings["Board"].tolist(), rankings["Appeared"].tolist(), PALETTE[:len(rankings)], "Students by Board", height=440))
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    hdr_col, toggle_col = st.columns([4, 1])
    with hdr_col:
        st.subheader("Pass % Trend — All Boards (2024–2026)")
    with toggle_col:
        show_trend_table = st.toggle("Show table", value=False, key="trend_table_toggle")
    trend = master.sort_values(["Board", "Year"])
    fig = go.Figure()
    for i, board in enumerate(trend["Board"].unique()):
        b = trend[trend["Board"] == board]
        fig.add_trace(go.Scatter(x=b["Year"], y=b["Pass %"], mode="lines", name=board,
                                  line=dict(width=3, shape="spline", smoothing=0.8, color=PALETTE[i % len(PALETTE)]),
                                  hovertemplate=f"{board}<br>%{{x}}: %{{y:.1f}}%<extra></extra>"))
    fig.update_layout(
        height=520,
        xaxis=dict(dtick=1, title="Year", showgrid=True, gridcolor="rgba(0,0,0,0.06)", griddash="dot", zeroline=False),
        yaxis=dict(title="Pass %", range=[max(0, trend["Pass %"].min() - 5), min(105, trend["Pass %"].max() + 5)],
                   showgrid=True, gridcolor="rgba(0,0,0,0.06)", griddash="dot", zeroline=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.03, x=0, xanchor="left", font=dict(size=11), tracegroupgap=6, bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=max(90, 26 * (len(trend["Board"].unique()) // 5 + 1)), b=52, l=20, r=30),
        hovermode="x unified", plot_bgcolor="rgba(0,0,0,0)",
    )
    show_chart(style_fig(fig))

    if show_trend_table:
        pass_pivot = trend.pivot_table(index="Board", columns="Year", values="Pass %", aggfunc="mean")
        pass_pivot.columns = [f"{int(c)} Pass %" for c in pass_pivot.columns]
        year_cols = sorted([c for c in pass_pivot.columns], key=lambda c: int(c.split()[0]))
        pass_pivot = pass_pivot[year_cols]
        first_col, last_col = year_cols[0], year_cols[-1]
        pass_pivot[last_col] = pd.to_numeric(pass_pivot[last_col], errors="coerce")
        pass_pivot[first_col] = pd.to_numeric(pass_pivot[first_col], errors="coerce")
        pass_pivot["Change (pp)"] = (pass_pivot[last_col] - pass_pivot[first_col]).round(2)
        pass_pivot = pass_pivot.reset_index().sort_values("Change (pp)")
        try:
            styled = (
                pass_pivot.style.format({c: "{:.1f}" for c in pass_pivot.columns if c != "Board"})
                .applymap(_pp_change_css, subset=["Change (pp)"])
            )
            st.dataframe(styled, use_container_width=True, hide_index=True)
        except Exception:
            # Fall back to a plain table if Styler ever misbehaves for any reason
            st.dataframe(pass_pivot, use_container_width=True, hide_index=True)
        csv_download_button(pass_pivot, "⬇️ Download trend table CSV", "pass_pct_trend_by_board.csv")
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Auto-flag boards with a large multi-year Pass % decline ────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("⚠️ Significant Pass % Declines — Flagged for Review")
    DECLINE_THRESHOLD = 15.0  # percentage points, first year in range vs last
    decline_rows = []
    for board in trend["Board"].unique():
        b = trend[trend["Board"] == board].sort_values("Year")
        if len(b) < 2:
            continue
        first, last = b.iloc[0], b.iloc[-1]
        change = float(last["Pass %"]) - float(first["Pass %"])
        if change <= -DECLINE_THRESHOLD:
            decline_rows.append({
                "Board": board,
                f"{int(first['Year'])} Pass %": round(float(first["Pass %"]), 2),
                f"{int(last['Year'])} Pass %": round(float(last["Pass %"]), 2),
                "Change (pp)": round(change, 2),
                f"{int(last['Year'])} Appeared": int(last["Appeared"]),
                f"{int(last['Year'])} Failed": int(last["Appeared"] - last["Passed"]),
            })

    if decline_rows:
        decline_df = pd.DataFrame(decline_rows).sort_values("Change (pp)")
        st.error(
            f"{len(decline_df)} board(s) dropped {DECLINE_THRESHOLD:.0f}+ percentage points between "
            f"{int(trend['Year'].min())} and {int(trend['Year'].max())} — worth investigating before drawing conclusions."
        )
        st.dataframe(decline_df, use_container_width=True, hide_index=True)
        for _, r in decline_df.iterrows():
            b = trend[trend["Board"] == r["Board"]][["Year", "Appeared", "Passed", "Pass %"]].reset_index(drop=True)
            with st.expander(f"🔍 {r['Board']} — {r['Change (pp)']:+.1f} pp — year-by-year detail"):
                st.dataframe(b, use_container_width=True, hide_index=True)
                st.caption(
                    "A drop this large is usually caused by one of: a stricter grading/checking policy that year, "
                    "a harder paper, a change in what's counted (e.g. 9th+10th merged vs 10th-only), or a board-wide "
                    "re-grading. Cross-check the figures above against that board's own published Result-at-a-Glance "
                    "notice for the affected year before treating it as a data issue."
                )
        csv_download_button(decline_df, "⬇️ Download flagged declines CSV", "flagged_pass_pct_declines.csv")
    else:
        st.success(f"No board dropped {DECLINE_THRESHOLD:.0f}+ percentage points across the period.")
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Provincial comparison — always shows all provinces regardless of the filter above ──
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("🏛️ Pass % Trend by Province")
    prov_trend = master_all_provinces.groupby(["Province", "Year"], as_index=False)[["Appeared", "Passed"]].sum()
    prov_trend["Appeared"] = pd.to_numeric(prov_trend["Appeared"], errors="coerce")
    prov_trend["Passed"] = pd.to_numeric(prov_trend["Passed"], errors="coerce")
    prov_trend["Pass %"] = (100 * prov_trend["Passed"] / prov_trend["Appeared"].replace(0, np.nan)).round(2)
    fig = go.Figure()
    for prov in sorted(prov_trend["Province"].unique()):
        pdata = prov_trend[prov_trend["Province"] == prov].sort_values("Year")
        fig.add_trace(go.Scatter(
            x=pdata["Year"], y=pdata["Pass %"], mode="lines+markers", name=prov,
            line=dict(width=4, color=PROVINCE_COLORS.get(prov, NAVY)), marker=dict(size=8),
            hovertemplate=f"{prov}<br>%{{x}}: %{{y:.1f}}%<extra></extra>",
        ))
    fig.update_layout(
        height=420,
        xaxis=dict(dtick=1, title="Year", showgrid=True, gridcolor="rgba(0,0,0,0.06)", griddash="dot", zeroline=False),
        yaxis=dict(title="Pass %", showgrid=True, gridcolor="rgba(0,0,0,0.06)", griddash="dot", zeroline=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.03, x=0, xanchor="left", bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=60, b=52, l=20, r=30), hovermode="x unified", plot_bgcolor="rgba(0,0,0,0)",
    )
    show_chart(style_fig(fig))
    prov_wide = prov_trend.pivot_table(index="Province", columns="Year", values="Pass %")
    prov_wide.columns = [f"{int(c)} Pass %" for c in prov_wide.columns]
    prov_wide = prov_wide.reset_index()
    st.dataframe(prov_wide, use_container_width=True, hide_index=True)
    st.caption(
        "KPK boards: Peshawar, Swat, Bannu, Abbottabad, Mardan, Kohat. Punjab boards: Sargodha, D.G. Khan, "
        "Rawalpindi, Faisalabad, Lahore, Bahawalpur, Gujranwala, Sahiwal. Federal: FBISE (Islamabad)."
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Gender disaggregation — rolled up across every board for the selected year ──
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("👥 Gender Distribution — All Boards")
    gender_rows, gender_by_board = [], []
    for name in board_iter_names:
        if selected_province != "All Provinces" and BOARD_PROVINCE.get(name, "Other") != selected_province:
            continue
        demo = extract_gender_type_rows(boards[board_map[name]], year)
        if year is None and not demo.empty:
            demo = aggregate_demo_rows(demo)
        g = summarize_gender(demo)
        for _, r in g.iterrows():
            gender_rows.append({"Gender": gender_label(r["Gender"]), "Appeared": r["Appeared"], "Passed": r["Passed"]})
            gender_by_board.append({"Board": name, "Gender": gender_label(r["Gender"]), "Appeared": r["Appeared"],
                                     "Passed": r["Passed"], "Pass %": r["Pass %"]})
    if gender_rows:
        gdf = pd.DataFrame(gender_rows).groupby("Gender", as_index=False)[["Appeared", "Passed"]].sum()
        gdf["Appeared"] = pd.to_numeric(gdf["Appeared"], errors="coerce")
        gdf["Passed"] = pd.to_numeric(gdf["Passed"], errors="coerce")
        gdf["Pass %"] = (100 * gdf["Passed"] / gdf["Appeared"].replace(0, np.nan)).round(2)
        gc1, gc2 = st.columns([1, 1.4])
        with gc1:
            show_chart(donut_pie(gdf["Gender"].tolist(), gdf["Appeared"].tolist(),
                                  [GENDER_COLORS.get(g, NAVY) for g in gdf["Gender"]],
                                  f"Appeared by Gender — {year_label}", height=360))
        with gc2:
            fig = go.Figure(go.Bar(x=gdf["Gender"], y=gdf["Pass %"], marker_color=[GENDER_COLORS.get(g, NAVY) for g in gdf["Gender"]],
                                    text=gdf["Pass %"], texttemplate="%{text:.1f}%", textposition="outside"))
            fig.update_layout(height=360, showlegend=False, yaxis_range=[0, 105], yaxis_title="Pass %",
                               margin=chart_margins(), plot_bgcolor="rgba(0,0,0,0)")
            show_chart(style_fig(fig))
        with st.expander("📋 Gender breakdown by board"):
            bdf = pd.DataFrame(gender_by_board).sort_values(["Board", "Gender"])
            st.dataframe(bdf, use_container_width=True, hide_index=True)
            csv_download_button(bdf, "⬇️ Download gender-by-board CSV", "gender_by_board.csv")
    else:
        st.info("No gender-wise data available for the current filter.")
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Subject-wise disaggregation — not every board publishes this ──────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("📚 Subject-wise Pass % — All Boards")
    subj_rows, boards_with_subjects, boards_without_subjects = [], [], []
    for name in board_iter_names:
        if selected_province != "All Provinces" and BOARD_PROVINCE.get(name, "Other") != selected_province:
            continue
        sdf = extract_subject_data(boards[board_map[name]], year)
        if sdf.empty:
            boards_without_subjects.append(name)
            continue
        boards_with_subjects.append(name)
        sdf = sdf.copy()
        sdf["Board"] = name
        subj_rows.append(sdf)
    if subj_rows:
        all_subj = pd.concat(subj_rows, ignore_index=True)
        all_subj["Appeared"] = pd.to_numeric(all_subj["Appeared"], errors="coerce")
        all_subj["Passed"] = pd.to_numeric(all_subj["Passed"], errors="coerce")
        agg = all_subj.groupby("Subject", as_index=False)[["Appeared", "Passed"]].sum()
        agg["Pass %"] = (100 * agg["Passed"] / agg["Appeared"].replace(0, np.nan)).round(2)
        top = agg.sort_values("Appeared", ascending=False).head(15).sort_values("Pass %")
        fig = go.Figure(go.Bar(x=top["Pass %"], y=top["Subject"], orientation="h", marker_color=ACCENT,
                                text=top["Pass %"], texttemplate="%{text:.1f}%", textposition="outside"))
        fig.update_layout(title=chart_title(f"Top-appeared Subjects — Pass % ({year_label}, all reporting boards combined)"),
                           height=max(400, 32 * len(top)), xaxis_range=[0, 105], showlegend=False, margin=chart_margins())
        show_chart(style_fig(fig))
        st.caption(
            f"✅ Subject-wise data available for **{len(boards_with_subjects)} of {len(boards_with_subjects) + len(boards_without_subjects)}** boards"
            f" for {year_label}: {', '.join(boards_with_subjects)}."
            + (f"  ⚠️ Not published for: {', '.join(boards_without_subjects)}." if boards_without_subjects else "")
        )
        with st.expander("📋 Full subject-wise table (all reporting boards)"):
            st.dataframe(agg.sort_values("Pass %"), use_container_width=True, hide_index=True)
            csv_download_button(agg, "⬇️ Download subject-wise CSV", "subject_wise_all_boards.csv")
    else:
        st.info(f"No board publishes subject-wise data for {year_label} under the current filter.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("🟢 Appeared Volume by Board (Stacked Area)")
    area_pivot = master.pivot_table(index="Year", columns="Board", values="Appeared", aggfunc="sum").fillna(0)
    show_chart(stacked_area_chart(area_pivot, "Total Appeared by Board, Year over Year"))
    st.markdown("</div>", unsafe_allow_html=True)

    rank_sorted = rankings.sort_values("Appeared", ascending=False)
    gb_failed = (rank_sorted["Appeared"] - rank_sorted["Passed"]).clip(lower=0) if "Failed" not in rank_sorted.columns else rank_sorted["Failed"]
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("🟦 Passed vs Failed by Board (Grouped Bar)")
    show_chart(grouped_bar_chart(rank_sorted["Board"].tolist(),
                                  {"Passed": rank_sorted["Passed"].tolist(), "Failed": gb_failed.tolist()},
                                  "Passed vs Failed — All Boards"))
    st.markdown("</div>", unsafe_allow_html=True)

    bc1, bc2 = st.columns(2)
    with bc1:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("🔵 Board Size vs Performance (Bubble)")
        show_chart(bubble_scatter_chart(rankings["Appeared"].tolist(), rankings["Pass %"].tolist(),
                                        rankings["Appeared"].tolist(), rankings["Board"].tolist(),
                                        "Appeared vs Pass % (bubble size = Appeared)", x_title="Total Appeared"))
        st.markdown("</div>", unsafe_allow_html=True)
    with bc2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("🟧 Board Share of Appeared (Treemap)")
        show_chart(treemap_chart(rankings["Board"].tolist(), rankings["Appeared"].tolist(), "Appeared Share by Board"))
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("🔻 Overall Result Funnel")
    show_chart(funnel_chart(["Appeared", "Passed"], [total_app, total_pass], "Appeared → Passed (All Boards)"))
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("🟥 Board × Year Pass % (Heatmap)")
    heat_pivot = master.pivot_table(index="Board", columns="Year", values="Pass %", aggfunc="mean")
    heat_pivot = heat_pivot.reindex(rankings.sort_values("Appeared", ascending=False)["Board"].tolist())
    show_chart(heatmap_chart(heat_pivot.values, [str(c) for c in heat_pivot.columns],
                              heat_pivot.index.tolist(), "Pass % Heatmap — Board × Year"))
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("📋 Total Students Appeared — Each Board · Each Year")
    appeared_tbl = get_board_appeared_table(boards)
    if not appeared_tbl.empty:
        st.dataframe(appeared_tbl, use_container_width=True, hide_index=True)
        csv_download_button(appeared_tbl, "⬇️ Download appeared CSV", "board_appeared_by_year.csv")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("All Boards Summary")
    st.dataframe(rankings, use_container_width=True, hide_index=True)
    csv_download_button(rankings, "⬇️ Download rankings CSV", "all_boards_rankings.csv")
    st.markdown("</div>", unsafe_allow_html=True)


