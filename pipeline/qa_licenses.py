"""Does every place show its own license? -> prints suspects, exits 1 if any are left (run after FL_APP=1 florida.py)

A place in the app carries one DBPR license (detail file "lic"), and with it that license's inspections. When the two names share no
distinctive word (town names don't count) or say they serve different things, and the house numbers differ too, the inspections are
probably someone else's: Flagler Fish Company's license once sat on Flagler Tea Company. A second class (QA 2026-10-09): the same house
number but names that aren't one business (official.same_business), e.g. a Subway listing on Church's Chicken's license at a shared
address. Each suspect is either a real mismatch to fix in the pipeline or a known good pair to list in OK below, with why.
"""
import glob, json, sys
import os
import pandas as pd
from rapidfuzz import fuzz
from common import FL, DATA, norm_name, _stems, GENERIC, kind_conflict, real_share, town_words
from addr import street_nums
from listings_util import _close_words
from official import same_business
import re
HOLDER = re.compile(r"\b(?:INN|HOTEL|RESORT|SUITES|MOTEL|LODGE|HILTON|MARRIOTT|HYATT|COURTYARD|SHERATON|WYNDHAM|ALOFT|CLUB|TEMPLE|HOSPITAL|UNIVERSITY|COLLEGE|SODEXO|ARAMARK|EUREST|MORRISON|CONCESSIONS?)\b")
LEGALISH = re.compile(r"\b(?:HOLDINGS?|ENTERPRISES?|GROUP|MANAGEMENT|VENTURES?|PARTNERS|INVESTMENTS?|PROPERTIES|OPERATIONS|SERVICES|SOLUTIONS|HOSPITALITY|LLC|INC|CORP)\b")

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
    "6474e4b47a3f",   # FAT CAT Pizza + Dogs: its listing says "(Formerly Original II)"; DBPR still names the license ORIGINAL PIZZA II
    "8f47396a77cc",   # La Belle Vie CAFE: its listing says "(formerly Elm City Cafe)"; DBPR still names the license ELM CITY CAFÉ STUART
    "cf4bea7c2834",   # Lighthouse Ice Cream & Snacks / LIGHTHOUSE ICE CREAM AND TREATS: one shop, the listing gives the plaza's number
    "55239aad9cf1",   # O.E.C Japanese Express / OEC HIBACHI SUSHI: one restaurant (OEC), two descriptions
    "1168469f7fb8",   # 2000 Cafe / 2000 CAFE: the same name (all digits but "cafe", so the word test can't see it)
}

sus, same_addr, n = [], [], 0
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
    if p["id"] in OK:
        continue
    if (not shared or conflict) and not same_num:
        sus.append((p["id"], p["n"], pa, lic, r["name"], la, VIA.get(p["id"], "?")))
    elif not any(same_business(a, k) for a in names for k in keys) and not HOLDER.search(str(r["name"]).upper()) \
            and not LEGALISH.search(str(r["name"]).upper()) and "legal name" not in VIA.get(p["id"], ""):
        # (a license in a hotel's or a company's name is the restaurant under the holder's name: by design, not flagged)
        same_addr.append((p["id"], p["n"], pa, lic, r["name"], la, VIA.get(p["id"], "?")))
print(f"places with a license: {n} | name and address both disagree: {len(sus)} | same address, another business's name: {len(same_addr)}")
for x in sus[:60] + same_addr[:60]:
    print("  ", x)
sys.exit(1 if sus or same_addr else 0)
