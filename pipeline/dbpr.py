"""Florida DBPR Division of Hotels and Restaurants public records -> data/fl/{licenses,inspections,closures,discipline}.parquet

Sources (www2.myfloridalicense.com/hotels-restaurants/public-records/, public records under Chapter 119 F.S., refreshed weekly):
- extracts/hrfood{1-7}.csv      every food service license by district: business name, location, rank (SEAT seating, NOST non-seating,
                                MFDV mobile, CATR catering...), status (20 Current, 45 Delinquent, 46 Voluntary Relinquishment), seats, risk.
- extracts/{1-7}fdinspi.csv     inspections since July 1 (this fiscal year), one row per visit.
- hr/inspections/fdinspi_YYZZ.xlsx  the statewide yearly files (converted to data/fl/insp_YYZZ.parquet by convert_xlsx.py).
- hr/inspections/documents/EOS_Weekly_Extract_<date>.xlsx  emergency closures, with the reason as text and the reopening time.
- extracts/rdarMMYY.csv         Restaurant Disciplinary Activity Reports: final orders and fines.

Florida gives no grade. DBPR: "Because conditions can change rapidly, establishments are not graded or rated." So we keep each visit's
official disposition verbatim and DBPR's own result group for it (Met Inspection Standards / Follow-Up Inspection Required / Facility
Temporarily Closed, from www2.myfloridalicense.com/hotels-restaurants/inspections/). Nothing here computes a score.

The inspection files hold counts per violation category (01-58) and High Priority / Intermediate / Basic totals, not the citation text.
Category 35 combines pests with "outer openings protected", so it is never read as proof of pests; only the closure file names the pest.
Categories 45-49 are fire items "for reporting purposes only".
"""
import os, re, glob, json, datetime as dt
import numpy as np, pandas as pd
from common import FL, RAW, norm_name

D = os.path.join(RAW, "dbpr")
FETCHED = dt.date.fromtimestamp(os.path.getmtime(f"{D}/1fdinspi.csv"))
# publication lag: DBPR refreshes weekly; keep a week's margin and drop anything after it
THROUGH = FETCHED - dt.timedelta(days=7)

GROUP = {  # DBPR's own result groups for each disposition
    "Inspection Completed - No Further Action": "met", "Call Back - Complied": "met", "Admin. Complaint Callback Complied": "met",
    "Emergency Order Callback Complied": "met",
    "Warning Issued": "followup", "Call Back - Extension given, pending": "followup", "Call Back - Admin. complaint recommended": "followup",
    "Administrative complaint recommended": "followup", "Admin. Complaint Callback Not Complied": "followup",
    "Administrative Complaint Time Extension": "followup", "Emergency Order Callback Time Extension": "followup",
    "Emergency order recommended": "closed", "Administrative determination recommended": "closed", "Emergency Order Callback Not Complied": "closed",
}
GROUP_LABEL = {"met": "Met Inspection Standards", "followup": "Follow-Up Inspection Required", "closed": "Facility Temporarily Closed"}


def fix_enc(s):
    """DBPR's files are UTF-8, but a few dozen apostrophes arrive as '¿' ("ADRIANO¿S"); curly quotes become plain."""
    if not isinstance(s, str):
        return s
    s = re.sub(r"(?<=[A-Za-z])\s?¿\s?(?=[A-Za-z])", "'", s).replace("¿", "'")
    s = s.replace("’", "'").replace("‘", "'").replace("´", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s).strip()


def lic_num(lic):
    """'SEA2300159' -> '2300159' (the inspection files carry the bare number)."""
    m = re.match(r"^[A-Z]{3}(\d+)$", lic or "")
    return m.group(1) if m else (lic or "")


