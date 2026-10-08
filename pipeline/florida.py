"""Stage 2: the Florida list -> site/florida.json (web leaderboard) or, with FL_APP=1, data/app/places.json (the App Store build)

Adapted from co-eats/pipeline/colorado.py. Florida is different from the other states in one big way: one agency, DBPR's Division of
Hotels and Restaurants, licenses and inspects every restaurant in the state, and publishes the full list weekly. So the base is official:
  - every current DBPR seating or non-seating food service license is a place (placed on its address by geocode.py),
  - a map listing (Overture) that matches a current license lends the place its map point, website, phone and category,
  - a map listing that matches no license is kept only by the rule calibrate.py measured against the licenses
    (data/fl/calibration*.json): mostly coffee shops, bakeries and juice bars, which Florida's Agriculture department (FDACS) licenses
    instead of DBPR, and confident Meta listings.
Inspections: DBPR's official disposition at every visit and its own result group (Met Inspection Standards / Follow-Up Inspection
Required / Facility Temporarily Closed). Florida gives no grade and we compute none.
Ratings, reviews and price level (web only): Google, Sep 2021 snapshot (UCSD Google Local).
"""
import os, re, sys, json, math, hashlib, unicodedata, collections, glob, datetime as dt
import numpy as np, pandas as pd
from shapely.geometry import shape, Point
from shapely.prepared import prep
from rapidfuzz import fuzz
from common import (real_share, kind_conflict, town_words, norm_name, nice, name_sim, cuisine, FOOD_COST, MARGIN, MARGIN_CUISINE, SPEND, GENERIC, _stems, DATA, FL, ROOT,
                    canon_city, town_key, CUISINE_RULES)
from brands import brand_of
import official
from official import REGION_OF
from listings_util import official_match, _close_words
from addr import street_key, street_nums, street_compat

APP = os.environ.get("FL_APP") == "1"
SITE = os.environ.get("FL_SITE") or (os.path.join(ROOT, "data", "app") if APP else os.path.join(ROOT, "site"))
GOOD_SOURCES = {"meta", "AllThePlaces", "DAC"}
BASE = {1: 600_000, 2: 1_000_000, 3: 2_200_000, 4: 3_500_000}   # typical yearly sales by price tier (same as Chicago)
B_FIT = 0.764   # review-volume exponent fit on Chicago's published sales (chi-eats meta.model.b)
DMETA = json.load(open(f"{FL}/dbpr_meta.json"))
TODAY = str(dt.date.today())
CAFE = {"coffee_shop", "cafe", "smoothie_juice_bar"}
TAX_CUISINE = {
    "pizza_restaurant": "Pizza", "mexican_restaurant": "Mexican", "taco_restaurant": "Mexican", "texmex_restaurant": "Mexican",
    "sandwich_shop": "Sandwiches & Deli", "delicatessen": "Sandwiches & Deli", "bakery": "Bakery & Sweets", "donut_shop": "Bakery & Sweets",
    "dessert_shop": "Bakery & Sweets", "ice_cream_shop": "Bakery & Sweets", "bagel_shop": "Bakery & Sweets", "cupcake_shop": "Bakery & Sweets",
    "frozen_yogurt_shop": "Bakery & Sweets", "chocolatier": "Bakery & Sweets", "popcorn_shop": "Bakery & Sweets",
    "bar_and_grill_restaurant": "Bar & Pub", "gastropub": "Bar & Pub", "bar": "Bar & Pub", "brewery": "Bar & Pub", "pub": "Bar & Pub",
    "sports_bar": "Bar & Pub", "cocktail_bar": "Bar & Pub", "wine_bar": "Bar & Pub", "dive_bar": "Bar & Pub", "beer_bar": "Bar & Pub",
    "irish_pub": "Bar & Pub", "tiki_bar": "Bar & Pub", "speakeasy": "Bar & Pub", "hookah_bar": "Bar & Pub", "gay_bar": "Bar & Pub",
    "chinese_restaurant": "Chinese", "italian_restaurant": "Italian", "burger_restaurant": "Burgers",
    "breakfast_and_brunch_restaurant": "Breakfast & Diner", "diner": "Breakfast & Diner", "barbecue_restaurant": "BBQ",
    "chicken_restaurant": "Chicken & Wings", "chicken_wings_restaurant": "Chicken & Wings", "sushi_restaurant": "Japanese & Sushi",
    "japanese_restaurant": "Japanese & Sushi", "ramen_restaurant": "Japanese & Sushi", "seafood_restaurant": "Seafood", "poke_restaurant": "Seafood",
    "steakhouse": "Steakhouse", "indian_restaurant": "South Asian", "pakistani_restaurant": "South Asian", "thai_restaurant": "Thai",
    "hot_dog_restaurant": "Hot Dogs & Sausages", "mediterranean_restaurant": "Mediterranean & Middle Eastern",
    "greek_restaurant": "Mediterranean & Middle Eastern", "middle_eastern_restaurant": "Mediterranean & Middle Eastern",
    "korean_restaurant": "Korean", "vietnamese_restaurant": "Vietnamese", "salad_bar": "Healthy & Vegan", "vegan_restaurant": "Healthy & Vegan",
    "vegetarian_restaurant": "Healthy & Vegan", "health_food_restaurant": "Healthy & Vegan", "coffee_shop": "Coffee & Café", "cafe": "Coffee & Café",
    "coffee_roastery": "Coffee & Café", "smoothie_juice_bar": "Healthy & Vegan", "juice_bar": "Healthy & Vegan", "bubble_tea_shop": "Coffee & Café",
    "tea_room": "Coffee & Café", "soul_food": "Soul & Southern", "southern_american_restaurant": "Soul & Southern",
    "cajun_and_creole_restaurant": "Seafood", "caribbean_restaurant": "Latin & Caribbean", "jamaican_restaurant": "Latin & Caribbean",
    "latin_american_restaurant": "Latin & Caribbean", "cuban_restaurant": "Latin & Caribbean", "puerto_rican_restaurant": "Latin & Caribbean",
    "peruvian_restaurant": "Latin & Caribbean", "colombian_restaurant": "Latin & Caribbean", "venezuelan_restaurant": "Latin & Caribbean",
    "haitian_restaurant": "Latin & Caribbean", "dominican_restaurant": "Latin & Caribbean", "salvadoran_restaurant": "Latin & Caribbean",
    "brazilian_restaurant": "Latin & Caribbean", "argentine_restaurant": "Latin & Caribbean", "honduran_restaurant": "Latin & Caribbean",
    "nicaraguan_restaurant": "Latin & Caribbean", "ecuadorian_restaurant": "Latin & Caribbean", "empanada_restaurant": "Latin & Caribbean",
    "african_restaurant": "African", "ethiopian_restaurant": "African",
    "french_restaurant": "European", "german_restaurant": "European", "polish_restaurant": "European",
    "spanish_restaurant": "European", "tapas_bar": "European", "noodles_restaurant": "Chinese",
    "belgian_restaurant": "European", "russian_restaurant": "European", "fondue_restaurant": "European",
    "scandinavian_restaurant": "European", "european_restaurant": "European", "eastern_european_restaurant": "European",
    "hungarian_restaurant": "European", "british_restaurant": "European", "dutch_restaurant": "European",
    "portuguese_restaurant": "European",
}
# keep rule for map listings that match no license (calibrate.py): see the printout and data/fl/calibration*.json
KEEP_APP = {"meta_high", "brand_feed"}            # + cafe-type meta_mid with a website, see below
KEEP_WEB = {"Meta + open in Google 2021", "Meta only", "brand feed + Google 2021", "brand feed only"}


def pct(s):
    return (s.rank(pct=True) * 100).round(1)


o = pd.read_pickle(f"{FL}/stage1.pkl")
G = pd.read_pickle(f"{FL}/google21.pkl")
if APP:   # the App Store build ignores every Google 2021 match
    o["in21"] = False; o["closed21"] = False; o["gi"] = np.nan
F = pd.read_pickle(f"{FL}/official.pkl")
o["off"] = o.off.fillna(-1).astype(int)
o["lic_active"] = [bool(F.active.iat[j]) if j >= 0 else False for j in o.off]
o["official"] = o.lic_active
o["via"] = np.where(o.off >= 0, "calibrate", None)   # which step tied a listing to its license (qa_licenses.py prints it)
o["lapsed"] = (o.off >= 0) & ~o.lic_active
o.loc[~o.official, "off"] = -1
print("listings matched to a current DBPR license:", int(o.official.sum()), "| only to a delinquent one:", int(o.lapsed.sum()))

# second pass: a current license nobody matched, sitting on an unmatched map listing (a slightly different name within 60 m, or the
# only license and the only eating listing at one street address in one zip): the listing is that licensed place
base_any = ~o.j_junk & ~o.j_outside & ~o.j_closedname & ~o.ov_closed & o.county.notna() & ~o.lapsed
U = F[F.active & F.kind.isin(["restaurant", "nonseating"]) & F.lat.notna() & ~F.index.isin(set(o.off[o.off >= 0]))]
V = o[base_any & (o.off < 0)]
vgrid = {}
for i, la, lo in zip(V.index, V.lat, V.lon):
    vgrid.setdefault((round(la / 0.0006), round(lo / 0.0007)), []).append(i)
pairs = []
for j, u in U.iterrows():
    ukeys = u["keys"] or []
    ust = set().union(*[_stems(k) - GENERIC for k in ukeys]) if ukeys else set()
    gy, gx = round(u.lat / 0.0006), round(u.lon / 0.0007)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            for i in vgrid.get((gy + dy, gx + dx), []):
                d_ = math.hypot((o.lat.iat[i] - u.lat) * 111000, (o.lon.iat[i] - u.lon) * 99000)
                if d_ > 60 or not o.k.iat[i]:
                    continue
                s_ = max((name_sim(o.k.iat[i], k) for k in ukeys), default=0)
                # a shared town name isn't a shared business name, and "fish" and "tea" are two businesses
                shared = (real_share(o.st.iat[i], ust) or _close_words(o.st.iat[i] - town_words(), ust - town_words())) and \
                    not all(kind_conflict(o.k.iat[i], k) for k in ukeys)
                if (s_ >= 88) or (shared and s_ >= 60) or (d_ <= 25 and s_ >= 75):
                    pairs.append((s_ - d_ / 10, i, j))
akey_u = collections.defaultdict(list)
for j, a_, z_ in zip(U.index, U.addr, U.zip):
    n_, s_ = street_key(a_)
    if n_ and s_:
        akey_u[(n_, s_, z_)].append(j)
akey_v = collections.defaultdict(list)
for i, a_, z_, c_ in zip(V.index, V.street, V.zip.fillna("").astype(str).str[:5], V.cat):
    n_, s_ = street_key(a_)
    if n_ and s_ and c_ not in CAFE:
        akey_v[(n_, s_, z_)].append(i)
for k_, js in akey_u.items():
    if len(js) == 1 and len(akey_v.get(k_, [])) == 1 and not k_[1].startswith(("US ", "SR ", "CR ")):
        pairs.append((50.0, akey_v[k_][0], js[0]))
taken_i, taken_j, n2 = set(), set(), 0
for sc, i, j in sorted(pairs, key=lambda t: -t[0]):
    if i in taken_i or j in taken_j:
        continue
    taken_i.add(i); taken_j.add(j)
    o.at[i, "off"] = j; o.at[i, "official"] = True; o.at[i, "lic_active"] = True; n2 += 1
    o.at[i, "via"] = "second pass, address" if sc == 50.0 else "second pass, name nearby"
print("second pass: unmatched licenses placed on their own map listing:", n2, "of", len(U))


