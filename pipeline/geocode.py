"""Place DBPR food licenses on the map -> data/fl/lic_geo.parquet (lic, lat, lon, geo)

DBPR's license file has street addresses but no coordinates. In order:
1. "ap"      Overture address points (state and county address files, via Overture's addresses theme): same house number, same street
             (directions, type and ordinals normalized) and same zip; then the same number and street core when that is unique in the zip.
2. "census"  the US Census Bureau's public batch geocoder for the rest (exact or non-exact match, in Florida, agreeing on zip or town).
             Answers are cached in data/fl/geocode_census.json, so a rebuild only asks about new addresses.
florida.py may still move a license onto its matched map listing when the two agree on the address.
"""
import csv, io, json, os, re, time
import numpy as np, pandas as pd, duckdb, requests
from common import FL
from addr import street_key, core_key

L = pd.read_parquet(f"{FL}/licenses.parquet")
L = L[L["rank"].isin(["SEAT", "NOST", "CATR", "PARK"]) & L.status.isin(["20", "45"])].copy()
L[["anum", "ast"]] = [list(street_key(a)) for a in L.addr]
L[["anum2", "acore"]] = [list(core_key(a)) for a in L.addr]
print("licenses to place:", len(L), "| with a house number:", int(L.anum.notna().sum()))

con = duckdb.connect()
con.register("want", L[L.anum.notna()][["anum", "zip"]].drop_duplicates())
P = con.execute(f"""SELECT a.number, a.street, a.postcode, a.muni, a.lat, a.lon FROM '{FL}/addresses_fl.parquet' a
                    JOIN want w ON a.number = w.anum AND a.postcode = w.zip""").df()
print("candidate address points:", len(P))
P["st"] = [street_key(f"{n} {s}")[1] for n, s in zip(P.number, P.street)]
P["core"] = [core_key(f"{n} {s}")[1] for n, s in zip(P.number, P.street)]
full = P.groupby(["number", "st", "postcode"])[["lat", "lon"]].median()
spread = P.groupby(["number", "st", "postcode"]).lat.agg(lambda x: x.max() - x.min())
full = full[spread < 0.01]   # one address, one place (a key spread over a kilometre is ambiguous)
cores = P.groupby(["number", "core", "postcode"]).agg(lat=("lat", "median"), lon=("lon", "median"), n_st=("st", "nunique"))
cores = cores[cores.n_st == 1]

out = {}
for lic, n, st, n2, co, z in zip(L.lic, L.anum, L.ast, L.anum2, L.acore, L.zip):
    if not n:
        continue
    h = full.index.get_indexer([(n, st, z)])[0] if st else -1
    if h >= 0:
        out[lic] = (full.lat.iat[h], full.lon.iat[h], "ap")
        continue
    h = cores.index.get_indexer([(n2, co, z)])[0] if co else -1
    if h >= 0:
        out[lic] = (cores.lat.iat[h], cores.lon.iat[h], "ap-core")
print("placed on address points:", len(out), f"({len(out) / len(L):.0%})")

# ---------------------------------------------------------------- US Census geocoder for the rest
cache_path = f"{FL}/geocode_census.json"
cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
misses = set(cache.pop("_misses", []))


def clean_addr(a):
    a = re.sub(r"\s+", " ", a or "").strip()
    return re.sub(r"\s(?:STE|SUITE|UNIT|BLDG|#)\b.*$", "", a, flags=re.I)


def qkey(a, c, z):
    return f"{a}, {c}, FL {z}"


todo = []
for lic, a, c, z in zip(L.lic, L.addr, L.city_raw, L.zip):
    if lic in out or not isinstance(a, str) or not a.strip():
        continue
    t = (clean_addr(a), (c or "").strip().title(), z or "")
    if qkey(*t) not in cache and qkey(*t) not in misses:
        todo.append(t)
