"""How often is a map listing a real, licensed restaurant? Florida licenses every restaurant, so this is measured statewide
-> data/fl/calibration.json (web grouping) and calibration_app.json (app grouping, no Google data)

Every Overture eating/drinking listing in Florida is checked against DBPR's current food service licenses (seating, non-seating,
catering, theme park carts), county by county. A match is the same business name nearby, or the same street address with a distinctive
name word in common (listings_util.official_match).
Caveat: coffee shops, bakeries, juice bars and grocery or convenience-store counters are often licensed by FDACS (Agriculture), not DBPR,
so for those kinds a missing DBPR match doesn't mean the place isn't real; rates are reported for restaurants/bars and for café-type
listings separately.
The other direction ("coverage"): the share of current seating and non-seating licenses that some open, cleaned listing matches.
"""
import json
import numpy as np, pandas as pd, shapely
from shapely.geometry import shape
from common import FL
from listings_util import official_match
import official

o = pd.read_pickle(f"{FL}/stage1.pkl")
F = official.load()
_SHAPES = {n.replace(" County", ""): shape(g) for n, g in json.load(open(f"{FL}/fl_counties_detail.geojson")).items()}
CTY = {n: g.buffer(0.0005) for n, g in _SHAPES.items()}
# a second, wider pass for waterfront points just off the outline (Keys Fisheries' dock in Marathon)
CTY_WIDE = {n: g.buffer(0.01) for n, g in _SHAPES.items()}
for g in list(CTY.values()) + list(CTY_WIDE.values()):
    shapely.prepare(g)


def county_of(lat, lon):
    out = np.full(len(lat), None, dtype=object)
    lat = np.asarray(lat, float); lon = np.asarray(lon, float)
    ok = ~np.isnan(lat)
    for shapes in (CTY, CTY_WIDE):
        for n, g in shapes.items():
            hit = ok & (out == None) & shapely.contains_xy(g, lon, lat)   # noqa: E711
            out[hit] = official.county_name(n)
    return out


o["county"] = county_of(o.lat, o.lon)
o["region"] = o.county.map(official.REGION_OF)
pc = county_of(F.lat, F.lon)
F["county"] = [p if p is not None else c for p, c in zip(pc, F.county)]
F["region"] = F.county.map(official.REGION_OF)
o.to_pickle(f"{FL}/stage1.pkl")
F.to_pickle(f"{FL}/official.pkl")
base = ~o.j_junk & ~o.j_outside
print("listings with a county:", int(o.county.notna().sum()), "of", len(o), "| licenses:", len(F), "current", int(F.active.sum()))

CAFE = {"coffee_shop", "cafe", "smoothie_juice_bar"}


def groups(L, app=False):
    s = L.src.fillna("none")
    conf = L.confidence.fillna(0)
    if app:
        return np.select([L.ov_closed | L.j_closedname, (s == "meta") & (conf >= 0.95), (s == "meta") & (conf >= 0.9) & (L.n_web.fillna(0) > 0),
                          (s == "meta") & (conf >= 0.9), s.isin(["AllThePlaces", "DAC"]), (s == "BrightQuery") & (conf >= 0.95),
                          (s == "Microsoft") & (conf >= 0.95), s == "meta"],
                         ["closed per Overture/name", "meta_high", "meta_mid_web", "meta_mid_noweb", "brand_feed", "bq_high", "ms_high",
                          "meta_low"], "other_sources")
    return np.select([L.closed21, L.ov_closed, (s == "meta") & L.in21, s == "meta", s.isin(["AllThePlaces", "DAC"]) & L.in21,
                      s.isin(["AllThePlaces", "DAC"]), L.in21, s == "Foursquare", s == "BrightQuery", s == "Microsoft"],
                     ["Google 2021 says closed", "Overture says closed", "Meta + open in Google 2021", "Meta only",
                      "brand feed + Google 2021", "brand feed only", "Foursquare/BrightQuery/Microsoft + Google 2021",
                      "Foursquare only", "BrightQuery only", "Microsoft only"], "other")


# match county by county (a street address like "100 Main St" exists in dozens of towns)
L = o[base & o.county.notna()].reset_index(drop=True)
L["hit"] = False; L["hit_cur"] = False; L["off"] = -1
for cty, sel in L.groupby("county").groups.items():
    R = F[F.county == cty]
    if not len(R):
        continue
    m = official_match(L.loc[sel].reset_index(drop=True), R.reset_index(drop=True))
    for i, j in m.items():
        L.at[sel[i], "off"] = R.index[j]
L["hit"] = L.off >= 0
L["hit_cur"] = L.hit & L.off.map(lambda j: bool(F.active.iat[j]) if j >= 0 else False)
L["kind"] = np.where(L.cat.isin(CAFE), "cafe-type", "restaurant/bar")
o = o.drop(columns=["off"], errors="ignore").merge(L[["id", "off"]], on="id", how="left")   # a re-run replaces the last run's matches
o["off"] = o.off.fillna(-1).astype(int)
o.to_pickle(f"{FL}/stage1.pkl")

res, app = {}, {}
for mode, store in ((False, res), (True, app)):
    L["grp"] = groups(L, mode)
    for scope, sub in [("statewide", L)] + [(r, L[L.region == r]) for r in official.REGIONS]:
        t = sub.groupby(["grp", "kind"]).agg(n=("id", "size"), current=("hit_cur", "mean"), any_license=("hit", "mean"))
        store.setdefault(scope, {})["groups"] = {f"{g}|{k}": {"n": int(r.n), "current": round(float(r.current), 3), "any": round(float(r.any_license), 3)}
                                                  for (g, k), r in t.iterrows()}
        if scope == "statewide":
            print(f"\n== {scope} ({'app' if mode else 'web'} grouping), {len(sub)} listings")
            print(t.assign(current=(t.current * 100).round(1), any_license=(t.any_license * 100).round(1)).to_string())

# coverage: current seating / non-seating licenses matched by an open, cleaned listing, by region and county
keepish = ~(L.ov_closed | L.j_closedname | L.closed21)
got = set(L.off[keepish & L.hit])
cur = F[F.active & F.kind.isin(["restaurant", "nonseating"])].copy()
cur["found"] = cur.index.isin(got)
cov_r = cur.groupby("region").agg(licenses=("lic", "size"), found=("found", "mean"), placed=("lat", lambda x: x.notna().mean()))
cov_c = cur.groupby("county").agg(licenses=("lic", "size"), found=("found", "mean"), placed=("lat", lambda x: x.notna().mean()))
lst = L[keepish].groupby("county").agg(listings=("id", "size"), matched=("hit_cur", "mean"))
cov_c = cov_c.join(lst, how="left")
print("\n== coverage by region\n" + cov_r.round(3).to_string())
print(f"\nstatewide: {cur.found.mean():.1%} of {len(cur)} current seating/non-seating licenses matched by a listing; placed {cur.lat.notna().mean():.1%}")
res["coverage"] = {"statewide": {"licenses": int(len(cur)), "found": round(float(cur.found.mean()), 3), "placed": round(float(cur.lat.notna().mean()), 3)},
                   "regions": {r: {k: (round(float(v), 3) if isinstance(v, float) else int(v)) for k, v in x.items()} for r, x in cov_r.iterrows()},
                   "counties": {c: {k: (round(float(v), 3) if isinstance(v, float) else int(v)) for k, v in x.items() if v == v} for c, x in cov_c.iterrows()}}
json.dump(res, open(f"{FL}/calibration.json", "w"), indent=1)
json.dump(app, open(f"{FL}/calibration_app.json", "w"), indent=1)