# ---------------------------------------------------------------- hand-checked research (data/research)
def curated_matcher(frame):
    """A researched place -> row of frame: same street number and street with a similar name; else a near-exact name in the same town;
    else a near-exact name that's unique statewide (the research uses the real municipality, the listings the mailing town)."""
    by_key = {}
    for i, a in enumerate(frame.street):
        sk = street_key(a)[1]
        for n in street_nums(a):
            if sk:
                by_key.setdefault((n, sk), []).append(i)
    towns = [canon_city(c).lower() if isinstance(c, str) else "" for c in frame.city]
    zips = [str(z)[:5] if isinstance(z, str) else "" for z in frame.zip]
    ks = list(frame.k.fillna(""))
    streets = list(frame.street)

    def other_branch(c, i):
        """Both addresses say where they are, and it isn't the same spot: another location of a multi-location place (the research
        has Cuban Coffee Queen's Duval St shop, the listing its Front St one). Next-door numbers on one street are the same place."""
        a, b = c.get("address") or "", streets[i] if isinstance(streets[i], str) else ""
        na, sa = street_key(a)
        nb, sb = street_key(b)
        if not (na and nb and sa and sb):
            return False
        if street_compat(sa, sb) and abs(int(na) - int(nb)) <= 40:
            return False
        return True

    def match(c):
        bare = lambda n: re.sub(r"\s*\([^)]*\)", "", n or "")
        keys = {norm_name(bare(m)) for m in (c.get("match_names") or [])} | {norm_name(bare(c["name"]))}
        keys.discard("")
        _, sk = street_key(c.get("address") or "")
        cands = set()
        for n in street_nums(c.get("address") or ""):
            cands.update(by_key.get((n, sk), []))
            if not cands and sk:   # directions or street type missing on one side
                for (n2, s2), v in by_key.items():
                    if n2 == n and s2 and s2.split()[-1:] and (s2 in sk or sk in s2):
                        cands.update(v)
        ctown_ = (canon_city(c.get("city") or "") or "").lower()
        czip = str(c.get("zip") or "")[:5]
        # the same street number and name in another town is another place ("400 N Ocean Dr, Hollywood" vs "400 Ocean Dr, Miami Beach")
        cands = {i for i in cands if not ctown_ and not czip or towns[i] == ctown_ or (czip and zips[i] == czip)}
        best, bs = None, 0
        for i in cands:
            s_ = max((fuzz.token_set_ratio(m, ks[i]) for m in keys), default=0)
            if s_ >= 60 and s_ > bs:
                best, bs = i, s_
        # (no address-only match: in a shared building the one listing we have at an address is often a different business, and an
        # address-only fallback put Kabooki Sushi on a Jet's Pizza and Cuban Coffee Queen on a Key West bar; an unmatched researched
        # place is added on its own geocoded address instead)
        if best is None and not c.get("chain"):
            ctown = (canon_city(c.get("city") or "") or "").lower()
            sim = [max(fuzz.ratio(m, k) for m in keys) if k else 0 for k in ks]
            hits = [i for i, s_ in enumerate(sim) if s_ >= 90 and towns[i] == ctown] or [i for i, s_ in enumerate(sim) if s_ >= 95]
            if len(hits) == 1 and not other_branch(c, hits[0]):
                best = hits[0]
        return best
    return match


def load_curated():
    """MICHELIN Guide Florida 2026 and James Beard honors -> curated entries (facts only, each with sources)."""
    out, by = [], {}

    def entry(name, address, city, zip_=None, rank=1):
        key = (norm_name(name), (canon_city(city) or "").lower())
        if key not in by:
            by[key] = {"name": name, "address": address, "city": city, "zip": zip_, "chain": False, "match_names": [name.upper()],
                       "james_beard": [], "tags": [], "open": True, "sources": [], "name_rank": rank}
            out.append(by[key])
        return by[key]
    mpath = f"{DATA}/research/michelin.json"
    if os.path.exists(mpath):
        for r in json.load(open(mpath)).get("restaurants", []):
            c = entry(r["name"], r.get("address"), r.get("city"), r.get("zip"), rank=3)   # MICHELIN's own spelling
            c["michelin"] = r.get("distinction")
            c["green_star"] = bool(r.get("green_star"))
            c["sources"] += (r.get("sources") or []) + ([r["michelin_url"]] if r.get("michelin_url") else [])
            if r.get("open") is False or r.get("closed_after_release"):   # Papa Llama closed after the May 2026 release
                c["open"] = False
                CLOSED_HONORS.append({"name": r["name"], "address": r.get("address"), "city": r.get("city"), "closed_reason": r.get("note")})
    jpath = f"{DATA}/research/jbf.json"
    if os.path.exists(jpath):
        for r in json.load(open(jpath)):
            c = entry(r["name"], r.get("address"), r.get("city"), r.get("zip"))
            if r["name"] in NOT_THEIRS:   # the honor went to a group that no longer runs the place (honors_notes.md)
                continue
            c["james_beard"] += [h for h in r.get("honors") or [] if h not in c["james_beard"]]
            c["sources"] += r.get("sources") or []
            if r.get("open") is False:
                c["open"] = False
    return out


CLOSED_HONORS = []
NOT_THEIRS = {"Mamey"}   # its 2023 Restaurateur semifinalist honor was Alpareno's, which stopped operating it in Jan 2024
CUR = load_curated()


def load_research():
    """data/research/app/*.json: hand-checked Cuban and Latin spots, stone crabs, grouper, Keys classics, oyster bars, fish camps and the
    oldest places (facts only, each with a 2025-26 source). An entry for a place already in CUR adds its kinds and notes there."""
    out, by = [], {(norm_name(c["name"]), (canon_city(c.get("city")) or "").lower()): c for c in CUR}
    for f in sorted(glob.glob(f"{DATA}/research/app/*.json")):
        if os.path.basename(f).startswith("closed"):
            continue
        try:
            entries = json.load(open(f))
        except json.JSONDecodeError as e:
            print("skipping unreadable research file", f, e); continue
        for e in entries:
            if e.get("open") is False or not e.get("name"):
                continue
            key = (norm_name(e["name"]), (canon_city(e.get("city")) or "").lower())
            c = by.get(key)
            if c is None:
                c = {"name": e["name"], "address": e.get("address"), "city": e.get("city"), "zip": e.get("zip"), "chain": False,
                     "match_names": [e["name"].upper()], "founded": e.get("founded"), "open": True, "tags": [], "research_only": True,
                     "name_rank": 2}   # the name on the place's own site
                by[key] = c; out.append(c)
            c["tags"] = list(dict.fromkeys((c.get("tags") or []) + [k.lower() for k in (e.get("kinds") or [])]))
            c["dishes"] = list(dict.fromkeys((c.get("dishes") or []) + (e.get("dishes") or [])))
            c["rsources"] = list(dict.fromkeys((c.get("rsources") or []) + (e.get("sources") or [])))
            for k in ("note", "website", "seasonal", "founded_note", "evidence_date"):
                c[k] = c.get(k) or e.get(k)
            if not c.get("founded") and e.get("founded"):
                c["founded"] = e["founded"]
    return out


CUR = CUR + load_research()
CLOSED = list(CLOSED_HONORS)
for f in [f"{DATA}/research/closed.json"] + sorted(glob.glob(f"{DATA}/research/app/closed_*.json")):
    if os.path.exists(f):
        try:
            CLOSED += json.load(open(f))
        except json.JSONDecodeError:
            pass
print("verified places: honors", sum(1 for c in CUR if not c.get("research_only")), "+ research-only", sum(1 for c in CUR if c.get("research_only")),
      "| verified closed:", len(CLOSED))

# ---------------------------------------------------------------- keep rule for the map listings
base_ok = ~o.j_junk & ~o.j_closedname & ~o.j_outside & ~o.j_far & ~o.ov_closed & ~(o.nowhere & ~o.in21) & o.county.notna()
_m = curated_matcher(o[base_ok].reset_index())
_bo = o.index[base_ok]
verified = pd.Series(False, index=o.index)
for c in CUR:
    if c.get("open") is not False:
        j = _m(c)
        if j is not None:
            verified[_bo[j]] = True
conf = o.confidence.fillna(0)
has_web = o.n_web.fillna(0).astype(int) > 0
cafe = o.cat.isin(CAFE)
barcat = o.cat.isin(["bar", "brewery"])
src = o.src.fillna("")
# DBPR licenses every restaurant, so a restaurant listing that matches no current license is mostly a closed place or a licensed one under
# another name (already on the list from its license): those are dropped. Kept without a license: cafe-type listings (FDACS licenses many
# of them) and bars (a bar serving no food needs no DBPR license), when the listing is confident: statewide, Meta listings at 0.95+ matched
# a license 76% of the time for restaurants; two-source listings (Meta + open in Google 2021) 79%.
if APP:
    rule = (cafe | barcat) & (((src == "meta") & (conf >= 0.95)) | src.isin(["AllThePlaces", "DAC"]))
else:
    rule = (cafe | barcat) & (((src == "meta") & (o.in21 | (conf >= 0.95))) | (src.isin(["AllThePlaces", "DAC"]) & o.in21)) & ~o.closed21
keep = base_ok & ~o.lapsed & (o.official | verified | rule)
print("kept listings:", int(keep.sum()), "of", len(o), "| official", int((keep & o.official).sum()), "| by the source rule only",
      int((keep & ~o.official & ~verified).sum()), "| hand-verified", int((keep & verified & ~o.official).sum()))
o = o[keep].reset_index(drop=True)

# ---------------------------------------------------------------- duplicate listings of one place
o["biz"] = o.off.where(o.off >= 0, np.nan)
o["rank"] = o.official.astype(int) * 8 + o.in21.astype(int) * 4 + o.src.isin(GOOD_SOURCES).astype(int) * 2 + o.confidence.fillna(0)
o = o.sort_values("rank", ascending=False).reset_index(drop=True)
cell, drop = {}, set()
for i, r in o.iterrows():
    key = (round(r.lat / 0.001), round(r.lon / 0.0011))
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            for j in cell.get((key[0] + dy, key[1] + dx), []):
                d_ = math.hypot((o.lat.iat[j] - r.lat) * 111000, (o.lon.iat[j] - r.lon) * 99000)
                same_biz = r.biz == r.biz and r.biz == o.biz.iat[j]
                if same_biz or (d_ < 80 and (r.k == o.k.iat[j] or (fuzz.token_set_ratio(r.k, o.k.iat[j]) >= 92 and r.st & o.st.iat[j]))) or (
                        d_ < 150 and isinstance(r.brand_n, str) and r.brand_n == o.brand_n.iat[j]):
                    drop.add(i); break
            if i in drop: break
        if i in drop: break
    if i not in drop:
        cell.setdefault(key, []).append(i)
# two listings on one license far apart (a chain's license matched by name twice): the license keeps the nearer one only
o = o.drop(index=list(drop)).reset_index(drop=True)
akey = [(b if isinstance(b, str) else k, n, c) if n and isinstance(c, str) else None for b, k, n, c in zip(o.brand_n, o.k, o.num, o.city)]
seen, dup = set(), []
for a in akey:
    dup.append(a is not None and a in seen)
    if a is not None:
        seen.add(a)
o = o[~np.array(dup)].reset_index(drop=True)
lic_seen, dup2 = set(), []
for b in o.biz:
    dup2.append(b == b and b in lic_seen)
    if b == b:
        lic_seen.add(b)
o = o[~np.array(dup2)].reset_index(drop=True)
print("after merging duplicate listings:", len(o), "(dropped", len(drop) + sum(dup) + sum(dup2), ")")
confirmed = ((o.src == "meta") & (o.confidence.fillna(0) >= 0.95)) if APP else o.in21
o["tier"] = np.where(o.official, "official", np.where(confirmed, "both", "listing"))


# ---------------------------------------------------------------- licensed places the map listings don't have
def is_legal(n):
    return bool(re.search(r"\b(?:INC|LLC|L L C|CORP|CORPORATION|LTD|LLP|LP|PA|PLLC|CO)\b\.?\s*$", (n or "").upper()))


LEGALISH = re.compile(r"\b(?:HOLDINGS?|ENTERPRISES?|GROUP|MANAGEMENT|VENTURES?|PARTNERS|PARTNERSHIP|INVESTMENTS?|PROPERTIES|OPERATIONS|"
                      r"OPERATING|DEVELOPMENT|ASSOCIATES|CAPITAL|SERVICES|SOLUTIONS|FRANCHISE|FRANCHISING|CONCEPTS|HOSPITALITY|"
                      r"OF FLORIDA|OF FL|OF AMERICA|USA|INTERNATIONAL|DEVEL|PRTNRS|PTNRS)\b")


def clean_official(n, dbas=(), brand=None):
    """A license's Business Name -> the name shown. Corporate suffixes and store numbers go; a name that's still a legal entity
    ("SWEETWATER FRANCHISE GROUP") gives way to an inspection DBA that isn't one, or to the chain's brand."""
    def strip(x):
        x = re.split(r"\s*;\s*", x if isinstance(x, str) else "")[0]
        x = re.sub(r"\s*\((?:MOBILE|CATERING|CP|INSIDE [^)]*|AT [^)]*)\)\s*$", "", x, flags=re.I)
        x = re.sub(r"\s*#\s*\d+\w*.*$|\s*\(#?[A-Z]?\d+\)|\s+(?:STORE|UNIT|NO\.?)\s*\d+\s*$|\s+\d{3,}\s*$", "", x)
        x = re.sub(r"(?:(?:,?\s+|\.)(?:INC|LLC|L\.L\.C|L L C|CORP|CORPORATION|LTD|LLP|PLLC|P\.A)\.?)+\s*$", "", x, flags=re.I)
        x = re.sub(r"^(?:THE\s+)?(?:CITY|TOWN|COUNTY|VILLAGE) OF\s+.*$", "", x, flags=re.I) or x
        x = re.sub(r"\s+DBA\s+", " / ", x, flags=re.I)
        x = re.split(r"\s*/\s*", x)[-1] if "/" in x and re.search(r"\b(?:INC|LLC|CORP)\b", x.split("/")[0], re.I) else x
        return x.strip(" -,&/.")
    n0 = strip(n)
    if not n0 or is_legal(n) or LEGALISH.search(n0.upper()):
        for d in dbas:
            d0 = strip(d)
            if d0 and not is_legal(d) and not LEGALISH.search(d0.upper()) and norm_name(d0):
                n0 = d0; break
    if isinstance(brand, str) and (not n0 or LEGALISH.search(n0.upper()) or norm_name(n0).startswith(norm_name(brand))):
        n0 = brand
    return nice(n0) if n0.isupper() or n0.islower() else n0


