"""Is every hand-checked place where its research says? -> prints suspects (run after FL_APP=1 florida.py)

Each researched place (data/research/app/*.json, MICHELIN, James Beard) has a street address from its 2025–26 source. The app's
hand-checked place with that name must be at the same house number (or next door on the same street); otherwise the
research facts (tags, dishes, founding year, honors) sit on the wrong place, or a stale listing won the match.
"""
import glob, json, sys
from rapidfuzz import fuzz
from common import DATA, norm_name, canon_city
from addr import street_nums, street_key, street_compat

D = json.load(open(f"{DATA}/app/places.json"))
cities = D["cities"]
R = []
for f in glob.glob(f"{DATA}/research/app/*.json") + [f"{DATA}/research/michelin.json"]:
    if "closed" in f:
        continue
    x = json.load(open(f))
    R += x if isinstance(x, list) else x.get("restaurants", [])
hc = [p for p in D["places"] if p.get("hc") or p.get("mi")]
by_town = {}
for p in hc:
    by_town.setdefault((cities[p["c"]] if isinstance(p.get("c"), int) else "").lower(), []).append(p)

sus, n = [], 0
for r in R:
    if r.get("open") is False or not r.get("address"):
        continue
    town = (canon_city(r.get("city") or "") or "").lower()
    k = norm_name(r["name"])
    cands = [p for p in by_town.get(town, []) if max(fuzz.token_set_ratio(k, norm_name(p["n"])), fuzz.token_set_ratio(k, norm_name(p.get("aka") or ""))) >= 85]
    if not cands:
        continue
    n += 1
    def same_spot(p):
        na, sa = street_key(r["address"])
        nb, sb = street_key(p.get("a") or "")
        if not (na and nb and sa and sb):
            return True   # one side has no house number: nothing to compare
        return bool(street_nums(r["address"]) & street_nums(p["a"])) or (street_compat(sa, sb) and abs(int(na) - int(nb)) <= 40)
    ok = any(same_spot(p) for p in cands)
    if not ok:
        sus.append((r["name"], r.get("address"), r.get("city"), [(p["n"], p.get("a")) for p in cands][:2]))
print(f"researched places found in the app: {n} | address disagrees: {len(sus)}")
for s in sus:
    print("  ", s)
sys.exit(1 if sus else 0)
