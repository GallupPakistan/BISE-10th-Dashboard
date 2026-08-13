"""Merge KPK + Punjab/Federal SSC master workbooks into one file. Run: python build_pro_master.py"""

from pathlib import Path

import pandas as pd

import data_loader

BASE = Path(__file__).parent
KPK = BASE / "BISE_All_Boards_SSC_Master_2024-2026.xlsx"
OUTPUT = BASE / "BISE_SSC_MASTER_FINAL_2024-2026.xlsx"
SKIP_FRAGMENTS = ("README", "Notes & Data", "Notes and Data")


def should_skip(name: str) -> bool:
    return any(x in name for x in SKIP_FRAGMENTS)


def merge():
    sources = [p for p in [KPK, data_loader._punjab_path()] if p and p.exists()]
    if not sources:
        raise FileNotFoundError("No source workbook found.")

    used: set[str] = set()
    with pd.ExcelWriter(OUTPUT, engine="openpyxl") as writer:
        for src in sources:
            xl = pd.ExcelFile(src)
            for name in xl.sheet_names:
                if should_skip(name):
                    continue
                out_name = name[:31]
                n = 1
                while out_name in used:
                    tag = src.stem[:6]
                    out_name = f"{tag}_{name}"[:31]
                    if out_name in used:
                        out_name = f"{name[:27]}_{n}"[:31]
                        n += 1
                used.add(out_name)
                pd.read_excel(xl, sheet_name=name, header=None).to_excel(
                    writer, sheet_name=out_name, index=False, header=False
                )
    print(f"Created {OUTPUT} ({len(used)} sheets from {len(sources)} files)")


if __name__ == "__main__":
    merge()