found = set(o.biz.dropna().astype(int))
eligible = F.active & F.kind.isin(["restaurant", "nonseating", "park", "catering"]) & F.lat.notna()
add = F[eligible & ~F.index.isin(found)].copy()
print("current licenses the kept map listings don't have:", len(add), add.kind.value_counts().to_dict())
rows = []
for j, f in add.iterrows():
    kb = brand_of(norm_name(f["name"]), *[norm_name(d) for d in f.dbas])
    rows.append({"id": f.lic, "name": clean_official(f["name"], f.dbas, kb), "street": f.addr, "city": f.city, "zip": f.zip, "lat": f.lat,
                 "lon": f.lon, "cat": "restaurant", "tax": None, "confidence": np.nan, "brand": kb, "src": "official", "official": True,
                 "off": j, "biz": j, "tier": "official", "in21": False, "closed21": False, "dom": None, "county": f.county, "region": f.region,
                 "n_web": 0, "kind_lic": f.kind, "via": "license row"})
A = pd.DataFrame(rows)
A = A[A.name.fillna("").str.len() > 0].reset_index(drop=True)
A["k"] = A.name.map(norm_name)
A["st"] = A.k.map(lambda k: _stems(k) - GENERIC if k else set())
A["num"] = A.street.map(lambda a: (re.match(r"\s*(\d+)", a or "") or [None, None])[1])
A["brand_n"] = [b if isinstance(b, str) else brand_of(k) for b, k in zip(A.brand, A.k)]
# the same business holding two licenses at one address (seating + non-seating, a hotel's restaurant and its pool bar under one name):
# one place, the seating license first
A["pri"] = A.kind_lic.map({"restaurant": 0, "nonseating": 1, "park": 2, "catering": 3})
A = A.sort_values("pri").reset_index(drop=True)
A["akey"] = [(k, n, street_key(s)[1]) for k, n, s in zip(A.k, A.num, A.street)]
A = A[~A.akey.duplicated() | A.num.isna()].reset_index(drop=True)

# Google 2021 listings for the added rows (web only)
taken = set(o.gi.dropna().astype(int))
grid = {}
for i, (la, lo) in enumerate(zip(G.latitude, G.longitude)):
    grid.setdefault((round(la / 0.0018), round(lo / 0.002)), []).append(i)
pairs = []
for ai, r in ([] if APP else A.iterrows()):
    if not r.k:
        continue
    gy, gx = round(r.lat / 0.0018), round(r.lon / 0.002)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            for gi in grid.get((gy + dy, gx + dx), []):
                if gi in taken or not G.k.iat[gi] or G.closed21.iat[gi]:
                    continue
                dist = math.hypot((G.latitude.iat[gi] - r.lat) * 111000, (G.longitude.iat[gi] - r.lon) * 99000)
                if dist > 200:
                    continue
                s = name_sim(r.k, G.k.iat[gi])
                same_num = r.num is not None and G.num.iat[gi] == r.num
                if same_num and r.st & G.st.iat[gi]:
                    s = max(s, 80)
                if s < 95 and not r.st & G.st2.iat[gi]:
                    continue
                if (s >= 88 and dist < 150) or (s >= 75 and same_num):
                    pairs.append((s + (10 if same_num else 0) - dist / 25, ai, gi))
A["gi"] = np.nan
ta, tg = set(), set()
for sc, ai, gi in sorted(pairs, key=lambda t: -t[0]):
    if ai in ta or gi in tg:
        continue
    ta.add(ai); tg.add(gi); A.at[ai, "gi"] = gi
A["in21"] = A.gi.notna()
print("license rows added:", len(A), "| matched to Google 2021:", int(A.in21.sum()))
o = pd.concat([o, A.drop(columns=["akey", "pri"])], ignore_index=True)
o["city"] = o.city.map(canon_city)
main = o.city.dropna().groupby(o.city.dropna().map(town_key)).agg(lambda x: x.mode().iat[0])
o["city"] = o.city.map(lambda c: main.get(town_key(c), c) if isinstance(c, str) else c)
# DBPR's city field is typed by hand: "Kissimee", "Hialiah", "Ponte Vedra Beac", "Hialeah, Fl, Us". A rare spelling (under 5 places) that is
# close to its zip's usual town, or to any common town, becomes that town.
tcount = o.city.value_counts()
common_towns = [t for t, n_ in tcount.items() if n_ >= 5]
o["z5"] = o.zip.fillna("").astype(str).str[:5]
zip_town = o[o.city.isin(common_towns)].groupby("z5").city.agg(lambda x: x.mode().iat[0])
snapped = 0
for i_, c_, z_ in zip(o.index, o.city, o.z5):
    if not isinstance(c_, str) or tcount.get(c_, 0) >= 5:
        continue
    zt = zip_town.get(z_)
    cc = re.sub(r",.*$|\s*\.\s.*$", "", c_).strip()
    if zt and (fuzz.ratio(cc.lower(), zt.lower()) >= 75 or zt.lower() in c_.lower() or c_.lower() in zt.lower()):
        o.at[i_, "city"] = zt; snapped += 1; continue
    best_t = max(common_towns, key=lambda t: fuzz.ratio(cc.lower(), t.lower()))
    if fuzz.ratio(cc.lower(), best_t.lower()) >= 90:
        o.at[i_, "city"] = best_t; snapped += 1
print("misspelled towns snapped to the zip's or a common town:", snapped)

# ---------------------------------------------------------------- hand-checked places neither list has (rare: DBPR licenses them all)
_m = curated_matcher(o)
missing = [c for c in CUR if c.get("open") is not False and not c.get("chain") and _m(c) is None]
GEOCACHE = json.load(open(f"{FL}/geocode_census.json")) if os.path.exists(f"{FL}/geocode_census.json") else {}
_OVP = None


def ov_point(c):
    """A hand-checked place's point from Overture: one place (any category) with the same name, in the same town, at the same house
    number when both have one. City Seafood (702 Begonia St, Everglades City) and Burdines Waterfront (a marina) are FDACS-licensed or
    listed under the marina, so no DBPR license places them."""
    global _OVP
    if _OVP is None:
        import duckdb
        _OVP = duckdb.connect().execute(f"""SELECT name, street, city, lat, lon FROM '{FL}/overture_fl_bbox.parquet'
                                            WHERE region = 'FL' AND name IS NOT NULL""").df()
        _OVP["k"] = _OVP.name.map(norm_name); _OVP["town"] = _OVP.city.map(lambda x: (canon_city(x) or "").lower())
    k, town = norm_name(re.sub(r"\s*\([^)]*\)", "", c["name"])), (canon_city(c.get("city") or "") or "").lower()
    num = street_key(c.get("address") or "")[0]
    g = _OVP[(_OVP.town == town) & (_OVP.k.map(lambda x: fuzz.ratio(k, x) if x else 0) >= 92)]
    g = g[[not (num and street_key(s_ or "")[0] and street_key(s_ or "")[0] != num) for s_ in g.street]]
    if len(g) and (g.lat.max() - g.lat.min()) < 0.002:
        return {"lat": round(float(g.lat.iat[0]), 6), "lon": round(float(g.lon.iat[0]), 6)}
    return None


added, GEO_TODO = [], []
for c in missing:
    a, t = (c.get("address") or "").strip(), (c.get("city") or "").strip()
    gq = f"{a}, {t.title()}, FL {c.get('zip') or ''}".strip() if re.match(r"\s*\d", a) and t else None
    hit = GEOCACHE.get(gq) if gq else None
    if not hit:
        hit = ov_point(c)   # the Census geocoder doesn't know some small-town and Keys addresses; Overture's own listing of the place does
    if not hit:
        if gq:
            GEO_TODO.append(gq)
        continue
    added.append({"id": "research-" + c["name"], "name": c["name"], "street": a, "city": canon_city(t), "zip": c.get("zip"),
                  "lat": hit["lat"], "lon": hit["lon"], "cat": "restaurant", "tax": None, "confidence": np.nan, "brand": None, "src": "research",
                  "official": False, "off": -1, "biz": np.nan, "tier": "both", "in21": False, "closed21": False, "dom": None, "gi": np.nan,
                  "k": norm_name(c["name"]), "st": _stems(norm_name(c["name"])) - GENERIC, "num": (re.match(r"\s*(\d+)", a) or [None, None])[1],
                  "brand_n": None, "web": c.get("website"), "n_web": 1})
if added:
    o = pd.concat([o, pd.DataFrame(added)], ignore_index=True)
os.makedirs(f"{DATA}/research", exist_ok=True)
json.dump(sorted(set(GEO_TODO)), open(f"{DATA}/research/geocode_todo.json", "w"), indent=1)
print("hand-verified places added (in neither list):", len(added), "of", len(missing), "| waiting for the geocoder:", len(set(GEO_TODO)),
      "| e.g.", [c["name"] for c in missing][:12])

# counties and regions for every row
CTY = {official.county_name(n.replace(" County", "")): prep(shape(g).buffer(0.002)) for n, g in json.load(open(f"{FL}/fl_counties_detail.geojson")).items()}
miss_c = o.county.isna() & o.lat.notna()
o.loc[miss_c, "county"] = [next((n for n, p in CTY.items() if p.contains(Point(lo, la))), None) for la, lo in zip(o.lat[miss_c], o.lon[miss_c])]
o["region"] = o.county.map(REGION_OF)
split = 0
for c, grp in o[o.city.notna() & o.county.notna()].groupby("city"):
    if grp.county.nunique() < 2:
        continue
    med = grp.groupby("county")[["lat", "lon"]].median()
    big = grp.county.value_counts().index[0]
    far = {n for n, m in med.iterrows() if math.hypot((m.lat - med.lat[big]) * 111, (m.lon - med.lon[big]) * 99) > 40}
    if far:
        sel = grp.index[grp.county.isin(far)]
        o.loc[sel, "city"] = [f"{c} ({n} Co.)" for n in grp.county[grp.county.isin(far)]]
        split += 1
print("same-name towns split by county:", split)

# ---------------------------------------------------------------- fields
gi = [int(v) if v == v and v is not None else None for v in o.gi]
o["rating"] = [G.avg_rating.iat[i] if i is not None else np.nan for i in gi]
o["reviews"] = [G.num_of_reviews.iat[i] if i is not None else np.nan for i in gi]
o["gprice"] = [len(G.price.iat[i]) if i is not None and isinstance(G.price.iat[i], str) else np.nan for i in gi]
o["gcats"] = ["|".join(G.category.iat[i] or []) if i is not None else "" for i in gi]
o["gmap_id"] = [G.gmap_id.iat[i] if i is not None else None for i in gi]
o["name_out"] = [b if isinstance(b, str) and fuzz.ratio(norm_name(n), norm_name(b)) >= 88 else nice(n) if n.isupper() or n.islower() else n
                 for n, b in zip(o.name, o.brand_n)]


def pick_cuisine(tax, k, gcats, raw):
    for c, pat in CUISINE_RULES[:-1]:          # a specific word in the name wins
        if pat.search(k or ""):
            return c
    if isinstance(tax, str) and tax in TAX_CUISINE:
        return TAX_CUISINE[tax]
    return cuisine(k, gcats, raw)


o["cuisine"] = [pick_cuisine(t, k, gc, n) for t, k, gc, n in zip(o.tax, o.k, o.gcats, o.name)]
first_cat = o.gcats.str.split("|").str[0].fillna("")
cafe_tax = o.tax.isin(["cafe", "coffee_shop"]) & o.cuisine.eq("Coffee & Café") & first_cat.ne("") & ~first_cat.str.contains(r"Coffee|Cafe|Café|Espresso|Tea|Bakery|Donut|Dessert|Ice cream|Juice|Breakfast")
o.loc[cafe_tax, "cuisine"] = [cuisine(k, g, "") for k, g in zip(o.loc[cafe_tax, "k"], o.loc[cafe_tax, "gcats"])]
o.loc[o.cat.isin(["bar", "brewery"]) & (o.cuisine == "American & Other"), "cuisine"] = "Bar & Pub"
o.loc[o.cat.isin(["coffee_shop", "cafe"]) & (o.cuisine == "American & Other"), "cuisine"] = "Coffee & Café"
o.loc[o.city.fillna("") == "", "city"] = None


def mode(x):
    return x.mode().iat[0]


bdom = {}
for b, grp in o[o.brand_n.notna()].groupby("brand_n"):
    d = grp.dom.dropna()
    if len(d) >= 3:
        top, n = collections.Counter(d).most_common(1)[0]
        if n >= 0.5 * len(d):
            bdom[b] = top
FAMILY = {"Chicken & Wings": "quick", "Burgers": "quick", "Hot Dogs & Sausages": "quick", "Sandwiches & Deli": "cafe", "Pizza": "pizza",
          "Mexican": "mex", "Latin & Caribbean": "mex", "Coffee & Café": "cafe", "Bakery & Sweets": "cafe",
          "Breakfast & Diner": "cafe", "Healthy & Vegan": "cafe", "Steakhouse": "sitdown", "Seafood": "sea",
          "Bar & Pub": "bar", "Italian": "italian", "Chinese": "asian", "Japanese & Sushi": "asian", "Thai": "asian", "Korean": "asian",
          "Vietnamese": "asian", "South Asian": "sasian", "Mediterranean & Middle Eastern": "med", "European": "sitdown", "BBQ": "bbq",
          "Soul & Southern": "soul", "African": "african"}