todo = list(dict.fromkeys(todo))
print("to ask the Census geocoder:", len(todo))
URL = "https://geocoding.geo.census.gov/geocoder/locations/addressbatch"
UA = {"User-Agent": "FloridaEatsResearch/1.0 (work-with-nick@gmail.com)"}
for start in range(0, len(todo), 2500):
    chunk = todo[start:start + 2500]
    buf = io.StringIO()
    w = csv.writer(buf)
    for i, (a, c, z) in enumerate(chunk):
        w.writerow([i, a, c, "FL", z])
    for attempt in range(3):
        try:
            r = requests.post(URL, files={"addressFile": ("a.csv", buf.getvalue(), "text/csv")},
                              data={"benchmark": "Public_AR_Current"}, headers=UA, timeout=900)
            r.raise_for_status()
            break
        except Exception as e:
            print("retry", attempt, e, flush=True); time.sleep(20)
    else:
        continue
    got = 0
    for row in csv.reader(io.StringIO(r.text)):
        if len(row) < 3 or not row[0].isdigit():
            continue
        i = int(row[0]); q = qkey(*chunk[i])
        a_, c_, z_ = chunk[i]
        mt = row[4].upper() if len(row) > 4 else ""
        agrees = (z_ and mt.rstrip().endswith(z_)) or (c_ and f", {c_.upper()}, FL" in mt)
        if row[2] == "Match" and len(row) >= 6 and row[3] in ("Exact", "Non_Exact") and ", FL," in row[4] and agrees:
            lon, lat = map(float, row[5].split(","))
            cache[q] = {"lat": round(lat, 6), "lon": round(lon, 6), "matched": row[4], "exact": row[3] == "Exact"}
            got += 1
        else:
            misses.add(q)
    print(f"census batch {start // 2500 + 1}: {got}/{len(chunk)} matched", flush=True)
    cache["_misses"] = sorted(misses)
    json.dump(cache, open(cache_path, "w"), indent=0, sort_keys=True)
    cache.pop("_misses")
    time.sleep(5)
cache["_misses"] = sorted(misses)
json.dump(cache, open(cache_path, "w"), indent=0, sort_keys=True)
cache.pop("_misses")

for lic, a, c, z in zip(L.lic, L.addr, L.city_raw, L.zip):
    if lic in out or not isinstance(a, str):
        continue
    h = cache.get(qkey(clean_addr(a), (c or "").strip().title(), z or ""))
    if h:
        out[lic] = (h["lat"], h["lon"], "census" if h["exact"] else "census-approx")
# 3. "ov-name": a license neither geocoder could place, matched by name to an Overture place (any category) in the same zip or town:
# small-town addresses ("202 Camellia St, Everglades City") are often missing from both address sources. The house numbers must agree
# when both have one: by name alone this put Flagler Fish Company on an old listing a block away (then on the tea shop next to it),
# a Burger King on another Burger King, and stadium stands on their brands' other locations.
from common import norm_name, canon_city, _stems, GENERIC
from addr import street_nums
from rapidfuzz import fuzz
left = L[~L.lic.isin(out)].copy()
if len(left):
    OV = duckdb.connect().execute(f"""SELECT name, street, city, zip, lat, lon FROM '{FL}/overture_fl_bbox.parquet'
                                      WHERE region = 'FL' AND name IS NOT NULL""").df()
    OV["k"] = OV.name.map(norm_name); OV["z5"] = OV.zip.fillna("").astype(str).str[:5]; OV["town"] = OV.city.map(lambda c: (canon_city(c) or "").lower())
    OV["num"] = [street_key(s_)[0] if isinstance(s_, str) else None for s_ in OV.street]
    by_zip = {z: g for z, g in OV.groupby("z5")}
    by_town = {t: g for t, g in OV.groupby("town")}
    n3, refused = 0, 0
    for lic, nm, z, c, a in zip(left.lic, left.bname, left.zip, left.city_raw, left.addr):
        k = norm_name(nm)
        if not k or len(k) < 4:
            continue
        cands = pd.concat([g for g in (by_zip.get(z), by_town.get((canon_city(c) or "").lower())) if g is not None]).drop_duplicates()
        if not len(cands):
            continue
        nums = street_nums(a) if isinstance(a, str) else set()
        words = _stems(k) - GENERIC
        ok = []
        for i, (x, num) in enumerate(zip(cands.k, cands.num)):
            if not x or fuzz.ratio(k, x) < 90:
                continue
            if nums and num:
                if num in nums:
                    ok.append(i)
                else:
                    refused += 1
            elif words and words == _stems(x) - GENERIC and fuzz.ratio(k, x) >= 95:   # one side has no number: the same name, word for word
                ok.append(i)
        if ok:
            hits = cands.iloc[ok]
            if (hits.lat.max() - hits.lat.min()) < 0.01:   # one place, not a chain's several stores in one zip
                out[lic] = (float(hits.lat.iat[0]), float(hits.lon.iat[0]), "ov-name"); n3 += 1
    print("placed by name on an Overture place in the same zip or town:", n3, "of", len(left), "| refused (house numbers differ):", refused)

G = pd.DataFrame([(k, *v) for k, v in out.items()], columns=["lic", "lat", "lon", "geo"])
G.to_parquet(f"{FL}/lic_geo.parquet")
cur = L[L.status.eq("20") & L["rank"].isin(["SEAT", "NOST"])]
print("placed:", G.geo.value_counts().to_dict(), "| current SEAT+NOST placed:", f"{cur.lic.isin(G.lic).mean():.1%}",
      "| unplaced by county:", cur[~cur.lic.isin(G.lic)].county.value_counts().head(8).to_dict())
