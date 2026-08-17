"""
BISE 10th Grade 2024–26 Result — Enhanced Results Dashboard
Run: streamlit run app.py
"""

import json
import time

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from data_loader import (
    BOARD_NAMES,
    aggregate_demo_rows,
    board_display_name,
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
    get_all_board_rankings,
    get_available_years,
    get_board_appeared_table,
    get_master_summary,
    group_by_board,
    list_board_prefixes,
    load_workbook,
    summarize_gender,
    summarize_type,
    split_matches_total,
    validate_totals,
    _extract_groupwise_type as extract_groupwise_type,
)
import data_loader

# ── Debug log ────────────────────────────────────────────────────────────────
DEBUG_LOG_PATH = "debug-c865f9.log"
DEBUG_ENDPOINT = "http://127.0.0.1:7778/ingest/b2547032-ded2-4a39-b793-e630640d666a"
DEBUG_SESSION = "c865f9"


def debug_log(location, message, data=None, hypothesis_id="A", run_id="features"):
    payload = {
        "sessionId": DEBUG_SESSION,
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data or {},
        "timestamp": int(time.time() * 1000),
    }
    try:
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload) + "\n")
    except OSError:
        pass
    try:
        import urllib.request
        req = urllib.request.Request(
            DEBUG_ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-Debug-Session-Id": DEBUG_SESSION},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=1)
    except Exception:
        pass


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BISE 10th Grade Results Dashboard",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design tokens ─────────────────────────────────────────────────────────────
BG = "#F4F6FA"
CARD = "#FFFFFF"
BORDER = "#E2E8F0"
TEXT = "#1F2937"
MUTED = "#64748B"
NAVY = "#0F5694"
NAVY_LIGHT = "#1A6BB5"
SIDEBAR_DARK = "#0B2763"
SIDEBAR_MID = "#0F5694"
NAVY_SOFT = "#E8F2FB"
TEAL = "#2EC4B6"
ACCENT = TEAL
LIGHT_RED = "#F87171"
PALETTE = [
    NAVY, "#F59E0B", ACCENT, "#E11D48", "#8B5CF6", "#10B981", "#F97316", "#3B82C4",
    "#EC4899", "#84CC16", "#06B6D4", "#A855F7", "#EAB308", NAVY_LIGHT, "#78716C",
    "#65A30D", "#0EA5E9", "#D946EF",
]
MALE_COLOR = "#3D9A8B"
FEMALE_COLOR = "#F5C842"
PASS_COLOR = TEAL
FAIL_COLOR = LIGHT_RED
CHART_CONFIG = {"displayModeBar": False, "responsive": True}
GENDER_COLORS = {"Male": MALE_COLOR, "Female": FEMALE_COLOR, "Boys": MALE_COLOR, "Girls": FEMALE_COLOR}


def gender_label(g):
    return "Boys" if g == "Male" else "Girls"


def render_hero_banner(board_count=8):
    watermark = """
    <svg class="hero-watermark" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
      <path fill="white" d="M60 8L10 32v8l50 24 50-24v-8L60 8zm0 18.5L22 32 60 45.5 98 32 60 26.5zM20 48v32l40 20 40-20V48l-40 20-40-20zm40 52L30 84.5V56l30 15 30-15v28.5L60 100z"/>
    </svg>"""
    return f"""
    <div class="hero-banner">
      {watermark}
      <div class="hero-grid"></div>
      <div class="hero-inner">
        <div class="hero-left">
          <div class="hero-brand">
            <div class="hero-logo">🎓</div>
            <div><div class="hero-brand-title">BISE Analytics</div><div class="hero-brand-sub">SSC Dashboard</div></div>
          </div>
          <div class="hero-crumb">🏠 / Dashboard / SSC Results</div>
          <div class="hero-title-row"><span class="hero-accent"></span>
            <h1 class="hero-title">10th Grade Results 2024–26</h1></div>
          <p class="hero-desc">Board-wise pass/fail, gender ratios, districts, subjects & year-over-year trends for all BISE boards.</p>
          <div class="hero-pill">📅 SSC Annual-I · 2024–2026</div>
        </div>
        <div class="hero-stat">
          <div class="hero-stat-icon">🎓</div>
          <div><div class="hero-stat-num">{board_count}</div><div class="hero-stat-label">TOTAL BOARDS</div></div>
        </div>
      </div>
    </div>"""


def kpi_card(label, value, sub, accent=NAVY):
    return f"""<div class="kpi-box" style="border-left-color:{accent};">
    <div class="kpi-label">{label}</div><div class="kpi-value">{value}</div>
    <div class="kpi-sub">{sub}</div></div>"""


# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <style>
    #MainMenu, footer {{visibility: hidden;}}
    div[data-testid="stDecoration"], div[data-testid="stStatusWidget"] {{display: none;}}
    header[data-testid="stHeader"] {{
        visibility: hidden !important; height: 0 !important; min-height: 0 !important;
        max-height: 0 !important; margin: 0 !important; padding: 0 !important;
        border: none !important; background: transparent !important; overflow: visible !important;
    }}
    button[data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"] {{
        visibility: visible !important; display: flex !important;
        color: {SIDEBAR_DARK} !important; position: fixed !important;
        top: 8px !important; left: 8px !important; z-index: 999999 !important;
        background: rgba(255,255,255,0.95) !important; border-radius: 8px !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.12) !important;
    }}
    .stApp {{ background: {BG}; color: {TEXT}; }}
    [data-testid="stAppViewContainer"], [data-testid="stMain"], section.main {{
        padding-top: 0 !important; margin-top: 0 !important;
    }}
    div.block-container, [data-testid="stMainBlockContainer"] {{
        padding-top: 0.25rem !important; max-width: 100%;
    }}
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {SIDEBAR_DARK} 0%, {SIDEBAR_MID} 100%) !important;
        min-width: 300px !important; width: 300px !important;
        border-right: 1px solid rgba(255,255,255,0.08);
    }}
    [data-testid="stSidebar"] > div:first-child {{
        background: transparent !important; padding-top: 0 !important;
    }}
    [data-testid="stSidebarContent"] {{ padding-top: 0.5rem !important; }}
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stCaption {{ color: rgba(255,255,255,0.95) !important; }}
    [data-testid="stSidebar"] .sidebar-brand {{
        display: flex; align-items: center; gap: 12px;
        padding: 4px 4px 16px 4px; margin-bottom: 4px;
    }}
    [data-testid="stSidebar"] .sidebar-brand-icon {{
        width: 44px; height: 44px; border-radius: 10px;
        background: rgba(255,255,255,0.14);
        display: flex; align-items: center; justify-content: center;
        font-size: 22px; flex-shrink: 0;
    }}
    [data-testid="stSidebar"] .sidebar-brand-title {{
        color: #FFFFFF !important; font-weight: 700; font-size: 1.05rem; line-height: 1.2;
    }}
    [data-testid="stSidebar"] .sidebar-brand-sub {{
        color: rgba(255,255,255,0.72) !important; font-size: 12px; margin-top: 2px;
    }}
    [data-testid="stSidebar"] .sidebar-section {{
        color: rgba(255,255,255,0.55) !important;
        font-size: 11px; font-weight: 700; letter-spacing: 0.08em;
        text-transform: uppercase; margin: 18px 0 10px 2px;
    }}
    [data-testid="stSidebar"] .sidebar-active {{
        background: rgba(255,255,255,0.12); border-radius: 10px;
        padding: 10px 12px; margin-top: 12px;
        border: 1px solid rgba(255,255,255,0.15);
    }}
    [data-testid="stSidebar"] .sidebar-active-label {{
        color: rgba(255,255,255,0.65) !important; font-size: 11px;
        text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px;
    }}
    [data-testid="stSidebar"] .sidebar-active-value {{
        color: #FFFFFF !important; font-size: 13px; font-weight: 600; line-height: 1.4;
    }}
    [data-testid="stSidebar"] .stSelectbox > div > div {{
        background-color: rgba(255,255,255,0.12) !important;
        border: 1px solid rgba(255,255,255,0.28) !important;
        border-radius: 8px !important; color: #FFFFFF !important;
    }}
    [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div {{
        color: #FFFFFF !important; background: transparent !important;
    }}
    [data-testid="stSidebar"] .stSelectbox svg {{ fill: rgba(255,255,255,0.85) !important; }}
    [data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,0.2); margin: 16px 0; }}
    [data-testid="stSidebar"] .stMultiSelect > div > div {{
        background-color: #FFFFFF !important;
        border: 1px solid rgba(255,255,255,0.35) !important;
        border-radius: 8px !important;
    }}
    [data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] {{
        background: {NAVY} !important;
        border: 1px solid {NAVY} !important;
        color: #FFFFFF !important;
    }}
    [data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] span {{
        color: #FFFFFF !important;
    }}
    [data-testid="stSidebar"] .stMultiSelect input {{
        color: #1A1A2E !important;
    }}
    [data-testid="stSidebar"] .stSlider {{ color: rgba(255,255,255,0.9) !important; }}
    h1, h2, h3, h4 {{ color: {TEXT} !important; font-weight: 700; }}
    .filter-bar, .section-card, .insight-box, .legend-bar {{
        background: {CARD}; border: 1px solid {BORDER}; border-radius: 16px;
        padding: 16px 20px; margin-bottom: 16px;
        box-shadow: 0 2px 10px rgba(16,24,40,0.05);
    }}
    .kpi-box {{
        border-radius: 12px; padding: 18px 20px; min-height: 92px;
        background: {CARD}; border: 1px solid {BORDER}; border-left: 4px solid {NAVY};
        box-shadow: 0 2px 8px rgba(27,42,74,0.06); color: {TEXT};
    }}
    .kpi-label {{ font-size: 13px; color: {MUTED}; font-weight: 500; }}
    .kpi-value {{ font-size: 26px; font-weight: 700; margin-top: 4px; color: {NAVY}; }}
    .kpi-sub {{ font-size: 12px; color: {MUTED}; margin-top: 2px; }}
    .insight-box {{ border-left: 4px solid {NAVY}; }}
    .legend-bar {{ display: flex; gap: 18px; flex-wrap: wrap; font-size: 13px; }}
    .legend-item {{ display: flex; align-items: center; gap: 6px; }}
    .legend-dot {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; }}
    div[data-testid="stPlotlyChart"] {{ overflow: visible !important; min-height: 280px; }}
    .hero-banner {{
        position: relative; overflow: hidden; border-radius: 16px;
        margin: 0 0 20px 0;
        background: linear-gradient(135deg, {NAVY} 0%, {NAVY_LIGHT} 100%);
        box-shadow: 0 4px 20px rgba(15,86,148,0.22); padding: 0;
    }}
    .hero-watermark {{
        position: absolute; right: 32%; top: 42%; transform: translateY(-50%);
        width: 140px; height: 140px; opacity: 0.10; pointer-events: none; z-index: 0;
    }}
    .hero-grid {{
        position: absolute; right: 12px; top: 12px; width: 80px; height: 80px;
        background-image: radial-gradient(rgba(255,255,255,0.25) 1px, transparent 1px);
        background-size: 10px 10px; opacity: 0.5; pointer-events: none;
    }}
    .hero-inner {{
        position: relative; z-index: 1; display: flex; justify-content: space-between;
        align-items: center; gap: 24px; padding: 28px 32px; flex-wrap: wrap;
    }}
    .hero-left {{ flex: 1; min-width: 280px; }}
    .hero-brand {{ display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }}
    .hero-logo {{
        width: 42px; height: 42px; border-radius: 10px; background: rgba(255,255,255,0.15);
        display: flex; align-items: center; justify-content: center; font-size: 22px;
    }}
    .hero-brand-title {{ color: #FFFFFF !important; font-weight: 700; font-size: 16px; }}
    .hero-brand-sub {{ color: rgba(255,255,255,0.75); font-size: 12px; }}
    .hero-crumb {{ color: rgba(255,255,255,0.85); font-size: 13px; margin-bottom: 12px; }}
    .hero-title-row {{ display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }}
    .hero-accent {{ width: 4px; height: 32px; background: {ACCENT}; border-radius: 2px; flex-shrink: 0; }}
    .hero-title {{ color: #FFFFFF !important; font-size: 1.85rem !important; font-weight: 700 !important;
        margin: 0 !important; line-height: 1.2; }}
    .hero-desc {{ color: rgba(255,255,255,0.92) !important; font-size: 14px; margin: 0 0 14px 0; max-width: 620px; }}
    .hero-pill {{
        display: inline-block; background: rgba(0,0,0,0.18); color: rgba(255,255,255,0.95);
        padding: 6px 14px; border-radius: 20px; font-size: 12px;
    }}
    .hero-stat {{
        background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.2);
        border-radius: 14px; padding: 18px 22px; display: flex; align-items: center; gap: 14px;
        min-width: 180px; backdrop-filter: blur(4px);
    }}
    .hero-stat-icon {{ font-size: 28px; opacity: 0.9; }}
    .hero-stat-num {{ color: #FFFFFF !important; font-size: 2rem; font-weight: 700; line-height: 1; }}
    .hero-stat-label {{ color: rgba(255,255,255,0.75); font-size: 11px; letter-spacing: 0.06em; margin-top: 4px; }}
    .board-header {{
        background: {CARD}; border: 1px solid {BORDER}; border-radius: 12px;
        padding: 14px 18px; margin-bottom: 16px; border-left: 4px solid {NAVY};
    }}
    .board-header-title {{ font-size: 1.25rem; font-weight: 700; color: {NAVY}; margin: 0; }}
    .board-header-sub {{ color: {MUTED}; font-size: 13px; margin-top: 4px; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Plotly helpers ─────────────────────────────────────────────────────────────
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=TEXT, family="Segoe UI, Helvetica Neue, Arial, sans-serif", size=13),
    autosize=True,
)


def style_fig(fig):
    updates = dict(PLOTLY_LAYOUT)
    cur_margin = fig.layout.margin
    if cur_margin is not None and any(getattr(cur_margin, k, None) is not None for k in ("t", "b", "l", "r")):
        updates.pop("margin", None)
    cur_legend = fig.layout.legend
    if cur_legend is not None and getattr(cur_legend, "orientation", None) is not None:
        updates.pop("legend", None)
    fig.update_layout(**updates)
    return fig


def chart_title(text):
    if not text:
        return None
    return dict(text=text, x=0, xanchor="left", font=dict(size=14), pad=dict(t=4, b=18))


def legend_top_right():
    return dict(orientation="h", yanchor="bottom", y=1.0, x=1.0, xanchor="right",
                bgcolor="rgba(255,255,255,0.9)", tracegroupgap=10)


def legend_bottom_clear(extra_rows=0):
    return dict(orientation="h", yanchor="top", y=-0.24 - (extra_rows * 0.08), x=0.5, xanchor="center",
                bgcolor="rgba(255,255,255,0.9)", tracegroupgap=10)


def chart_margins(title="", legend_pos="none", extra_right=0):
    top = 72 if title else 44
    bottom = 52
    if legend_pos == "top":
        top = max(top, 58)
    elif legend_pos == "bottom":
        bottom = 92
    elif legend_pos == "bottom_multi":
        bottom = 115
    return dict(t=top, b=bottom, l=20, r=30 + extra_right)


def show_chart(fig):
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)


def fmt_k(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.0f}K"
    return f"{n:,}"


def csv_download_button(df, label, filename):
    if df is not None and not df.empty:
        st.download_button(label, df.to_csv(index=False).encode("utf-8"), filename, "text/csv")


def render_chart_legend():
    st.markdown(
        f"""<div class="legend-bar">
        <div class="legend-item"><span class="legend-dot" style="background:{MALE_COLOR}"></span> Boys</div>
        <div class="legend-item"><span class="legend-dot" style="background:{FEMALE_COLOR}"></span> Girls</div>
        <div class="legend-item"><span class="legend-dot" style="background:{PASS_COLOR}"></span> Passed</div>
        <div class="legend-item"><span class="legend-dot" style="background:{FAIL_COLOR}"></span> Failed</div>
        </div>""",
        unsafe_allow_html=True,
    )


# ── Chart factory functions ────────────────────────────────────────────────────
def donut_pie(labels, values, colors, title="", height=400):
    n = len(labels)
    fig = go.Figure(data=[go.Pie(
        labels=labels, values=values, hole=0.45, marker=dict(colors=colors),
        textinfo="percent", texttemplate="%{percent:.1%}",
        textposition="inside", insidetextorientation="horizontal",
        hovertemplate="%{label}: %{value:,}<br>%{percent:.1%}<extra></extra>",
    )])
    if n > 4:
        fig.update_traces(domain=dict(x=[0.06, 0.94], y=[0.18, 1.0]))
        legend_cfg = dict(orientation="h", yanchor="top", y=-0.02, x=0.5, xanchor="center",
                          font=dict(size=10), tracegroupgap=6, bgcolor="rgba(255,255,255,0.85)")
        margins = dict(t=55, b=115, l=10, r=10)
        chart_height = max(height + 140, 600)
    else:
        legend_cfg = dict(orientation="h", yanchor="bottom", y=-0.18, x=0.5, xanchor="center")
        margins = dict(t=55, b=90, l=30, r=30)
        chart_height = height
    fig.update_layout(title=title, height=chart_height, showlegend=True, legend=legend_cfg, margin=margins)
    return style_fig(fig)


def pass_fail_pie(passed, failed, title="", height=400):
    if passed + failed <= 0:
        return None
    return donut_pie(["Passed", "Failed"], [passed, failed], [PASS_COLOR, FAIL_COLOR], title=title, height=height)


def pass_fail_hbar(df, label_col, title="", height=None):
    if df.empty:
        return None
    plot_df = df.copy()
    if "Pass %" not in plot_df.columns or plot_df["Pass %"].isna().all():
        plot_df["Pass %"] = (100 * plot_df["Passed"] / plot_df["Appeared"].replace(0, pd.NA)).round(1)
    plot_df["Fail %"] = (100 - plot_df["Pass %"]).clip(lower=0).round(1)
    chart_h = height or max(260, 90 * len(plot_df))
    fig = go.Figure()
    fig.add_trace(go.Bar(y=plot_df[label_col].astype(str), x=plot_df["Pass %"], name="Passed",
                         orientation="h", marker_color=PASS_COLOR,
                         text=[f"{v:.0f}%" for v in plot_df["Pass %"]],
                         textposition="inside", insidetextanchor="middle"))
    fig.add_trace(go.Bar(y=plot_df[label_col].astype(str), x=plot_df["Fail %"], name="Failed",
                         orientation="h", marker_color=FAIL_COLOR,
                         text=[f"{v:.0f}%" for v in plot_df["Fail %"]],
                         textposition="inside", insidetextanchor="middle"))
    fig.update_layout(title=chart_title(title), barmode="stack",
                      xaxis=dict(range=[0, 100], title="Percentage"),
                      yaxis=dict(automargin=True), height=chart_h, showlegend=False,
                      margin=chart_margins(title=title))
    return style_fig(fig)


def subject_pass_hbar(subjects, top_n=15):
    if subjects.empty:
        return None
    data = subjects.sort_values("Pass %", ascending=True).tail(top_n)
    fig = go.Figure(go.Bar(
        x=data["Pass %"], y=data["Subject"], orientation="h",
        marker=dict(color=data["Pass %"], colorscale=[[0, FAIL_COLOR], [0.5, NAVY_LIGHT], [1, PASS_COLOR]]),
        text=[f"{v:.1f}%" for v in data["Pass %"]], textposition="outside",
    ))
    fig.update_layout(title=chart_title(f"Subject-wise Pass % (top {len(data)})"),
                      xaxis=dict(range=[0, 105], title="Pass %"), yaxis=dict(automargin=True),
                      height=max(420, 28 * len(data)), showlegend=False,
                      margin=chart_margins(title="x", extra_right=40))
    return style_fig(fig)


def district_pass_hbar(districts, top_n=12):
    if districts.empty:
        return None
    data = districts.sort_values("Pass %", ascending=True).tail(top_n)
    fig = go.Figure(go.Bar(
        x=data["Pass %"], y=data["District"], orientation="h",
        marker=dict(color=data["Pass %"], colorscale=[[0, FAIL_COLOR], [0.5, NAVY_LIGHT], [1, PASS_COLOR]]),
        text=[f"{v:.1f}%" for v in data["Pass %"]], textposition="outside",
    ))
    fig.update_layout(title=chart_title(f"District / City Pass % (top {len(data)})"),
                      xaxis=dict(range=[0, 105], title="Pass %"), yaxis=dict(automargin=True),
                      height=max(380, 32 * len(data)), showlegend=False,
                      margin=chart_margins(title="x", extra_right=40))
    return style_fig(fig)


def gender_split_pie(gender_df, title="Gender Distribution"):
    if gender_df.empty:
        return None
    labels, values, colors = [], [], []
    for _, row in gender_df.iterrows():
        label = gender_label(row["Gender"])
        labels.append(label)
        values.append(int(row["Appeared"]))
        colors.append(GENDER_COLORS.get(row["Gender"], TEAL))
    return donut_pie(labels, values, colors, title=title, height=400)


def trend_line_chart(df, title, y_col="Pass %", color=NAVY):
    if df.empty or y_col not in df.columns:
        return None
    plot_df = df.dropna(subset=[y_col]).copy()
    if plot_df.empty:
        return None
    yvals = plot_df[y_col].astype(float)
    y_min, y_max = yvals.min(), yvals.max()
    pad = max(3, (y_max - y_min) * 0.15)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=plot_df["Year"], y=plot_df[y_col], mode="lines+markers",
        line=dict(color=color, width=3), marker=dict(size=10),
        hovertemplate="Year %{x}<br>%{y:.1f}%<extra></extra>" if y_col == "Pass %" else "Year %{x}<br>%{y:,.0f}<extra></extra>",
        name=y_col,
    ))
    fig.update_layout(title=chart_title(title), xaxis=dict(dtick=1, title="Year"),
                      yaxis=dict(title=y_col, range=[max(0, y_min - pad), y_max + pad + 5]),
                      height=400, showlegend=False, margin=dict(t=80, b=52, l=20, r=30))
    return style_fig(fig)