brand_cuisine = o[o.brand_n.notna()].groupby("brand_n").cuisine.agg(mode)


def core(k):
    w = [x for x in k.split() if x not in GENERIC and x not in ("RESTAURANT", "RESTAURANTS", "CAFE", "STORE")]
    return " ".join(w) or k


def brand_ok(b, dm, cu, tax, obrand, name, src_):
    if not isinstance(b, str):
        return None
    dm = dm if isinstance(dm, str) else None
    nk, bk = norm_name(name), norm_name(b)
    if src_ not in ("AllThePlaces", "DAC") and brand_of(nk) != b:
        return None
    ob = norm_name(obrand) if isinstance(obrand, str) else ""
    brand_feed = src_ in ("AllThePlaces", "DAC")
    label = bool(ob) and fuzz.token_set_ratio(ob, bk) >= 80
    related = brand_feed or fuzz.partial_ratio(bk, nk) >= 60 or (label and fuzz.partial_ratio(ob, nk) >= 60)
    if not related:
        return None
    squashed = re.sub(r"[^a-z]", "", b.lower())
    own_site = dm and (bdom.get(b) == dm or dm.split(".")[0].replace("-", "") in (squashed, squashed + "s"))
    exact = fuzz.ratio(core(nk), core(bk)) >= 90 or (label and fuzz.ratio(core(nk), core(ob)) >= 90) \
        or (len(bk) >= 6 and (nk == bk or nk.startswith(bk + " ")))
    if exact or own_site or (label and brand_feed) or src_ == "official":
        return b
    if dm and b in bdom and src_ != "BrightQuery":
        return None
    want = brand_cuisine.get(b)
    if isinstance(tax, str) and tax in TAX_CUISINE and want and FAMILY.get(cu) and FAMILY.get(want) and FAMILY[cu] != FAMILY[want]:
        return None
    return b


old_brand = o.brand_n.copy()
o["brand_n"] = [brand_ok(b, dm, cu, t, ob, n, sr) for b, dm, cu, t, ob, n, sr in zip(o.brand_n, o.dom, o.cuisine, o.tax, o.brand, o.name, o.src)]
rej = o[old_brand.notna() & o.brand_n.isna()]
print("brand matches rejected:", len(rej), collections.Counter(old_brand[rej.index]).most_common(10))
o.loc[o.brand_n.notna(), "name_out"] = [b if fuzz.ratio(norm_name(n), norm_name(b)) >= 80 or len(norm_name(n)) <= len(norm_name(b)) + 2 else n
                                        for n, b in zip(o.loc[o.brand_n.notna(), "name_out"], o.loc[o.brand_n.notna(), "brand_n"])]


def chain_mode(x):
    real = x[x != "American & Other"]
    return (real if len(real) else x).mode().iat[0]


CHAIN_CUISINE = {"Culver's": "Burgers", "Freddy's": "Burgers", "Steak 'n Shake": "Burgers", "Krystal": "Burgers", "Checkers": "Burgers",
                 "BurgerFi": "Burgers", "Whataburger": "Burgers", "Perkins": "Breakfast & Diner", "Waffle House": "Breakfast & Diner",
                 "First Watch": "Breakfast & Diner", "IHOP": "Breakfast & Diner", "Denny's": "Breakfast & Diner", "Dairy Queen": "Bakery & Sweets",
                 "Cold Stone Creamery": "Bakery & Sweets", "Baskin-Robbins": "Bakery & Sweets", "Carvel": "Bakery & Sweets", "Kilwins": "Bakery & Sweets",
                 "Einstein Bros. Bagels": "Bakery & Sweets", "Panera Bread": "Sandwiches & Deli", "Miami Subs": "Sandwiches & Deli",
                 "Firehouse Subs": "Sandwiches & Deli", "Pollo Tropical": "Latin & Caribbean", "Pollo Campero": "Latin & Caribbean",
                 "La Carreta": "Latin & Caribbean", "Sergio's": "Latin & Caribbean", "Latin House Grill": "Latin & Caribbean",
                 "Tijuana Flats": "Mexican", "Moe's Southwest Grill": "Mexican", "Bubbakoo's Burritos": "Mexican", "Chuy's": "Mexican",
                 "4 Rivers Smokehouse": "BBQ", "Sonny's BBQ": "BBQ", "Dickey's Barbecue Pit": "BBQ", "Smokey Bones": "BBQ",
                 "Texas Roadhouse": "Steakhouse", "Outback Steakhouse": "Steakhouse", "LongHorn Steakhouse": "Steakhouse",
                 "Bonefish Grill": "Seafood", "Shells Seafood": "Seafood", "Red Lobster": "Seafood", "Joe's Crab Shack": "Seafood",
                 "Carrabba's Italian Grill": "Italian", "Olive Garden": "Italian", "Tropical Smoothie Cafe": "Healthy & Vegan",
                 "Smoothie King": "Healthy & Vegan", "Jamba": "Healthy & Vegan", "Bolay": "Healthy & Vegan", "Playa Bowls": "Healthy & Vegan",
                 "Clean Juice": "Healthy & Vegan", "Starbucks": "Coffee & Café", "Dunkin'": "Coffee & Café", "Dutch Bros": "Coffee & Café",
                 "Cracker Barrel": "Soul & Southern", "Golden Corral": "American & Other", "Hooters": "Chicken & Wings",
                 "Hurricane Grill & Wings": "Chicken & Wings", "Ker's WingHouse": "Chicken & Wings", "PDQ": "Chicken & Wings",
                 "Miller's Ale House": "Bar & Pub", "Duffy's Sports Grill": "Bar & Pub", "Flanigan's": "Bar & Pub", "Beef 'O' Brady's": "Bar & Pub",
                 "Mellow Mushroom": "Pizza", "Hungry Howie's": "Pizza", "Anthony's Coal Fired Pizza": "Pizza", "Seasons 52": "American & Other",
                 "Ford's Garage": "Burgers", "Bento Asian Kitchen": "Japanese & Sushi", "Gyro Shack": "Mediterranean & Middle Eastern"}
allc = o.loc[o.brand_n.notna(), ["brand_n", "cuisine"]]
all_brand_cuisine = allc.groupby("brand_n").cuisine.agg(chain_mode)
o.loc[o.brand_n.notna(), "cuisine"] = o.loc[o.brand_n.notna(), "brand_n"].map(lambda b: CHAIN_CUISINE.get(b) or all_brand_cuisine.get(b))

# price: Google price level, else the chain's usual level, else the cuisine's usual level (both from Florida's own Google data)
o["price"] = o.gprice
o["price_est"] = o.price.isna().astype(int)
bp = o[o.gprice.notna()].groupby("brand_n").gprice.median()
o.loc[o.price.isna() & o.brand_n.notna(), "price"] = o.brand_n.map(bp)
cp = o[o.gprice.notna()].groupby("cuisine").gprice.median()
o.loc[o.price.isna(), "price"] = o.cuisine.map(cp)
o["price"] = o.price.fillna(2).round().clip(1, 4).astype(int)

bc = o.brand_n.value_counts()
o["chain_n"] = o.brand_n.map(lambda b: int(bc.get(b, 0)) if isinstance(b, str) else 1)
STORE_DOMS_ALL = {"publix.com", "winndixie.com", "sedanos.com", "walmart.com", "samsclub.com", "target.com", "costco.com", "bjs.com", "aldi.us",
                  "lidl.com", "wholefoodsmarket.com", "freshmarket.com", "thefreshmarket.com", "traderjoes.com", "sprouts.com", "wawa.com",
                  "racetrac.com", "circlek.com", "7-eleven.com", "speedway.com", "sunoco.com", "shell.us", "buc-ees.com", "loves.com",
                  "pilotflyingj.com", "cvs.com", "walgreens.com"}
first_stem = o.k.fillna("").map(lambda k: next((w for w in k.split() if w not in GENERIC and len(w) >= 3), None))
grpkey = pd.Series([(d, s) if isinstance(d, str) and isinstance(s, str) and not isinstance(b, str) and d not in STORE_DOMS_ALL else None for d, s, b in zip(o.dom, first_stem, o.brand_n)], index=o.index)
gsize = grpkey.dropna().value_counts()
member = [g is not None and gsize.get(g, 0) >= 2 for g in grpkey]
o.loc[member, "chain_n"] = [int(gsize[g]) for g, m in zip(grpkey, member) if m]
o["ckey"] = grpkey.map(lambda g: "|".join(g) if g else None)
grp_cuisine = o[member].groupby("ckey").cuisine.agg(chain_mode)
o.loc[member, "cuisine"] = [grp_cuisine.get(k) for k in o.loc[member, "ckey"]]
sib = o.gprice.notna()
for key, sel in (("brand_n", o.brand_n.notna()), ("ckey", pd.Series(member, index=o.index))):
    med = o[sel & sib].groupby(key).gprice.median()
    fill = sel & (o.price_est == 1) & o[key].isin(med.index)
    o.loc[fill, "price"] = o.loc[fill, key].map(med).round().clip(1, 4).astype(int)
print("name-based chains:", int(pd.Series(member).sum()), "locations")

o["bar"] = o.cat.isin(["bar", "brewery"]) | (o.cuisine == "Bar & Pub")
o["name_out"] = o.name_out.map(lambda n: re.sub(r"\b(?:Tcby|Ihop|Bj's|Bjs)\b", lambda m: {"tcby": "TCBY", "ihop": "IHOP"}.get(m.group(0).lower(), "BJ's"), n))
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]+")
CJK = r"[぀-ヿ㐀-鿿가-힯豈-﫿＀-￯]"
TAILWORDS = re.compile(r"^(?:best|award|voted|magazine|official|order|delivery|takeout|take out|catering|now open|open|to go|curbside|franchise|inside .*|"
                       r"(?:(?:ice cream|chocolates?|fudge|coffee|cafe|café|restaurant|bar|grill|pizza|shawarma|hookah lounge|juicy seafood|latin tavern|"
                       r"bakery|deli|sandwiches|tacos|gifts?|shopping|treats|sweets|full bar|food|game room|drinks|spirits|live music|events|patio|"
                       r"lodging|rooms|resort|motel|campground|cocktails|beer|wine|burgers|wings|craft beer|sports bar|seafood|raw bar|tiki bar|"
                       r"waterfront|beachfront|dock ?side|and|&|,|-|\s)+))$", re.I)


def tidy(n, brand):
    """Emoji and non-Latin duplicates of an English name, LLC in the middle, marketing tails, notes in parentheses."""
    n = unicodedata.normalize("NFKC", n)
    if re.search(r"[ÃÂâð][\u0080-¿ŒœŠšŸŽžƒˆ˜–-›€™]", n):
        for enc in ("cp1252", "latin-1"):
            try:
                n = n.encode(enc).decode("utf-8"); break
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass
    n = re.sub(r"[®™©℠]", "", EMOJI.sub("", n))
    if re.search(r"[A-Za-z]{3,}", re.sub(CJK, "", n)):
        n = re.sub(r"\s*\([^()]*" + CJK + r"[^()]*\)", "", n)
    latin = re.sub(CJK + "+", " ", n)
    if re.search(r"[A-Za-z]{3,}", latin) and re.search(CJK, n):
        n = re.sub(r"\(\s*\)", "", latin)
    m = re.match(r"^(.*?)[,\s]+(?:LLC|Inc)\.?\s*-{1,2}\s*(.+)$", n, flags=re.I)
    if m:
        n = m.group(2) if len(m.group(2).split()) >= 2 and len(m.group(1).split()) <= 2 else m.group(1)
    n = re.sub(r"[,\s.]+(?:LLC|L\.L\.C|LLP|L\.L\.P|Inc|Corp)\.?(?=\s|$|,)", "", n, flags=re.I)
    n = re.sub(r"\s*\([^()]*\)\s*$", "", n) if re.sub(r"\s*\([^()]*\)\s*$", "", n).strip() else n
    n = re.sub(r",?\s+(?:FL|Fla\.?|Florida)\s*$", "", n)
    parts = re.split(r"\s+[-–]{1,2}\s+|--", n)
    if len(parts) > 1:
        tail = " ".join(parts[1:])
        if TAILWORDS.match(tail.strip()) or re.search(r"\b(?:Best|Award|Magazine|Voted|20\d\d)\b", tail):
            n = parts[0]
    if isinstance(brand, str):
        n = re.sub(r"\s*#\s*\d+\s*$", "", n)
    n = re.sub(r"\s+", " ", n).strip(" -–,") or n
    m_ = re.match(r"^(.+?),?\s+(?:THE|The|the)$", n)   # DBPR's "INN AT COCOA BEACH, THE"
    if m_:
        n = "The " + m_.group(1)
    n = re.sub(r"(?:\s+(?:of|OF|Of|and|AND|And|&|at|AT|At|de|DE|De|the|THE))+$", "", n) or n   # a name the 30-character field cut off
    return nice(n) if n.isupper() and len(n) > 4 else n