def load_licenses():
    cols = {"License Type Code": "ltype", "Licensee Name": "legal", "Rank Code": "rank", "Business Name": "bname", "Location Street Address": "addr",
            "Location Address Line 2": "addr2", "Location Address Line 3": "addr3", "Location City": "city_raw", "Location Zip Code": "zip9",
            "Location County": "county", "Location County Code": "county_code", "Secondary Phone Number": "phone", "Primary Phone Number": "phone_mail",
            "District": "district", "License Number": "lic", "Primary Status Code": "status", "Secondary Status Code": "status2",
            "License Expiry Date": "expires", "Last Inspection Date": "last_insp", "Number of Seats or Rental Units": "seats",
            "Base Risk Level": "risk", "Location State Code": "state"}
    L = pd.concat([pd.read_csv(f, dtype=str, encoding="utf-8", keep_default_na=False) for f in sorted(glob.glob(f"{D}/hrfood*.csv"))],
                  ignore_index=True)[list(cols)].rename(columns=cols)
    for c in ("legal", "bname", "addr", "addr2", "addr3", "city_raw"):
        L[c] = L[c].map(fix_enc)
    L["num"] = L.lic.map(lic_num)
    L["zip"] = L.zip9.str[:5]
    L["seats"] = pd.to_numeric(L.seats, errors="coerce").fillna(0).astype(int)
    L["active"] = L.status.eq("20")
    L = L.drop_duplicates(["lic"], keep="first")
    return L


# the yearly workbooks before FY 2025-26 use database column names
ALIAS = {"PROFESSION": "License Type Code", "LICENSE_NO": "License Number", "DBA_NAME": "Business (DBA-Does Business As) Name",
         "LOC_ADDRESS": "Location Address", "LOC_CITY": "Location City", "LOC_ZIP": "Location Zip Code", "CNTY_DESC": "County Name",
         "INSP_NO": "Inspection Number", "VISIT_NO": "Visit Number", "INSPCLASS": "Inspection Class", "INSPTYPE": "Inspection Type",
         "DISPOSITION": "Inspection Disposition", "INSP_DATE": "Inspection Date", "HIGH_VIOL": "Number of High Priority Violations",
         "INTERMED_VIOL": "Number of Intermediate Violations", "BASIC_VIOL": "Number of Basic Violations", "VIOLATIONS": "Number of Total Violations",
         "INSP_VST_ID": "Inspection Visit ID", "LIC_ID": "License ID"}


def _insp_frame(df):
    df = df.rename(columns=lambda c: re.sub(r"\s+", " ", str(c)).strip())
    df = df.rename(columns=lambda c: ALIAS.get(c, re.sub(r"^V_(\d\d)$", r"Violation \1", c)))
    if "Inspection Class" in df.columns:
        df = df[df["Inspection Class"].fillna("Food").astype(str).str.strip().str.lower().eq("food")]
    out = pd.DataFrame({
        "ltype": df["License Type Code"].astype(str).str.strip(), "num": df["License Number"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True),
        "dba": df["Business (DBA-Does Business As) Name"].map(fix_enc), "addr": df["Location Address"].map(fix_enc),
        "city": df["Location City"], "zip": df["Location Zip Code"].astype(str).str[:5], "county": df["County Name"],
        "insp_no": df["Inspection Number"].astype(str).str.replace(r"\.0$", "", regex=True), "visit": pd.to_numeric(df["Visit Number"], errors="coerce"),
        "itype": df["Inspection Type"], "disp": df["Inspection Disposition"].map(lambda s: re.sub(r"\s+", " ", s).strip() if isinstance(s, str) else s),
        "date": pd.to_datetime(df["Inspection Date"], errors="coerce", format="mixed"),
        "hp": pd.to_numeric(df["Number of High Priority Violations"], errors="coerce"),
        "im": pd.to_numeric(df["Number of Intermediate Violations"], errors="coerce"),
        "bs": pd.to_numeric(df["Number of Basic Violations"], errors="coerce"),
        "tot": pd.to_numeric(df["Number of Total Violations"], errors="coerce"),
    })
    vcols = [c for c in df.columns if re.fullmatch(r"Violation \d\d", c)]
    v = df[vcols].apply(pd.to_numeric, errors="coerce").fillna(0).astype(int).to_numpy()
    # compact per-category counts, e.g. "3:2,22:1" (category 3 cited twice, category 22 once); reporting-only fire items 45-49 left out
    cats = [int(c[-2:]) for c in vcols]
    out["cats"] = [",".join(f"{c}:{n}" for c, n in zip(cats, row) if n and not 45 <= c <= 49) for row in v]
    out["vid"] = df.get("Inspection Visit ID", pd.Series([None] * len(df))).astype(str)
    return out


