"""
common.py
Shared design tokens, CSS, chart factories, and analytics helpers used by
every page of the BISE 10th Grade Results Dashboard.
"""

import re
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

# Province each BISE board sits in (static — BISE boards are organized by
# province/territory, not by year, so this doesn't need to come from the workbook).
BOARD_PROVINCE = {
    "BISE Peshawar": "KPK", "BISE Swat": "KPK", "BISE Bannu": "KPK",
    "BISE Abbottabad": "KPK", "BISE Mardan": "KPK", "BISE Kohat": "KPK",
    "BISE Sargodha": "Punjab", "BISE Dera Ghazi Khan": "Punjab", "BISE Rawalpindi": "Punjab",
    "BISE Faisalabad": "Punjab", "BISE Lahore": "Punjab", "BISE Bahawalpur": "Punjab",
    "BISE Gujranwala": "Punjab", "BISE Sahiwal": "Punjab",
    "FBISE": "Federal (Islamabad)",
}
PROVINCE_COLORS = {"KPK": "#2E7D32", "Punjab": "#1565C0", "Federal (Islamabad)": "#8B5CF6", "Other": "#94A3B8"}


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


def _tnode(label, value, sub="", color=NAVY, leaf=False):
    pad = "8px 12px" if leaf else "10px 16px"
    minw = "72px" if leaf else "94px"
    subhtml = f'<div style="font-size:11px;opacity:.85;margin-top:1px;">{sub}</div>' if sub else ""
    return (f'<div style="display:inline-block;background:{color};color:#FFFFFF;border-radius:12px;'
            f'padding:{pad};min-width:{minw};box-shadow:0 3px 10px rgba(16,24,40,0.18);text-align:center;white-space:nowrap;">'
            f'<div style="font-size:10.5px;font-weight:600;opacity:.92;letter-spacing:.02em;">{label}</div>'
            f'<div style="font-size:17px;font-weight:700;line-height:1.25;margin-top:1px;">{value}</div>{subhtml}</div>')


TREE_LINE = "#334155"  # dark slate — connector lines


def _stem(h=16):
    return f'<div style="width:2px;height:{h}px;background:{TREE_LINE};margin:0 auto;"></div>'


def _connector_row(children_html):
    """Precise per-child half-border connectors so the horizontal line only
    spans between actual siblings — it never overspreads past the outermost
    child or bleeds into unrelated gaps."""
    n = len(children_html)
    cells = []
    for i, c in enumerate(children_html):
        lb = f'2px solid {TREE_LINE}' if i > 0 else '2px solid transparent'
        rb = f'2px solid {TREE_LINE}' if i < n - 1 else '2px solid transparent'
        connector = (
            f'<div style="display:flex;width:100%;height:0;">'
            f'<div style="flex:1;border-top:{lb};"></div>'
            f'<div style="flex:1;border-top:{rb};"></div></div>'
        )
        cells.append(
            f'<div style="display:flex;flex-direction:column;align-items:center;padding:0 8px;">'
            f'{connector}{_stem()}{c}</div>'
        )
    return f'<div style="display:flex;align-items:flex-start;">{"".join(cells)}</div>'


def _subtree(node_html, children_html=None):
    """Recursively wraps a node + its children into an inline-styled flex tree.
    children_html: list of already-built subtree HTML strings (siblings)."""
    if not children_html:
        return f'<div style="display:inline-flex;flex-direction:column;align-items:center;">{node_html}</div>'
    if len(children_html) == 1:
        row = f'<div style="display:flex;flex-direction:column;align-items:center;">{_stem()}{children_html[0]}</div>'
    else:
        row = f'{_stem()}{_connector_row(children_html)}'
    return f'<div style="display:inline-flex;flex-direction:column;align-items:center;">{node_html}{row}</div>'


def _leaf_pair(appeared, passed, failed, pass_pct, fail_pct):
    return [
        _subtree(_tnode("Pass", fmt_k(passed), f"{pass_pct:.0f}%", PASS_COLOR, leaf=True)),
        _subtree(_tnode("Fail", fmt_k(failed), f"{fail_pct:.0f}%", FAIL_COLOR, leaf=True)),
    ]