o["name_out"] = [tidy(n, b) for n, b in zip(o.name_out, o.brand_n)]
o.loc[o.brand_n.notna(), "name_out"] = [b if norm_name(n).startswith(norm_name(b)) and len(norm_name(b)) >= 3 else n
                                        for n, b in zip(o.loc[o.brand_n.notna(), "name_out"], o.loc[o.brand_n.notna(), "brand_n"])]
o["spell"] = o.name_out.map(lambda n: re.sub(r"[^a-z0-9]", "", n.lower()))
o["name_out"] = o.groupby("spell").name_out.transform(lambda s: s.mode().iat[0] if len(s) > 1 else s.iat[0])
towns_l = set(o.city.dropna().str.lower())
nm = o.name_out.fillna("")
junk = (nm.str.match(r"(?i)^\d+\s+(?:[NSEW]{1,2}\.?\s+)?[\w.' ]+?\b(?:St|Street|Ave|Avenue|Dr|Drive|Rd|Road|Blvd|Ln|Lane|Way|Ct|Pl|Hwy|Pkwy|Trl|Ter)\b\.?(?:\s*#\s*\w+)?(?:\s*,.*|\s+[A-Z][a-z]+,\s*FL\b.*)?$")
        | nm.str.contains(r"(?i)(?:\bclosed|\bretired)\s*\)?\s*$") | (nm.str.lower().str.strip().isin(towns_l) & o.brand_n.isna() & ~o.official)
        | nm.str.match(r"(?i)^(?:village|city|town) of ") | nm.str.strip().str.lower().isin(["kitchen", "bar", "pub", "tavern", "grill", "deli", "pizza", "bakery", "coffee", "diner", "restaurant", "cafe", "café"])
        | ~nm.str.contains(r"[A-Za-z]"))
print("junk names dropped:", int(junk.sum()), nm[junk].head(12).tolist())
o = o[~junk].reset_index(drop=True)

# a license name that is still a legal entity ("Daroma Holdings", "Rudolph E Robinson Enterprises": possibly a person's name) is never shown:
# an unmatched map listing for a place to eat within 40 m lends its name, else the record is hidden with the non-restaurants
o["name_out"] = o.name_out.str.replace(r"^(?:Under New Management|New Owners?|Grand Opening|Now Open)\s*[-–:]\s*", "", regex=True, case=False)
LEGAL_END = re.compile(r"(?i)(?:\b(?:llc|l\.l\.c|inc|corp|corporation|ltd)\b\.?|''llc''|\binc\.s)\s*$")
FOODISH = re.compile(r"(?i)\b(?:restaurant|cafe|café|grill|kitchen|pizza|bar|pub|tavern|bistro|diner|deli|bakery|coffee|seafood|sushi|taco|burger|bbq|"
                     r"cantina|eatery|steak|wings|subs|sandwich|cuban|oyster|crab|fish|chicken|thai|chinese|mexican|italian|indian|"
                     r"juice|smoothie|ice cream|donut|bagel|tea|boba|pho|ramen|noodle|buffet|lounge|saloon|brewing|brewery)\b")
legal_left = o.src.eq("official") & (o.name_out.str.contains(LEGAL_END)
                                     | (o.name_out.str.upper().str.contains(LEGALISH) & ~o.name_out.str.contains(FOODISH)))
lg = 0
if legal_left.any():
    S1 = pd.read_pickle(f"{FL}/stage1.pkl")
    S1 = S1[~S1.j_junk & S1.name.notna() & S1.cat.isin(["restaurant", "casual_eatery", "bar", "fast_food_restaurant", "coffee_shop", "cafe"])]
    for i_ in o.index[legal_left]:
        la_, lo_ = o.at[i_, "lat"], o.at[i_, "lon"]
        near = S1[(abs(S1.lat - la_) < 0.0004) & (abs(S1.lon - lo_) < 0.0004)]
        if len(near) == 1:
            o.at[i_, "name_out"] = tidy(near.name.iat[0], None); lg += 1
            o.at[i_, "via"] = "license row, listing's name for a legal name"
        else:
            o.at[i_, "legal_hidden"] = True
o["legal_hidden"] = o.get("legal_hidden", pd.Series(False, index=o.index)).fillna(False).astype(bool)
print("legal-entity names replaced by a listing's:", lg, "| hidden:", int(o.legal_hidden.sum()), o.name_out[o.legal_hidden].head(8).tolist())

# ---------------------------------------------------------------- not restaurants (hidden unless "include non-restaurants" is on)
STORE = re.compile(r"^(?:PUBLIX(?: SUPER MARKETS?)?(?: DELI)?|WINN DIXIE|SEDANOS|WALMART\b.*|COSTCO\b.*|TARGET|SAMS CLUB|BJS WHOLESALE.*|ALDI|LIDL|"
                   r"TRADER JOES|WHOLE FOODS(?: MARKET)?|THE FRESH MARKET|FRESH MARKET|SPROUTS(?: FARMERS MARKET)?|WAWA|RACE ?TRAC|CIRCLE K|"
                   r"7 ELEVEN|SPEEDWAY|SUNOCO|SHELL|CHEVRON|MOBIL|EXXON|MARATHON|CITGO|VALERO|BP|GATE|KWIK STOP|FOOD MART|MINI MART|"
                   r"BUC EES|DOLLAR GENERAL|FAMILY DOLLAR|CVS|WALGREENS|DASHMART)$|\b(?:SAMS CLUB|PUBLIX|WINN DIXIE|SEDANOS|BIMBO BAKERIES|"
                   r"BAKERY OUTLET|THRIFT STORE|HUNT BROTHERS|HOT STUFF (?:PIZZA|FOODS|KITCHEN)|KRISPY KRUNCHY|CHESTERS (?:FRIED )?CHICKEN|"
                   r"GAS STATION|FOOD STORE|FOOD MART|SUPERMARKET|SUPER MARKET|MINI MARKET|CONVENIENCE|TRAVEL (?:CENTER|PLAZA|STOP)|TRUCK STOP|"
                   r"TRUCKSTOP|PILOT FLYING J|FLYING J|LOVES TRAVEL|FARMERS FRIDGE|MRBEAST|MR BEAST|ITS JUST WINGS|WOW BAO|GHOST KITCHEN|"
                   r"VIRTUAL KITCHEN|LIQUORS? (?:STORE|MART|DEPOT|OUTLET|BARN|WAREHOUSE)|LIQUORS?$|TOTAL WINE|ABC FINE WINE|WINE AND SPIRITS|"
                   r"AND SPIRITS$|GENTLEM[AE]NS CLUB|SHOWGIRLS|CABARET|STRIP CLUB|SCORES|TOOTSIES|TRAMPOLINE|INDOOR PLAYGROUND|DISPENSARY|"
                   r"CANNABIS|MARIJUANA|TRULIEVE|MEAT MARKET|MEATS$|BUTCHER|JERKY|VENDING|COMMISSARY|FOOD PANTRY|FOOD BANK|"
                   r"WINE (?:MERCHANTS?|SHOP|STORE|DEPOT|OUTLET)|HOOKAH SUPPLY|SMOKE SHOP|VAPE)\b")
REALFOOD = re.compile(r"\b(?:RESTAURANT|GRILL|BAR|PUB|TAVERN|PIZZA|CAFE|KITCHEN|STEAK|BISTRO|DINER|BREWING|BREWERY|TAP|SALOON|"
                      r"TAPROOM|LOUNGE|INN|EATERY|BURGERS?|BBQ|TACOS?|DRIVE IN|DELI|COFFEE|ICE CREAM|CREAMERY|BAKERY|DONUTS?|"
                      r"CANTINA|TAQUERIA|BURRITOS?|SEAFOOD|OYSTERS?|RAW BAR|FISH|CRAB|SUSHI|CUBAN|CAFETERIA|VENTANITA)\b")
CANDY = re.compile(r"\b(?:CANDY|CANDIES|FUDGE|POPCORN|CONFECTION\w*|CHOCOLATES?|CHOCOLATIER|TRUFFLES?|SWEETS? SHOPPE?|KETTLE CORN|NUTRITION)\b")
HARD = re.compile(r"\b(?:AIRPORT|TERMINAL|CONCOURSE|HARD ROCK STADIUM|RAYMOND JAMES STADIUM|AMWAY CENTER|KASEYA CENTER|LOANDEPOT PARK|"
                  r"TROPICANA FIELD|CAMPING WORLD STADIUM|EVERBANK|DAILYS PLACE|FAIRGROUNDS?|STATE FAIR|SPEEDWAY CONCESSIONS|LEVY|AVIANDS|SODEXO|"
                  r"ARAMARK|DELAWARE NORTH|CENTERPLATE|COMPASS GROUP|CHARTWELLS|BON APPETIT|HMSHOST|OTG|EUREST|SSP AMERICA|PARADIES|"
                  r"LEGENDS HOSPITALITY|DELTA SKY CLUB|UNITED CLUB|AMERICAN AIRLINES ADMIRALS|ADMIRALS CLUB|CENTURION LOUNGE|COMMISSARY|"
                  r"DINING HALL|UNIVERSITY DINING|CORRECTIONAL|PRISON|DETENTION|JAIL|SENIOR DINING|AIR FORCE BASE|NAVAL AIR STATION|"
                  r"NAS JAX|MACDILL|EGLIN|TYNDALL|PATRICK SPACE FORCE|HURLBURT|CRUISE TERMINAL|PORTMIAMI|GUN CLUB|SHOOTING RANGE)\b")
SOFT = re.compile(r"\b(?:STADIUM|ARENA|AMPHITHEATER|AMPHITHEATRE|FESTIVAL|CONCESSIONS?|CONCESSION STAND|FOOD ?SERVICES?|UNIVERSITY|COLLEGE|SCHOOL|"
                  r"ACADEMY|ELEMENTARY|STUDENT|CAMPUS|HOSPITAL|MEDICAL CENTER|CLINIC|HEALTH CENTER|SENIOR|RETIREMENT|ASSISTED LIVING|NURSING|"
                  r"CARE CENTER|REHAB|CHURCH|PARISH|CONGREGATION|TEMPLE|SYNAGOGUE|MOSQUE|MINISTR(?:Y|IES)|VFW|AMERICAN LEGION|AMVETS|"
                  r"EAGLES|FRATERNAL ORDER|ELKS LODGE|MOOSE LODGE|KNIGHTS OF COLUMBUS|COUNTRY CLUB|GOLF CLUB|GOLF COURSE|GOLF CLUBHOUSE|GUN CLUB|SHOOTING|RIFLE|"
                  r"YACHT CLUB|ATHLETIC CLUB|SOCIAL CLUB|TENNIS CLUB|RACQUET CLUB|BEACH CLUB|CATERING|CATERERS?|BANQUETS?|BANQUET HALL|"
                  r"EVENT (?:CENTER|VENUE|SPACE)|CONVENTION CENTER|CONFERENCE CENTER|MUSEUM|ZOO|AQUARIUM|THEATER|THEATRE|CINEMAS?|"
                  r"BOWLING|LANES|CASINO|HOTEL|MOTEL|INN AND SUITES|SUITES|MARRIOTT|HILTON|HYATT|SHERATON|WESTIN|HOLIDAY INN|HAMPTON INN|"
                  r"FAIRFIELD INN|RESIDENCE INN|COURTYARD|SPRINGHILL|RADISSON|BEST WESTERN|COMFORT INN|SUPER 8|RED ROOF|DAYS INN|LA QUINTA|"
                  r"EMBASSY SUITES|DOUBLETREE|WYNDHAM|LOEWS|RITZ CARLTON|FOUR SEASONS|CORPORATE|EMPLOYEE|CAFETERIA|MOBILE|FOOD TRUCK|"
                  r"KIOSK|CART|GYM|FITNESS|YMCA|YWCA|BOYS AND GIRLS CLUB|DAYCARE|DAY CARE|CHILD CARE|CHILDCARE|LEARNING CENTER|MILITARY|"
                  r"NATIONAL GUARD|BUILDING|POOL BAR|POOL GRILL|POOLSIDE|CLUBHOUSE|CONDOMINIUM|ASSOCIATION|HOA|MARINA|RV RESORT|"
                  r"CAMPGROUND|MOBILE HOME|ESTATES|PARK OPERATIONS|VENDING)\b")
kd = o.name_out.map(norm_name).fillna("")
k_ = o.k.fillna("")
busy = o.reviews.fillna(0) >= 200
gfirst = o.gcats.fillna("").str.split("|").str[0]
plainly_food = kd.str.contains(REALFOOD) | o.cat.isin(["bar", "brewery", "coffee_shop", "cafe"]) \
    | gfirst.str.contains(r"\b(?:Bar|Pub|Restaurant|Cafe|Café|Coffee|Tavern|Grill|Brewery|Diner|Bakery)\b", regex=True)
brand_store = o.brand_n.isin(["Publix", "Winn-Dixie", "Sedano's", "Walmart", "Target", "Wawa", "RaceTrac", "Circle K", "7-Eleven", "Sheetz",
                              "Buc-ee's", "Love's", "Pilot", "Kwik Stop", "Hunt Brothers Pizza", "Hot Stuff Pizza", "Krispy Krunchy Chicken",
                              "MrBeast Burger", "It's Just Wings"])
