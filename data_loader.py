"""
data_loader.py
Generic loader for the BISE SSC (10th Class) master workbook.
"""

import re
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
KPK_CANDIDATE = BASE_DIR / "BISE_All_Boards_SSC_Master_2024-2026.xlsx"
FINAL_CANDIDATE = BASE_DIR / "BISE_SSC_MASTER_FINAL_2024-2026.xlsx"


def _punjab_path() -> Path | None:
    candidates = [
        BASE_DIR / "Punjab_Federal_SSC_2024-2026_MASTER.xlsx",
        BASE_DIR / "Punjab_Federal_SSC_2024-2026_MASTER (1).xlsx",
        BASE_DIR.parent / "Punjab_Federal_SSC_2024-2026_MASTER.xlsx",
    ]
    candidates.extend(sorted(BASE_DIR.glob("Punjab_Federal*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True))
    seen = set()
    for p in candidates:
        if p.exists() and p not in seen:
            return p
        seen.add(p)
    return None


def _workbook_paths() -> list[Path]:
    paths = []
    if KPK_CANDIDATE.exists():
        paths.append(KPK_CANDIDATE)
    punjab = _punjab_path()
    if punjab and punjab not in paths:
        paths.append(punjab)
    if not paths and FINAL_CANDIDATE.exists():
        paths.append(FINAL_CANDIDATE)
    return paths

BOARD_NAMES = {
    "Master": "All Boards (Overview)",
    "Pes": "BISE Peshawar",
    "Swat": "BISE Swat",
    "Ban": "BISE Bannu",
    "Abb": "BISE Abbottabad",
    "Sar": "BISE Sargodha",
    "Mar": "BISE Mardan",
    "Koh": "BISE Kohat",
    "DGK": "BISE Dera Ghazi Khan",
    "FBISE": "FBISE",
    "SWL": "BISE Sahiwal",
    "RWP": "BISE Rawalpindi",
    "FSD": "BISE Faisalabad",
    "LHR": "BISE Lahore",
    "BWP": "BISE Bahawalpur",
    "GRW": "BISE Gujranwala",
}

# Some boards publish official 10th-class headline stats on a row other than "Overall".
# FSD's "Overall" row (Regular + Private combined) is the board's official published
# total (verified against BISE Faisalabad gazette figures) — do not override it here.
BOARD_TOTAL_MODE = {}

PUNJAB_PREFIXES = ("FBISE", "SWL", "RWP", "FSD", "LHR", "BWP", "GRW")

SHEET_LABELS = {
    "Summary": "Summary",
    "Overview": "Overview",
    "Overall Summary": "Overall Summary",
    "Group-wise Distribution": "Group-wise Distribution",
    "Group-wise": "Group-wise",
    "Gender-wise Result": "Gender-wise Result",
    "Gender-wise": "Gender-wise",
    "Subject-wise Pass %": "Subject-wise Pass %",
    "Subject-wise": "Subject-wise",
    "Subject Counts": "Subject Counts",
    "Category-wise": "Category-wise",
    "Grades": "Grade Distribution",
    "Grades Summary": "Grade Distribution",
    "District-wise": "District-wise",
    "Grade Dist. by District": "Grade Distribution by District",
    "Trend Summary": "3-Year Trend",
    "Historical Trend": "Historical Trend",
    "Science Group": "Science Group",
    "Humanities Group": "Humanities Group",
    "General Group": "General Group",
    "Overall by Type-Gender": "By Candidate Type & Gender",
    "Additional-Qualifying": "Additional / Qualifying Subjects",
    "9th 2025": "SSC 9th (2025 only)",
    "SSC-10th Summary": "SSC-10th Summary",
    "SSC-10th Category-wise": "SSC-10th Category-wise",
    "SSC-10th Grades": "SSC-10th Grades",
    "SSC-9th 2025": "SSC-9th 2025",
    "Result At a Glance": "Summary",
    "Overview Summary": "Overall Summary",
    "Overall Summary": "Overall Summary",
    "Year-over-Year Summary": "Summary (2024-2026)",
    "Groupwise Pass %": "Group-wise Distribution",
    "Subjectwise Pass %": "Subject-wise Pass %",
    "Statistical Grading": "Grade Distribution",
    "District Pass %": "District-wise",
    "Board Comparison": "Board Comparison",
    "Grades by Gender": "Gender-wise Result",
    "Regular Gender-School": "Gender-wise Result",
    "Private Gender": "Gender-wise",
    "Pass % by Category": "Group-wise Distribution",
    "Group Wise Pass %": "Group-wise Distribution",
    "Subject Wise Pass %": "Subject-wise Pass %",
    "District Wise Performance": "District-wise",
    "Regional Details": "District-wise",
}


def _split_sheet_name(sheet_name: str):
    if sheet_name in ("Master Summary", "Board Comparison Summary"):
        return "Master", "Board Comparison" if "Comparison" in sheet_name else "Summary"
    for prefix in sorted(PUNJAB_PREFIXES + tuple(BOARD_NAMES.keys()), key=len, reverse=True):
        if prefix == "Master":
            continue
        if sheet_name.startswith(prefix + " "):
            return prefix, sheet_name[len(prefix) + 1 :].strip()
        if sheet_name.startswith(prefix + "-"):
            return prefix, sheet_name[len(prefix) + 1 :].strip()
    if "-" in sheet_name:
        prefix, rest = sheet_name.split("-", 1)
        return prefix, rest
    return sheet_name, sheet_name


def filter_df_year(df: pd.DataFrame, year):
    class_col = find_col(df, "Exam Class", "Class")
    if class_col is not None:
        df = df[~df[class_col].astype(str).str.contains("9th", case=False, na=False)]
    ycol = find_col(df, "Year")
    if year is None:
        # "All Years": still drop rows whose Year cell isn't an actual year — some
        # boards (e.g. DG Khan) add "Change 2025 vs 2024" delta rows to their
        # Overall Summary sheet, which would otherwise get summed/averaged in
        # alongside real yearly rows and badly corrupt the combined totals.
        if ycol is not None:
            yr_all = pd.to_numeric(df[ycol], errors="coerce")
            df = df[yr_all.notna()]
        return df.copy()
    if ycol is None:
        return pd.DataFrame(columns=df.columns)
    yr = pd.to_numeric(df[ycol], errors="coerce")
    out = df[yr == year]
    return out.copy()


BOARD_DISPLAY_NAMES = {
    "Abbottabad": "BISE Abbottabad",
    "Bannu": "BISE Bannu",
    "D.G. Khan": "BISE Dera Ghazi Khan",
    "Kohat": "BISE Kohat",
    "Mardan": "BISE Mardan",
    "Peshawar": "BISE Peshawar",
    "Sargodha": "BISE Sargodha",
    "Swat": "BISE Swat",
    "Sahiwal": "BISE Sahiwal",
    "FBISE": "FBISE",
    "Rawalpindi": "BISE Rawalpindi",
    "Faisalabad": "BISE Faisalabad",
    "Lahore": "BISE Lahore",
    "Bahawalpur": "BISE Bahawalpur",
    "Gujranwala": "BISE Gujranwala",
}


def _years_from_sheet_names(board_sheets: dict) -> list[int]:
    years = set()
    for label in board_sheets:
        for m in re.finditer(r"\b(202[4-6])\b", str(label)):
            years.add(int(m.group(1)))
    return sorted(years)


def get_available_years(board_sheets: dict) -> list[int]:
    years = set()
    for name in [
        "Overall Summary",
        "Summary",
        "Summary (2024-2026)",
        "Overview",
        "SSC-10th Summary",
        "Year-over-Year Summary",
    ]:
        df = _pick_sheet(board_sheets, [name])
        if df is None or df.empty:
            continue
        ycol = find_col(_coerce_numeric(df), "Year")
        if ycol:
            vals = pd.to_numeric(df[ycol], errors="coerce").dropna().astype(int).tolist()
            years.update(vals)
    if not years:
        years.update(_years_from_sheet_names(board_sheets))
    return sorted(years)


def _extract_punjab_glance_totals(df: pd.DataFrame) -> dict:
    """Parse Punjab 'Result at a Glance' key-value layout for one exam year."""
    if df is None or df.empty:
        return {"appeared": 0, "passed": 0, "failed": 0, "pass_pct": 0}
    appeared_total = passed_total = None
    for _, row in df.iterrows():
        cells = [str(c).strip() if pd.notna(c) else "" for c in row.tolist()]
        cells_lower = [c.lower() for c in cells]
        row_text = " ".join(cells_lower)
        nums = [pd.to_numeric(c, errors="coerce") for c in row.tolist()]
        nums = [int(n) for n in nums if pd.notna(n) and n > 0]
        if not nums:
            continue
        val = nums[-1]
        if "appeared" in row_text and "total" in row_text:
            appeared_total = val
        elif "successful" in row_text and "total" in row_text:
            passed_total = val
        elif "successful" in row_text and passed_total is None:
            passed_total = val
    if appeared_total and passed_total:
        failed = max(appeared_total - passed_total, 0)
        pass_pct = round(100 * passed_total / appeared_total, 2) if appeared_total else 0
        return {
            "appeared": appeared_total,
            "passed": passed_total,
            "failed": failed,
            "pass_pct": pass_pct,
        }
    return {"appeared": 0, "passed": 0, "failed": 0, "pass_pct": 0}


def board_display_name(prefix: str) -> str:
    if prefix in BOARD_NAMES:
        return BOARD_NAMES[prefix]
    return prefix


def list_board_prefixes(boards: dict) -> list[str]:
    skip_fragments = ("Punjab_F", "README", "Comparison Summary", "Institute", "Notes")
    out = []
    for prefix in boards:
        if prefix == "Master":
            continue
        if any(frag in prefix for frag in skip_fragments):
            continue
        if prefix.endswith(" Year") or prefix.endswith(" Year-over-Year Summary"):
            continue
        if prefix in BOARD_NAMES or prefix in PUNJAB_PREFIXES:
            out.append(prefix)
            continue
        if len(prefix) <= 4 and prefix.isalpha():
            out.append(prefix)
    return sorted(set(out), key=lambda p: board_display_name(p))


def _parse_board_comparison(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Board", "Year", "Appeared", "Passed", "Pass %"])
    header_idx = None
    for i, row in df.iterrows():
        cells = [str(c).strip().lower() for c in row.tolist() if pd.notna(c)]
        if "year" in cells and "board" in cells:
            header_idx = i
            break
    if header_idx is None:
        return pd.DataFrame(columns=["Board", "Year", "Appeared", "Passed", "Pass %"])
    headers = [str(c).strip() if pd.notna(c) else "" for c in df.iloc[header_idx].tolist()]
    body = df.iloc[header_idx + 1 :].copy()
    body.columns = headers + [f"x{j}" for j in range(max(0, len(body.columns) - len(headers)))]
    body = body[[c for c in body.columns if not str(c).startswith("x")]]
    ycol = find_col(body, "Year")
    bcol = find_col(body, "Board")
    acol = find_col(body, "Appeared")
    pcol = find_col(body, "Passed", "Pass")
    pp = find_col(body, "Pass %", "Pass%")
    if not all([ycol, bcol, acol]):
        return pd.DataFrame(columns=["Board", "Year", "Appeared", "Passed", "Pass %"])
    out = body[[ycol, bcol, acol] + ([pcol] if pcol else []) + ([pp] if pp else [])].copy()
    out.columns = ["Year", "Board", "Appeared"] + (["Passed"] if pcol else []) + (["Pass %"] if pp else [])
    out["Year"] = pd.to_numeric(out["Year"], errors="coerce")
    out["Appeared"] = pd.to_numeric(out["Appeared"], errors="coerce")
    if "Passed" in out.columns:
        out["Passed"] = pd.to_numeric(out["Passed"], errors="coerce")
    if "Pass %" in out.columns:
        out["Pass %"] = normalize_pct(pd.to_numeric(out["Pass %"], errors="coerce"))
    out = out.dropna(subset=["Year", "Board", "Appeared"])
    out = out[out["Appeared"] > 0]
    return out.reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_workbook():
    paths = _workbook_paths()
    if not paths:
        raise FileNotFoundError("No SSC master workbook found.")

    parsed = {}
    for path in paths:
        raw_sheets = pd.read_excel(path, sheet_name=None, header=None)
        for sheet_name, raw in raw_sheets.items():
            if sheet_name.startswith("README") or "Notes & Data" in sheet_name or sheet_name.endswith("README"):
                continue
            if re.search(r"\b9th\b", sheet_name, re.I) or re.search(r"ssc-9", sheet_name, re.I):
                continue
            header_row_idx = None
            for i, row in raw.iterrows():
                if row.notna().sum() >= 3:
                    header_row_idx = i
                    break
            if header_row_idx is None:
                continue
            headers = raw.iloc[header_row_idx].tolist()
            headers_norm = [str(h).strip().lower() if pd.notna(h) else "" for h in headers]
            data_rows = []
            i = header_row_idx + 1
            n = len(raw)
            while i < n:
                row = raw.iloc[i]
                if row.notna().sum() == 0:
                    # Blank row: look ahead past any blank/label rows for a repeated header,
                    # which signals a stacked sub-table (e.g. "Science Group" then "General
                    # Group" in the same sheet) that would otherwise be silently dropped.
                    j = i + 1
                    found_header = False
                    while j < n:
                        nn = raw.iloc[j].notna().sum()
                        if nn == 0:
                            j += 1
                            continue
                        if nn == 1:
                            j += 1  # section-title row, keep looking
                            continue
                        candidate_norm = [str(c).strip().lower() if pd.notna(c) else "" for c in raw.iloc[j].tolist()]
                        if candidate_norm == headers_norm:
                            found_header = True
                            j += 1
                        break
                    if found_header:
                        i = j
                        continue
                    if data_rows:
                        break
                    i += 1
                    continue
                data_rows.append(row)
                i += 1
            if not data_rows:
                continue
            df = pd.DataFrame(data_rows)
            df.columns = [str(h).strip() if pd.notna(h) else f"col_{j}" for j, h in enumerate(headers)]
            df = df.dropna(axis=1, how="all")
            df = df[df.notna().sum(axis=1) >= 2]
            df = df.reset_index(drop=True)
            key = sheet_name if sheet_name not in parsed else f"{path.stem[:8]}_{sheet_name}"[:31]
            parsed[key] = df
    return parsed


def group_by_board(sheets: dict):
    boards = {}
    for sheet_name, df in sheets.items():
        prefix, rest = _split_sheet_name(sheet_name)
        label = SHEET_LABELS.get(rest, rest)
        boards.setdefault(prefix, {})[label] = df
    return boards


def numeric_grade_columns(df: pd.DataFrame):
    known = {"A1", "A", "A-1", "A+", "B", "C", "D", "E", "E/NO GRADE", "F", "FAIL"}
    return [c for c in df.columns if str(c).strip().upper() in known]


def find_col(df: pd.DataFrame, *candidates):
    lower_map = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    return None


def normalize_pct(series: pd.Series) -> pd.Series:
    vals = pd.to_numeric(series, errors="coerce")
    if vals.dropna().empty:
        return vals
    if vals.dropna().max() <= 1.5:
        return vals * 100
    return vals


def parse_category_field(value):
    text = str(value).strip().lower()
    cand_type = "Private" if "private" in text else ("Regular" if "regular" in text else None)
    if any(k in text for k in ("female", "girls", "girl")):
        gender = "Female"
    elif any(k in text for k in ("male", "boys", "boy")):
        gender = "Male"
    else:
        gender = None
    return cand_type, gender


def normalize_gender(value):
    text = str(value).strip().lower()
    if any(k in text for k in ("female", "girls", "girl")):
        return "Female"
    if any(k in text for k in ("male", "boys", "boy")):
        return "Male"
    return str(value).strip()


def normalize_type(value):
    text = str(value).strip().lower()
    if "private" in text:
        return "Private"
    if "regular" in text:
        return "Regular"
    return str(value).strip()


def _coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        converted = pd.to_numeric(out[col], errors="coerce")
        if converted.notna().sum() >= max(1, int(0.4 * len(out))):
            out[col] = converted
    return out


def _pick_sheet(board_sheets: dict, names: list[str]):
    for name in names:
        if name in board_sheets:
            return board_sheets[name]
    return None


def _filter_board_summary_rows(df: pd.DataFrame, board_prefix: str | None = None) -> pd.DataFrame:
    """Keep one official SSC-10th total row per year — never sum regions/sub-categories."""
    if df.empty:
        return df
    out = df.copy()

    group_col = find_col(out, "Group")
    if group_col:
        g = out[group_col].astype(str).str.strip().str.upper()
        grand = out[g.str.contains("GRAND TOTAL", na=False)]
        if not grand.empty:
            return grand

    area_col = find_col(out, "Area")
    if area_col:
        mask = out[area_col].astype(str).str.strip().str.lower() == "all areas"
        filtered = out[mask]
        if not filtered.empty:
            return filtered

    cat_col = find_col(out, "Category")
    if cat_col:
        c = out[cat_col].astype(str).str.strip().str.lower()
        pref = BOARD_TOTAL_MODE.get(board_prefix or "")
        if pref == "regular":
            regular = out[c == "regular"]
            if not regular.empty:
                return regular
        overall = out[c.isin(["overall", "grand total", "all areas", "all"])]
        if not overall.empty:
            return overall

    if group_col:
        g = out[group_col].astype(str).str.strip().str.upper()
        non_sub = out[~g.str.contains("SUB TOTAL", na=False)]
        if len(non_sub) < len(out):
            return non_sub

    return out


def split_matches_total(split_df: pd.DataFrame, total_appeared: int, value_col: str = "Appeared") -> bool:
    """True when a gender/type split sums close enough to the board total.
    A small tolerance (0.5% or 5 students, whichever is larger) absorbs minor
    source-data rounding without masking genuinely incomplete/missing splits."""
    if split_df.empty or total_appeared <= 0 or value_col not in split_df.columns:
        return False
    split_sum = int(pd.to_numeric(split_df[value_col], errors="coerce").fillna(0).sum())
    tolerance = max(5, round(total_appeared * 0.005))
    return abs(split_sum - int(total_appeared)) <= tolerance


def _count_columns(df: pd.DataFrame):
    appeared = find_col(df, "Total Appeared", "Appeared", "Total Students", "Candidates", "Applied", "Enrolled")
    passed = find_col(df, "Total Pass", "Total Passed", "Passed", "Pass")
    failed = find_col(df, "Failed", "Fail", "Fail (approx)")
    pass_pct = find_col(df, "Pass %", "Pass%", "Pass_Pct", "Overall Pass %")
    return appeared, passed, failed, pass_pct


def _row_is_subtotal(text: str) -> bool:
    t = str(text).strip().lower()
    return t in ("total", "overall", "sub-total", "sub total", "grand total") or t.endswith(" total")


def _parse_grw_category_field(value) -> tuple[str | None, str | None]:
    text = str(value).strip().lower()
    if _row_is_subtotal(text):
        return None, None
    cand_type = "Regular" if "regular" in text else ("Private" if "private" in text else None)
    if any(k in text for k in ("female", "girls", "girl")):
        gender = "Female"
    elif any(k in text for k in ("male", "boys", "boy")):
        gender = "Male"
    else:
        gender = None
    return gender, cand_type


def _extract_grw_group_stats_gender(board_sheets: dict, year=None) -> pd.DataFrame:
    """Parse GRW Science/General group stat sheets (Category = Regular Male, etc.)."""
    empty = pd.DataFrame(columns=["Gender", "Candidate Type", "Group", "Appeared", "Passed", "Failed", "Pass %"])
    years = [year] if year else get_available_years(board_sheets) or _years_from_sheet_names(board_sheets)
    rows = []
    stat_markers = (
        "science group stats",
        "science & general grou",
        "general group stats",
        "deaf & dumb stats",
    )
    for y in years:
        ys = str(y)
        for label, df in board_sheets.items():
            ll = label.lower()
            if ys not in ll:
                continue
            if not any(m in ll for m in stat_markers):
                continue
            if "general group" in ll and "stats" not in ll and "science" not in ll:
                continue
            chunk = _coerce_numeric(df)
            cat_col = find_col(chunk, "Category")
            appeared_col = find_col(chunk, "Appeared")
            passed_col = find_col(chunk, "Pass", "Passed")
            if not cat_col or not appeared_col:
                continue
            for _, r in chunk.iterrows():
                gender, cand_type = _parse_grw_category_field(r.get(cat_col))
                if gender is None or cand_type is None:
                    continue
                appeared = pd.to_numeric(r.get(appeared_col), errors="coerce")
                passed = pd.to_numeric(r.get(passed_col), errors="coerce") if passed_col else None
                if pd.isna(appeared) or appeared <= 0:
                    continue
                if pd.isna(passed):
                    passed = 0
                rows.append(
                    {
                        "Gender": gender,
                        "Candidate Type": cand_type,
                        "Group": "All",
                        "Appeared": int(appeared),
                        "Passed": int(passed),
                        "Failed": max(int(appeared - passed), 0),
                        "Pass %": round(100 * passed / appeared, 2) if appeared else None,
                    }
                )
    if not rows:
        return empty
    out = pd.DataFrame(rows)
    out = out.groupby(["Gender", "Candidate Type", "Group"], as_index=False)[["Appeared", "Passed", "Failed"]].sum()
    out["Pass %"] = (100 * out["Passed"] / out["Appeared"].replace(0, pd.NA)).round(2)
    return out


def _gender_rows_for_summary(demo_df: pd.DataFrame) -> pd.DataFrame:
    """Avoid double-counting when demo rows include both All and Regular/Private."""
    if demo_df.empty or "Candidate Type" not in demo_df.columns:
        return demo_df
    all_rows = demo_df[demo_df["Candidate Type"] == "All"]
    typed = demo_df[demo_df["Candidate Type"].isin(["Regular", "Private"])]
    if not typed.empty:
        if all_rows.empty or typed["Appeared"].sum() >= all_rows["Appeared"].sum():
            return typed
    if not all_rows.empty:
        return all_rows
    return demo_df


def _extract_overview_gender_split(board_sheets: dict, year=None) -> pd.DataFrame:
    df = _pick_sheet(board_sheets, ["Overall Summary", "Overview Summary"])
    if df is None or df.empty:
        return pd.DataFrame(columns=["Gender", "Candidate Type", "Group", "Appeared", "Passed", "Failed", "Pass %"])
    df = _coerce_numeric(filter_df_year(df, year))
    specs = [
        ("Male", ("Male_Appeared", "Male Appeared"), ("Male_Passed", "Male Passed"), ("Male_Pass_Pct", "Male Pass Pct")),
        ("Female", ("Female_Appeared", "Female Appeared"), ("Female_Passed", "Female Passed"), ("Female_Pass_Pct", "Female Pass Pct")),
    ]
    rows = []
    for gender, app_keys, pass_keys, pct_keys in specs:
        ac = find_col(df, *app_keys)
        pc = find_col(df, *pass_keys)
        pp = find_col(df, *pct_keys)
        if ac is None:
            continue
        appeared = pd.to_numeric(df[ac], errors="coerce").sum()
        passed = pd.to_numeric(df[pc], errors="coerce").sum() if pc else 0
        if pd.isna(appeared) or appeared <= 0:
            continue
        pct = pd.to_numeric(df[pp], errors="coerce").mean() if pp else None
        if pd.notna(pct):
            pct = normalize_pct(pd.Series([pct])).iloc[0]
        else:
            pct = 100 * passed / appeared if appeared else 0
        rows.append(
            {
                "Gender": gender,
                "Candidate Type": "All",
                "Group": "All",
                "Appeared": int(appeared),
                "Passed": int(passed),
                "Failed": max(int(appeared - passed), 0),
                "Pass %": round(float(pct), 2),
            }
        )
    return pd.DataFrame(rows)


def _extract_pass_percentage_gender(board_sheets: dict, year=None) -> pd.DataFrame:
    df = board_sheets.get("Pass Percentage")
    if df is None or df.empty:
        return pd.DataFrame(columns=["Gender", "Candidate Type", "Group", "Appeared", "Passed", "Failed", "Pass %"])
    df = _coerce_numeric(filter_df_year(df, year))
    cat_col = find_col(df, "Category")
    group_col = find_col(df, "Group")
    gender_col = find_col(df, "Gender")
    appeared_col = find_col(df, "Appeared")
    passed_col = find_col(df, "Pass", "Passed", "Total Pass")
    pass_col = find_col(df, "Pass %", "Pass%")
    if not gender_col or not appeared_col:
        return pd.DataFrame(columns=["Gender", "Candidate Type", "Group", "Appeared", "Passed", "Failed", "Pass %"])
    rows = []
    for _, r in df.iterrows():
        group = str(r.get(group_col, "")).strip().upper() if group_col else "TOTAL"
        if group_col and group != "TOTAL":
            continue
        gender = normalize_gender(r[gender_col])
        if gender not in ("Male", "Female"):
            continue
        cat = str(r.get(cat_col, "")).strip().upper() if cat_col else "ALL"
        if "REGULAR" in cat:
            cand_type = "Regular"
        elif "PRIVATE" in cat:
            cand_type = "Private"
        elif cat in ("OVERALL", "ALL"):
            cand_type = "All"
        else:
            continue
        appeared = pd.to_numeric(r.get(appeared_col), errors="coerce")
        passed = pd.to_numeric(r.get(passed_col), errors="coerce") if passed_col else None
        if pd.isna(appeared) or appeared <= 0:
            continue
        if pd.isna(passed):
            passed = 0
        pct = pd.to_numeric(r.get(pass_col), errors="coerce") if pass_col else None
        if pd.isna(pct) and appeared:
            pct = 100 * passed / appeared
        rows.append(
            {
                "Gender": gender,
                "Candidate Type": cand_type,
                "Group": "All",
                "Appeared": int(appeared),
                "Passed": int(passed),
                "Failed": max(int(appeared - passed), 0),
                "Pass %": round(float(pct), 2) if pd.notna(pct) else None,
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    if out["Candidate Type"].isin(["Regular", "Private"]).any():
        out = out.groupby(["Gender", "Candidate Type"], as_index=False)[["Appeared", "Passed", "Failed"]].sum()
    else:
        out = out.groupby("Gender", as_index=False)[["Appeared", "Passed", "Failed"]].sum()
        out["Candidate Type"] = "All"
    out["Group"] = "All"
    out["Pass %"] = (100 * out["Passed"] / out["Appeared"].replace(0, pd.NA)).round(2)
    return out


def extract_type_from_pass_percentage(board_sheets: dict, year=None) -> pd.DataFrame:
    df = board_sheets.get("Pass Percentage")
    if df is None or df.empty:
        return pd.DataFrame(columns=["Candidate Type", "Appeared", "Passed", "Failed", "Pass %"])
    df = _coerce_numeric(filter_df_year(df, year))
    cat_col = find_col(df, "Category")
    group_col = find_col(df, "Group")
    gender_col = find_col(df, "Gender")
    appeared_col = find_col(df, "Appeared")
    passed_col = find_col(df, "Pass", "Passed")
    if not cat_col or not appeared_col:
        return pd.DataFrame(columns=["Candidate Type", "Appeared", "Passed", "Failed", "Pass %"])
    rows = []
    for _, r in df.iterrows():
        group = str(r.get(group_col, "")).strip().upper() if group_col else "TOTAL"
        gender = str(r.get(gender_col, "")).strip().upper() if gender_col else "TOTAL"
        if group_col and group != "TOTAL":
            continue
        if gender_col and gender != "TOTAL":
            continue
        cat = str(r.get(cat_col, "")).strip().upper()
        if "REGULAR" in cat:
            ctype = "Regular"
        elif "PRIVATE" in cat:
            ctype = "Private"
        else:
            continue
        appeared = pd.to_numeric(r.get(appeared_col), errors="coerce")
        passed = pd.to_numeric(r.get(passed_col), errors="coerce") if passed_col else None
        if pd.isna(appeared) or appeared <= 0:
            continue
        if pd.isna(passed):
            passed = 0
        rows.append(
            {
                "Candidate Type": ctype,
                "Appeared": int(appeared),
                "Passed": int(passed),
                "Failed": max(int(appeared - passed), 0),
                "Pass %": round(100 * passed / appeared, 2),
            }
        )
    return pd.DataFrame(rows)


def _extract_fbise_gender(board_sheets: dict, year=None) -> pd.DataFrame:
    df = _pick_sheet(board_sheets, ["District-wise"])
    if df is None or df.empty:
        return pd.DataFrame(columns=["Gender", "Candidate Type", "Group", "Appeared", "Passed", "Failed", "Pass %"])
    df = _coerce_numeric(filter_df_year(df, year))
    area_col = find_col(df, "Area")
    row_type = find_col(df, "Row_Type", "Row Type")
    gender_col = find_col(df, "Gender")
    type_col = find_col(df, "Candidate_Type", "Candidate Type")
    appeared_col = find_col(df, "Appeared", "Appd.")
    passed_col = find_col(df, "Pass", "Passed")
    if not all([area_col, gender_col, appeared_col]):
        return pd.DataFrame(columns=["Gender", "Candidate Type", "Group", "Appeared", "Passed", "Failed", "Pass %"])
    mask = df[area_col].astype(str).str.strip().str.lower() == "all areas"
    if row_type:
        mask &= df[row_type].astype(str).str.strip().str.lower() == "detail"
    chunk = df[mask].copy()
    chunk = chunk[chunk[gender_col].astype(str).str.strip().isin(["Male", "Female"])]
    if chunk.empty:
        return pd.DataFrame(columns=["Gender", "Candidate Type", "Group", "Appeared", "Passed", "Failed", "Pass %"])
    chunk["Gender"] = chunk[gender_col].map(normalize_gender)
    if type_col:
        chunk["Candidate Type"] = chunk[type_col].astype(str).map(
            lambda x: "Regular" if "regular" in x.lower() else ("Private" if "private" in x.lower() else "All")
        )
    else:
        chunk["Candidate Type"] = "All"
    chunk["Appeared"] = pd.to_numeric(chunk[appeared_col], errors="coerce").fillna(0).astype(int)
    chunk["Passed"] = pd.to_numeric(chunk[passed_col], errors="coerce").fillna(0).astype(int) if passed_col else 0
    chunk["Failed"] = (chunk["Appeared"] - chunk["Passed"]).clip(lower=0)
    out = chunk.groupby(["Gender", "Candidate Type"], as_index=False)[["Appeared", "Passed", "Failed"]].sum()
    out["Group"] = "All"
    out["Pass %"] = (100 * out["Passed"] / out["Appeared"].replace(0, pd.NA)).round(2)
    return out


def _extract_groupwise_type(board_sheets: dict, year=None) -> pd.DataFrame:
    """Regular/Private totals from Group-wise Distribution (Gender=Total rows only)."""
    df = _pick_sheet(board_sheets, ["Group-wise Distribution", "Group-wise"])
    if df is None or df.empty:
        return pd.DataFrame(columns=["Candidate Type", "Appeared", "Passed", "Failed", "Pass %"])
    df = _coerce_numeric(filter_df_year(df, year))
    type_col = find_col(df, "Candidate Type", "Candidate_Type", "Category")
    gender_col = find_col(df, "Gender")
    appeared_col = find_col(df, "Appeared", "Candidates")
    passed_col = find_col(df, "Passed", "Pass")
    group_col = find_col(df, "Group")
    if not type_col or not appeared_col:
        return pd.DataFrame(columns=["Candidate Type", "Appeared", "Passed", "Failed", "Pass %"])
    chunk = df.copy()
    chunk["_type"] = chunk[type_col].astype(str).str.strip().str.title()
    chunk = chunk[chunk["_type"].isin(["Regular", "Private"])]
    if gender_col:
        chunk = chunk[chunk[gender_col].astype(str).str.strip().str.lower() == "total"]
    if group_col:
        chunk = chunk[~chunk[group_col].astype(str).str.lower().str.contains("total|grand", na=False)]
    if chunk.empty:
        return pd.DataFrame(columns=["Candidate Type", "Appeared", "Passed", "Failed", "Pass %"])
    rows = []
    for ctype in ("Regular", "Private"):
        sub = chunk[chunk["_type"] == ctype]
        appeared = pd.to_numeric(sub[appeared_col], errors="coerce").sum()
        passed = pd.to_numeric(sub[passed_col], errors="coerce").sum() if passed_col else 0
        if pd.isna(appeared) or appeared <= 0:
            continue
        passed = 0 if pd.isna(passed) else int(passed)
        rows.append(
            {
                "Candidate Type": ctype,
                "Appeared": int(appeared),
                "Passed": passed,
                "Failed": max(int(appeared - passed), 0),
                "Pass %": round(100 * passed / appeared, 2),
            }
        )
    return pd.DataFrame(rows)


def _extract_combined_category_group_sheets(board_sheets: dict, year=None) -> pd.DataFrame:
    """Parse boards (e.g. Kohat, Mardan) where each subject-group sheet ('Science
    Group', 'General Group', 'Humanities Group', ...) has a single 'Category' column
    combining gender + candidate type, e.g. 'Regular (Boys)' / 'Private (Female)'.
    Sums matching rows across every such sheet for the board."""
    empty = pd.DataFrame(columns=["Gender", "Candidate Type", "Group", "Appeared", "Passed", "Failed", "Pass %"])
    rows = []
    for label, df in board_sheets.items():
        if "group" not in label.lower():
            continue
        cat_col = find_col(df, "Category")
        appeared_col = find_col(df, "Appeared")
        passed_col = find_col(df, "Passed", "Pass")
        if not cat_col or not appeared_col:
            continue
        chunk = _coerce_numeric(filter_df_year(df, year))
        for _, r in chunk.iterrows():
            cand_type, gender = parse_category_field(r.get(cat_col))
            if gender is None or cand_type is None:
                continue
            appeared = pd.to_numeric(r.get(appeared_col), errors="coerce")
            passed = pd.to_numeric(r.get(passed_col), errors="coerce") if passed_col else None
            if pd.isna(appeared) or appeared <= 0:
                continue
            if pd.isna(passed):
                passed = 0
            rows.append(
                {
                    "Gender": gender,
                    "Candidate Type": cand_type,
                    "Group": "All",
                    "Appeared": int(appeared),
                    "Passed": int(passed),
                    "Failed": max(int(appeared - passed), 0),
                }
            )
    if not rows:
        return empty
    out = pd.DataFrame(rows)
    out = out.groupby(["Gender", "Candidate Type", "Group"], as_index=False)[["Appeared", "Passed", "Failed"]].sum()
    out["Pass %"] = (100 * out["Passed"] / out["Appeared"].replace(0, pd.NA)).round(2)
    return out


def _gender_extractors():
    return (
        _extract_overview_gender_split,
        _extract_pass_percentage_gender,
        _extract_fbise_gender,
        _extract_grw_group_stats_gender,
        _extract_fsd_gender,
        _extract_grades_by_gender,
        _extract_punjab_grand_total,
        _extract_yoy_regular_private,
        _extract_combined_category_group_sheets,
    )


def _parse_group_gender_rows(df: pd.DataFrame, cand_type: str, year=None) -> list[dict]:
    if df is None or df.empty:
        return []
    df = _coerce_numeric(df)
    gender_col = find_col(df, "Gender")
    appeared_col = find_col(df, "Appeared", "Candidates")
    passed_col = find_col(df, "Passed", "Pass")
    pass_col = find_col(df, "Pass %", "Pass%")
    group_col = find_col(df, "Group")
    class_col = find_col(df, "Exam Class", "Class")
    if class_col:
        df = df[~df[class_col].astype(str).str.contains("9th", case=False, na=False)]
    if year is not None:
        ys = str(year)
        appeared_col = appeared_col if appeared_col and ys in str(appeared_col) else find_col(df, f"{ys} Appeared") or appeared_col
        passed_col = passed_col if passed_col and ys in str(passed_col) else find_col(df, f"{ys} Passed") or passed_col
        pass_col = pass_col if pass_col and ys in str(pass_col) else find_col(df, f"{ys} Pass %", f"{ys} Pass%") or pass_col
    if not gender_col or not appeared_col:
        return []
    rows = []
    current_group = "All"
    for _, r in df.iterrows():
        if group_col and pd.notna(r.get(group_col)):
            current_group = str(r[group_col]).strip()
        raw_g = r.get(gender_col)
        if pd.isna(raw_g):
            continue
        gtext = str(raw_g).strip().lower()
        if gtext in ("total", "sub-total", "sub total", "overall", ""):
            continue
        gender = normalize_gender(raw_g)
        if gender not in ("Male", "Female"):
            continue
        appeared = pd.to_numeric(r.get(appeared_col), errors="coerce")
        passed = pd.to_numeric(r.get(passed_col), errors="coerce")
        if pd.isna(appeared) or appeared <= 0:
            continue
        failed = max(int(appeared - passed), 0) if pd.notna(passed) else 0
        pct = pd.to_numeric(r.get(pass_col), errors="coerce") if pass_col else None
        if pd.isna(pct) and pd.notna(passed) and appeared > 0:
            pct = 100 * passed / appeared
        elif pd.notna(pct):
            pct = normalize_pct(pd.Series([pct])).iloc[0]
        group_val = current_group if current_group else "All"
        if any(x in group_val.lower() for x in ("sub-total", "sub total")):
            continue
        rows.append(
            {
                "Gender": gender,
                "Candidate Type": cand_type,
                "Group": group_val,
                "Appeared": int(appeared),
                "Passed": int(passed) if pd.notna(passed) else 0,
                "Failed": failed,
                "Pass %": round(float(pct), 2) if pd.notna(pct) else None,
            }
        )
    if not rows:
        return []
    overall = [r for r in rows if str(r["Group"]).lower() == "overall"]
    if overall:
        for r in overall:
            r["Group"] = "All"
        return overall
    return [r for r in rows if str(r["Group"]).lower() not in ("total", "grand total")]


def _extract_punjab_grand_total(board_sheets: dict, year=None) -> pd.DataFrame:
    rows = []
    years = [year] if year else get_available_years(board_sheets) or _years_from_sheet_names(board_sheets)
    for y in years:
        ys = str(y)
        grand_labels = [lb for lb in board_sheets if ys in lb and "grand total" in lb.lower()]
        if grand_labels:
            rows.extend(_parse_group_gender_rows(board_sheets[grand_labels[0]], "All"))
            continue
        for label, df in board_sheets.items():
            if ys not in label:
                continue
            ll = label.lower()
            if "regular" in ll and ("govt" in ll or "affiliated" in ll or "candidates sta" in ll):
                rows.extend(_parse_group_gender_rows(df, "Regular", year=y))
            elif "private" in ll and "candidates sta" in ll:
                rows.extend(_parse_group_gender_rows(df, "Private", year=y))
            elif re.search(rf"{ys}\s+private$", ll) or (ll.endswith(" private") and "district" not in ll and "pass" not in ll):
                rows.extend(_parse_group_gender_rows(df, "Private", year=y))
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.groupby(["Gender", "Candidate Type", "Group"], as_index=False)[["Appeared", "Passed", "Failed"]].sum().assign(
        **{"Pass %": lambda d: (100 * d["Passed"] / d["Appeared"].replace(0, pd.NA)).round(2)}
    )


def _extract_grades_by_gender(board_sheets: dict, year=None) -> pd.DataFrame:
    df = _pick_sheet(board_sheets, ["Gender-wise Result", "Gender-wise"])
    if df is None or df.empty:
        return pd.DataFrame(columns=["Gender", "Candidate Type", "Group", "Appeared", "Passed", "Failed", "Pass %"])
    df = _coerce_numeric(filter_df_year(df, year))
    gender_col = find_col(df, "Gender")
    type_col = find_col(df, "Category", "Candidate Type", "Student Type")
    group_col = find_col(df, "Group")
    appeared_col = find_col(df, "Appeared", "Candidates")
    passed_col = find_col(df, "Passed", "Pass")
    pass_col = find_col(df, "Pass %", "Pass%")
    if not gender_col:
        return pd.DataFrame(columns=["Gender", "Candidate Type", "Group", "Appeared", "Passed", "Failed", "Pass %"])
    rows = []
    for _, r in df.iterrows():
        cat = str(r.get(type_col, "")).strip() if type_col else "All"
        if _row_is_subtotal(cat):
            continue
        group_val = str(r[group_col]).strip() if group_col and pd.notna(r.get(group_col)) else "All"
        if _row_is_subtotal(group_val):
            continue
        cand_type = normalize_type(cat) if cat else "All"
        if cand_type not in ("Regular", "Private", "All"):
            if "regular" in cat.lower():
                cand_type = "Regular"
            elif "private" in cat.lower():
                cand_type = "Private"
            else:
                cand_type = "All"
        gender = normalize_gender(r[gender_col])
        if gender not in ("Male", "Female"):
            continue
        appeared = pd.to_numeric(r.get(appeared_col), errors="coerce")
        passed = pd.to_numeric(r.get(passed_col), errors="coerce")
        if pd.isna(appeared) or appeared <= 0:
            continue
        failed = max(int(appeared - passed), 0) if pd.notna(passed) else 0
        pct = pd.to_numeric(r.get(pass_col), errors="coerce") if pass_col else None
        if pd.isna(pct) and pd.notna(passed):
            pct = 100 * passed / appeared
        rows.append(
            {
                "Gender": gender,
                "Candidate Type": cand_type,
                "Group": group_val,
                "Appeared": int(appeared),
                "Passed": int(passed) if pd.notna(passed) else 0,
                "Failed": failed,
                "Pass %": round(float(pct), 2) if pd.notna(pct) else None,
            }
        )
    return pd.DataFrame(rows)


def _extract_fsd_gender(board_sheets: dict, year=None) -> pd.DataFrame:
    """FSD gender split: Regular candidates come from the Regular Gender-School sheet
    (mapped to 'Gender-wise Result'), Private candidates from the Private Gender sheet
    (mapped to 'Gender-wise'). Both must be combined or the split silently drops every
    private candidate and undercounts the board's true Appeared/Boys/Girls figures.

    This layout (two separate sheets, one per candidate type) is specific to FSD.
    Other boards (e.g. DGK) publish a single plain 'Gender-wise' sheet that is the
    board's OVERALL gender total with no Regular/Private distinction at all — if this
    function fired on that sheet alone, it would mislabel 100% of the board's real
    total as "Private", fabricating a split that doesn't exist in the source workbook.
    Requiring both sheets to be present makes this extractor FSD-specific and safe."""
    empty = pd.DataFrame(columns=["Gender", "Candidate Type", "Group", "Appeared", "Passed", "Failed", "Pass %"])
    if board_sheets.get("Gender-wise Result") is None or board_sheets.get("Gender-wise") is None:
        return empty
    sources = [
        ("Gender-wise Result", "Regular"),
        ("Gender-wise", "Private"),
    ]
    rows = []
    for sheet_name, cand_type in sources:
        df = board_sheets.get(sheet_name)
        if df is None or df.empty:
            continue
        df = _coerce_numeric(filter_df_year(df, year))
        gender_col = find_col(df, "Gender")
        appeared_col = find_col(df, "Appeared")
        passed_col = find_col(df, "Passed", "Pass")
        row_type_col = find_col(df, "Row_Type", "Row Type")
        if not gender_col or not appeared_col:
            continue
        chunk = df.copy()
        if row_type_col:
            chunk = chunk[chunk[row_type_col].astype(str).str.strip().str.lower() == "detail"]
        chunk = chunk[chunk[gender_col].astype(str).str.strip().isin(["Male", "Female"])]
        if chunk.empty:
            continue
        for gender in ("Male", "Female"):
            sub = chunk[chunk[gender_col].astype(str).str.strip() == gender]
            appeared = pd.to_numeric(sub[appeared_col], errors="coerce").sum()
            passed = pd.to_numeric(sub[passed_col], errors="coerce").sum() if passed_col else 0
            if pd.isna(appeared) or appeared <= 0:
                continue
            passed = 0 if pd.isna(passed) else int(passed)
            rows.append(
                {
                    "Gender": gender,
                    "Candidate Type": cand_type,
                    "Group": "All",
                    "Appeared": int(appeared),
                    "Passed": passed,
                    "Failed": max(int(appeared - passed), 0),
                    "Pass %": round(100 * passed / appeared, 2) if appeared else None,
                }
            )
    if not rows:
        return empty
    out = pd.DataFrame(rows)
    out = out.groupby(["Gender", "Candidate Type", "Group"], as_index=False)[["Appeared", "Passed", "Failed"]].sum()
    out["Pass %"] = (100 * out["Passed"] / out["Appeared"].replace(0, pd.NA)).round(2)
    return out


def extract_type_from_yoy(board_sheets: dict, year=None) -> pd.DataFrame:
    df = _pick_sheet(board_sheets, ["Summary (2024-2026)", "Overall Summary", "Summary"])
    if df is None or df.empty:
        return pd.DataFrame(columns=["Candidate Type", "Appeared", "Passed", "Failed", "Pass %"])
    df = _coerce_numeric(filter_df_year(df, year))
    reg_app = find_col(df, "Regular Appeared")
    reg_pass = find_col(df, "Regular Passed")
    priv_app = find_col(df, "Private Appeared")
    priv_pass = find_col(df, "Private Passed")
    rows = []
    for _, r in df.iterrows():
        if reg_app and pd.notna(r.get(reg_app)) and int(r[reg_app]) > 0:
            app, pas = int(r[reg_app]), int(r[reg_pass]) if reg_pass and pd.notna(r.get(reg_pass)) else 0
            rows.append({"Candidate Type": "Regular", "Appeared": app, "Passed": pas, "Failed": max(app - pas, 0), "Pass %": round(100 * pas / app, 2)})
        if priv_app and pd.notna(r.get(priv_app)) and int(r[priv_app]) > 0:
            app, pas = int(r[priv_app]), int(r[priv_pass]) if priv_pass and pd.notna(r.get(priv_pass)) else 0
            rows.append({"Candidate Type": "Private", "Appeared": app, "Passed": pas, "Failed": max(app - pas, 0), "Pass %": round(100 * pas / app, 2)})
    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(columns=["Candidate Type", "Appeared", "Passed", "Failed", "Pass %"])
    return out.groupby("Candidate Type", as_index=False)[["Appeared", "Passed", "Failed"]].sum().assign(
        **{"Pass %": lambda d: (100 * d["Passed"] / d["Appeared"].replace(0, pd.NA)).round(2)}
    )


def _extract_yoy_regular_private(board_sheets: dict, year=None) -> pd.DataFrame:
    type_df = extract_type_from_yoy(board_sheets, year)
    if type_df.empty:
        return pd.DataFrame(columns=["Gender", "Candidate Type", "Group", "Appeared", "Passed", "Failed", "Pass %"])
    rows = []
    for _, r in type_df.iterrows():
        rows.append(
            {
                "Gender": "Male",
                "Candidate Type": r["Candidate Type"],
                "Group": "All",
                "Appeared": r["Appeared"],
                "Passed": r["Passed"],
                "Failed": r["Failed"],
                "Pass %": r["Pass %"],
            }
        )
    return pd.DataFrame(rows)


def extract_gender_type_rows(board_sheets: dict, year=None) -> pd.DataFrame:
    """Return normalized rows: Gender, Candidate Type, Appeared, Passed, Failed, Pass %."""
    empty = pd.DataFrame(columns=["Gender", "Candidate Type", "Group", "Appeared", "Passed", "Failed", "Pass %"])

    for extractor in _gender_extractors():
        out = extractor(board_sheets, year)
        if not out.empty and out["Appeared"].sum() > 0:
            return out.reset_index(drop=True)

    priority = [
        "Gender-wise Result",
        "Gender-wise",
        "SSC-10th Category-wise",
        "Group-wise",
        "Group-wise Distribution",
        "By Candidate Type & Gender",
    ]
    df = _pick_sheet(board_sheets, priority)
    if df is None or df.empty:
        return empty

    df = _coerce_numeric(filter_df_year(df, year))
    gender_col = find_col(df, "Gender")
    type_col = find_col(df, "Candidate Type", "Category", "Student Type")
    group_col = find_col(df, "Group")
    appeared_col = find_col(df, "Appeared", "Candidates", "Total Students", "Total Appeared")
    passed_col = find_col(df, "Passed", "Pass", "Total Pass")
    failed_col = find_col(df, "Failed", "Fail")
    pass_col = find_col(df, "Pass %", "Pass%")

    rows = []
    for _, r in df.iterrows():
        if gender_col and pd.notna(r.get(gender_col)):
            gender = normalize_gender(r[gender_col])
        else:
            gender = None

        if type_col and pd.notna(r.get(type_col)):
            parsed_type, parsed_gender = parse_category_field(r[type_col])
            cand_type = parsed_type or normalize_type(r[type_col])
            if gender is None:
                gender = parsed_gender
        elif gender_col and pd.notna(r.get(gender_col)):
            cand_type = "All"
        else:
            cand_type, parsed_gender = parse_category_field(r.get(type_col or ""))
            if gender is None:
                gender = parsed_gender

        if gender is None or gender not in ("Male", "Female"):
            continue
        if cand_type in (None, "Unknown", "All") and type_col is None:
            cand_type = "All"
        if type_col and _row_is_subtotal(r.get(type_col, "")):
            continue
        group_val = str(r[group_col]).strip() if group_col and pd.notna(r.get(group_col)) else "All"
        if _row_is_subtotal(group_val):
            continue

        appeared = pd.to_numeric(r.get(appeared_col), errors="coerce") if appeared_col else None
        passed = pd.to_numeric(r.get(passed_col), errors="coerce") if passed_col else None
        failed = pd.to_numeric(r.get(failed_col), errors="coerce") if failed_col else None
        if pd.isna(appeared) and pd.isna(passed):
            continue
        if pd.isna(appeared) and pd.notna(passed) and pd.notna(failed):
            appeared = passed + failed
        if pd.isna(failed) and pd.notna(appeared) and pd.notna(passed):
            failed = max(appeared - passed, 0)

        pct = pd.to_numeric(r.get(pass_col), errors="coerce") if pass_col else None
        if pd.isna(pct) and pd.notna(appeared) and appeared > 0 and pd.notna(passed):
            pct = 100 * passed / appeared
        elif pd.notna(pct):
            pct = normalize_pct(pd.Series([pct])).iloc[0]

        if any(x in group_val.lower() for x in ("total", "grand", "sub total")):
            continue

        rows.append(
            {
                "Gender": gender,
                "Candidate Type": cand_type or "Unknown",
                "Group": group_val,
                "Appeared": int(appeared) if pd.notna(appeared) else 0,
                "Passed": int(passed) if pd.notna(passed) else 0,
                "Failed": int(failed) if pd.notna(failed) else 0,
                "Pass %": round(float(pct), 2) if pd.notna(pct) else None,
            }
        )

    out = pd.DataFrame(rows)
    if out.empty or out["Appeared"].sum() <= 0:
        return empty
    if out["Candidate Type"].isin(["Regular", "Private"]).any():
        out = out[out["Candidate Type"].isin(["Regular", "Private"])].copy()
    elif (out["Candidate Type"] == "Overall").any():
        out = out[out["Candidate Type"] == "Overall"].copy()
    return out.reset_index(drop=True)


def aggregate_demo_rows(demo_df: pd.DataFrame) -> pd.DataFrame:
    """Combine multi-year demo rows into one row per gender/type/group."""
    if demo_df.empty:
        return demo_df
    keys = [c for c in ["Candidate Type", "Gender", "Group"] if c in demo_df.columns]
    out = demo_df.groupby(keys, as_index=False)[["Appeared", "Passed", "Failed"]].sum()
    out["Pass %"] = (100 * out["Passed"] / out["Appeared"].replace(0, pd.NA)).round(2)
    return out


def summarize_gender(demo_df: pd.DataFrame) -> pd.DataFrame:
    if demo_df.empty:
        return pd.DataFrame(columns=["Gender", "Appeared", "Passed", "Failed", "Pass %"])
    out = _gender_rows_for_summary(demo_df).groupby("Gender", as_index=False)[["Appeared", "Passed", "Failed"]].sum()
    out["Pass %"] = out.apply(
        lambda r: round(100 * r["Passed"] / r["Appeared"], 2) if r["Appeared"] > 0 else 0,
        axis=1,
    )
    return out


def summarize_type(demo_df: pd.DataFrame) -> pd.DataFrame:
    empty = pd.DataFrame(columns=["Candidate Type", "Appeared", "Passed", "Failed", "Pass %"])
    if demo_df.empty or "Candidate Type" not in demo_df.columns:
        return empty
    filtered = demo_df[demo_df["Candidate Type"].isin(["Regular", "Private"])].copy()
    if filtered.empty:
        filtered = demo_df[~demo_df["Candidate Type"].isin(["All", "Unknown"])].copy()
    if filtered.empty:
        return empty
    out = filtered.groupby("Candidate Type", as_index=False)[["Appeared", "Passed", "Failed"]].sum()
    out["Pass %"] = out.apply(
        lambda r: round(100 * r["Passed"] / r["Appeared"], 2) if r["Appeared"] > 0 else 0,
        axis=1,
    )
    return out


def extract_subject_group_data(board_sheets: dict, year=None) -> pd.DataFrame:
    """Subject/group pass % with gender split when available."""
    df = _pick_sheet(
        board_sheets,
        ["Group-wise", "Group-wise Distribution", "SSC-10th Category-wise", "Science Group", "Humanities Group", "General Group"],
    )
    if df is None or df.empty:
        return pd.DataFrame(columns=["Group", "Gender", "Pass %"])

    df = _coerce_numeric(filter_df_year(df, year))
    group_col = find_col(df, "Group")
    gender_col = find_col(df, "Gender")
    type_col = find_col(df, "Candidate Type", "Candidate_Type", "Category", "Student Type")
    pass_col = find_col(df, "Pass %", "Pass%", "Pass_Pct")
    appeared_col = find_col(df, "Appeared", "Total Students", "Candidates")
    passed_col = find_col(df, "Passed", "Pass")

    if not group_col:
        return pd.DataFrame(columns=["Group", "Gender", "Pass %"])

    if type_col:
        types = df[type_col].astype(str).str.strip().str.lower()
        if types.isin(["regular", "private"]).any():
            df = df[types.isin(["regular", "private"])].copy()
        elif types.eq("overall").any():
            df = df[types.eq("overall")].copy()
    if gender_col:
        genders = df[gender_col].astype(str).str.strip().str.lower()
        if genders.eq("total").any():
            df = df[genders.eq("total")].copy()

    rows = []
    for _, r in df.iterrows():
        group = str(r[group_col]).strip()
        if any(x in group.lower() for x in ("total", "grand", "sub total")):
            continue

        if gender_col:
            gender = normalize_gender(r[gender_col])
        elif type_col:
            _, gender = parse_category_field(r[type_col])
        else:
            gender = "All"

        pct = pd.to_numeric(r.get(pass_col), errors="coerce") if pass_col else None
        appeared = pd.to_numeric(r.get(appeared_col), errors="coerce") if appeared_col else None
        passed = pd.to_numeric(r.get(passed_col), errors="coerce") if passed_col else None
        if pd.isna(pct) and pd.notna(appeared) and appeared > 0 and pd.notna(passed):
            pct = 100 * passed / appeared
        if pd.isna(pct):
            continue
        pct = normalize_pct(pd.Series([pct])).iloc[0]
        rows.append(
            {
                "Group": group,
                "Gender": gender or "All",
                "Appeared": int(appeared) if pd.notna(appeared) else 0,
                "Passed": int(passed) if pd.notna(passed) else 0,
                "Pass %": round(float(pct), 1),
            }
        )

    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(columns=["Group", "Gender", "Pass %"])
    if year is None and len(out) > 0:
        out = out.groupby(["Group", "Gender"], as_index=False)[["Appeared", "Passed"]].sum()
        out["Pass %"] = (100 * out["Passed"] / out["Appeared"].replace(0, pd.NA)).round(1)
    return out[["Group", "Gender", "Pass %"]]


def _pick_punjab_year_sheet(board_sheets: dict, year, kind: str):
    """Find year-specific Punjab sheets (subject / district)."""
    keys = {
        "subject": ("subject", "pass"),
        "district": ("district", "pass"),
    }
    need = keys.get(kind, ())
    years = [year] if year else sorted(get_available_years(board_sheets) or _years_from_sheet_names(board_sheets))
    for y in reversed(years):
        ys = str(y)
        for label, df in board_sheets.items():
            ll = label.lower()
            if ys not in label or not all(k in ll for k in need):
                continue
            if kind == "subject" and re.search(r"part\s*-?\s*i\b", ll) and "part-ii" not in ll and "part ii" not in ll:
                continue
            return df, y
    return None, None


def _extract_fsd_style_subject_sheet(board_sheets: dict, year):
    """Faisalabad's 'Subjects' sheet is long-format: Year, Candidate_Type,
    Part, Subject_Name, Enroll, Absent, Appear, Pass, Pass_Pct. Collapse
    Regular+Private candidate types into one Overall row per subject."""
    df = board_sheets.get("Subjects")
    if df is None or df.empty:
        return None, None
    df = df.copy()
    ycol = find_col(df, "Year")
    subj_col = find_col(df, "Subject_Name", "Subject Name", "Subject")
    appear_col = find_col(df, "Appear", "Appeared")
    pass_col = find_col(df, "Pass")
    if ycol is None or subj_col is None or appear_col is None or pass_col is None:
        return None, None
    years = [year] if year else sorted(pd.to_numeric(df[ycol], errors="coerce").dropna().astype(int).unique().tolist())
    for y in reversed(years):
        yd = df[pd.to_numeric(df[ycol], errors="coerce") == y]
        if yd.empty:
            continue
        agg = yd.groupby(subj_col, as_index=False)[[appear_col, pass_col]].sum()
        agg = agg.rename(columns={subj_col: "Subject", appear_col: "Appeared", pass_col: "Passed"})
        agg["Appeared"] = pd.to_numeric(agg["Appeared"], errors="coerce")
        agg["Passed"] = pd.to_numeric(agg["Passed"], errors="coerce")
        agg["Pass %"] = (100 * agg["Passed"] / agg["Appeared"].replace(0, float("nan"))).round(2)
        return agg, y
    return None, None


def extract_subject_data(board_sheets: dict, year=None) -> pd.DataFrame:
    df = _pick_sheet(board_sheets, ["Subject-wise Pass %", "Subject-wise"])
    if df is None or df.empty:
        df, sheet_year = _pick_punjab_year_sheet(board_sheets, year, "subject")
        if df is None:
            df, sheet_year = _extract_fsd_style_subject_sheet(board_sheets, year)
            if df is None:
                return pd.DataFrame(columns=["Subject", "Appeared", "Passed", "Pass %"])
        year = sheet_year if year is None else year

    df = _coerce_numeric(df.copy())
    subject_col = find_col(df, "Subject", "Subject Name", "Subject_Name")
    if subject_col is None:
        return pd.DataFrame(columns=["Subject", "Appeared", "Passed", "Pass %"])

    ycol = find_col(df, "Year")
    if ycol and year is not None:
        df = filter_df_year(df, year)

    # Some boards (Lahore, Sahiwal, ...) publish Regular/Private/Overall split
    # columns instead of plain Appeared/Passed/Pass % — fall back to those.
    appeared_col = find_col(df, "Appeared", "Overall Appeared", "Appear", "Reg. Appeared")
    passed_col = find_col(df, "Passed", "Overall Passed", "Overall Pass", "Pass", "Reg. Pass")
    pass_col = find_col(df, "Pass %", "Pass%", "Overall Pass %", "Pass_Pct")

    year_pass_cols = [c for c in df.columns if re.search(rf"{year}\s*pass\s*%", str(c), re.I)] if year else []
    year_app_cols = [c for c in df.columns if re.search(rf"{year}\s*appeared", str(c), re.I)] if year else []
    year_passed_cols = [c for c in df.columns if re.search(rf"{year}\s*passed", str(c), re.I)] if year else []
    all_pass_cols = [c for c in df.columns if re.search(r"20\d{2}\s*pass\s*%", str(c), re.I)] if year is None else []
    all_app_cols = [c for c in df.columns if re.search(r"20\d{2}\s*appeared", str(c), re.I)] if year is None else []
    all_passed_cols = [c for c in df.columns if re.search(r"20\d{2}\s*passed", str(c), re.I)] if year is None else []

    rows = []
    for _, r in df.iterrows():
        subject = str(r[subject_col]).strip()
        if not subject or subject.lower() in ("total", "grand total"):
            continue

        appeared = passed = pct = None
        if year_pass_cols:
            pct = pd.to_numeric(r[year_pass_cols[0]], errors="coerce")
        elif all_pass_cols:
            pct_vals = pd.to_numeric([r[c] for c in all_pass_cols], errors="coerce")
            pct = normalize_pct(pd.Series(pct_vals)).mean()
        if year_app_cols:
            appeared = pd.to_numeric(r[year_app_cols[0]], errors="coerce")
        elif all_app_cols:
            appeared = pd.to_numeric([r[c] for c in all_app_cols], errors="coerce").sum()
        if year_passed_cols:
            passed = pd.to_numeric(r[year_passed_cols[0]], errors="coerce")
        elif all_passed_cols:
            passed = pd.to_numeric([r[c] for c in all_passed_cols], errors="coerce").sum()
        if pass_col and pd.isna(pct):
            pct = pd.to_numeric(r.get(pass_col), errors="coerce")
        if appeared_col and pd.isna(appeared):
            appeared = pd.to_numeric(r.get(appeared_col), errors="coerce")
        if passed_col and pd.isna(passed):
            passed = pd.to_numeric(r.get(passed_col), errors="coerce")

        if pd.isna(pct) and pd.notna(appeared) and appeared > 0 and pd.notna(passed):
            pct = 100 * passed / appeared
        if pd.isna(pct):
            continue

        pct = normalize_pct(pd.Series([pct])).iloc[0]
        rows.append(
            {
                "Subject": subject,
                "Appeared": int(appeared) if pd.notna(appeared) else None,
                "Passed": int(passed) if pd.notna(passed) else None,
                "Pass %": round(float(pct), 1),
            }
        )

    out = pd.DataFrame(rows)
    if not out.empty:
        if year is None and ycol and ycol in df.columns:
            out = out.groupby("Subject", as_index=False).agg(
                {"Appeared": "sum", "Passed": "sum", "Pass %": "mean"}
            )
            out["Pass %"] = out.apply(
                lambda row: round(100 * row["Passed"] / row["Appeared"], 1)
                if pd.notna(row["Appeared"]) and row["Appeared"] > 0 and pd.notna(row["Passed"])
                else round(row["Pass %"], 1),
                axis=1,
            )
        out = out.sort_values("Pass %", ascending=False)
    return out


def extract_district_data(board_sheets: dict, year=None) -> pd.DataFrame:
    df = _pick_sheet(board_sheets, ["District-wise", "Grade Distribution by District"])
    if df is None or df.empty:
        df, sheet_year = _pick_punjab_year_sheet(board_sheets, year, "district")
        if df is None:
            return pd.DataFrame(columns=["District", "Appeared", "Passed", "Failed", "Pass %"])
        year = sheet_year if year is None else year

    df = _coerce_numeric(filter_df_year(df, year))
    district_col = find_col(df, "District")
    category_col = find_col(df, "Category")
    row_type_col = find_col(df, "Row_Type", "Row Type")
    appeared_col = find_col(df, "Total Appeared", "Total_Appeared", "Appeared")
    passed_col = find_col(df, "Total Passed", "Total_Passed", "Passed", "Total Pass")
    failed_col = find_col(df, "Failed")
    pass_col = find_col(df, "Total Pass Pct", "Total_Pass_Pct", "Total Pass %", "Pass %", "Pass%", "Total %")

    if district_col is None:
        return pd.DataFrame(columns=["District", "Appeared", "Passed", "Failed", "Pass %"])

    rows = []
    for _, r in df.iterrows():
        district = str(r[district_col]).strip()
        if not district or district.lower() in ("total", "grand total", "overall"):
            continue
        if row_type_col and pd.notna(r.get(row_type_col)):
            rt = str(r[row_type_col]).strip().lower()
            if rt not in ("detail", ""):
                continue
        ycol = find_col(df, "Year")
        if ycol and year is not None:
            row_year = pd.to_numeric(r.get(ycol), errors="coerce")
            if pd.notna(row_year) and int(row_year) != int(year):
                continue
        category = str(r[category_col]).strip() if category_col and pd.notna(r.get(category_col)) else "All"
        if category.lower() == "total":
            category = "All"

        appeared = pd.to_numeric(r.get(appeared_col), errors="coerce") if appeared_col else None
        passed = pd.to_numeric(r.get(passed_col), errors="coerce") if passed_col else None
        failed = pd.to_numeric(r.get(failed_col), errors="coerce") if failed_col else None
        pct = pd.to_numeric(r.get(pass_col), errors="coerce") if pass_col else None

        if pd.isna(pct) and pd.notna(appeared) and appeared > 0 and pd.notna(passed):
            pct = 100 * passed / appeared
        if pd.isna(pct):
            continue
        pct = normalize_pct(pd.Series([pct])).iloc[0]

        label = district if category == "All" else f"{district} ({category})"
        rows.append(
            {
                "District": label,
                "Appeared": int(appeared) if pd.notna(appeared) else 0,
                "Passed": int(passed) if pd.notna(passed) else 0,
                "Failed": int(failed) if pd.notna(failed) else 0,
                "Pass %": round(float(pct), 1),
            }
        )

    out = pd.DataFrame(rows)
    if not out.empty:
        if year is None:
            out = out.groupby("District", as_index=False)[["Appeared", "Passed", "Failed"]].sum()
            out["Pass %"] = (100 * out["Passed"] / out["Appeared"].replace(0, pd.NA)).round(1)
        out = out.sort_values("Pass %", ascending=True)
    return out


def extract_board_totals(board_sheets: dict, year=None, board_prefix: str | None = None) -> dict:
    zero = {"appeared": 0, "passed": 0, "failed": 0, "pass_pct": 0}
    if year is not None:
        avail = get_available_years(board_sheets)
        if avail and year not in avail:
            return zero

    df = _pick_sheet(
        board_sheets,
        [
            "Overall Summary",
            "Overview Summary",
            "Summary",
            "Summary (2024-2026)",
            "Overview",
            "SSC-10th Summary",
        ],
    )
    if year is not None and (df is None or filter_df_year(_coerce_numeric(df), year).empty):
        for label, sheet in board_sheets.items():
            if str(year) in label and "result at a glance" in label.lower():
                totals = _extract_punjab_glance_totals(sheet)
                if totals["appeared"] > 0:
                    return totals
        return zero

    if df is None or df.empty:
        return zero

    df = _coerce_numeric(filter_df_year(df, year))
    if year is not None and df.empty:
        return zero
    df = _filter_board_summary_rows(df, board_prefix)
    if df.empty:
        return zero
    appeared_col, passed_col, failed_col, pass_col = _count_columns(df)

    if appeared_col is None and passed_col is None:
        return zero

    appeared = pd.to_numeric(df[appeared_col], errors="coerce").sum() if appeared_col else None
    passed = pd.to_numeric(df[passed_col], errors="coerce").sum() if passed_col else None
    failed = pd.to_numeric(df[failed_col], errors="coerce").sum() if failed_col else None

    if appeared and passed_col is None and (passed is None or pd.isna(passed)):
        if failed_col and failed is not None and not pd.isna(failed) and failed > 0:
            passed = max(int(appeared - failed), 0)
        elif pass_col:
            pct_vals = normalize_pct(pd.to_numeric(df[pass_col], errors="coerce"))
            if not pct_vals.dropna().empty:
                pct = float(pct_vals.mean())
                if pct > 0:
                    passed = int(round(appeared * pct / 100))

    if passed is None or pd.isna(passed):
        passed = 0
    if pd.isna(failed) and appeared and passed:
        failed = max(int(appeared - passed), 0)

    pass_pct = round(100 * passed / appeared, 2) if appeared and passed else 0
    if pass_col and appeared:
        pct_vals = normalize_pct(pd.to_numeric(df[pass_col], errors="coerce"))
        if not pct_vals.dropna().empty:
            pass_pct = round(float(pct_vals.mean()), 2)

    return {
        "appeared": int(appeared) if pd.notna(appeared) else 0,
        "passed": int(passed) if pd.notna(passed) else 0,
        "failed": int(failed) if pd.notna(failed) else 0,
        "pass_pct": round(float(pass_pct), 2) if pd.notna(pass_pct) else 0,
    }


def _normalize_master_chunk(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Board", "Year", "Appeared", "Passed", "Pass %"])
    ycol = find_col(df, "Year")
    bcol = find_col(df, "Board")
    acol = find_col(df, "Appeared", "Total Appeared", "Total Students")
    pcol = find_col(df, "Passed", "Pass", "Total Pass")
    pp = find_col(df, "Pass %", "Pass%")
    if not all([ycol, bcol, acol]):
        return pd.DataFrame(columns=["Board", "Year", "Appeared", "Passed", "Pass %"])
    chunk = df[[ycol, bcol, acol] + ([pcol] if pcol else []) + ([pp] if pp else [])].copy()
    cols = ["Year", "Board", "Appeared"] + (["Passed"] if pcol else []) + (["Pass %"] if pp else [])
    chunk.columns = cols
    chunk["Year"] = pd.to_numeric(chunk["Year"], errors="coerce")
    chunk["Appeared"] = pd.to_numeric(chunk["Appeared"], errors="coerce")
    if "Passed" in chunk.columns:
        chunk["Passed"] = pd.to_numeric(chunk["Passed"], errors="coerce")
    if "Pass %" in chunk.columns:
        chunk["Pass %"] = normalize_pct(pd.to_numeric(chunk["Pass %"], errors="coerce"))
    elif "Passed" in chunk.columns:
        chunk["Pass %"] = (100 * chunk["Passed"] / chunk["Appeared"].replace(0, pd.NA)).round(2)
    chunk = chunk.dropna(subset=["Year", "Board", "Appeared"])
    chunk = chunk[chunk["Appeared"] > 0]
    chunk["Board"] = chunk["Board"].astype(str).str.strip().map(lambda b: BOARD_DISPLAY_NAMES.get(b, b))
    return chunk.reset_index(drop=True)


def get_master_summary(boards: dict) -> pd.DataFrame:
    parts = []
    kpk = boards.get("Master", {}).get("Summary", pd.DataFrame()).copy()
    if not kpk.empty:
        parts.append(_normalize_master_chunk(kpk))
    comp_raw = boards.get("Master", {}).get("Board Comparison", pd.DataFrame())
    if not comp_raw.empty:
        if find_col(comp_raw, "Year") and find_col(comp_raw, "Board"):
            parts.append(_normalize_master_chunk(comp_raw))
        else:
            parsed = _parse_board_comparison(comp_raw)
            if not parsed.empty:
                parsed["Board"] = parsed["Board"].astype(str).str.strip().map(lambda b: BOARD_DISPLAY_NAMES.get(b, b))
                parts.append(parsed)
    if not parts:
        return pd.DataFrame(columns=["Board", "Year", "Appeared", "Passed", "Pass %"])
    out = pd.concat(parts, ignore_index=True)
    out = out.drop_duplicates(subset=["Board", "Year"], keep="first")
    return out.sort_values(["Board", "Year"]).reset_index(drop=True)


def get_board_appeared_table(boards: dict) -> pd.DataFrame:
    rows = []
    seen = set()
    for prefix in list_board_prefixes(boards):
        name = board_display_name(prefix)
        for y in get_available_years(boards[prefix]):
            totals = extract_board_totals(boards[prefix], y, board_prefix=prefix)
            if totals["appeared"] <= 0:
                continue
            key = (name, y)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "Board": name,
                    "Year": y,
                    "Appeared": totals["appeared"],
                    "Passed": totals["passed"],
                    "Pass %": totals["pass_pct"],
                }
            )
    if not rows:
        return pd.DataFrame(columns=["Board", "Year", "Appeared", "Passed", "Pass %"])
    return pd.DataFrame(rows).sort_values(["Board", "Year"]).reset_index(drop=True)


def get_all_board_rankings(boards: dict, year=None) -> pd.DataFrame:
    master = get_master_summary(boards)
    if master.empty:
        return pd.DataFrame(columns=["Board", "Appeared", "Passed", "Pass %"])
    df = master.copy()
    if year is not None and "Year" in df.columns:
        df = df[df["Year"] == year]
    if year is None:
        df = df.groupby("Board", as_index=False)[["Appeared", "Passed"]].sum()
        df["Pass %"] = (100 * df["Passed"] / df["Appeared"].replace(0, pd.NA)).round(2)
    return df.sort_values("Pass %", ascending=False).reset_index(drop=True)


def extract_yearly_trend(board_sheets: dict, board_prefix: str | None = None) -> pd.DataFrame:
    df = _pick_sheet(
        board_sheets,
        [
            "Overall Summary",
            "Overview Summary",
            "Summary",
            "Summary (2024-2026)",
            "Overview",
            "SSC-10th Summary",
        ],
    )
    if df is None or df.empty:
        return pd.DataFrame(columns=["Year", "Appeared", "Passed", "Pass %"])
    df = _coerce_numeric(df)
    df = _filter_board_summary_rows(df, board_prefix)
    ycol = find_col(df, "Year")
    if ycol is None:
        return pd.DataFrame(columns=["Year", "Appeared", "Passed", "Pass %"])
    appeared_col, passed_col, failed_col, pass_col = _count_columns(df)
    if appeared_col is None:
        return pd.DataFrame(columns=["Year", "Appeared", "Passed", "Pass %"])
    out = pd.DataFrame({"Year": pd.to_numeric(df[ycol], errors="coerce")})
    out["Appeared"] = pd.to_numeric(df[appeared_col], errors="coerce")
    if passed_col:
        out["Passed"] = pd.to_numeric(df[passed_col], errors="coerce")
    elif failed_col:
        fail_vals = pd.to_numeric(df[failed_col], errors="coerce")
        out["Passed"] = (out["Appeared"] - fail_vals).clip(lower=0)
    else:
        out["Passed"] = pd.NA
    if pass_col:
        out["Pass %"] = normalize_pct(pd.to_numeric(df[pass_col], errors="coerce"))
    elif passed_col or failed_col:
        out["Pass %"] = (100 * out["Passed"] / out["Appeared"].replace(0, pd.NA)).round(2)
    if out["Passed"].isna().all() and "Pass %" in out.columns:
        out["Passed"] = (out["Appeared"] * out["Pass %"] / 100).round().astype("Int64")
    out = out.dropna(subset=["Year", "Appeared"])
    out = out[out["Appeared"] > 0]
    if "Passed" in out.columns:
        out["Failed"] = (out["Appeared"] - out["Passed"].fillna(0)).clip(lower=0)
    return out.sort_values("Year").reset_index(drop=True)


def _extract_grade_dist_from_candidates_sta(board_sheets: dict, year=None) -> pd.DataFrame:
    """Fallback grade-distribution extractor for boards (e.g. BISE Lahore) whose per-year
    data lives in separate "<year> ... Candidates Sta" sheets rather than one unified
    "Grade Distribution" sheet. The "... Private Candidates Sta" sheet for each year carries
    a "Grand Total" row that already combines Regular + Private candidates for that year,
    so that single row is the board's full grade breakdown for the year."""
    year_sheet_re = re.compile(r"^(\d{4})\s+Private Candidates Sta", re.IGNORECASE)
    grade_col_re = re.compile(r"^(A\+|A|B|C|D|E)\s*Passed$", re.IGNORECASE)
    totals: dict[str, float] = {}
    for label, sheet_df in board_sheets.items():
        m = year_sheet_re.match(str(label).strip())
        if not m:
            continue
        if year is not None and int(m.group(1)) != year:
            continue
        if sheet_df is None or sheet_df.empty:
            continue
        cat_col = find_col(sheet_df, "Category")
        if cat_col is None:
            continue
        grand = sheet_df[sheet_df[cat_col].astype(str).str.strip().str.lower() == "grand total"]
        if grand.empty:
            continue
        grade_cols = [c for c in sheet_df.columns if grade_col_re.fullmatch(str(c).strip())]
        for c in grade_cols:
            val = pd.to_numeric(grand[c], errors="coerce").sum()
            if pd.notna(val):
                key = str(c).replace("Passed", "").strip()
                totals[key] = totals.get(key, 0) + val
    totals = {k: v for k, v in totals.items() if v > 0}
    if not totals:
        return pd.DataFrame(columns=["Grade", "Count"])
    return pd.DataFrame({"Grade": list(totals.keys()), "Count": [int(v) for v in totals.values()]})


def extract_grade_distribution(board_sheets: dict, year=None) -> pd.DataFrame:
    df = _pick_sheet(
        board_sheets,
        [
            "Grade Distribution",
            "SSC-10th Grades",
            "Group-wise Distribution",
            "Group-wise",
            "Gender-wise Result",
            "Gender-wise",
        ],
    )
    if df is not None and not df.empty:
        df = _coerce_numeric(filter_df_year(df, year))
        grade_cols = numeric_grade_columns(df)
        if grade_cols:
            fail_col = find_col(df, "Fail", "Failed", "F")
            cols = grade_cols[:]
            if fail_col and fail_col not in cols:
                cols.append(fail_col)
            totals = df[cols].apply(pd.to_numeric, errors="coerce").sum()
            totals = totals[totals > 0]
            if not totals.empty:
                return pd.DataFrame({"Grade": totals.index.astype(str), "Count": totals.values.astype(int)})

    # Fallback for boards whose grade data isn't in a dedicated sheet (e.g. BISE Lahore,
    # where it's embedded in per-year "Candidates Sta" sheets instead).
    return _extract_grade_dist_from_candidates_sta(board_sheets, year)


def extract_stream_summary(demo_df: pd.DataFrame) -> pd.DataFrame:
    if demo_df.empty or "Group" not in demo_df.columns:
        return pd.DataFrame(columns=["Stream", "Appeared", "Passed", "Pass %"])
    df = demo_df.copy()
    df["Stream"] = df["Group"].astype(str).apply(
        lambda g: "Science" if "science" in g.lower() else ("Arts/Humanities" if any(k in g.lower() for k in ("arts", "human", "general")) else g)
    )
    out = df.groupby("Stream", as_index=False)[["Appeared", "Passed"]].sum()
    out = out[~out["Stream"].str.contains("total|grand", case=False, na=False)]
    out["Pass %"] = (100 * out["Passed"] / out["Appeared"].replace(0, pd.NA)).round(1)
    return out.sort_values("Pass %", ascending=False)


def check_data_availability(board_sheets: dict) -> dict:
    return {
        "gender_type": _pick_sheet(board_sheets, ["Gender-wise Result", "Gender-wise", "Group-wise", "SSC-10th Category-wise"]) is not None,
        "districts": _pick_sheet(board_sheets, ["District-wise", "Grade Distribution by District"]) is not None,
        "subjects": _pick_sheet(board_sheets, ["Subject-wise Pass %", "Subject-wise"]) is not None,
        "grades": _pick_sheet(board_sheets, ["Grade Distribution", "SSC-10th Grades", "Group-wise Distribution"]) is not None,
        "groups": _pick_sheet(board_sheets, ["Group-wise", "Group-wise Distribution", "Science Group"]) is not None,
    }


def validate_totals(totals: dict) -> dict:
    appeared = totals.get("appeared", 0)
    passed = totals.get("passed", 0)
    failed = totals.get("failed", 0)
    expected = passed + failed
    diff = abs(appeared - expected) if appeared else 0
    ok = diff <= max(1, 0.01 * appeared) if appeared else True
    return {"ok": ok, "difference": int(diff), "message": "Totals verified" if ok else f"Appeared differs from Passed+Failed by {diff:,}"}


def find_missing_years(board_sheets: dict, board_prefix: str | None = None) -> dict:
    """For the 'All Years' combined view: report which individual years are
    missing from (a) the board's overall totals and (b) the Boys/Girls and
    Regular/Private breakdowns. A year can have full totals but still lack a
    breakdown (e.g. Rawalpindi 2025 has totals but no Regular/Private split),
    so the two are tracked separately. Used to generate an explicit note like
    "2025 data missing" on the combined 'All Years' tree instead of silently
    dropping that year out of the total."""
    years = get_available_years(board_sheets)
    missing_totals, missing_gender, missing_type = [], [], []
    for yr in years:
        totals_yr = extract_board_totals(board_sheets, yr, board_prefix=board_prefix)
        if totals_yr["appeared"] <= 0:
            missing_totals.append(yr)
            continue
        demo_yr = extract_gender_type_rows(board_sheets, yr)
        g_yr = summarize_gender(demo_yr)
        t_yr = summarize_type(demo_yr)
        if t_yr.empty:
            t_yr = extract_type_from_yoy(board_sheets, yr)
        if t_yr.empty:
            t_yr = extract_type_from_pass_percentage(board_sheets, yr)
        if t_yr.empty:
            t_yr = _extract_groupwise_type(board_sheets, yr)
        if g_yr.empty or not split_matches_total(g_yr, totals_yr["appeared"]):
            missing_gender.append(yr)
        if t_yr.empty or not split_matches_total(t_yr, totals_yr["appeared"]):
            missing_type.append(yr)
    return {
        "years_available": years,
        "missing_totals": missing_totals,
        "missing_gender": missing_gender,
        "missing_type": missing_type,
    }


__all__ = [
    "BOARD_NAMES",
    "board_display_name",
    "list_board_prefixes",
    "load_workbook",
    "group_by_board",
    "aggregate_demo_rows",
    "summarize_gender",
    "summarize_type",
    "extract_type_from_yoy",
    "extract_type_from_pass_percentage",
    "extract_gender_type_rows",
    "extract_board_totals",
    "extract_subject_group_data",
    "extract_subject_data",
    "extract_district_data",
    "get_master_summary",
    "get_board_appeared_table",
    "get_available_years",
    "get_all_board_rankings",
    "extract_yearly_trend",
    "extract_grade_distribution",
    "extract_stream_summary",
    "check_data_availability",
    "validate_totals",
    "find_missing_years",
    "split_matches_total",
    "_extract_groupwise_type",
]