def render_gender_type_flow(board_name, year_label, totals, gender_df, type_df):
    """Horizontal org-chart flow: Total Appeared -> Gender / Type -> Boys,Girls / Regular,Private -> Pass/Fail.
    Built with inline-styled flexbox (no external CSS dependency), styled with our own navy/teal palette."""
    total_appeared = totals.get("appeared", 0) or 0
    branches = []

    # ── Gender branch ───────────────────────────────────────────────────────
    if not gender_df.empty and "Gender" in gender_df.columns:
        g = gender_df.copy()
        g_total = int(g["Appeared"].sum())
        gender_kids = []
        for _, row in g.iterrows():
            lbl = gender_label(row["Gender"])
            appeared = int(row["Appeared"]) if pd.notna(row["Appeared"]) else 0
            passed = int(row["Passed"]) if pd.notna(row.get("Passed", np.nan)) else 0
            failed = max(appeared - passed, 0)
            pct = round(100 * passed / appeared, 1) if appeared else 0
            color = GENDER_COLORS.get(lbl, NAVY)
            node = _tnode(lbl, fmt_k(appeared), f"{pct:.0f}%", color)
            gender_kids.append(_subtree(node, _leaf_pair(appeared, passed, failed, pct, round(100 - pct, 1))))
        branches.append(_subtree(_tnode("Total by Gender", fmt_k(g_total), "", NAVY_LIGHT), gender_kids))

    # ── Type branch ──────────────────────────────────────────────────────────
    if not type_df.empty and "Candidate Type" in type_df.columns:
        t = type_df.copy()
        t_total = int(t["Appeared"].sum())
        type_kids = []
        for _, row in t.iterrows():
            lbl = row["Candidate Type"]
            appeared = int(row["Appeared"]) if pd.notna(row["Appeared"]) else 0
            passed = int(row["Passed"]) if pd.notna(row.get("Passed", np.nan)) else 0
            failed = max(appeared - passed, 0)
            pct = round(100 * passed / appeared, 1) if appeared else 0
            color = ACCENT if "regular" in str(lbl).lower() else "#8B5CF6"
            node = _tnode(lbl, fmt_k(appeared), f"{pct:.0f}%", color)
            type_kids.append(_subtree(node, _leaf_pair(appeared, passed, failed, pct, round(100 - pct, 1))))
        branches.append(_subtree(_tnode("Total by Type", fmt_k(t_total), "", "#0B2763"), type_kids))

    if not branches:
        return  # nothing to draw

    tree_html = _subtree(_tnode("Total Appeared", fmt_k(total_appeared), year_label, NAVY), branches)
    scroll_id = "flow-scroll-" + re.sub(r"[^a-z0-9]+", "-", board_name.lower())
    html = (f'<div id="{scroll_id}" style="overflow-x:auto;padding:10px 8px 16px 8px;">'
            f'<div style="display:flex;justify-content:center;min-width:680px;padding:0 20px 4px 20px;">{tree_html}</div></div>'
            f'<script>const el=document.getElementById("{scroll_id}");'
            f'if(el){{el.scrollLeft=(el.scrollWidth-el.clientWidth)/2;}}</script>')
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader(f"🌳 Result Flow — {board_name}")
    st.markdown(html, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)




def inject_css():
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
    
        /* ── Multipage nav ("app" / "Browse" links) — styled to match the sidebar ── */
        [data-testid="stSidebarNav"] {{
            background: rgba(255,255,255,0.06) !important;
            border: 1px solid rgba(255,255,255,0.14) !important;
            border-radius: 12px !important;
            padding: 8px 6px !important;
            margin: 6px 0 18px 0 !important;
        }}
        [data-testid="stSidebarNav"] ul {{ padding: 0 !important; }}
        [data-testid="stSidebarNav"] li {{ list-style: none !important; margin: 2px 0 !important; }}
        [data-testid="stSidebarNav"] a {{
            border-radius: 8px !important; padding: 9px 12px !important;
            color: rgba(255,255,255,0.88) !important; font-weight: 600 !important;
            font-size: 13.5px !important; letter-spacing: 0.01em;
            transition: background 0.15s ease, color 0.15s ease;
        }}
        [data-testid="stSidebarNav"] a:hover {{
            background: rgba(255,255,255,0.14) !important; color: #FFFFFF !important;
        }}
        [data-testid="stSidebarNav"] a[aria-current="page"] {{
            background: rgba(255,255,255,0.22) !important; color: #FFFFFF !important;
            box-shadow: inset 3px 0 0 {ACCENT};
        }}
        [data-testid="stSidebarNav"] span {{ font-weight: inherit !important; text-transform: capitalize; }}
        [data-testid="stSidebarNav"] li:first-child a span::before {{ content: "🏠  "; }}
    
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
            box-sizing: border-box; overflow-wrap: break-word; word-break: normal;
        }}
        .kpi-label {{
            font-size: 13px; color: {MUTED}; font-weight: 500;
            overflow-wrap: break-word; word-break: normal; white-space: normal; line-height: 1.3;
        }}
        .kpi-value {{ font-size: 26px; font-weight: 700; margin-top: 4px; color: {NAVY}; white-space: nowrap; }}
        .kpi-sub {{ font-size: 12px; color: {MUTED}; margin-top: 2px; white-space: nowrap; }}
        /* Responsive card grid — used instead of st.columns() when the number of
           cards is dynamic (e.g. Compare Boards with 2–15+ boards selected).
           Cards keep a sane minimum width and wrap onto new rows instead of
           being squeezed into unreadable slivers. */
        .kpi-grid {{
            display: flex; flex-wrap: wrap; gap: 14px; margin-bottom: 6px;
        }}
        .kpi-grid .kpi-box {{
            flex: 1 1 168px; min-width: 168px; max-width: 240px;
        }}
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
    
        /* ── Nav cards (Browse by Board / Browse by Year) ─────────────────────── */
        [data-testid="stVerticalBlockBorderWrapper"]:has(button[kind]) {{
            transition: box-shadow 0.15s ease, transform 0.15s ease;
        }}
        .navcard-title {{ font-size: 14px; font-weight: 700; color: {TEXT}; margin-bottom: 2px; }}
        .navcard-sub {{ font-size: 11.5px; color: {MUTED}; margin-bottom: 8px; }}
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
        plot_df["Pass %"] = (100 * plot_df["Passed"] / plot_df["Appeared"].replace(0, float("nan"))).round(1)
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
    layout_kwargs = dict(barmode="stack",
                      xaxis=dict(range=[0, 100], title="Percentage"),
                      yaxis=dict(automargin=True), height=chart_h, showlegend=False,
                      margin=chart_margins(title=title))
    ct = chart_title(title)
    if ct is not None:
        layout_kwargs["title"] = ct
    fig.update_layout(**layout_kwargs)
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


