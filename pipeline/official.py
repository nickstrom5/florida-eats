"""Florida's official food service licenses (DBPR Hotels and Restaurants) as one matching table.

load() returns one row per license: jur ("dbpr"), lic ("SEA2300159"), num ("2300159"), rank, kind, name (the license's Business Name,
cleaned), keys (name keys for matching: business name, inspection DBA names, and the licensee name, which is never shown), addr, city,
zip, street (address key), lat, lon (geocode.py), county, active (status 20 Current), seats, risk, last_insp, expires.

Ranks kept: SEAT (seating), NOST (non-seating), CATR (catering), PARK (theme park food carts). Mobile units, hot dog carts, vending and
temporary events are left out: their address is a commissary or the owner's, not a place to eat.
"""
import os, re, json
import numpy as np, pandas as pd
from rapidfuzz import fuzz
from common import FL, norm_name, canon_city, _stems, GENERIC, town_words, kind_conflict
from addr import street_key

KIND = {"SEAT": "restaurant", "NOST": "nonseating", "CATR": "catering", "PARK": "park"}
COUNTY_FIX = {"Dade": "Miami-Dade", "Desoto": "DeSoto", "St Johns": "St. Johns", "St Lucie": "St. Lucie", "Saint Johns": "St. Johns",
              "Saint Lucie": "St. Lucie"}
REGIONS = {
    "South Florida": ["Miami-Dade", "Broward", "Palm Beach"],
    "Keys": ["Monroe"],
    "Space & Treasure Coast": ["Brevard", "Indian River", "St. Lucie", "Martin", "Okeechobee"],
    "Central": ["Orange", "Seminole", "Osceola", "Lake", "Volusia", "Polk", "Sumter", "Marion", "Highlands", "Hardee"],
    "Tampa Bay": ["Hillsborough", "Pinellas", "Pasco", "Hernando", "Citrus", "Manatee"],
    "Southwest": ["Sarasota", "Charlotte", "Lee", "Collier", "DeSoto", "Hendry", "Glades"],
    "Northeast": ["Duval", "St. Johns", "Clay", "Nassau", "Baker", "Flagler", "Putnam", "Alachua", "Bradford", "Union", "Columbia",
                  "Suwannee", "Hamilton", "Gilchrist", "Levy", "Dixie", "Lafayette"],
    "Panhandle": ["Escambia", "Santa Rosa", "Okaloosa", "Walton", "Holmes", "Washington", "Bay", "Jackson", "Calhoun", "Gulf", "Liberty",
                  "Franklin", "Gadsden", "Leon", "Wakulla", "Jefferson", "Madison", "Taylor"],
}
REGION_OF = {c: r for r, cs in REGIONS.items() for c in cs}
assert len(REGION_OF) == 67, len(REGION_OF)


def county_name(c):
    """DBPR's county ('Dade', 'St Johns') -> the plain county name used everywhere here ('Miami-Dade', 'St. Johns')."""
    if not isinstance(c, str) or not c.strip():
        return None
    c = c.strip().title().replace(" County", "")
    return COUNTY_FIX.get(c, c)


def _names(*vals):
    out = []
    for v in vals:
        if not isinstance(v, str):
            continue
        for part in re.split(r"\s*/\s*|\s+\bd/?b/?a\b\.?\s+|\s+\bAKA\b\s+", v, flags=re.I):
            k = norm_name(re.sub(r"\b(?:LLC|L L C|INC|CORP|CORPORATION|LTD|CO|PA|LLP|LP|PLLC)\b\.?", "", part, flags=re.I))
            if k and k not in out:
                out.append(k)
    return out