def year_compare_chart(trend_df):
    if trend_df.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Bar(x=trend_df["Year"], y=trend_df["Passed"], name="Passed", marker_color=PASS_COLOR))
    fig.add_trace(go.Bar(x=trend_df["Year"], y=trend_df["Failed"], name="Failed", marker_color=FAIL_COLOR))
    fig.update_layout(title=chart_title("Passed vs Failed by Year"), barmode="stack",
                      height=360, showlegend=False, margin=chart_margins(title="Passed vs Failed by Year"))
    return style_fig(fig)


def subject_multi_year_trend_chart(df, title="Subject Pass % Trend"):
    if df.empty or "Pass %" not in df.columns:
        return None
    plot_df = df.dropna(subset=["Pass %"]).copy()
    if plot_df.empty:
        return None
    fig = go.Figure()
    for i, subject in enumerate(sorted(plot_df["Subject"].unique())):
        sd = plot_df[plot_df["Subject"] == subject].sort_values("Year")
        if len(sd) < 1:
            continue
        fig.add_trace(go.Scatter(
            x=sd["Year"], y=sd["Pass %"], mode="lines+markers", name=subject,
            line=dict(width=3, shape="spline", smoothing=0.8, color=PALETTE[i % len(PALETTE)]),
            marker=dict(size=7),
            hovertemplate=f"{subject}<br>%{{x}}: %{{y:.1f}}%<extra></extra>",
        ))
    fig.update_layout(
        title=chart_title(title), height=440,
        xaxis=dict(dtick=1, title="Year", showgrid=True, gridcolor="rgba(0,0,0,0.06)", griddash="dot"),
        yaxis=dict(title="Pass %", showgrid=True, gridcolor="rgba(0,0,0,0.06)", griddash="dot"),
        legend=legend_bottom_clear(extra_rows=len(plot_df["Subject"].unique()) // 4),
        margin=chart_margins(title=title, legend_pos="bottom_multi"),
        hovermode="x unified",
    )
    return style_fig(fig)


def grade_hbar(grades_df, title="Grade Bands"):
    if grades_df.empty:
        return None
    data = grades_df.sort_values("Count", ascending=True)
    fig = go.Figure(go.Bar(
        x=data["Count"], y=data["Grade"].astype(str), orientation="h",
        marker_color=PALETTE[: len(data)],
        text=[f"{v:,}" for v in data["Count"]], textposition="outside",
    ))
    fig.update_layout(title=chart_title(title), xaxis_title="Students",
                      yaxis=dict(automargin=True), height=max(320, 36 * len(data)),
                      showlegend=False, margin=chart_margins(title=title))
    return style_fig(fig)


def subject_group_chart(df):
    if df.empty:
        return None
    pivot = df.pivot_table(index="Group", columns="Gender", values="Pass %", aggfunc="mean").reset_index()
    fig = go.Figure()
    colors = {"Male": MALE_COLOR, "Female": FEMALE_COLOR, "All": NAVY}
    for gender in pivot.columns:
        if gender == "Group":
            continue
        fig.add_trace(go.Bar(
            x=pivot["Group"], y=pivot[gender],
            name=gender_label(gender) if gender in ("Male", "Female") else gender,
            marker_color=colors.get(gender, NAVY),
            text=[f"{v:.0f}%" if pd.notna(v) else "" for v in pivot[gender]],
            textposition="outside",
        ))
    fig.update_layout(title=chart_title("Pass % by Subject Group"), barmode="group",
                      yaxis=dict(range=[0, 110]), height=max(420, 80 * len(pivot)),
                      legend=legend_top_right(),
                      margin=chart_margins(title="Pass % by Subject Group", legend_pos="top"))
    return style_fig(fig)


def gauge_chart(value, title, height=280):
    if value is None or pd.isna(value):
        return None
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=round(float(value), 1),
        number={"suffix": "%", "font": {"size": 32}},
        title={"text": title, "font": {"size": 14}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1},
            "bar": {"color": PASS_COLOR, "thickness": 0.28},
            "bgcolor": "white", "borderwidth": 0,
            "steps": [{"range": [0, 50], "color": "#FCE4E4"},
                       {"range": [50, 75], "color": "#FDF3D8"},
                       {"range": [75, 100], "color": "#DFF5F1"}],
            "threshold": {"line": {"color": NAVY, "width": 3}, "thickness": 0.85, "value": round(float(value), 1)},
        },
    ))
    fig.update_layout(height=height, margin=dict(t=50, b=10, l=30, r=30))
    return style_fig(fig)