store = kd.str.contains(STORE) | k_.str.contains(r"\b(?:GAS STATION)\b") | brand_store \
    | (o.dom.isin(STORE_DOMS_ALL) & ~plainly_food) | (kd.str.contains(CANDY) & ~kd.str.contains(REALFOOD) & ~busy)
venue = kd.str.contains(HARD) | k_.str.contains(HARD) | o.name.fillna("").str.upper().str.contains(r"\(T-?\d|\bGATE [A-Z]?\d|\bCONCOURSE [A-H]\b", regex=True) \
    | (kd.str.contains(SOFT) & ~(busy | plainly_food))
lic_only = o.src.eq("official")
kind_lic = o.get("kind_lic", pd.Series(None, index=o.index))
venue |= lic_only & kind_lic.isin(["park", "catering"])
LICENSE_ONLY_NONREST = re.compile(r"\b(?:APARTMENTS?|POOLS?|SWIM|AQUATIC|ASSOCIATION|ATTN|C O|EVENTS?|STUDIOS?|BOATS|CHARTERS?|CRUISES?|"
                                  r"SPORTS CENTER|HOSPITALITY GROUP|HEALTH|CONDOMINIUMS?|HOMEOWNERS|NEIGHBORHOOD|COMMUNITY|PARKS AND REC|RECREATION|"
                                  r"CAMP|BIBLE|FOUNDATION|SOCIETY|COUNCIL|LEAGUE|UNION|INSTITUTE|CENTER$|FARMS?|AMUSEMENT|PREP|EDUCATIONAL|"
                                  r"ENTERTAINMENT|CORPORATION|HOLDINGS|MANAGEMENT|VENTURES|FIELD|GOLF|COUNTRY CLUB|RACQUET|LODGING|HOTEL|MOTEL|"
                                  r"SUITES|THEATRE|THEATER|CINEMA|BOWL|LANES|STADIUM|ARENA|RESORT|VILLAS?|CONDO|CLUB$|MARINA|SCHOOL|ACADEMY|"
                                  r"CHURCH|HOSPITAL|SENIOR|LIVING|CARE|REHAB|SHIP|AIRLINES?)\b")
club = kd.str.contains(r"\bCLUB\b") & ~kd.str.contains(r"NIGHT ?CLUB|CLUB HOUSE GRILL|SANDWICH|SUPPER CLUB")
venue |= lic_only & (kd.str.contains(LICENSE_ONLY_NONREST) | club) & ~busy & ~kd.str.contains(REALFOOD)
o["venue"] = store | venue | o.legal_hidden
# Disney and Universal: a restaurant inside a ticketed park or a resort stays (and says so); theme-park carts and kiosks are hidden
o["legal"] = [F.legal.iat[int(b)] if b == b else None for b in o.biz]
o["mouse"] = o.legal.fillna("").str.upper().str.contains(r"WALT DISNEY|DISNEY PARKS|DISNEY WORLD|DISNEY VACATION|UNIVERSAL CITY DEVEL|UNIVERSAL ORLANDO", regex=True)
print("non-restaurants flagged:", int(o.venue.sum()), "| stores:", int(store.sum()), "| venues:", int((venue & ~store).sum()),
      "| Disney/Universal-operated places:", int(o.mouse.sum()))

# ---------------------------------------------------------------- honors and hand-checked facts (data/research)
for col in ("jbf", "michelin", "green_star", "founded", "founded_note", "cur_tags", "dishes", "rnote", "rsite", "seasonal", "evidence", "aka"):
    o[col] = None
o["name_rank"] = np.nan
match_curated = curated_matcher(o)
o["hc"] = False
matched_cur, unmatched = 0, []
for c in CUR:
    if c.get("open") is False:
        continue
    best = match_curated(c)
    if best is None:
        unmatched.append(c["name"] + " (" + (c.get("city") or "") + ")")
        continue
    matched_cur += 1
    i = o.index[best]
    o.at[i, "hc"] = True
    # a hand-checked place shows its verified name ("Versailles Restaurant", not a listing's "Cafe Versailles Calle 8"); the old one
    # stays searchable as an aka. MICHELIN's spelling first, then the place's own site, then James Beard's.
    vname = re.sub(r"\s*\([^)]*\)", "", c["name"]).strip()
    if vname and c.get("name_rank", 1) > (o.at[i, "name_rank"] if "name_rank" in o.columns and o.at[i, "name_rank"] == o.at[i, "name_rank"] else 0):
        if norm_name(vname) != norm_name(o.at[i, "name_out"]):
            o.at[i, "aka"] = o.at[i, "name_out"]
        o.at[i, "name_out"] = vname
        o.at[i, "name_rank"] = c.get("name_rank", 1)
    for col, vals in (("jbf", c.get("james_beard")), ("cur_tags", c.get("tags")), ("dishes", c.get("dishes"))):
        if vals:
            have = [x for x in (o.at[i, col] or "").split("; ") if x]
            o.at[i, col] = "; ".join(have + [v for v in dict.fromkeys(vals) if v not in have])
    for col, v in (("michelin", c.get("michelin")), ("green_star", c.get("green_star") or None), ("founded", c.get("founded")),
                   ("founded_note", c.get("founded_note")), ("rnote", c.get("note")), ("rsite", c.get("website")), ("seasonal", c.get("seasonal")),
                   ("evidence", c.get("evidence_date"))):
        if v and not o.at[i, col]:
            o.at[i, col] = v
print(f"verified entries matched: {matched_cur}/{sum(1 for c in CUR if c.get('open') is not False)}; unmatched ({len(unmatched)}): {unmatched[:30]}")
# a closed place is matched by name, never by address alone: a new business often sits at a closed one's address
gone = [(c["name"], o.name_out.iat[b]) for c in CLOSED for b in [match_curated({**c, "address_ok": False})] if b is not None]
drop_closed = {o.index[b] for c in CLOSED for b in [match_curated({**c, "address_ok": False})] if b is not None}
o = o.drop(index=list(drop_closed)).reset_index(drop=True)
print("verified closed, removed:", len(drop_closed), gone[:20])

# ---------------------------------------------------------------- Florida tags: hand-checked (both builds) or, on the web, 3+ Google reviews mentioning it
TAGS = ["cuban", "stonecrab", "grouper", "keys", "oyster", "fishcamp", "latin", "oldest"]
tags_c = o.cur_tags.fillna("").str.lower()
SIGF = f"{FL}/review_signals.parquet"
SIG = pd.read_parquet(SIGF).set_index("gmap_id") if (os.path.exists(SIGF) and not APP) else None
for k in ("cuban", "cafecito", "stonecrab", "grouper", "keylime", "oyster", "fishdip", "conch"):
    o["n_" + k] = [int(SIG["n_" + k].get(g, 0)) if SIG is not None and isinstance(g, str) and g in SIG.index else 0 for g in o.gmap_id]
    o["r_" + k] = [SIG["r_" + k].get(g) if SIG is not None and isinstance(g, str) and g in SIG.index else None for g in o.gmap_id]
rv = o.reviews.fillna(0)
ment = lambda *ks: sum(o["n_" + k] for k in ks)
strong = lambda n: (n >= 3) & (n >= 0.02 * rv)
o["t_cuban"] = o.hc & tags_c.str.contains(r"\bcuban\b|cafecito")
o["t_stonecrab"] = o.hc & tags_c.str.contains("stonecrab|stone crab")
o["t_grouper"] = o.hc & tags_c.str.contains("grouper")
# conch counts as a Keys classic as conch fritters (the guide's promise) or in the Keys: Chef Creole's Haitian fried and stewed conch
# belongs to Latin & Caribbean, not Keys Classics
dish_c = o.dishes.fillna("").str.lower()
o["t_keys"] = o.hc & (tags_c.str.contains(r"\bkeys\b|keylime|key lime")
                      | (tags_c.str.contains("conch") & (dish_c.str.contains("conch fritter") | o.region.eq("Keys"))))
o["t_oyster"] = o.hc & tags_c.str.contains("oyster")
o["t_fishcamp"] = o.hc & tags_c.str.contains("fishcamp|fish camp|smokedfish|smoked fish")
o["t_latin"] = o.hc & tags_c.str.contains(r"\blatin\b|minorcan|haitian|venezuelan|colombian|nicaraguan|puerto rican")
o["t_oldest"] = o.hc & pd.to_numeric(o.founded, errors="coerce").le(1960)
if not APP:   # the web leaderboard also counts places 3+ Google reviews (2%+ of them) called out for it in 2021
    o["t_cuban"] |= strong(ment("cuban", "cafecito"))
    o["t_stonecrab"] |= strong(ment("stonecrab"))
    o["t_grouper"] |= strong(ment("grouper"))
    o["t_keys"] |= strong(ment("keylime", "conch")) & o.county.eq("Monroe")
    o["t_oyster"] |= strong(ment("oyster"))
    o["t_fishcamp"] |= strong(ment("fishdip"))
o["honored"] = o.jbf.notna() | o.michelin.notna() | o.t_oldest
o.loc[o.michelin.notna() & o.cuisine.eq("Bar & Pub"), "cuisine"] = "American & Other"
o.loc[o.michelin.isin(["1 Star", "2 Stars", "3 Stars"]) & o.price_est.eq(1), "price"] = 4
o.loc[o.honored | o.hc, "venue"] = False
print("tags:", {t: int(o["t_" + t].sum()) for t in TAGS})

# ---------------------------------------------------------------- DBPR inspections (official dispositions; no grade)
I = pd.read_parquet(f"{FL}/inspections.parquet")
I = I[I.date >= pd.Timestamp("2023-07-01")].copy()
I["d"] = I.date.dt.strftime("%Y-%m-%d")
I["key"] = I.ltype.astype(str) + "|" + I.num.astype(str)
I = I.sort_values(["key", "date", "visit"])
DISP = sorted(I.disp.dropna().unique().tolist())
ITYPE = sorted(I.itype.dropna().unique().tolist())
GRP = {"met": 0, "followup": 1, "closed": 2}
by_key = {k: g for k, g in I.groupby("key")}
C_ = pd.read_parquet(f"{FL}/closures.parquet")
clo_by = {k: g.sort_values("date") for k, g in C_.groupby("num")}
R_ = pd.read_parquet(f"{FL}/discipline.parquet")
fine_by = {k: g.sort_values("order_date") for k, g in R_.groupby("num")}
cols_i = ["in_g", "in_disp", "in_d", "in_t", "in_rd", "in_hp", "in_im", "in_bs", "in_n", "in_eo", "in_hist", "in_cl", "in_fines", "lic_no", "seats"]
recs = []
for b in o.biz:
    if b != b:
        recs.append([None] * len(cols_i)); continue
    f = F.loc[int(b)]
    g = by_key.get(f"{f.ltype}|{f.num}")
    cl = clo_by.get(f.num)
    fn = fine_by.get(f.num)
    cl_list = [[str(r.date.date()), r.reason, str(r.reopened.date()) if r.reopened == r.reopened and r.reopened is not None else None]
               for r in cl.itertuples()] if cl is not None else []
    fn_list = [[str(r.order_date.date()), int(r.fine) if r.fine == r.fine else None] for r in fn.itertuples()] if fn is not None else []
    if g is None or not len(g):
        recs.append([None] * 10 + [None, cl_list or None, fn_list or None, f.lic, int(f.seats)]); continue
    last = g.iloc[-1]
    rout = g[g.itype.eq("Routine - Food")]
    lr = rout.iloc[-1] if len(rout) else None
    hist = [[r.d, r.itype, r.disp, None if r.hp != r.hp else int(r.hp), None if r.im != r.im else int(r.im), None if r.bs != r.bs else int(r.bs), r.cats]
            for r in g.iloc[::-1].head(12).itertuples()]
    recs.append([GRP.get(last.group), last.disp, last.d, last.itype, lr.d if lr is not None else None,
                 None if lr is None or lr.hp != lr.hp else int(lr.hp), None if lr is None or lr.im != lr.im else int(lr.im),
                 None if lr is None or lr.bs != lr.bs else int(lr.bs), int(len(g)), int((g.disp == "Emergency order recommended").sum()),
                 hist, cl_list or None, fn_list or None, f.lic, int(f.seats)])
o[cols_i] = pd.DataFrame(recs, index=o.index, columns=cols_i)
print("places with DBPR inspections:", int(o.in_disp.notna().sum()), "| latest result group:",
      o.in_g.map({0: "met", 1: "followup", 2: "closed"}).value_counts().to_dict(), "| through", DMETA["through"])


def own_jbf(jb):
    """James Beard lines about the restaurant or its chef; an Outstanding Restaurateur honor belongs to the owners' whole group."""
    return "; ".join(h for h in (jb or "").split("; ") if "Restaurateur" not in h)


def hon_flags(x):
    jb = own_jbf(x.jbf)
    return ((1 if "America's Classic" in jb else 0) | (2 if re.search(r"\bwinner\b", jb) else 0) | (4 if re.search(r"(?<!semi)finalist", jb) else 0)
            | (8 if "semifinalist" in jb else 0) | (16 if x.t_oldest else 0))