def same_business(a, b):
    """Two names for one business: one's words inside the other's ("SUBWAY" / "SUBWAY 1234"), nearly the same spelling, or a distinctive
    word in common that isn't a town ("FLACO'S CUBAN AND LATIN FOOD" / "FLACOS CUBAN BAKERY"). "LA FIESTA MEXICAN RESTAURANT" and
    "RIO BRAVO" are two."""
    # a note in parentheses isn't the name ("Thai Orchid restaurant (beach-kernan)", "(Downtown WPB)"), unless it names the business
    # it used to be ("FAT CAT Pizza + Dogs (Formerly Original II)")
    unnote = lambda x: re.sub(r"\s*\((?!\s*(?:formerly|fka|f/k/a|was)\b)[^)]*\)", " ", x if isinstance(x, str) else "", flags=re.I)
    a, b = norm_name(unnote(a)), norm_name(unnote(b))
    if not a or not b:
        return True
    if kind_conflict(a, b) and a != b:   # each says what it serves, and they disagree: FLAGLER FISH COMPANY isn't FLAGLER TEA COMPANY
        return False
    fa, fb = a.replace(" ", ""), b.replace(" ", "")
    if fa in fb or fb in fa or fuzz.ratio(fa, fb) >= 85 or fuzz.token_set_ratio(a, b) >= 85:
        return True
    # a misspelling inside a longer name ("LITTLE CEASARS PIZZA", "CHURRULAND" / "CHURROLAND MIAMI"), or one chain ("DQ GRILL & CHILL")
    if min(len(fa), len(fb)) >= 6 and fuzz.partial_ratio(fa, fb) >= 88:
        return True
    from brands import brand_of
    ba = brand_of(a)
    if ba and ba == brand_of(b):
        return True
    wa, wb = (_stems(a) - GENERIC) - town_words(), (_stems(b) - GENERIC) - town_words()
    if wa & wb:
        return True
    return any(len(x) >= 5 and len(y) >= 5 and fuzz.ratio(x, y) >= 85 for x in wa for y in wb)   # "ATLACATL" / "ATLACAT"


def current_era(g, name):
    """A license's inspections from its current business only: the visits after the last one under a name that isn't this business's.
    When a restaurant changes hands the license number often stays, so earlier visits (and their trade names) belong to the previous
    business. g is sorted oldest first; returns the suffix (empty when even the latest visit was under another business's name)."""
    ok = [same_business(d, name) if isinstance(d, str) else True for d in g.dba]
    start = 0
    for i, v in enumerate(ok):
        if not v:
            start = i + 1
    return g.iloc[start:]


def load(with_inactive=True):
    L = pd.read_parquet(f"{FL}/licenses.parquet")
    L = L[L["rank"].isin(list(KIND)) & L.status.isin(["20", "45"] if with_inactive else ["20"])].copy()
    geo = pd.read_parquet(f"{FL}/lic_geo.parquet") if os.path.exists(f"{FL}/lic_geo.parquet") else pd.DataFrame(columns=["lic", "lat", "lon", "geo"])
    L = L.merge(geo, on="lic", how="left")
    I = pd.read_parquet(f"{FL}/inspections.parquet", columns=["ltype", "num", "dba", "date", "insp_no", "visit"]) \
        if os.path.exists(f"{FL}/inspections.parquet") else None
    dbas = {}
    if I is not None:
        # match names: only the trade names of the license's current business (a former business's name would match a stale listing)
        I["insp_i"] = pd.to_numeric(I.insp_no, errors="coerce")
        I = I.sort_values(["ltype", "num", "date", "insp_i", "visit"])
        cur = {(r.ltype, r.num): r.bname for r in L.itertuples()}
        for (lt, n), g in I.groupby(["ltype", "num"]):
            if (lt, n) in cur:
                dbas[(lt, n)] = list(dict.fromkeys(current_era(g, cur[(lt, n)]).dba.dropna()))
    rows = []
    for r in L.itertuples():
        other = dbas.get((r.ltype, r.num), [])
        rows.append({"jur": "dbpr", "lic": r.lic, "num": r.num, "ltype": r.ltype, "rank": r.rank, "kind": KIND[r.rank], "name": r.bname or None,
                     "dbas": other, "keys": _names(r.bname, *other, r.legal), "addr": r.addr, "city": canon_city(r.city_raw), "zip": r.zip,
                     "street": street_key(r.addr)[1], "lat": r.lat, "lon": r.lon, "geo": r.geo, "county": county_name(r.county),
                     "active": r.status == "20", "status": r.status, "seats": r.seats, "risk": r.risk, "last_insp": r.last_insp,
                     "expires": r.expires, "phone": r.phone or None, "legal": r.legal})
    F = pd.DataFrame(rows)
    F["region"] = F.county.map(REGION_OF)
    F["biz"] = np.arange(len(F))
    return F


if __name__ == "__main__":
    F = load()
    print(len(F), F.kind.value_counts().to_dict(), "| placed:", f"{F.lat.notna().mean():.1%}", "| regions:", F[F.active].region.value_counts().to_dict())
    print("counties without a region:", F[F.region.isna()].county.value_counts().head().to_dict())
