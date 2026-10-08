"""Geocode hand-checked places that neither DBPR's list nor the map listings place (data/research/geocode_todo.json, written by
florida.py) with the US Census Bureau's public geocoder, into the same cache geocode.py uses (data/fl/geocode_census.json).
Only exact or non-exact matches in Florida that agree on the zip or town are kept. Then re-run florida.py."""
import csv, io, json, os, re
import requests
from common import FL, DATA

todo = json.load(open(f"{DATA}/research/geocode_todo.json"))
cache_path = f"{FL}/geocode_census.json"
cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
misses = set(cache.pop("_misses", []))
rows = []
for q in todo:
    m = re.match(r"^(.*?),\s*([^,]+),\s*FL\s*(\d{5})?\s*$", q)
    if m and q not in cache:
        a = re.sub(r",?\s*(?:Ste|Suite|Unit|#)\s*\S+$", "", m.group(1), flags=re.I)
        rows.append((q, a, m.group(2), m.group(3) or ""))
buf = io.StringIO(); w = csv.writer(buf)
for i, (q, a, c, z) in enumerate(rows):
    w.writerow([i, a, c, "FL", z])
got = 0
if rows:
    r = requests.post("https://geocoding.geo.census.gov/geocoder/locations/addressbatch", files={"addressFile": ("a.csv", buf.getvalue(), "text/csv")},
                      data={"benchmark": "Public_AR_Current"}, headers={"User-Agent": "FloridaEatsResearch/1.0 (work-with-nick@gmail.com)"}, timeout=600)
    r.raise_for_status()
    for row in csv.reader(io.StringIO(r.text)):
        if len(row) < 3 or not row[0].isdigit():
            continue
        q, a, c, z = rows[int(row[0])]
        mt = row[4].upper() if len(row) > 4 else ""
        if row[2] == "Match" and len(row) >= 6 and ", FL," in mt and ((z and mt.rstrip().endswith(z)) or f", {c.upper()}, FL" in mt):
            lon, lat = map(float, row[5].split(","))
            cache[q] = {"lat": round(lat, 6), "lon": round(lon, 6), "matched": row[4], "exact": row[3] == "Exact"}; got += 1
        else:
            misses.add(q)
cache["_misses"] = sorted(misses)
json.dump(cache, open(cache_path, "w"), indent=0, sort_keys=True)
print("research addresses geocoded:", got, "of", len(rows), "| not matched:", [q for q, *_ in rows if q not in cache][:20])