MI_LEVEL = {"Recommended": 1, "Bib Gourmand": 2, "1 Star": 3, "2 Stars": 4, "3 Stars": 5}
o = o[o.lat.notna()].reset_index(drop=True)

# ---------------------------------------------------------------- the same place twice: same name at the same street address, or
# (not a chain) the same name in one town within 400 m. The licensed record wins, then a hand-checked one; the kept copy inherits facts.
rank = o.tier.map({"official": 2, "both": 1, "listing": 0}).fillna(0) * 10 + o.hc.astype(int) * 5 + o.get("web", pd.Series(None, index=o.index)).notna().astype(int)
keyname = o.name_out.map(norm_name)
keyaddr = ["|".join(k) if all(k := street_key(s_)) else None for s_ in o.street]
drop, merged, seen = set(), [], {}
for pos, i in enumerate(o.index):
    if keyaddr[pos] and keyname[i]:
        k = (keyname[i], keyaddr[pos], o.city[i])
        if k in seen:
            j = seen[k]
            lose = i if rank[i] <= rank[j] else j
            drop.add(lose); seen[k] = j if lose == i else i
            merged.append((seen[k], lose))
        else:
            seen[k] = i
single = o[(o.chain_n.fillna(1) < 2) & ~o.index.isin(drop)]
for (nm_, town), g in single.groupby([keyname[single.index], single.city]):
    if len(g) < 2 or not nm_:
        continue
    idx = list(g.index)
    for a_ in range(len(idx)):
        for b_ in range(a_ + 1, len(idx)):
            i, j = idx[a_], idx[b_]
            if i in drop or j in drop or (o.at[i, "official"] and o.at[j, "official"]):
                continue
            if math.hypot((o.at[j, "lat"] - o.at[i, "lat"]) * 111, (o.at[j, "lon"] - o.at[i, "lon"]) * 99) < 0.4:
                lose = i if rank[i] <= rank[j] else j
                drop.add(lose); merged.append((j if lose == i else i, lose))
for keep_, lose in merged:
    for col in [c for c in o.columns if c.startswith("t_")] + ["hc", "honored"]:
        if bool(o.at[lose, col]) and not bool(o.at[keep_, col]):
            o.at[keep_, col] = o.at[lose, col]
    for col in ("jbf", "michelin", "green_star", "founded", "founded_note", "cur_tags", "dishes", "rnote", "rsite", "seasonal", "evidence", "web",
                "phone") + tuple(cols_i):
        if col in o.columns and (o.at[keep_, col] is None or (isinstance(o.at[keep_, col], float) and o.at[keep_, col] != o.at[keep_, col])):
            v = o.at[lose, col]
            if v is not None and not (isinstance(v, float) and v != v):
                o.at[keep_, col] = v
print("same place twice, merged:", len(drop))
o = o.drop(index=list(drop)).reset_index(drop=True)
webs = o.get("web", pd.Series("", index=o.index)).fillna("").astype(str) + " " + o.rsite.fillna("").astype(str)
adult = o.name_out.str.contains(r"gentlem[ae]n'?s club|exotic dancer|strip club|adult entertainment|showclub|cabaret|^scores\b|tootsie'?s cabaret|^tootsies$|"
                                r"cheetah (?:lounge|club|hallandale|pompano)|booby trap|king of diamonds|e11even|rachel'?s (?:steakhouse|gentlem|club)|"
                                r"thee dollhouse|^pink pony|mons venus|club pink",
                                case=False, regex=True) \
    | webs.str.contains(r"gentlemensclub|stripclub|cheetahclub|scoresclub|tootsies|kingofdiamonds|e11evenmiami|theedollhouse", case=False, regex=True)
print("adult clubs removed:", int(adult.sum()), o.name_out[adult].tolist()[:12])
o = o[~adult].reset_index(drop=True)
smoke = o.name_out.str.contains(r"\bvape\b|smoke shop|\btobacco\b|cigar lounge|\bcbd\b|dispensary|head shop|cannabis|marijuana|\bkava\b|kratom", case=False, regex=True)
o.loc[smoke, "venue"] = True
fixes = json.load(open(f"{DATA}/research/name_fixes.json")) if os.path.exists(f"{DATA}/research/name_fixes.json") else []
for fx in fixes:
    hit = (o.name_out.str.upper() == fx["name"].upper()) & (o.city == fx["town"]) & o.street.fillna("").str.startswith(fx["street_number"] + " ")
    o.loc[hit, "name_out"] = fx["fixed"]
    print("name fix:", fx["name"], "->", fx["fixed"], int(hit.sum()))

# ---------------------------------------------------------------- sales / profit: the Chicago model (web only)
auv = {a["brand"]: a for a in json.load(open(f"{DATA}/chain_auv.json")) if a.get("auv_usd")}
med_rev = o[o.reviews.notna() & (o.chain_n < 5)].groupby("price").reviews.median()
rel = (o.reviews + 10) / (o.price.map(med_rev) + 10)
bump = np.where(o.bar, 1.15, 1.0)
o["rev"] = (o.price.map(BASE) * bump * rel.fillna(0.6) ** B_FIT).clip(100_000, 40_000_000)
o["rev_src"] = np.where(o.reviews.notna(), "model", "model-low")
n_auv = 0
for b, a in auv.items():
    sel = o.brand_n == b
    if not sel.any():
        continue
    n_auv += 1
    med = o.loc[sel, "reviews"].median()
    r_ = (o.loc[sel, "reviews"] / med) ** 0.35 if med == med else pd.Series(np.nan, index=o.index[sel])
    o.loc[sel, "rev"] = a["auv_usd"] * r_.fillna(0.85).clip(0.6, 1.5)
    o.loc[sel, "rev_src"] = "chain"
o.loc[o.venue & o.rev_src.isin(["model", "model-low"]), "rev_src"] = "venue"
m_rat = o.rating.mean()
o["bayes"] = (o.reviews * o.rating + 40 * m_rat) / (o.reviews + 40)
margin = o.price.map(MARGIN)
margin = o.cuisine.map(MARGIN_CUISINE).fillna(margin) * (0.8 + 0.4 * pct(o.bayes).fillna(40) / 100)
o["margin"] = margin.round(4)
o["profit"] = o.rev * o.margin
o["value_raw"] = o.bayes - 0.18 * (o.price - 1)
jb = o.jbf.map(lambda v: own_jbf(v) if isinstance(v, str) else "")
MI_PTS = {"3 Stars": 70, "2 Stars": 62, "1 Star": 52, "Bib Gourmand": 36, "Recommended": 22}
acc = (jb.str.contains("America's Classic") * 40 + jb.str.contains(r"\bwinner\b") * 26
       + (jb.str.contains(r"(?<!semi)finalist") & ~jb.str.contains(r"\bwinner\b")) * 14 + (jb.str.contains("semifinalist") & ~jb.str.contains(r"(?<!semi)finalist|\bwinner\b")) * 6
       + o.michelin.map(MI_PTS).fillna(0) + o.t_oldest * 16).clip(upper=70)
years = (2026 - pd.to_numeric(o.founded, errors="coerce")).clip(lower=0)
o["s_icon"] = np.where(o.honored, (acc + years.fillna(0).clip(upper=100) / 100 * 24 + pct(np.log1p(o.reviews)).fillna(0) / 100 * 14).clip(upper=100), np.nan)


def r(x, n=0):
    if x is None or (isinstance(x, float) and x != x):
        return None
    return int(round(float(x))) if n == 0 else round(float(x), n)


def clean_url(u):
    base_, _, q = u.partition("?")
    keep_q = [kv for kv in q.split("&") if kv and not re.match(r"(rwg_token|utm_[a-z]+|fbclid|gclid|y_source)=", kv)]
    return base_ + ("?" + "&".join(keep_q) if keep_q else "")


COUNTIES = sorted(o.county.dropna().unique().tolist())
REGIONS = list(official.REGIONS)
SRCS = ["official", "meta", "AllThePlaces", "DAC", "research", "BrightQuery", "Foursquare", "Microsoft"]
GROUPS = ["Met Inspection Standards", "Follow-Up Inspection Required", "Facility Temporarily Closed"]
# DBPR's food service violation categories since 1/1/2013 (public-records layout page), in DBPR's words; 45-49 are reporting-only fire items
CATNAMES = {"1": "Approved source", "2": "Original container: properly labeled, date marking, consumer advisory",
            "3": "Time and temperature control (PH/TCS foods)", "4": "Facilities to maintain PH/TCS at the proper temperature",
            "5": "Food and food equipment thermometers provided and accurate", "6": "PH/TCS foods properly thawed",
            "7": "Unwrapped or PH/TCS food not re-served", "8": "Food protection, cross-contamination",
            "9": "Bare hand contact with RTE food; Alternative Operating Procedure", "10": "In use food dispensing utensils properly stored",
            "11": "Employee health knowledge; ill/symptomatic employee present", "12": "Hands washed and clean, good hygienic practices, eating/drinking/smoking",
            "13": "Clean clothes; hair restraints; jewelry; painted/artificial fingernails",
            "14": "Food-contact and nonfood-contact surfaces designed, constructed, maintained, installed, located",
            "16": "Dishwashing facilities; chemical test kit(s); gauges", "21": "Wiping cloths; clean and soiled linens; laundry facilities",
            "22": "Food-contact surfaces clean and sanitized", "23": "Non-food contact surfaces clean",
            "24": "Storage/handling of clean equipment, utensils; air drying", "25": "Single-service and single-use items",
            "27": "Water source safe, hot (100°F) and cold under pressure", "28": "Sewage and wastewater disposed properly",
            "29": "Plumbing installed and maintained; mop sink; water filters; backflow prevention", "31": "Hand wash sinks, hand washing supplies and hand wash sign",
            "32": "Bathrooms", "33": "Garbage and refuse; premises maintained",
            "35": "No presence or breeding of insects/rodents/pests; no live animals, outer openings protected from insects/pests, rodent proof",
            "36": "Floors, walls, ceilings and attached equipment properly constructed and clean; rooms and equipment properly vented",
            "38": "Lighting provided as required; fixtures shielded or bulbs protected", "40": "Employee personal belongings", "41": "Chemicals/toxic substances",
            "42": "Cleaning and maintenance equipment", "43": "Complete separation from living/sleeping area/private premise; kitchen restricted",
            "50": "Current license properly displayed", "51": "Other conditions sanitary and safe operation", "52": "Misrepresentation; misbranding",
            "53": "Food management certification valid / Employee training verification", "54": "Florida Clean Indoor Air Act", "55": "Automatic Gratuity Notice"}
meta_common = {"generated": TODAY, "overture_release": "2026-09-23.1", "inspections_through": DMETA["through"], "dbpr_fetched": DMETA["fetched"],
               "inspections_since": "2023-07-01",
               "counties": COUNTIES, "regions": REGIONS, "tags": TAGS, "srcs": SRCS, "groups": GROUPS, "dispositions": DISP, "itypes": ITYPE,
               "catnames": CATNAMES}

