# BISE SSC 10th Class Dashboard (2024-2026)

## Setup
1. Open this folder in VS Code.
2. Create a virtual env (optional) and install dependencies:
   pip install -r requirements.txt
3. Keep `BISE_All_Boards_SSC_Master_2024-2026.xlsx` in the same folder as `app.py`.
4. Run:
   streamlit run app.py

## What's inside
- `app.py` — the dashboard (dark navy/gold theme, sidebar dropdowns for Board + Year)
- `data_loader.py` — auto-parses all 37 sheets in the workbook into clean tables, grouped by board
- Overview page: KPIs, appeared-vs-passed bar chart, board share pie chart, 3-year pass% trend, pass% ranking
- Per-board pages: dropdown to pick any table for that board (Summary, Group-wise, Gender-wise,
  Subject-wise, District-wise, Grades, Trend, etc.) — each renders matching pie/bar/line charts
  (grade-distribution pies, gender/category pies, group pies, district/subject bar charts) plus the raw table
