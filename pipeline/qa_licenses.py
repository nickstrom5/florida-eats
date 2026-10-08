"""Does every place show its own license? -> prints suspects, exits 1 if any are left (run after FL_APP=1 florida.py)

A place in the app carries one DBPR license (detail file "lic"), and with it that license's inspections. When the two names share no
distinctive word (town names don't count) or say they serve different things, and the house numbers differ too, the inspections are
probably someone else's: Flagler Fish Company's license once sat on Flagler Tea Company. Each suspect is either a real mismatch to fix
in the pipeline or a known good pair to list in OK below, with why.
"""
import glob, json, sys
import os
import pandas as pd
from rapidfuzz import fuzz
from common import FL, DATA, norm_name, _stems, GENERIC, kind_conflict, real_share, town_words
from addr import street_nums
from listings_util import _close_words

D = json.load(open(f"{DATA}/app/places.json"))
DET = {}
for f in glob.glob(f"{DATA}/app/detail-*.json"):
    DET.update(json.load(open(f)))
L = pd.read_pickle(f"{FL}/official.pkl").drop_duplicates("lic").set_index("lic")   # keys: the business name, its DBAs and legal name
VIA = json.load(open(f"{FL}/app_via.json")) if os.path.exists(f"{FL}/app_via.json") else {}
# place ids checked by hand: the same business under another name at the same spot
OK = {
    "8c8d3970fd80",   # Country Creek Country Club (Estero): DBPR licenses its restaurant as THE VILLAGES OF COUNTRY CREEK, DBA CREEKSIDE
                      # RESTAURANT, on the club's grounds (21180 Country Creek Rd; the club's listing says 21131 Country Creek Dr)
}

sus, n = [], 0
for p in D["places"]:
    lic = (DET.get(p["id"]) or {}).get("lic")
    if not lic or lic not in L.index:
        continue
    n += 1
    r = L.loc[lic]
    names = [norm_name(x) for x in [p["n"], p.get("aka")] if x]
    keys = [k for k in (r["keys"] or []) + [norm_name(r["name"])] if k]
    mine = set().union(*[_stems(a) - GENERIC for a in names]) if names else set()
    theirs = set().union(*[_stems(k) - GENERIC for k in keys]) if keys else set()
    # the same name: one's words all in the other ("PIZZA HUT" / "PIZZA HUT 4275"), or a distinctive word in common that isn't just
    # the town (common.real_share: "Flagler", "Clermont"; Florida also has towns called Bell and Havana, so the subset test comes first)
    flat = lambda t: t.replace(" ", "")
    subset = any(set(a.split()) <= set(k.split()) or set(k.split()) <= set(a.split()) or flat(a) in flat(k) or flat(k) in flat(a)
                 or fuzz.ratio(flat(a), flat(k)) >= 88 for a in names for k in keys)   # "TAKEE OUTEE" / "TAKEEOUTEE", "CI CIS" / "CICIS"
    shared = subset or real_share(mine, theirs) or _close_words(mine - town_words(), theirs - town_words())
    conflict = all(kind_conflict(a, k) for a in names for k in keys)   # every pairing disagrees (a legal name may say anything)
    pa, la = p.get("a") or "", r.addr if isinstance(r.addr, str) else ""
    same_num = bool(street_nums(pa) & street_nums(la))
    if (not shared or conflict) and not same_num and p["id"] not in OK:
        sus.append((p["id"], p["n"], pa, lic, r["name"], la, VIA.get(p["id"], "?")))
print(f"places with a license: {n} | name and address both disagree: {len(sus)}")
for x in sus[:80]:
    print("  ", x)
sys.exit(1 if sus else 0)