if APP:
    nv = o[~o.venue]
    CITIES = sorted(o.city.dropna().unique().tolist()); CUIS = sorted(o.cuisine.unique().tolist()); BRANDS = sorted(o.brand_n.dropna().unique().tolist())
    ci, cu, br, cy = ({c: i for i, c in enumerate(L)} for L in (CITIES, CUIS, BRANDS, COUNTIES))
    TIER = {"listing": 0, "both": 1, "official": 2}
    places, seen_ids, via_out = [], set(), []
    # the app ships a statewide core file (lists, search, map: what every screen needs at launch) and one detail file per region
    # (inspection history, closures, license number, phone, website), read only when a place opens: the full statewide file was 24 MB
    details = collections.defaultdict(dict)
    RG = {r: i for i, r in enumerate(REGIONS)}
    LINKS = json.load(open(f"{FL}/website_check.json")) if os.path.exists(f"{FL}/website_check.json") else None
    link_drops, link_cands = collections.Counter(), {}
    for i, x in o.iterrows():
        # a stable id: the DBPR license number when there is one, else the normalized name + ~100 m cell
        idsrc = x.lic_no if isinstance(x.lic_no, str) else f"{norm_name(x.name_out)}|{round(float(x.lat), 3)}|{round(float(x.lon), 3)}"
        p = {"id": hashlib.md5(idsrc.encode()).hexdigest()[:12], "n": x.name_out, "c": ci.get(x.city) if isinstance(x.city, str) else None,
             "cu": cu[x.cuisine], "t": TIER[x.tier], "s": SRCS.index(x.src) if x.src in SRCS else 1}
        dt_ = {}
        if isinstance(x.county, str): p["co"] = cy[x.county]
        rg = RG.get(x.region) if isinstance(x.region, str) else None
        if rg is not None: p["rg"] = rg
        if isinstance(x.street, str): p["a"] = nice(x.street, addr=True)
        if isinstance(x.zip, str) and re.match(r"^3[234]\d{3}", x.zip): p["z"] = x.zip[:5]
        p["la"], p["lo"] = round(float(x.lat), 5), round(float(x.lon), 5)
        if isinstance(x.brand_n, str): p["b"] = br[x.brand_n]
        if x.chain_n and int(x.chain_n) > 1: p["ch"] = int(x.chain_n)
        if x.venue: p["v"] = 1
        if x.bar: p["bar"] = 1
        if x.mouse: p["dw"] = 1
        tg = sum(1 << bi for bi, t_ in enumerate(TAGS) if bool(x["t_" + t_]))
        if tg: p["g"] = tg
        if x.hc: p["hc"] = 1
        if x.honored:
            p["h"] = hon_flags(x)
            if isinstance(x.michelin, str): p["mi"] = MI_LEVEL.get(x.michelin, 0)
            if x.green_star: p["gs"] = 1
            if isinstance(x.jbf, str): p["jbf"] = x.jbf
            p["ip"] = round(float(x.s_icon), 1)
        if x.founded == x.founded and x.founded is not None: p["f"] = int(float(x.founded))
        for k, col in (("fn", "founded_note"), ("note", "rnote"), ("dish", "dishes"), ("seas", "seasonal"), ("aka", "aka")):
            if isinstance(x[col], str) and x[col]: p[k] = x[col]
        # a hand-checked place links only the site its research found, never a listing's
        web = x.rsite if isinstance(x.rsite, str) else (x.web if isinstance(x.get("web"), str) and not x.hc else None)
        if web:
            w_ = clean_url(web)
            # what the link checker needs to tell this place's own page from a namesake's: the name, and where the place is
            c_ = link_cands.setdefault(w_, {"name": x.brand_n if isinstance(x.brand_n, str) else x.name_out, "chain": isinstance(x.brand_n, str),
                                            "towns": [], "zips": [], "phones": [], "streets": []})
            for k_, v_ in (("towns", x.city), ("zips", x.zip), ("phones", x.get("phone")), ("streets", x.street)):
                if isinstance(v_, str) and v_ and v_ not in c_[k_] and len(c_[k_]) < 8:
                    c_[k_].append(v_)
            # only links pipeline/check_websites.py verified (2xx, same site, names the place and its town, address or phone, no
            # news/directory/spam/parked page); unchecked ones wait
            if LINKS is not None and LINKS.get(w_, {}).get("ok"):
                dt_["w"] = LINKS[w_].get("ship") or w_
            else:
                link_drops[(LINKS or {}).get(w_, {}).get("why", "not checked yet")] += 1
        if isinstance(x.get("phone"), str) and x.phone: dt_["ph"] = x.phone
        if isinstance(x.lic_no, str): dt_["lic"] = x.lic_no
        if isinstance(x.in_disp, str):
            # core: what the Inspections guide sorts and shows on a row (DBPR's result group, the date, the latest routine counts)
            # as a compact array [g, d] or [g, d, hp, im, bs]: 53,000 small dictionaries were a third of the app's launch-time parse
            p["in"] = [None if x.in_g != x.in_g or x.in_g is None else int(x.in_g), x.in_d]
            if isinstance(x.in_rd, str):
                p["in"] += [r(x.in_hp), r(x.in_im), r(x.in_bs)]
            dt_["in"] = {"dp": DISP.index(x.in_disp), "t": ITYPE.index(x.in_t), "n": int(x.in_n), "eo": int(x.in_eo),
                         "rd": x.in_rd if isinstance(x.in_rd, str) else None,
                         "h": [[d, ITYPE.index(t) if t in ITYPE else -1, DISP.index(dp) if dp in DISP else -1, hp, im, bs] for d, t, dp, hp, im, bs, cats in x.in_hist[:8]]}
        if isinstance(x.in_cl, list): dt_["cl"] = x.in_cl[-5:]
        while p["id"] in seen_ids:
            p["id"] = p["id"] + "x"
        seen_ids.add(p["id"])
        places.append(p); via_out.append(x.get("via") if isinstance(x.get("via"), str) else None)
        if dt_:
            details[REGIONS[rg] if rg is not None else "Other"][p["id"]] = dt_
    print("website links dropped:", sum(link_drops.values()), link_drops.most_common(8))
    json.dump(link_cands, open(f"{FL}/website_candidates.json", "w"), indent=0, ensure_ascii=False)
    calib_app = json.load(open(f"{FL}/calibration_app.json"))
    out = {"v": 2, **meta_common, "cities": CITIES, "cuisines": CUIS, "brands": BRANDS, "count": len(places), "count_restaurants": int(len(nv)),
           "calibration": {"statewide": calib_app.get("statewide")}, "places": places}
    os.makedirs(SITE, exist_ok=True)
    json.dump(out, open(f"{SITE}/places.json", "w"), separators=(",", ":"), ensure_ascii=False, allow_nan=False, default=str)
    # for pipeline/qa_licenses.py only (not copied into the app): which step tied each place to its license
    json.dump({p_["id"]: v_ for p_, v_ in zip(places, via_out) if v_}, open(f"{FL}/app_via.json", "w"))
    for f_ in glob.glob(f"{SITE}/detail-*.json"):
        os.remove(f_)
    for reg, dd in details.items():
        json.dump(dd, open(f"{SITE}/detail-{re.sub(r'[^a-z]+', '-', reg.lower()).strip('-')}.json", "w"), separators=(",", ":"), ensure_ascii=False, allow_nan=False, default=str)
    json.dump(json.load(open(f"{FL}/fl_shapes.json")), open(f"{SITE}/fl_shapes.json", "w"), separators=(",", ":"))
    sizes = {os.path.basename(f_): os.path.getsize(f_) // 1024 for f_ in sorted(glob.glob(f"{SITE}/detail-*.json"))}
    print("APP: wrote", len(places), "places (", len(nv), "restaurants ) | core", os.path.getsize(f"{SITE}/places.json") // 1024, "KB | details (KB):", sizes,
          "| tiers:", nv.tier.value_counts().to_dict(), "| tags:", {t_: int(nv["t_" + t_].sum()) for t_ in TAGS}, "| hand-checked:", int(nv.hc.sum()),
          "| honored:", int(nv.honored.sum()), "| inspections:", int(nv.in_disp.notna().sum()))
    sys.exit(0)

# ---------------------------------------------------------------- web leaderboard export (columnar; Google 2021 ratings labeled as such)
CITIES = sorted(o.city.dropna().unique().tolist()); CUIS = sorted(o.cuisine.unique().tolist()); BRANDS = sorted(o.brand_n.dropna().unique().tolist())
ci, cu, br, cy = ({c: i for i, c in enumerate(L)} for L in (CITIES, CUIS, BRANDS, COUNTIES))
SRC = {"model": 0, "model-low": 1, "chain": 2, "reported": 3, "venue": 4}
TIER = {"listing": 0, "both": 1, "official": 2}
SCALE = {"lat": 10000, "lon": 10000, "rating": 10, "margin": 1000, "value_raw": 1000}
C = collections.OrderedDict((c, []) for c in ["name", "addr", "city", "county", "zip", "lat", "lon", "cuisine", "brand", "chain_n", "rating", "reviews",
                                               "price", "price_est", "rev_k", "rev_src", "margin", "value_raw", "tier", "bar", "venue", "tags",
                                               "src", "hc", "dw"])
SP = {"hon": [], "insp": [], "sig": []}
SIGK = ["cuban", "cafecito", "stonecrab", "grouper", "keylime", "oyster", "fishdip", "conch"]
extra = {}
for i, x in o.iterrows():
    tg = sum(1 << b for b, t_ in enumerate(TAGS) if bool(x["t_" + t_]))
    z = int(x.zip[:5]) if isinstance(x.zip, str) and re.match(r"^3[234]\d{3}", x.zip) else None
    vals = {"name": x.name_out, "addr": nice(x.street, addr=True) if isinstance(x.street, str) else None,
            "city": ci.get(x.city) if isinstance(x.city, str) else None, "county": cy.get(x.county) if isinstance(x.county, str) else None,
            "zip": z, "lat": x.lat, "lon": x.lon, "cuisine": cu[x.cuisine],
            "brand": br.get(x.brand_n) if isinstance(x.brand_n, str) else None, "chain_n": int(x.chain_n), "rating": x.rating, "reviews": r(x.reviews),
            "price": int(x.price), "price_est": int(x.price_est), "rev_k": int(round(x.rev / 1000)), "rev_src": SRC[x.rev_src], "margin": x.margin,
            "value_raw": x.value_raw, "tier": TIER[x.tier], "bar": int(bool(x.bar)), "venue": int(bool(x.venue)), "tags": tg,
            "src": SRCS.index(x.src) if x.src in SRCS else 1, "hc": int(bool(x.hc)), "dw": int(bool(x.mouse))}
    if x.honored:
        SP["hon"].append([i, int(round(x.s_icon * 10)), hon_flags(x), MI_LEVEL.get(x.michelin, 0) if isinstance(x.michelin, str) else 0,
                          1 if x.green_star else 0])
    if isinstance(x.in_disp, str):
        SP["insp"].append([i, None if x.in_g != x.in_g or x.in_g is None else int(x.in_g), DISP.index(x.in_disp), x.in_d,
                           x.in_rd if isinstance(x.in_rd, str) else None, r(x.in_hp), r(x.in_im), r(x.in_bs), int(x.in_n), int(x.in_eo)])
    sg = [[k_i, int(x["n_" + k]), int(round(float(x["r_" + k]) * 100)) if x["r_" + k] is not None and x["r_" + k] == x["r_" + k] else None]
          for k_i, k in enumerate(SIGK) if x["n_" + k]]
    if sg:
        SP["sig"].append([i] + [v for s_ in sg for v in s_])
    for c, v in vals.items():
        if c in SCALE:
            v = None if v is None or v != v else int(round(float(v) * SCALE[c]))
        elif isinstance(v, float):
            v = None if v != v else v
        C[c].append(v.item() if hasattr(v, "item") else v)
    e = {k: v for k, v in (("jbf", x.jbf), ("michelin", x.michelin), ("founded", r(x.founded) if x.founded == x.founded and x.founded is not None else None),
                           ("founded_note", x.founded_note), ("note", x.rnote), ("dishes", x.dishes), ("seasonal", x.seasonal),
                           ("web", x.rsite if isinstance(x.rsite, str) else None), ("lic", x.lic_no if isinstance(x.lic_no, str) else None)) if isinstance(v, (str, int)) and v != ""}
    if isinstance(x.lic_no, str) and x.seats == x.seats and x.seats is not None:
        e["seats"] = int(x.seats)
    if isinstance(x.in_hist, list):   # compact: indexes into meta.itypes / meta.dispositions; categories for the latest visit only
        e["insp"] = [[d, ITYPE.index(t) if t in ITYPE else -1, DISP.index(dp) if dp in DISP else -1, hp, im, bs] for d, t, dp, hp, im, bs, cats in x.in_hist[:5]]
        if x.in_hist[0][6]:
            e["cats"] = x.in_hist[0][6]
        if len(x.in_hist) > 5:
            e["insp_n"] = len(x.in_hist)
    if isinstance(x.in_cl, list):
        e["closures"] = x.in_cl[-6:]
    if isinstance(x.in_fines, list):
        e["fines"] = x.in_fines[-6:]
    if e:
        extra[i] = e
nv = o[~o.venue]
meta = {**meta_common, "cities": CITIES, "cuisines": CUIS, "brands": BRANDS, "src": list(SRC), "tiers": list(TIER), "sigk": SIGK,
        "food_cost": dict(FOOD_COST), "spend": SPEND, "count": len(o), "count_restaurants": int(len(nv)),
        "count_official": int((nv.tier == "official").sum()), "count_both": int((nv.tier == "both").sum()), "count_listing": int((nv.tier == "listing").sum()),
        "n_cities": int(nv.city.nunique()), "rating_mean": round(float(m_rat), 3), "model": {"b": B_FIT, "n_chains": n_auv},
        "calibration": json.load(open(f"{FL}/calibration.json")), "n_honored": int(o.honored.sum())}
for _k, _v in list(C.items()) + list(SP.items()):
    _bad = [j for j, x in enumerate(_v) if (isinstance(x, float) and x != x) or (isinstance(x, list) and any(isinstance(y, float) and y != y for y in x))]
    if _bad: print("NaN in", _k, len(_bad), _v[_bad[0]])
os.makedirs(SITE, exist_ok=True)
json.dump({"n": len(o), "scale": SCALE, "cols": C, "sparse": SP, "meta": meta}, open(f"{SITE}/florida.json", "w"), separators=(",", ":"), allow_nan=False, default=str)
json.dump({"n": len(o), "extra": {str(k): v for k, v in extra.items()}}, open(f"{SITE}/fl_detail.json", "w"), separators=(",", ":"), allow_nan=False, default=str)
json.dump(json.load(open(f"{FL}/fl_shapes.json")), open(f"{SITE}/fl_shapes.json", "w"), separators=(",", ":"))
o.to_pickle(f"{FL}/stage2.pkl")
print("wrote", len(o), "places (", int(len(nv)), "restaurants ) in", nv.city.nunique(), "towns;", os.path.getsize(f"{SITE}/florida.json") // 1024,
      "KB | tiers:", nv.tier.value_counts().to_dict(), "| by region:", nv.region.value_counts().to_dict())