def funnel_chart(stages, values, title="", height=380):
    if not stages or not values or all(v <= 0 for v in values):
        return None
    fig = go.Figure(go.Funnel(
        y=stages, x=values, marker=dict(color=PALETTE[: len(stages)]),
        textinfo="value+percent initial", textposition="inside",
    ))
    fig.update_layout(title=chart_title(title), height=height, showlegend=False,
                      margin=chart_margins(title=title))
    return style_fig(fig)


def stacked_bar_breakdown_chart(appeared, passed, failed, title="", height=380):
    if appeared is None:
        return None
    pass_pct = (passed / appeared * 100) if appeared else 0
    fail_pct = (failed / appeared * 100) if appeared else 0
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["Result Breakdown"], y=[passed], name="Passed",
                         marker=dict(color=PASS_COLOR),
                         text=[f"Passed: {passed:,.0f} ({pass_pct:.1f}%)"],
                         textposition="inside", width=[0.45]))
    fig.add_trace(go.Bar(x=["Result Breakdown"], y=[failed], name="Failed",
                         marker=dict(color=FAIL_COLOR),
                         text=[f"Failed: {failed:,.0f} ({fail_pct:.1f}%)"],
                         textposition="inside", width=[0.45]))
    fig.update_layout(barmode="stack", title=chart_title(title), height=height,
                      showlegend=True, legend=legend_top_right(),
                      margin=chart_margins(title=title, legend_pos="top"),
                      yaxis=dict(title=f"Appeared: {appeared:,.0f}", showgrid=True,
                                 gridcolor="rgba(0,0,0,0.06)", griddash="dot"),
                      xaxis=dict(showgrid=False))
    return style_fig(fig)