def grouped_bar_chart(x, series, title="", y_title="Students", height=400, colors=None,
                      show_values=False, value_suffix=""):
    if x is None or len(x) == 0:
        return None
    fig = go.Figure()
    palette = colors or [PASS_COLOR, FAIL_COLOR, NAVY, ACCENT]
    for i, (name, values) in enumerate(series.items()):
        bar_kwargs = dict(x=x, y=values, name=name, marker_color=palette[i % len(palette)])
        if show_values:
            bar_kwargs["text"] = [f"{v:.1f}{value_suffix}" for v in values]
            bar_kwargs["textposition"] = "outside"
        fig.add_trace(go.Bar(**bar_kwargs))
    fig.update_layout(title=chart_title(title), barmode="group",
                      xaxis=dict(automargin=True), yaxis=dict(title=y_title),
                      height=height, legend=legend_top_right(),
                      margin=chart_margins(title=title, legend_pos="top"))
    return style_fig(fig)


def radar_chart(labels, values, title="", height=420):
    if not labels or not values:
        return None
    labels_c = list(labels) + [labels[0]]
    values_c = list(values) + [values[0]]
    fig = go.Figure(go.Scatterpolar(
        r=values_c, theta=labels_c, fill="toself",
        line=dict(color=NAVY, width=2), fillcolor="rgba(15,58,90,0.25)",
    ))
    fig.update_layout(title=chart_title(title), height=height,
                      polar=dict(radialaxis=dict(visible=True, showgrid=True)),
                      showlegend=False, margin=chart_margins(title=title))
    return style_fig(fig)


def board_rank_hbar(labels, values, title="", x_title="Pass %", height=None):
    if not labels or not values:
        return None
    order = sorted(range(len(values)), key=lambda i: values[i])
    labels_s = [labels[i] for i in order]
    values_s = [values[i] for i in order]
    chart_h = height or max(280, 42 * len(labels_s))
    fig = go.Figure(go.Bar(
        x=values_s, y=labels_s, orientation="h",
        marker=dict(color=values_s, colorscale=[[0, FAIL_COLOR], [0.5, NAVY_LIGHT], [1, PASS_COLOR]]),
        text=[f"{v:.1f}%" for v in values_s], textposition="outside",
    ))
    fig.update_layout(title=chart_title(title), xaxis=dict(range=[0, 105], title=x_title),
                      yaxis=dict(automargin=True), height=chart_h, showlegend=False,
                      margin=chart_margins(title=title, extra_right=40))
    return style_fig(fig)