def load_inspections():
    parts = []
    for f in sorted(glob.glob(f"{FL}/insp_*.parquet")):
        parts.append(_insp_frame(pd.read_parquet(f)).assign(src=os.path.basename(f)[5:9]))
    for f in sorted(glob.glob(f"{D}/[1-7]fdinspi.csv")):
        parts.append(_insp_frame(pd.read_csv(f, dtype=str, encoding="utf-8", encoding_errors="replace", keep_default_na=False)).assign(src="cur"))
    I = pd.concat(parts, ignore_index=True)
    I = I[I.date.notna() & (I.date <= pd.Timestamp(THROUGH))]
    # the yearly file and this year's extract can overlap at the July boundary: one row per visit
    I = I.drop_duplicates(["ltype", "num", "insp_no", "visit", "date"], keep="last")
    I["group"] = I.disp.map(GROUP)
    return I.reset_index(drop=True)


def load_closures():
    rows = []
    for f in sorted(glob.glob(f"{D}/eos/EOS_Weekly_Extract_*.xlsx")):
        e = pd.read_excel(f, dtype=str)
        e.columns = [re.sub(r"\s+", " ", c).strip() for c in e.columns]
        for _, r in e.iterrows():
            rows.append({"num": str(r.get("License Number") or "").strip().replace(".0", ""), "name": fix_enc(r.get("Business Name")),
                         "addr": fix_enc(r.get("Business Address")), "city": r.get("Business City"),
                         "date": pd.to_datetime(r.get("Date"), errors="coerce"), "reopened": pd.to_datetime(r.get("Date of order to vacate"), errors="coerce"),
                         "reason": fix_enc(r.get("Conditions for Closure")), "approved": r.get("Approved for Closure"), "file": os.path.basename(f)})
    C = pd.DataFrame(rows)
    C = C[C.date.notna() & (C.date <= pd.Timestamp(THROUGH))]
    return C.drop_duplicates(["num", "date", "reason"]).reset_index(drop=True)


def load_discipline():
    cols = ["case", "lic", "name", "addr", "addr2", "city", "state", "zip", "n_viol", "fine", "order_date", "viol_date"]
    parts = []
    for f in sorted(glob.glob(f"{D}/rdar/rdar*.csv")):
        d = pd.read_csv(f, dtype=str, header=None, names=cols, encoding="utf-8", encoding_errors="replace", keep_default_na=False)
        parts.append(d)
    R = pd.concat(parts, ignore_index=True)
    R["fine"] = pd.to_numeric(R.fine, errors="coerce")
    R["order_date"] = pd.to_datetime(R.order_date, errors="coerce", format="%m/%d/%Y")
    R["viol_date"] = pd.to_datetime(R.viol_date, errors="coerce", format="%m/%d/%Y")
    R["num"] = R.lic.map(lic_num)
    R = R[R.order_date.notna() & (R.order_date <= pd.Timestamp(THROUGH))]
    return R.drop_duplicates(["case"]).reset_index(drop=True)


if __name__ == "__main__":
    L = load_licenses()
    L.to_parquet(f"{FL}/licenses.parquet")
    cur = L[L.active & L["rank"].isin(["SEAT", "NOST"])]
    print("licenses:", len(L), "| current seating + non-seating:", len(cur), "| by rank (current):", L[L.active]["rank"].value_counts().to_dict())
    I = load_inspections()
    I.to_parquet(f"{FL}/inspections.parquet")
    print("inspection visits:", len(I), I.date.min().date(), "to", I.date.max().date(), "| through", THROUGH, "| by file:", I.src.value_counts().to_dict())
    print("dispositions without a DBPR group:", I[I.group.isna()].disp.value_counts().to_dict())
    C = load_closures()
    C.to_parquet(f"{FL}/closures.parquet")
    print("emergency closures:", len(C), C.date.min().date() if len(C) else None, "to", C.date.max().date() if len(C) else None)
    R = load_discipline()
    R.to_parquet(f"{FL}/discipline.parquet")
    print("final orders:", len(R), "| fines $", int(R.fine.sum()))
    json.dump({"fetched": str(FETCHED), "through": str(THROUGH)}, open(f"{FL}/dbpr_meta.json", "w"))
