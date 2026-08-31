"""views_board.py -- Single-board deep-dive page rendering logic."""
import pandas as pd
import numpy as np
import streamlit as st
from common import *

def render_board_page(
    selected_board_name, board_sheets, year, selected_year,
    demo_df, gender_df, type_df, totals,
    subject_groups, subjects, districts, trend_df, grades_df, stream_df,
    boards=None, board_map=None,
    # ── Filter params — all supplied by the sidebar ───────────────────────────
    filter_gender_list=None,   # ["Male"] / ["Female"] / ["Male","Female"]
    filter_type_list=None,     # ["Regular"] / ["Private"] / both
    min_pass_pct=0,            # hide subjects/districts below this %
    top_n_subjects=15,         # max bars in subject chart
    top_n_districts=12,        # max bars in district chart
    subj_trend_df=None,        # pre-computed & filtered subject trend data
    trend_boards=None,         # board names used in the trend
):
    # ── Apply data filters ────────────────────────────────────────────────────
    if filter_gender_list:
        if not gender_df.empty and "Gender" in gender_df.columns:
            gender_df = gender_df[gender_df["Gender"].isin(filter_gender_list)].copy()

    if filter_type_list:
        if not type_df.empty and "Candidate Type" in type_df.columns:
            type_df = type_df[type_df["Candidate Type"].isin(filter_type_list)].copy()

    if min_pass_pct > 0:
        if not subjects.empty and "Pass %" in subjects.columns:
            subjects = subjects[subjects["Pass %"] >= min_pass_pct].copy()
        if not districts.empty and "Pass %" in districts.columns:
            districts = districts[districts["Pass %"] >= min_pass_pct].copy()

    if subj_trend_df is None:
        subj_trend_df = pd.DataFrame(columns=["Year", "Subject", "Pass %", "Appeared"])

    # ── Guard ─────────────────────────────────────────────────────────────────
    if totals["appeared"] <= 0 and demo_df.empty and trend_df.empty:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown(f"**No records** in the master file for **{selected_board_name}** · **{selected_year}**.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    total_appeared = totals["appeared"]
    total_passed = totals["passed"]
    total_failed = totals["failed"] or max(total_appeared - total_passed, 0)
    pass_pct = totals["pass_pct"]
    fail_pct = round(100 - pass_pct, 1) if pass_pct else 0
    yoy = yoy_delta_from_trend(trend_df)

    insights = build_insights(gender_df, type_df, stream_df, subjects, pass_pct, yoy)
    year_label = selected_year if selected_year == "All Years" else selected_year
    st.markdown(
        f"""<div class="board-header">
        <div class="board-header-title">{selected_board_name}</div>
        <div class="board-header-sub">{year_label} · Total Appeared: <strong>{total_appeared:,}</strong> students</div>
        </div>""",
        unsafe_allow_html=True,
    )

    _check = validate_totals(totals)
    _gaps = []
    if not _check["ok"]:
        _gaps.append(_check["message"])
    if gender_df.empty:
        _gaps.append("Boys/Girls split not published for this selection")
    if type_df.empty:
        _gaps.append("Regular/Private split not published for this selection")
    if _gaps:
        st.caption("⚠️ Data completeness: " + " · ".join(_gaps))

    render_gender_type_flow(selected_board_name, str(year_label), totals, gender_df, type_df)

    st.markdown('<div class="insight-box">', unsafe_allow_html=True)
    st.subheader("💡 Key Insights")
    for line in insights:
        st.markdown(f"- {line}")
    st.markdown("</div>", unsafe_allow_html=True)

    boys = gender_df[gender_df["Gender"] == "Male"] if not gender_df.empty and "Gender" in gender_df.columns else pd.DataFrame()
    girls = gender_df[gender_df["Gender"] == "Female"] if not gender_df.empty and "Gender" in gender_df.columns else pd.DataFrame()
    boys_total = int(boys["Appeared"].sum()) if not boys.empty else 0
    girls_total = int(girls["Appeared"].sum()) if not girls.empty else 0
    gender_value = f"{fmt_k(boys_total)} / {fmt_k(girls_total)}" if not gender_df.empty else "Not available"
    reg_total = priv_total = 0
    if not type_df.empty and "Candidate Type" in type_df.columns:
        regular = type_df[type_df["Candidate Type"].str.contains("Regular", case=False, na=False)]
        private = type_df[type_df["Candidate Type"].str.contains("Private", case=False, na=False)]
        reg_total = int(regular["Appeared"].sum()) if not regular.empty else 0
        priv_total = int(private["Appeared"].sum()) if not private.empty else 0
    trend_note = f" · YoY Δ {yoy:+.1f}%" if yoy is not None else ""

    kpi_data = [
        ("Total Appeared", fmt_k(total_appeared), f"{selected_year if selected_year != 'All Years' else 'All years combined'}"),
        ("Total Pass", fmt_k(total_passed), f"{pass_pct:.0f}% of total{trend_note}"),
        ("Total Fail", fmt_k(total_failed), f"{fail_pct:.0f}% of total"),
        ("Boys / Girls", gender_value, "Gender split" if not gender_df.empty else "Not in source data"),
    ]
    cols = st.columns(4)
    for col, accent, (label, value, sub) in zip(cols, [NAVY, PASS_COLOR, FAIL_COLOR, MALE_COLOR], kpi_data):
        col.markdown(kpi_card(label, value, sub, accent), unsafe_allow_html=True)

    reg_priv_value = f"{fmt_k(reg_total)} / {fmt_k(priv_total)}" if reg_total + priv_total > 0 else "Not available"
    reg_priv_sub = "Student type split" if reg_total + priv_total > 0 else "Not in source data"
    st.markdown(kpi_card("Regular / Private", reg_priv_value, reg_priv_sub, NAVY_LIGHT), unsafe_allow_html=True)

    st.write("")
    render_chart_legend()

    gc1, gc2 = st.columns([1, 1.4])
    with gc1:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("🎯 Overall Pass Rate (Gauge)")
        show_chart(gauge_chart(pass_pct, f"{selected_board_name} · Pass %"))
        st.markdown("</div>", unsafe_allow_html=True)
    with gc2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("🧱 Result Breakdown (Passed vs Failed)")
        show_chart(stacked_bar_breakdown_chart(total_appeared, total_passed, total_failed, "Appeared → Passed / Failed"))
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("🔻 Result Funnel")
    show_chart(funnel_chart(["Appeared", "Passed"], [total_appeared, total_passed], f"{selected_board_name} — Appeared → Passed"))
    st.markdown("</div>", unsafe_allow_html=True)

    if not subject_groups.empty and "Appeared" in subject_groups.columns:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("🟧 Subject Group Share (Treemap)")
        grp_appeared = subject_groups.groupby("Group")["Appeared"].sum().reset_index()
        show_chart(treemap_chart(grp_appeared["Group"].tolist(), grp_appeared["Appeared"].tolist(), "Appeared Share by Subject Group"))
        st.markdown("</div>", unsafe_allow_html=True)
    elif not districts.empty:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("🟧 District Share (Treemap)")
        dist_val = districts.get("Appeared", districts.get("Pass %")) if isinstance(districts, dict) else (districts["Appeared"] if "Appeared" in districts.columns else districts["Pass %"])
        show_chart(treemap_chart(districts["District"].tolist(), dist_val.tolist(), "Share by District"))
        st.markdown("</div>", unsafe_allow_html=True)

    if not subjects.empty:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("🔵 Subjects: Volume vs Performance (Bubble)")
        subj_size = subjects["Appeared"].fillna(10).tolist() if "Appeared" in subjects.columns else [10] * len(subjects)
        show_chart(bubble_scatter_chart(subj_size, subjects["Pass %"].tolist(), subj_size, subjects["Subject"].tolist(),
                                        "Subject Appeared vs Pass % (bubble size = Appeared)", x_title="Appeared"))
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Subject trend (uses pre-computed subj_trend_df from main script) ──────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("📈 Subject Pass % Trend (Multi-Year)")

    if subj_trend_df.empty:
        st.info("No multi-year subject data available for the selected board(s) / filter settings.")
    else:
        all_subjects = sorted(subj_trend_df["Subject"].unique())
        default_subjects = (
            subj_trend_df.groupby("Subject")["Appeared"].sum().sort_values(ascending=False).head(6).index.tolist()
            if "Appeared" in subj_trend_df.columns else all_subjects[:6]
        )

        # ── FIX: clear stale session-state selections when available subjects change ──
        skey = f"subj_trend_pick_{selected_board_name}"
        stored_picks = st.session_state.get(skey, [])
        if stored_picks and not any(s in all_subjects for s in stored_picks):
            st.session_state[skey] = [s for s in default_subjects if s in all_subjects]

        picked_subjects = st.multiselect(
            "Subjects to plot", options=all_subjects,
            default=[s for s in default_subjects if s in all_subjects],
            key=skey,
        )
        plot_df = subj_trend_df[subj_trend_df["Subject"].isin(picked_subjects)] if picked_subjects else subj_trend_df

        if len(trend_boards or []) > 1 and not plot_df.empty and "Board" in plot_df.columns:
            plot_df = plot_df.copy()
            plot_df["Subject"] = plot_df["Subject"] + " — " + plot_df["Board"]

        if plot_df.empty:
            st.info("No data matches the current filters.")
        else:
            show_chart(subject_multi_year_trend_chart(plot_df, "Subject Pass % by Year"))

            trend_stats = compute_subject_trend_stats(subj_trend_df)
            if not trend_stats.empty:
                st.markdown("##### 🔎 Trend Insights")
                improved = trend_stats.sort_values("Slope (pp/yr)", ascending=False).head(5)
                declined = trend_stats.sort_values("Slope (pp/yr)", ascending=True).head(5)
                ic1, ic2 = st.columns(2)
                with ic1:
                    st.markdown("**📈 Most Improved**")
                    st.dataframe(improved[["Subject", "Slope (pp/yr)", "Total Change (pp)", "Start %", "End %"]], use_container_width=True, hide_index=True)
                with ic2:
                    st.markdown("**📉 Most Declining**")
                    st.dataframe(declined[["Subject", "Slope (pp/yr)", "Total Change (pp)", "Start %", "End %"]], use_container_width=True, hide_index=True)
                with st.expander("📐 Next-year projection (linear trend, not an actual result)"):
                    st.caption("Projected by fitting a straight line through each subject's Pass % across the selected years and extrapolating one year forward. Treat as a rough directional estimate only.")
                    proj_tbl = trend_stats.sort_values("Next Yr Proj %", ascending=False)[["Subject", "Years", "End %", "Next Yr Proj %"]]
                    st.dataframe(proj_tbl, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

    has_gender = not gender_df.empty
    has_passfail = total_passed + total_failed > 0
    if has_gender and has_passfail:
        col_gender, col_board = st.columns(2)
        with col_gender:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.subheader("Gender Distribution")
            show_chart(gender_split_pie(gender_df))
            st.markdown("</div>", unsafe_allow_html=True)
        with col_board:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.subheader("Board Pass / Fail")
            show_chart(pass_fail_pie(total_passed, total_failed, selected_board_name))
            st.markdown("</div>", unsafe_allow_html=True)
    elif has_gender:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Gender Distribution")
        show_chart(gender_split_pie(gender_df))
        st.markdown("</div>", unsafe_allow_html=True)
    elif has_passfail:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Board Pass / Fail")
        show_chart(pass_fail_pie(total_passed, total_failed, selected_board_name))
        st.markdown("</div>", unsafe_allow_html=True)

    col_gender_bar, col_type_bar = st.columns(2)
    with col_gender_bar:
        if has_gender:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.subheader("Pass / Fail by Gender")
            gender_bar = gender_df.copy()
            gender_bar["Label"] = gender_bar["Gender"].map(gender_label)
            show_chart(pass_fail_hbar(gender_bar, "Label"))
            st.markdown("</div>", unsafe_allow_html=True)
    with col_type_bar:
        if not type_df.empty and "Candidate Type" in type_df.columns:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.subheader("Pass / Fail by Student Type")
            show_chart(pass_fail_hbar(type_df, "Candidate Type"))
            st.markdown("</div>", unsafe_allow_html=True)

    if not trend_df.empty:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("📈 Year-over-Year Comparison (2024–2026)")
        tc1, tc2 = st.columns(2)
        with tc1:
            show_chart(trend_line_chart(trend_df, "Pass % Trend"))
        with tc2:
            td = trend_df.copy()
            if "Failed" not in td.columns:
                td["Failed"] = td["Appeared"] - td["Passed"]
            show_chart(year_compare_chart(td))
        st.markdown("</div>", unsafe_allow_html=True)

    sc1, sc2 = st.columns(2)
    if not stream_df.empty or not grades_df.empty:
        with sc1:
            if not stream_df.empty:
                st.markdown('<div class="section-card">', unsafe_allow_html=True)
                st.subheader("🔬 Science vs Arts / Humanities")
                show_chart(pass_fail_hbar(stream_df, "Stream", "Stream Pass / Fail"))
                st.dataframe(stream_df, use_container_width=True, hide_index=True)
                st.markdown("</div>", unsafe_allow_html=True)
        with sc2:
            if not grades_df.empty:
                st.markdown('<div class="section-card">', unsafe_allow_html=True)
                st.subheader("🎓 Grade Distribution")
                show_chart(grade_hbar(grades_df))
                st.markdown("</div>", unsafe_allow_html=True)

    if not subject_groups.empty:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("📊 Pass Performance by Subject Group")
        show_chart(subject_group_chart(subject_groups))
        st.markdown("</div>", unsafe_allow_html=True)

    if not subjects.empty:
        weak = subjects[subjects["Pass %"] < 70].sort_values("Pass %")
        if not weak.empty:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.subheader("⚠️ Subjects Below 70% Pass Rate")
            st.dataframe(weak[["Subject", "Pass %"] + [c for c in ["Appeared", "Passed"] if c in weak.columns]],
                         use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)

    if not demo_df.empty:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Breakdown Table")
        table_df = demo_df.copy()
        if "Pass %" not in table_df.columns or table_df["Pass %"].isna().all():
            table_df["Pass %"] = (100 * table_df["Passed"] / table_df["Appeared"].replace(0, float("nan"))).round(1)
        search = st.text_input(
            "🔍 Search table", placeholder="Filter by gender, group, type...",
            key=f"breakdown_search_{selected_board_name}",
        )
        if search:
            mask = table_df.astype(str).apply(lambda r: r.str.contains(search, case=False, na=False).any(), axis=1)
            table_df = table_df[mask]
        display_cols = [c for c in ["Candidate Type", "Gender", "Group", "Appeared", "Passed", "Failed", "Pass %"] if c in table_df.columns]
        st.dataframe(table_df[display_cols], use_container_width=True, hide_index=True)
        csv_download_button(table_df[display_cols], "⬇️ Download breakdown CSV", f"{selected_board_name}_breakdown.csv")
        st.markdown("</div>", unsafe_allow_html=True)

    if not districts.empty:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("🏙️ District / City Pass %")
        show_chart(district_pass_hbar(districts, top_n=top_n_districts))
        csv_download_button(districts, "⬇️ Download districts CSV", f"{selected_board_name}_districts.csv")
        st.markdown("</div>", unsafe_allow_html=True)

    if not subjects.empty:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("📚 Subject-wise Pass %")
        show_chart(subject_pass_hbar(subjects, top_n=top_n_subjects))
        csv_download_button(subjects, "⬇️ Download subjects CSV", f"{selected_board_name}_subjects.csv")
        st.markdown("</div>", unsafe_allow_html=True)