def cumulative_grade_line_chart(grade_order, series, title="", height=440):
    if not grade_order or not series:
        return None
    fig = go.Figure()
    for i, (name, values) in enumerate(series.items()):
        fig.add_trace(go.Scatter(
            x=grade_order, y=values, mode="lines+markers", name=str(name),
            line=dict(width=2, color=PALETTE[i % len(PALETTE)]),
        ))
    fig.update_layout(title=chart_title(title), xaxis=dict(title="Grade (best → worst)"),
                      yaxis=dict(title="Cumulative % of students", range=[0, 105]),
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




# ── Shared data loading ─────────────────────────────────────────────────────
def load_boards():
    """Load workbook + group by board. Raises FileNotFoundError if missing
    (callers should catch and st.stop())."""
    sheets = load_workbook()
    boards = group_by_board(sheets)
    board_prefixes = list_board_prefixes(boards)
    board_map = {board_display_name(p): p for p in board_prefixes}
    all_board_names = sorted(board_map.keys())
    return boards, board_prefixes, board_map, all_board_names


def show_missing_workbook_error():
    st.error(
        "Place **BISE_All_Boards_SSC_Master_2024-2026.xlsx** and "
        "**Punjab_Federal_SSC_2024-2026_MASTER.xlsx** in this folder, then run "
        "`python build_pro_master.py` to rebuild the merged master."
    )
    st.stop()


def render_sidebar_brand():
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
    if st.button("🔄 Refresh Data", help="Reload workbook from disk", key="refresh_data_btn"):
        data_loader.load_workbook.clear()
        st.rerun()


def render_currently_viewing(label_value: str):
    st.markdown(
        f"""<div class="sidebar-active">
        <div class="sidebar-active-label">Currently viewing</div>
        <div class="sidebar-active-value">{label_value}</div>
        </div>""",
        unsafe_allow_html=True,
    )


# ── Global Year + Boards filter — shared across every page ──────────────────
# Renders once per page (inside `with st.sidebar:`), but reads/writes the same
# st.session_state keys everywhere, so a choice made on one page is still in
# effect when the user navigates to another page. Defaults to the latest year
# in the workbook (2026) until the user changes it.
GLOBAL_YEAR_KEY = "global_year_filter"
GLOBAL_BOARDS_KEY = "global_boards_filter"

# Streamlit forbids writing to st.session_state[key] once a widget with that
# key has already been instantiated in the current script run. Quick-Jump /
# navcard buttons elsewhere on a page can't set GLOBAL_YEAR_KEY /
# GLOBAL_BOARDS_KEY directly for that reason (they run *after*
# render_global_filters() has already created the sidebar widgets). Instead
# they stash the desired value under these "pending" keys and call
# st.rerun(); on the next run we apply the pending value here, BEFORE the
# widgets are created, then clear it.
PENDING_YEAR_KEY = "_pending_global_year_filter"
PENDING_BOARDS_KEY = "_pending_global_boards_filter"


def render_global_filters(boards, all_board_names):
    master = get_master_summary(boards)
    available_years = sorted({int(y) for y in master["Year"].dropna().unique()}, reverse=True)
    latest_year = available_years[0] if available_years else None
    year_options = [str(y) for y in available_years] + ["All Years"]

    # Apply any pending override requested by a button on a previous run,
    # before the widgets below get instantiated.
    if PENDING_YEAR_KEY in st.session_state:
        st.session_state[GLOBAL_YEAR_KEY] = st.session_state.pop(PENDING_YEAR_KEY)
    if PENDING_BOARDS_KEY in st.session_state:
        st.session_state[GLOBAL_BOARDS_KEY] = st.session_state.pop(PENDING_BOARDS_KEY)

    # Seed session_state only the first time — after that, the widgets below
    # read/write it directly, which is what makes the choice persist as the
    # user moves between pages.
    if GLOBAL_YEAR_KEY not in st.session_state:
        st.session_state[GLOBAL_YEAR_KEY] = str(latest_year) if latest_year is not None else "All Years"
    elif st.session_state[GLOBAL_YEAR_KEY] not in year_options:
        st.session_state[GLOBAL_YEAR_KEY] = str(latest_year) if latest_year is not None else "All Years"

    # Boards default to an EMPTY selection, which we treat as "All boards".
    # Pre-selecting all 15 boards as tags made the multiselect render as a
    # tall stacked list in the sidebar — an empty box with an "All boards"
    # placeholder stays compact until the user actually narrows it down.
    if GLOBAL_BOARDS_KEY not in st.session_state:
        st.session_state[GLOBAL_BOARDS_KEY] = []
    else:
        kept = [b for b in st.session_state[GLOBAL_BOARDS_KEY] if b in all_board_names]
        st.session_state[GLOBAL_BOARDS_KEY] = kept

    st.markdown("**Filters**")
    year_choice = st.selectbox("Year", year_options, key=GLOBAL_YEAR_KEY)
    raw_selected = st.multiselect(
        "Boards", all_board_names, key=GLOBAL_BOARDS_KEY, placeholder="All boards",
    )
    selected_boards = raw_selected if raw_selected else list(all_board_names)

    year = None if year_choice == "All Years" else int(year_choice)
    return year, selected_boards, year_choice
