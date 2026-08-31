"""
Subject-wise Analysis — pass % by subject, combined across all boards and per-board, all years.
"""
import pandas as pd
import streamlit as st

from common import (
    inject_css, render_hero_banner, render_sidebar_brand, render_currently_viewing,
    render_global_filters,
    load_boards, show_missing_workbook_error,
    extract_subject_data, kpi_card, show_chart, subject_pass_hbar,
    csv_download_button, fmt_k, NAVY, TEAL,
)

st.set_page_config(page_title="Subject-wise Analysis — BISE Dashboard", page_icon="📚", layout="wide")
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
    render_currently_viewing(f"Subject-wise — {len(boards_sel)} board(s)<br>{year_label_sb}")

if not boards_sel:
    st.info("Select at least one board from the sidebar Filters to see results.")
    st.stop()

year_label = "All Years" if year is None else str(year)
st.markdown(render_hero_banner(len(board_prefixes)), unsafe_allow_html=True)
st.subheader(f"📚 Subject-wise Analysis — {len(boards_sel)} board(s), {year_label}")

frames = []
for name in boards_sel:
    prefix = board_map[name]
    df = extract_subject_data(boards[prefix], year)
    if df.empty:
        continue
    df = df.copy()
    df["Board"] = name
    frames.append(df)

if not frames:
    st.info("No subject data available.")
    st.stop()

all_subj = pd.concat(frames, ignore_index=True)
all_subj["Appeared"] = pd.to_numeric(all_subj["Appeared"], errors="coerce")
all_subj["Passed"] = pd.to_numeric(all_subj["Passed"], errors="coerce")

# ── Merge duplicate subject names that only differ by casing/spacing ───────
# The source sheets spell the same subject inconsistently across boards
# (e.g. "Wood Work" vs "WOOD WORK (FURNITURE MAKING)" is a genuinely different
# subject, but "Tailoring" vs "TAILORING" and "Embroidery" vs "EMBORIDERY"
# are the same subject typed differently) — normalizing on stripped-upper
# text merges the latter without inventing any numbers.
all_subj["Subject"] = all_subj["Subject"].astype(str).str.strip()
all_subj["SubjectKey"] = all_subj["Subject"].str.upper()
# Keep the most common original casing as the display label for each key.
_display_names = all_subj.groupby("SubjectKey")["Subject"].agg(lambda s: s.value_counts().idxmax())
all_subj["Subject"] = all_subj["SubjectKey"].map(_display_names)

combined = all_subj.groupby("Subject", as_index=False).agg(
    Appeared=("Appeared", "sum"), Passed=("Passed", "sum")
)
combined["Pass %"] = (100 * combined["Passed"] / combined["Appeared"].replace(0, float('nan'))).round(1)
combined = combined.sort_values("Pass %", ascending=False)

# ── Minimum-appeared filter ──────────────────────────────────────────────────
# Subjects with only a handful of candidates (e.g. 1-4 students) swing to a
# fake-looking 100% or 0% purely from small-sample noise, not real performance.
# Let the reader set a floor instead of silently hiding or fabricating numbers.
st.markdown("<br>", unsafe_allow_html=True)
min_appeared = st.slider(
    "Minimum students appeared (filters out tiny-sample subjects that show misleading 100%/0%)",
    min_value=0, max_value=2000, value=300, step=50, key="subject_min_appeared",
)
excluded_count = int((combined["Appeared"] < min_appeared).sum())
reliable = combined[combined["Appeared"] >= min_appeared].copy()
if excluded_count:
    st.caption(f"⚠️ {excluded_count} subject(s) below {min_appeared:,} appeared are hidden from rankings/KPIs below (still in the full download).")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(kpi_card("SUBJECTS (RELIABLE)", str(len(reliable)), f"{len(combined)} total · {len(boards_sel)} boards", NAVY), unsafe_allow_html=True)
if not reliable.empty:
    with c2:
        best = reliable.iloc[0]
        st.markdown(kpi_card("BEST SUBJECT", f"{best['Pass %']:.1f}%", f"{best['Subject']} · {fmt_k(int(best['Appeared']))} appeared", TEAL), unsafe_allow_html=True)
    with c3:
        worst = reliable.sort_values("Pass %").iloc[0]
        st.markdown(kpi_card("WEAKEST SUBJECT", f"{worst['Pass %']:.1f}%", f"{worst['Subject']} · {fmt_k(int(worst['Appeared']))} appeared", "#E11D48"), unsafe_allow_html=True)
else:
    with c2:
        st.markdown(kpi_card("BEST SUBJECT", "—", "No subject meets the minimum", TEAL), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card("WEAKEST SUBJECT", "—", "No subject meets the minimum", "#E11D48"), unsafe_allow_html=True)

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.subheader("📊 Subject-wise Pass %")

view_mode = st.radio(
    "View",
    ["📊 Top 10 (Chart)", "📋 All Subjects (Table)"],
    horizontal=True,
    label_visibility="collapsed",
    key="subject_view_mode",
)

if view_mode == "📊 Top 10 (Chart)":
    top10 = reliable.head(10)
    if top10.empty:
        st.info("No subjects meet the minimum-appeared threshold above. Lower the slider to see results.")
    else:
        show_chart(subject_pass_hbar(top10, top_n=10))
        st.caption(
            f"Showing the top 10 of **{len(reliable)}** subjects with at least {min_appeared:,} students appeared, by Pass %. "
            "Switch to **All Subjects (Table)** above to see the rest — it's searchable and downloadable."
        )
else:
    search = st.text_input("🔍 Search subjects", placeholder="Type to filter by subject name...", key="subject_search")
    table_df = reliable.copy()
    if search:
        table_df = table_df[table_df["Subject"].str.contains(search, case=False, na=False)]
    st.dataframe(table_df, use_container_width=True, hide_index=True)

csv_download_button(combined, "⬇️ Download combined CSV (all subjects, no threshold)", "subject_wise_combined.csv")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown("**Per-board detail — every board, every subject**")
per_board_display = all_subj.drop(columns=["SubjectKey"], errors="ignore").sort_values(["Board", "Pass %"], ascending=[True, False])
st.dataframe(per_board_display, use_container_width=True, hide_index=True)
csv_download_button(per_board_display, "⬇️ Download per-board CSV", "subject_wise_per_board.csv")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")
st.caption("Data source: BISE SSC master workbooks only · no estimated values")