def treemap_chart(labels, values, title="", height=420):
    if not labels or not values:
        return None
    values = [v if pd.notna(v) and v > 0 else 0 for v in values]
    if sum(values) <= 0:
        return None
    fig = go.Figure(go.Treemap(
        labels=labels, parents=[""] * len(labels), values=values,
        marker=dict(colors=(PALETTE * (len(labels) // len(PALETTE) + 1))[: len(labels)]),
        textinfo="label+value+percent parent",
    ))
    fig.update_layout(title=chart_title(title), height=height, margin=chart_margins(title=title))
    return style_fig(fig)


def bubble_scatter_chart(x, y, size, text, title="", x_title="", y_title="Pass %", height=440):
    if x is None or len(x) == 0:
        return None
    x = [v if pd.notna(v) else 0 for v in x]
    y = [v if pd.notna(v) else 0 for v in y]
    size = [v if pd.notna(v) and v > 0 else 1 for v in size]
    max_size = max(size) if len(size) else 1
    show_labels = len(x) <= 8
    fig = go.Figure(go.Scatter(
        x=x, y=y, mode="markers+text" if show_labels else "markers",
        text=text if show_labels else None, textposition="top center",
        textfont=dict(size=10), customdata=text,
        hovertemplate="<b>%{customdata}</b><br>" + (x_title or "X") + ": %{x:,.0f}<br>" + y_title + ": %{y:.1f}%<extra></extra>",
        marker=dict(size=size, sizemode="area", sizeref=2.0 * max_size / (46.0 ** 2), sizemin=6,
                    color=y, colorscale=[[0, FAIL_COLOR], [0.5, NAVY_LIGHT], [1, PASS_COLOR]],
                    showscale=False, line=dict(width=1, color="white"), opacity=0.85),
    ))
    fig.update_layout(title=chart_title(title),
                      xaxis=dict(title=x_title), yaxis=dict(title=y_title, range=[0, 105]),
                      height=height, showlegend=False, margin=chart_margins(title=title))
    return style_fig(fig)


def stacked_area_chart(pivot_df, title="", y_title="Appeared", height=420):
    if pivot_df is None or pivot_df.empty:
        return None
    fig = go.Figure()
    for i, col in enumerate(pivot_df.columns):
        fig.add_trace(go.Scatter(
            x=pivot_df.index, y=pivot_df[col], mode="lines", stackgroup="one",
            name=str(col), line=dict(width=0.5, color=PALETTE[i % len(PALETTE)]),
        ))
    fig.update_layout(title=chart_title(title), xaxis=dict(dtick=1, title="Year"),
                      yaxis=dict(title=y_title), height=height,
                      legend=legend_bottom_clear(extra_rows=max(0, len(pivot_df.columns) // 5)),
                      margin=chart_margins(title=title, legend_pos="bottom_multi"))
    return style_fig(fig)


def grouped_bar_chart(x, series, title="", y_title="Students", height=400, colors=None):
    if x is None or len(x) == 0:
        return None
    fig = go.Figure()
    palette = colors or [PASS_COLOR, FAIL_COLOR, NAVY, ACCENT]
    for i, (name, values) in enumerate(series.items()):
        fig.add_trace(go.Bar(x=x, y=values, name=name, marker_color=palette[i % len(palette)]))
    fig.update_layout(title=chart_title(title), barmode="group",
                      xaxis=dict(automargin=True), yaxis=dict(title=y_title),
                      height=height, legend=legend_top_right(),
                      margin=chart_margins(title=title, legend_pos="top"))
    return style_fig(fig)


def heatmap_chart(z, x_labels, y_labels, title="", height=420):
    if z is None or len(z) == 0:
        return None
    fig = go.Figure(go.Heatmap(
        z=z, x=x_labels, y=y_labels,
        colorscale=[[0, FAIL_COLOR], [0.5, NAVY_LIGHT], [1, PASS_COLOR]],
        text=[[f"{v:.1f}%" if pd.notna(v) else "" for v in row] for row in z],
        texttemplate="%{text}", hovertemplate="%{y} · %{x}<br>%{z:.1f}%<extra></extra>",
        colorbar=dict(title="Pass %"),
    ))
    fig.update_layout(title=chart_title(title), xaxis=dict(dtick=1, title="Year"),
                      yaxis=dict(automargin=True),
                      height=max(height, 28 * len(y_labels)), margin=chart_margins(title=title))
    return style_fig(fig)


# ── Analytics helpers ──────────────────────────────────────────────────────────
def build_insights(gender_df, type_df, stream_df, subjects, pass_pct, yoy_delta):
    insights = []
    if not gender_df.empty and len(gender_df) >= 2:
        g = gender_df.set_index("Gender")
        if "Male" in g.index and "Female" in g.index:
            gap = g.loc["Female", "Pass %"] - g.loc["Male", "Pass %"]
            who = "Girls" if gap >= 0 else "Boys"
            insights.append(f"{who} pass **{abs(gap):.1f}%** higher than the other gender.")
    if not type_df.empty and len(type_df) >= 2 and "Candidate Type" in type_df.columns:
        t = type_df.set_index("Candidate Type")
        if "Regular" in t.index and "Private" in t.index:
            gap = t.loc["Regular", "Pass %"] - t.loc["Private", "Pass %"]
            insights.append(f"Regular students pass **{gap:.1f}%** higher than Private students.")
    if not stream_df.empty:
        best = stream_df.iloc[0]
        insights.append(f"Highest stream: **{best['Stream']}** at **{best['Pass %']:.1f}%** pass rate.")
    if not subjects.empty:
        weak = subjects[subjects["Pass %"] < 70]
        if not weak.empty:
            insights.append(f"**{len(weak)}** subject(s) below 70% pass rate — review needed.")
    if yoy_delta is not None:
        arrow = "improved" if yoy_delta >= 0 else "declined"
        insights.append(f"Pass rate {arrow} **{abs(yoy_delta):.1f}%** from 2024 to 2026.")
    insights.append(f"Overall pass rate for selected view: **{pass_pct:.1f}%**.")
    return insights


def yoy_delta_from_trend(trend_df):
    if trend_df.empty or "Pass %" not in trend_df.columns or len(trend_df) < 2:
        return None
    t = trend_df.sort_values("Year")
    return float(t.iloc[-1]["Pass %"] - t.iloc[0]["Pass %"])


def build_subject_year_trend(board_sheets):
    """Stack extract_subject_data across every available year."""
    frames = []
    for y in get_available_years(board_sheets):
        sd = extract_subject_data(board_sheets, y)
        if sd.empty or "Subject" not in sd.columns or "Pass %" not in sd.columns:
            continue
        sd = sd.copy()
        sd["Year"] = y
        frames.append(sd)
    if not frames:
        return pd.DataFrame(columns=["Year", "Subject", "Pass %", "Appeared"])
    return pd.concat(frames, ignore_index=True)


def compute_subject_trend_stats(df):
    if df.empty or df["Year"].nunique() < 2:
        return pd.DataFrame(columns=["Subject", "Years", "Slope (pp/yr)", "Total Change (pp)", "Start %", "End %", "Next Yr Proj %"])
    rows = []
    for subject, sd in df.groupby("Subject"):
        sd = sd.dropna(subset=["Pass %"]).sort_values("Year")
        if len(sd) < 2:
            continue
        years = sd["Year"].astype(float).to_numpy()
        pass_pct = sd["Pass %"].astype(float).to_numpy()
        slope, intercept = np.polyfit(years, pass_pct, 1)
        next_year = years.max() + 1
        projection = float(np.clip(slope * next_year + intercept, 0, 100))
        rows.append({
            "Subject": subject, "Years": f"{int(years.min())}–{int(years.max())}",
            "Slope (pp/yr)": round(float(slope), 2),
            "Total Change (pp)": round(float(pass_pct[-1] - pass_pct[0]), 2),
            "Start %": round(float(pass_pct[0]), 1), "End %": round(float(pass_pct[-1]), 1),
            "Next Yr Proj %": round(projection, 1),
        })
    return pd.DataFrame(rows)


# ── Overview page ──────────────────────────────────────────────────────────────
def render_overview(boards, year):
    master = get_master_summary(boards)
    rankings = get_all_board_rankings(boards, year)
    if master.empty:
        st.warning("Master summary not found in workbook.")
        return

    df = master if year is None else master[master["Year"] == year]
    total_app = int(df["Appeared"].sum())
    total_pass = int(df["Passed"].sum())
    total_fail = max(total_app - total_pass, 0)
    pass_pct = round(100 * total_pass / max(total_app, 1), 2)

    kpi = [("Boards", f"{df['Board'].nunique()}", "All BISE boards"),
           ("Total Appeared", fmt_k(total_app), "Combined students"),
           ("Total Passed", fmt_k(total_pass), f"{pass_pct:.1f}% pass rate"),
           ("Total Failed", fmt_k(total_fail), f"{100-pass_pct:.1f}% fail rate")]
    cols = st.columns(4)
    for col, accent, (label, val, sub) in zip(cols, [NAVY, ACCENT, PASS_COLOR, FAIL_COLOR], kpi):
        col.markdown(kpi_card(label, val, sub, accent), unsafe_allow_html=True)

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
    st.subheader("Pass % Trend — All Boards (2024–2026)")
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
    debug_log("app.py:overview", "Overview rendered", {"boards": len(rankings)}, "G")


# ── Board page ─────────────────────────────────────────────────────────────────
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
            table_df["Pass %"] = (100 * table_df["Passed"] / table_df["Appeared"].replace(0, pd.NA)).round(1)
        search = st.text_input("🔍 Search table", placeholder="Filter by gender, group, type...")
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

    debug_log("app.py:board", "Board page rendered", {"board": selected_board_name, "insights": len(insights)}, "H")


# ── Compare page ───────────────────────────────────────────────────────────────
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
    agg["Pass %"] = (100 * agg["Passed"] / agg["Appeared"].replace(0, pd.NA)).round(1)
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

    cols = st.columns(len(selected_names))
    for i, (col, (_, row)) in enumerate(zip(cols, agg.iterrows())):
        accent = PALETTE[i % len(PALETTE)]
        pass_val = f"{row['Pass %']:.1f}%" if pd.notna(row["Pass %"]) else "—"
        col.markdown(kpi_card(row["Board"], pass_val, f"{fmt_k(int(row['Appeared']))} appeared", accent), unsafe_allow_html=True)

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
                                      "Pass % by Gender — Selected Boards", y_title="Pass %", colors=gender_colors))
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("📋 Comparison Table")
    st.dataframe(agg, use_container_width=True, hide_index=True)
    csv_download_button(agg, "⬇️ Download comparison CSV", "board_comparison.csv")
    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════════════════════════════
try:
    sheets = load_workbook()
except FileNotFoundError:
    st.error(
        "Place **BISE_All_Boards_SSC_Master_2024-2026.xlsx** and "
        "**Punjab_Federal_SSC_2024-2026_MASTER.xlsx** in this folder, then run "
        "`python build_pro_master.py` to rebuild the merged master."
    )
    st.stop()

boards = group_by_board(sheets)
board_prefixes = list_board_prefixes(boards)
board_map = {board_display_name(p): p for p in board_prefixes}
ALL_BOARD_NAMES = sorted(board_map.keys())
board_list = ["Overview — All Boards", "🆚 Compare Boards"] + ALL_BOARD_NAMES

debug_log("app.py:load", "Workbook loaded", {"board_count": len(board_prefixes)}, "A")

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — ALL FILTERS LIVE HERE (no sidebar blocks inside render functions)
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(
        """<div class="sidebar-brand">
        <div class="sidebar-brand-icon">🎓</div>
        <div>
          <div class="sidebar-brand-title">BISE Analytics</div>
          <div class="sidebar-brand-sub">SSC Dashboard</div>
        </div>
        </div>""",
        unsafe_allow_html=True,
    )

    if st.button("🔄 Refresh Data", help="Reload workbook from disk"):
        data_loader.load_workbook.clear()
        st.rerun()

    # ── Primary filters ────────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-section">Primary Filters</div>', unsafe_allow_html=True)
    selected_board_name = st.selectbox("📍 Select Board", options=board_list, key="board_filter")

    is_overview = selected_board_name == "Overview — All Boards"
    is_compare  = selected_board_name == "🆚 Compare Boards"
    is_board_page = not is_overview and not is_compare

    if is_overview or is_compare:
        master_years = get_master_summary(boards)
        avail_years = sorted(master_years["Year"].dropna().astype(int).unique().tolist()) if not master_years.empty else []
    else:
        avail_years = get_available_years(boards[board_map[selected_board_name]])

    year_options = (["All Years"] + avail_years) if len(avail_years) > 1 else (avail_years or [2024])

    if "year_filter" in st.session_state and st.session_state["year_filter"] not in year_options:
        st.session_state["year_filter"] = year_options[0]

    selected_year = st.selectbox("📅 Select Year", options=year_options, index=0, key="year_filter")
    year = None if selected_year == "All Years" else int(selected_year)

    # ── Compare: board multiselect ─────────────────────────────────────────────
    compare_boards_list = []
    if is_compare:
        st.markdown('<div class="sidebar-section">Boards to Compare</div>', unsafe_allow_html=True)
        compare_boards_list = st.multiselect(
            "Select boards", options=ALL_BOARD_NAMES,
            default=ALL_BOARD_NAMES[:2], key="compare_boards",
            help="Pick 2 or more boards to compare side by side.",
        )

    # ── Data filters (board page only) ─────────────────────────────────────────
    # Defaults (pass-through = no filtering)
    filter_gender_list = ["Male", "Female"]
    filter_type_list   = ["Regular", "Private"]
    min_pass_pct       = 0
    top_n_subjects     = 15
    top_n_districts    = 12
    trend_boards       = []
    _subj_trend_raw    = pd.DataFrame(columns=["Year", "Subject", "Pass %", "Appeared", "Board"])
    trend_yr_range     = None
    trend_pct_range    = (0, 100)

    if is_board_page:
        st.markdown("---")
        st.markdown('<div class="sidebar-section">Data Filters</div>', unsafe_allow_html=True)

        gender_sel = st.multiselect(
            "👥 Gender", options=["Boys", "Girls"], default=["Boys", "Girls"],
            key="filter_gender",
            help="Show only the selected gender(s) in all gender charts.",
        )
        filter_gender_list = [("Male" if g == "Boys" else "Female") for g in gender_sel] or ["Male", "Female"]

        filter_type_list = st.multiselect(
            "🏫 Student Type", options=["Regular", "Private"], default=["Regular", "Private"],
            key="filter_type",
            help="Show only Regular, only Private, or both.",
        ) or ["Regular", "Private"]

        min_pass_pct = st.slider(
            "🎯 Min Pass % — Subjects & Districts",
            min_value=0, max_value=100, value=0, step=5,
            key="min_pass_pct",
            help="Hides any subject or district whose pass rate is below this value.",
        )

        st.markdown("---")
        st.markdown('<div class="sidebar-section">Chart Settings</div>', unsafe_allow_html=True)

        top_n_subjects = st.slider("📚 Top N Subjects (chart)", 5, 30, 15, key="top_n_subjects")
        top_n_districts = st.slider("🏙️ Top N Districts (chart)", 5, 20, 12, key="top_n_districts")

        # ── Subject trend filters ──────────────────────────────────────────────
        st.markdown("---")
        st.markdown('<div class="sidebar-section">Subject Trend</div>', unsafe_allow_html=True)

        _default_trend_bds = [selected_board_name] if selected_board_name in ALL_BOARD_NAMES else ALL_BOARD_NAMES[:1]
        trend_boards = st.multiselect(
            "🏫 Board(s) in trend", options=ALL_BOARD_NAMES,
            default=_default_trend_bds,
            key=f"trend_boards_{selected_board_name}",   # resets when board changes
            help="Add other boards to overlay their subject trends on the same chart.",
        ) or _default_trend_bds

        # Build raw trend data so we know what years are available
        _frames = []
        for _b in trend_boards:
            _bdf = build_subject_year_trend(boards[board_map[_b]])
            if not _bdf.empty:
                _bdf = _bdf.copy()
                _bdf["Board"] = _b
                _frames.append(_bdf)
        _subj_trend_raw = pd.concat(_frames, ignore_index=True) if _frames else pd.DataFrame(
            columns=["Year", "Subject", "Pass %", "Appeared", "Board"]
        )

        if not _subj_trend_raw.empty:
            _avail_yrs = sorted(_subj_trend_raw["Year"].unique())

            if len(_avail_yrs) > 1:
                trend_yr_range = st.select_slider(
                    "📅 Year range",
                    options=_avail_yrs,
                    value=(_avail_yrs[0], _avail_yrs[-1]),
                    key=f"trend_yr_{selected_board_name}",
                    help="Restrict the trend chart to this year window.",
                )
            else:
                # Only one year available — set a valid tuple, no slider needed
                trend_yr_range = (_avail_yrs[0], _avail_yrs[0])
                st.caption(f"📅 Only one year of data: {_avail_yrs[0]}")

            trend_pct_range = st.slider(
                "🎯 Subject avg Pass % range",
                min_value=0, max_value=100, value=(0, 100),
                key=f"trend_pct_{selected_board_name}",
                help="Only plot subjects whose average pass % falls in this range.",
            )
        else:
            st.caption("ℹ️ No multi-year subject data found for selected board(s).")
            trend_yr_range  = None
            trend_pct_range = (0, 100)

    # ── Currently viewing ──────────────────────────────────────────────────────
    _yl = selected_year if selected_year == "All Years" else str(selected_year)
    st.markdown(
        f"""<div class="sidebar-active">
        <div class="sidebar-active-label">Currently viewing</div>
        <div class="sidebar-active-value">{selected_board_name}<br>{_yl}</div>
        </div>""",
        unsafe_allow_html=True,
    )
    debug_log("app.py:sidebar", "Sidebar rendered", {"board": selected_board_name, "year": _yl}, "S")

# ══════════════════════════════════════════════════════════════════════════════
# APPLY SUBJECT TREND FILTERS (outside sidebar block — result is passed to page)
# ══════════════════════════════════════════════════════════════════════════════
if is_board_page and not _subj_trend_raw.empty and trend_yr_range is not None:
    subj_trend_df = _subj_trend_raw[
        (_subj_trend_raw["Year"] >= trend_yr_range[0]) &
        (_subj_trend_raw["Year"] <= trend_yr_range[1])
    ].copy()

    _avg_pct = subj_trend_df.groupby("Subject")["Pass %"].mean()
    _keep = _avg_pct[
        (_avg_pct >= trend_pct_range[0]) & (_avg_pct <= trend_pct_range[1])
    ].index.tolist()
    subj_trend_df = subj_trend_df[subj_trend_df["Subject"].isin(_keep)]
else:
    subj_trend_df = pd.DataFrame(columns=["Year", "Subject", "Pass %", "Appeared", "Board"])

# ══════════════════════════════════════════════════════════════════════════════
# HERO BANNER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(render_hero_banner(len(board_prefixes)), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE ROUTING
# ══════════════════════════════════════════════════════════════════════════════
if is_overview:
    render_overview(boards, year)

elif is_compare:
    render_compare_page(boards, board_map, compare_boards_list, year)

else:
    prefix = board_map[selected_board_name]
    board_sheets = boards[prefix]

    demo_df = extract_gender_type_rows(board_sheets, year)
    if year is None and not demo_df.empty:
        demo_df = aggregate_demo_rows(demo_df)

    totals   = extract_board_totals(board_sheets, year, board_prefix=prefix)
    gender_df = summarize_gender(demo_df)
    type_df   = summarize_type(demo_df)

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

    debug_log("app.py:board_totals", "Board totals",
              {"board": selected_board_name, "year": year,
               "appeared": totals["appeared"], "passed": totals["passed"],
               "pass_pct": totals["pass_pct"]}, "B", run_id="post-fix")

    render_board_page(
        selected_board_name, board_sheets, year, selected_year,
        demo_df, gender_df, type_df, totals,
        extract_subject_group_data(board_sheets, year),
        extract_subject_data(board_sheets, year),
        extract_district_data(board_sheets, year),
        extract_yearly_trend(board_sheets, board_prefix=prefix),
        extract_grade_distribution(board_sheets, year),
        extract_stream_summary(demo_df),
        boards=boards,
        board_map=board_map,
        # ── All sidebar filter values ──────────────────────────────────────────
        filter_gender_list=filter_gender_list,
        filter_type_list=filter_type_list,
        min_pass_pct=min_pass_pct,
        top_n_subjects=top_n_subjects,
        top_n_districts=top_n_districts,
        subj_trend_df=subj_trend_df,
        trend_boards=trend_boards,
    )

st.markdown("---")
st.caption("Data source: BISE SSC master workbooks only · no estimated values")
