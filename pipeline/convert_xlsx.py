"""Convert DBPR's statewide yearly inspection workbooks (fdinspi_YYZZ.xlsx, ~50 MB each) to parquet once -> data/fl/insp_YYZZ.parquet.
openpyxl in read-only mode streams the rows; every column is kept as text, exactly as published."""
import os, sys, time
import pandas as pd
from openpyxl import load_workbook
RAW = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "dbpr")
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "fl")
os.makedirs(OUT, exist_ok=True)
for fy in sys.argv[1:] or ["2526", "2425", "2324"]:
    dst = f"{OUT}/insp_{fy}.parquet"
    if os.path.exists(dst):
        continue
    t = time.time()
    wb = load_workbook(f"{RAW}/fdinspi_{fy}.xlsx", read_only=True)
    ws = wb.worksheets[0]
    it = ws.iter_rows(values_only=True)
    head = [str(h).strip() if h is not None else f"c{i}" for i, h in enumerate(next(it))]
    rows = [[None if v is None else str(v) for v in r] for r in it]
    df = pd.DataFrame(rows, columns=head)
    df.to_parquet(dst)
    print(fy, len(df), "rows", len(head), "cols", round(time.time() - t), "s", head[:16], flush=True)
