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

# researched places checked by hand whose address differs from the app's but is the same spot
OK = {
    "El Turco": "corner building: research 184 NE 50th Terr, DBPR license SEA2335956 at 5020 NE 2 Ave",
    "Torno Subito Miami": "corner building: research 191 NE 40th St, DBPR license SEA2337997 at 4040 NE 2 Ave",
    "Supernatural Food & Wine": "corner of E Polk St and N Tampa St: research 305 E Polk St, map listing 811 N Tampa St",
    "Roux 30A": "Grand Boulevard, corner of Logan Ln and Clayton Ln: research 114 Logan Ln, map listing 38 Clayton Ln",
}
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
    if not ok and r["name"] not in OK:
        sus.append((r["name"], r.get("address"), r.get("city"), [(p["n"], p.get("a")) for p in cands][:2]))
# a hand-checked copy with no license while a licensed place of the same name sits at its address (Columbia Sand Key was listed twice)
import glob as _g
DET = {}
for f in _g.glob(f"{DATA}/app/detail-*.json"):
    DET.update(json.load(open(f)))
from official import same_business
licensed = {}
for p in D["places"]:
    if (DET.get(p["id"]) or {}).get("lic"):
        licensed.setdefault(street_key(p.get("a") or ""), []).append(p)
twins = [(p["n"], p.get("a"), [q["n"] for q in licensed.get(street_key(p.get("a") or ""), []) if same_business(q["n"], p["n"])])
         for p in D["places"] if p.get("hc") and not (DET.get(p["id"]) or {}).get("lic") and street_key(p.get("a") or "")[0]]
twins = [t for t in twins if t[2]]
sus += [("twin", *t) for t in twins]
print(f"researched places found in the app: {n} | address disagrees or an unlicensed copy beside a licensed twin: {len(sus)}")
for s in sus:
    print("  ", s)
sys.exit(1 if sus else 0)
