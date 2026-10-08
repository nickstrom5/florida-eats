"""Writes the public website in docs/ from the same data the app ships (data/app/places.json, plus the data/app/detail-*.json files
that hold licenses, phones, websites, inspection histories and closures when the pipeline splits them out).

Pages: the landing page; eight statewide hand-checked guides (Cuban sandwiches & cafecito, stone crabs, grouper & seafood shacks,
Keys classics, oyster bars, fish camps & smoked fish, Latin & Caribbean, the oldest places); MICHELIN & James Beard; an explainer of
Florida's DBPR inspections (counts only, no place named); one page per big city or resort town with enough hand-checked or honored
places to say something real, plus a cities index; the web app (/explore/); privacy; terms; 404; sitemap.xml, robots.txt,
site.webmanifest and playbook/site-numbers.json. Everything listed is hand-checked research or public records; nothing comes from
Google, Yelp or any ratings site, and nothing is ranked by ratings. Adapted from co-eats/scripts/make-site.py.

Rules the copy keeps (scripts/qa-site.py checks them):
- Every number is counted from the data here, never typed in. DBPR's license list is the state's official list of licensed food
  service establishments, but our lists are "places we list": no sentence claims "every" or "all N" restaurants.
- "Checked" only for the hand-checked lists (`hc`, a 2025-26 source for each place).
- Florida has no inspection grade ("establishments are not graded or rated") and we never compute one: the site shows DBPR's own
  disposition text and DBPR's result group, with the date, labeled as DBPR's.
- A place whose latest DBPR result group is Follow-Up Inspection Required or Facility Temporarily Closed is never named in a title,
  description, lede or other promotional spot. The inspections page names no place at all and has no "worst" list.
- Every page carries a hash-pinned Content-Security-Policy; inline scripts and styles are hashed after the page is final.

Usage (from fl-eats/): .venv/bin/python scripts/make-site.py           (github.io address, BASE /florida-eats)
                       FL_DOMAIN=florida.eatsranked.com .venv/bin/python scripts/make-site.py   (once Nick's CNAME resolves)
Re-run it after every data rebuild, then check the pages with scripts/qa-site.py. Never hand-edit docs/*.html.
"""
import base64
import datetime as dt
import glob
import gzip
import hashlib
import html
import json
import math
import os
import re
import struct
import urllib.parse
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS = f"{ROOT}/docs"
# Where the site lives. Until Nick's Cloudflare record (CNAME florida -> nickstrom5.github.io, DNS only) resolves, GitHub Pages serves
# the project address. When `dig florida.eatsranked.com` shows the CNAME, run with FL_DOMAIN=florida.eatsranked.com and push: this
# writes docs/CNAME, and GitHub then forwards the old github.io links (the ones inside shipped app builds).
CUSTOM_DOMAIN = os.environ.get("FL_DOMAIN", "").strip().lower().removeprefix("https://").removeprefix("http://").strip("/")
REPO = "florida-eats"
DOMAIN = f"https://{CUSTOM_DOMAIN}" if CUSTOM_DOMAIN else f"https://nickstrom5.github.io/{REPO}"
BASE = "" if CUSTOM_DOMAIN else f"/{REPO}"     # path prefix for root-relative links
BRAND = "Florida Eats"
APP_NAME = "Florida Eats: Restaurants"
TAGLINE = "Cuban, seafood & more"
EMAIL = "work-with-nick@gmail.com"
PUBLISHED = "2026-10-07"        # the site's first publication (Article datePublished)
SITE_REV = "2026-10-07"         # the last change to this generator's own copy or code: bump it when you change the words
POLICY_UPDATED = "2026-10-07"   # privacy policy and terms: bump only when their text changes
CHECKED = "fall 2026"
STORAGE_PREFIX = "fleats-"      # the web app's localStorage keys (other state sites share the nickstrom5.github.io origin)

# ---------------------------------------------------------------- data: the core file plus, when split out, the detail files
D = json.load(open(f"{ROOT}/data/app/places.json"))
assert D.get("generated"), "data/app/places.json has no 'generated' field: the pipeline hasn't finished writing it"
DETAIL_SRC = {}
for _f in sorted(glob.glob(f"{ROOT}/data/app/detail-*.json")):
    DETAIL_SRC.update(json.load(open(_f)))
if D.get("v", 1) >= 2:
    assert DETAIL_SRC, "places.json is a v2 core file but data/app/detail-*.json are missing"


def core_in(v):
    """The core file's inspection summary: a compact array [g, d] or [g, d, hp, im, bs] (older files: a dictionary)."""
    if isinstance(v, list):
        return dict(zip(("g", "d", "hp", "im", "bs"), v))
    return v


def merged(r):
    """One place with its detail fields put back (v2 moved lic, ph, w, cl and most of 'in' into the detail files)."""
    det = DETAIL_SRC.get(r["id"]) or {}
    if "in" in r:
        r = {**r, "in": core_in(r["in"])}
    if not det:
        return r
    out = dict(r)
    for k, v in det.items():
        if k == "in" and isinstance(v, dict):
            out["in"] = {**(r.get("in") or {}), **v}
        else:
            out[k] = v
    return out


RECS = [merged(r) for r in D["places"]]
TODAY = max(str(D.get("generated") or SITE_REV)[:10], SITE_REV)   # sitemap lastmod and dateModified move with the data or the copy
INS_THROUGH = D.get("inspections_through") or ""
DBPR_FETCHED = D.get("dbpr_fetched") or ""
CITIES, CUISINES, COUNTIES = D["cities"], D["cuisines"], D["counties"]
DISP, ITYPES = D.get("dispositions") or [], D.get("itypes") or []
CUBAN, STONECRAB, GROUPER, KEYS, OYSTER, FISHCAMP, LATIN, OLDEST = 1, 2, 4, 8, 16, 32, 64, 128
MI = ["", "MICHELIN Recommended", "Bib Gourmand", "1 MICHELIN Star", "2 MICHELIN Stars", "3 MICHELIN Stars"]
GROUPS = ["Met Inspection Standards", "Follow-Up Inspection Required", "Facility Temporarily Closed"]
# DBPR's own grouping of its dispositions (www2.myfloridalicense.com/hotels-restaurants/inspections/), spelled as DBPR's data spells
# them; the same table as pipeline/dbpr.py. Dispositions outside it ("Allegation Not Observed") are ones DBPR doesn't group.
DBPR_GROUP = {
    "Inspection Completed - No Further Action": 0, "Call Back - Complied": 0, "Admin. Complaint Callback Complied": 0,
    "Emergency Order Callback Complied": 0,
    "Warning Issued": 1, "Call Back - Extension given, pending": 1, "Call Back - Admin. complaint recommended": 1,
    "Administrative complaint recommended": 1, "Admin. Complaint Callback Not Complied": 1, "Administrative Complaint Time Extension": 1,
    "Emergency Order Callback Time Extension": 1,
    "Emergency order recommended": 2, "Administrative determination recommended": 2, "Emergency Order Callback Not Complied": 2,
}
DBPR_INSPECTIONS = "https://www2.myfloridalicense.com/hotels-restaurants/inspections/"
DBPR_RECORDS = "https://www2.myfloridalicense.com/hotels-restaurants/public-records/"
DBPR_SEARCH = "https://www.myfloridalicense.com/portalsearches/VerifyLicensee?Mode=0&BoardType=H"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
NUM_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
NO_GRADE = "establishments are not graded or rated"   # DBPR's words, quoted wherever the site explains the results


def hdate(iso):
    """2026-09-24 -> September 24, 2026"""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    return f"{MONTHS[int(m[2]) - 1]} {int(m[3])}, {m[1]}" if m else str(iso or "")


def hmonth(iso):
    m = re.match(r"(\d{4})-(\d{2})", str(iso or ""))
    return f"{MONTHS[int(m[2]) - 1]} {m[1]}" if m else str(iso or "")


def plural(n, one, many=None):
    return f"{n:,} {one if n == 1 else (many or one + 's')}"


def words_num(n):
    return NUM_WORDS[n] if 0 <= n < len(NUM_WORDS) else f"{n:,}"


def safe_url(u):
    """Only http(s) links leave the site; a bare host ("example.com/menu") gets https://. Anything else is dropped."""
    u = str(u or "").strip()
    if re.fullmatch(r"https?://[^\s\"'<>\\]+", u, re.I):
        return u
    if re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)*\.[a-z]{2,}(?:[/?#][^\s\"'<>\\]*)?", u, re.I):
        return "https://" + u
    return ""


class P:
    """One place, with the same meaning the app gives each field (FloridaEats/Models/Place.swift)."""

    def __init__(self, r):
        self.r = r
        self.name = str(r["n"])
        self.city = CITIES[r["c"]] if r.get("c") is not None else ""
        self.county = COUNTIES[r["co"]] if r.get("co") is not None else None
        self.cuisine = CUISINES[r["cu"]] if r.get("cu") is not None else ""
        self.addr = (r.get("a") or "").strip().rstrip(",").strip()
        self.zip = str(r.get("z") or "")
        self.lat, self.lon = r.get("la"), r.get("lo")
        self.tags = r.get("g") or 0
        self.chain = (r.get("ch") or 0) >= 5
        self.venue = r.get("v") == 1
        self.mouse = r.get("dw") == 1     # run by Walt Disney World or Universal Orlando; some are inside ticketed parks
        self.ip = r.get("ip")
        self.founded = r.get("f") if isinstance(r.get("f"), int) else None
        self.fn = r.get("fn") or ""
        self.dishes = (r.get("dish") or "").replace("; ", ", ")
        self.season = r.get("seas") or ""
        self.note = r.get("note") or ""
        self.site = safe_url(r.get("w"))
        self.jbf = r.get("jbf") or ""
        self.h = r.get("h") or 0
        self.mi = r.get("mi") if r.get("mi") in range(1, len(MI)) else 0
        self.gs = r.get("gs") == 1
        self.hc = r.get("hc") == 1   # hand-checked against a 2025-26 source; the only places the themed guides list
        self.lic = r.get("lic") or ""
        ins = r.get("in")
        self.ins = ins if isinstance(ins, dict) and ins.get("d") else None
        self.group = self.ins.get("g") if self.ins and self.ins.get("g") in (0, 1, 2) else None
        self.cl = r.get("cl") or []

    def featured_key(self):
        # the app's "Featured first": honored places, then documented founding year, then name
        return (-(self.ip if self.ip is not None else -1), self.founded or 9999, self.name.lower())

    def jb_label(self):
        return ("America's Classic" if self.h & 1 else "James Beard winner" if self.h & 2 else "James Beard finalist" if self.h & 4
                else "James Beard semifinalist" if self.h & 8 else None)

    def promo_ok(self):
        """Never name a place whose latest DBPR result is Follow-Up Inspection Required or Facility Temporarily Closed in a title,
        description, lede or other promotional spot."""
        return self.group not in (1, 2)

    def in_guide(self, tag):
        return self.hc and bool(self.tags & tag)


PLACES = [P(r) for r in RECS]
REST = [p for p in PLACES if not p.venue]

# the dispositions in the data must group the way DBPR groups them (or the copy below would mislabel a result)
for p in REST:
    if p.ins and p.ins.get("dp") is not None and 0 <= p.ins["dp"] < len(DISP):
        want = DBPR_GROUP.get(DISP[p.ins["dp"]])
        assert want == p.group, (p.name, DISP[p.ins["dp"]], p.group, want)

GUIDE_TAGS = [("cuban", CUBAN), ("stonecrab", STONECRAB), ("grouper", GROUPER), ("keys", KEYS), ("oyster", OYSTER),
              ("fishcamp", FISHCAMP), ("latin", LATIN)]
L = {k: sorted([p for p in REST if p.in_guide(t)], key=P.featured_key) for k, t in GUIDE_TAGS}
HON_L = sorted([p for p in REST if p.mi or p.jbf], key=P.featured_key)
OLD_L = sorted([p for p in REST if p.founded and p.in_guide(OLDEST)], key=lambda p: (p.founded, p.name.lower()))
HC_ANY = [p for p in REST if p.hc and p.tags]   # on at least one hand-checked guide
INS_L = [p for p in REST if p.ins]

# ---------------------------------------------------------------- regions (by county; all 67), as pipeline/official.py has them
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
REGION_NAME = {"South Florida": "South Florida", "Keys": "The Florida Keys", "Space & Treasure Coast": "Space & Treasure Coast",
               "Central": "Central Florida", "Tampa Bay": "Tampa Bay", "Southwest": "Southwest Florida", "Northeast": "Northeast Florida",
               "Panhandle": "The Panhandle"}
REGION_ORDER = ["Keys", "South Florida", "Southwest", "Tampa Bay", "Central", "Space & Treasure Coast", "Northeast", "Panhandle"]
for p in PLACES:
    p.region = REGION_OF.get(p.county) if p.county else None


def miles(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))


# ---------------------------------------------------------------- html helpers
e = html.escape


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower().replace("'", "").replace("&", "and")).strip("-")


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    return struct.unpack(">II", head[16:24])


def join_words(xs, conj="and"):
    xs = [x for x in xs if x]
    if len(xs) <= 1:
        return "".join(xs)
    return ", ".join(xs[:-1]) + f" {conj} " + xs[-1]


def fit(cands, lo, hi, what=""):
    seen = []
    for o in cands:
        if lo <= len(o) <= hi:
            return o
        seen.append(o)
    raise ValueError(f"nothing fits {lo}-{hi} for {what}: {[(len(o), o) for o in seen[:12]]}")


# The app icon in miniature (scripts/make-brand.swift's claw, same geometry): a stone crab claw with black-tipped pincers on Gulf
# teal over a low wave. Drawn in the icon's y-up units, flipped once.
LOGO = ('<svg viewBox="0 0 64 64" width="30" height="30" aria-hidden="true"><defs>'
        '<clipPath id="lg-r"><rect width="64" height="64" rx="14"/></clipPath>'
        '<clipPath id="lg-f"><path d="M-.02-.18C.18-.19.37-.12.42-.015C.40.012.35-.02.31-.035C.21-.05.10-.03.02-.005Z"/>'
        '<path d="M-.06.18C.15.23.37.15.42.035C.41.012.35.035.31.05C.21.07.10.06.02.045Z"/></clipPath>'
        '<clipPath id="lg-p"><ellipse cx="-.14" cy="0" rx=".26" ry=".2"/></clipPath></defs>'
        '<g clip-path="url(#lg-r)"><rect width="64" height="64" fill="#006D77"/><g transform="matrix(1 0 0 -1 0 64)">'
        '<path d="M0 0V8.96C10.24 13.44 21.76 13.44 32 8.96C42.24 4.48 53.76 4.48 64 8.96V0Z" fill="#0B7F89"/>'
        '<g transform="translate(33.92 33.92) rotate(40.107) scale(65.28)">'
        '<circle cx="-.4" cy="0" r=".1" fill="#C4401A"/>'
        '<g clip-path="url(#lg-f)"><rect x="-1" y="-1" width="2" height="2" fill="#E8572A"/><rect x=".25" y="-1" width="1" height="2" fill="#17191A"/></g>'
        '<g clip-path="url(#lg-p)"><rect x="-1" y="-1" width="2" height="2" fill="#E8572A"/>'
        '<path d="M-.45-.08C-.24-.15 0-.15.16-.1V-.3H-.45Z" fill="#F7E4C8"/></g>'
        '<g fill="#C4401A"><circle cx="-.2" cy=".09" r=".024"/><circle cx="-.07" cy=".11" r=".018"/><circle cx="-.27" cy=".01" r=".016"/>'
        '<circle cx=".02" cy=".05" r=".015"/></g></g></g></g></svg>')
FAVICON = "data:image/svg+xml," + LOGO.replace('width="30" height="30" ', "").replace(' aria-hidden="true"', "").replace("<svg ", "<svg xmlns='http://www.w3.org/2000/svg' ").replace('"', "'").replace("#", "%23").replace("<", "%3C").replace(">", "%3E")

# Nick's palette: Gulf teal #006D77 for text and accents (6.1:1 on white, 5.6:1 on sand), citrus orange #F28C28 and key lime #B5D46A
# only as fills under ink #0B3C49 text (4.9:1 and 7.2:1), sand #FBF5EA as the page tint, ink #0B3C49 for text.
CSS = """
  :root {
    --bg: #fbf5ea; --surface: #fff; --surface2: #f3ecdf; --rule: #e6dccb;
    --ink: #0b3c49; --ink2: #24505c; --muted: #56676c;
    --accent: #006d77; --accent2: #0b7f89; --on-accent: #fff; --orange: #f28c28; --lime: #b5d46a; --soft: #fde3c8; --limesoft: #e3efc4;
    --focus: #006d77;
    --radius: 16px;
    --display: "Avenir Next Condensed", "HelveticaNeue-CondensedBold", "Arial Narrow", system-ui, sans-serif;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #0b1f26; --surface: #10303a; --surface2: #163b46; --rule: #24505c; --ink: #eaf4f4; --ink2: #cfe2e4; --muted: #a8c2c6; --accent: #7fd3da; --accent2: #9fdfe4; --on-accent: #0b1f26; --focus: #f28c28; }
  }
  * { box-sizing: border-box; }
  html { -webkit-text-size-adjust: 100%; }
  @media (prefers-reduced-motion: no-preference) { html { scroll-behavior: smooth; } }
  @media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
  body { margin: 0; background: var(--bg); color: var(--ink); font: 17px/1.55 -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif; -webkit-font-smoothing: antialiased; }
  a { color: var(--accent); text-underline-offset: 2px; }
  a:focus-visible, summary:focus-visible, button:focus-visible, select:focus-visible, input:focus-visible, [tabindex]:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; border-radius: 6px; }
  .skip { position: absolute; left: -9999px; top: 0; background: var(--orange); color: #0b3c49; padding: 10px 14px; font-weight: 700; z-index: 10; }
  .skip:focus { left: 8px; top: 8px; }
  .wrap { max-width: 760px; margin: 0 auto; padding: 0 20px; }
  header.site { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 18px 0; border-bottom: 4px solid var(--orange); box-shadow: 0 4px 0 var(--lime); }
  .logo { display: flex; align-items: center; gap: 10px; font: 800 22px/1 var(--display); text-transform: uppercase; letter-spacing: .01em; color: var(--accent); text-decoration: none; }
  .logo svg { flex: 0 0 auto; border-radius: 7px; }
  header.site nav { display: flex; flex-wrap: wrap; gap: 4px 16px; justify-content: flex-end; }
  header.site nav a { color: var(--ink2); text-decoration: none; font-size: 15px; }
  header.site nav a:hover { color: var(--accent); text-decoration: underline; }
  h1, h2 { font-family: var(--display); font-weight: 800; color: var(--accent); letter-spacing: -.005em; }
  h1 { font-size: clamp(34px, 7.5vw, 54px); line-height: 1.04; margin: 0 0 16px; text-transform: uppercase; overflow-wrap: break-word; }
  .kicker { font: 700 15px/1.4 -apple-system, system-ui, sans-serif; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); margin: 0 0 12px; }
  h2 { font-size: 32px; line-height: 1.1; margin: 0 0 10px; }
  h3 { font-size: 18px; margin: 0; line-height: 1.3; }
  .lede { font-size: 19px; color: var(--ink2); margin: 0 0 26px; }
  .hero { padding: 44px 0 28px; }
  section { padding: 36px 0; border-top: 1px solid var(--rule); }
  section.hero { border: 0; }
  .sub { color: var(--ink2); margin: 0 0 22px; }
  .cta-row { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
  .btn { display: inline-flex; align-items: center; gap: 10px; background: var(--orange); color: #0b3c49; font-weight: 700; padding: 14px 20px; border-radius: 14px; text-decoration: none; font-size: 17px; }
  .btn-ghost { background: transparent; color: var(--accent); border: 2px solid var(--accent); }
  .pill { font-size: 14px; color: var(--muted); }
  .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 28px 0 0; padding: 0; list-style: none; }
  .stats li { background: var(--surface); border: 1px solid var(--rule); border-radius: 14px; padding: 14px; }
  .stats b { display: block; font: 800 30px/1 var(--display); color: var(--accent); }
  .stats span { font-size: 14px; color: var(--muted); }
  .steps { display: grid; gap: 12px; list-style: none; margin: 0; padding: 0; }
  .step { display: flex; gap: 14px; background: var(--surface); border: 1px solid var(--rule); border-radius: var(--radius); padding: 18px; }
  .step .n { flex: 0 0 32px; height: 32px; border-radius: 50%; background: var(--orange); color: #0b3c49; font-weight: 800; display: grid; place-items: center; }
  .step p { margin: 4px 0 0; color: var(--ink2); }
  .shots { display: flex; gap: 14px; overflow-x: auto; margin: 0 -20px; padding: 4px 20px 14px; scroll-snap-type: x proximity; list-style: none; }
  .shots li { flex: 0 0 auto; width: 210px; scroll-snap-align: start; }
  .shots img { display: block; width: 210px; height: auto; border-radius: 24px; border: 1px solid var(--rule); background: var(--surface2); }
  .shots p { font-size: 14px; color: var(--muted); margin: 8px 2px 0; }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  .card { background: var(--surface); border: 1px solid var(--rule); border-radius: var(--radius); padding: 18px; }
  .card p { margin: 6px 0 0; color: var(--ink2); }
  a.card { display: block; text-decoration: none; color: var(--ink); }
  a.card:hover h3 { text-decoration: underline; color: var(--accent); }
  .cities { display: flex; flex-wrap: wrap; gap: 8px; list-style: none; padding: 0; margin: 0; }
  .cities a { display: inline-block; padding: 8px 12px; border-radius: 999px; border: 1px solid var(--rule); background: var(--surface); text-decoration: none; color: var(--ink); font-size: 15px; }
  .cities a:hover { border-color: var(--accent); }
  .cities a[aria-current] { border-color: var(--accent); font-weight: 700; }
  details { background: var(--surface); border: 1px solid var(--rule); border-radius: 14px; padding: 2px 18px; margin-bottom: 10px; }
  summary { cursor: pointer; padding: 14px 0; font-weight: 600; list-style: none; display: flex; justify-content: space-between; gap: 12px; }
  summary::-webkit-details-marker { display: none; }
  summary::after { content: "+"; color: var(--accent); font-weight: 800; }
  details[open] summary::after { content: "\\2013"; }
  details p { margin: 0 0 16px; color: var(--ink2); }
  .final { text-align: center; }
  .final .cta-row { justify-content: center; }
  nav.crumbs { font-size: 14px; color: var(--muted); padding: 16px 0 0; }
  nav.crumbs ol { list-style: none; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: 6px; }
  nav.crumbs li + li::before { content: "/"; margin-right: 6px; color: var(--rule); }
  nav.crumbs a { color: var(--muted); }
  .places { list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; }
  .places li { background: var(--surface); border: 1px solid var(--rule); border-radius: 14px; padding: 14px 16px; min-width: 0; overflow-wrap: anywhere; scroll-margin-top: 12px; }
  .places li:target { border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent); }
  .places .where { margin: 2px 0 0; font-size: 15px; color: var(--muted); }
  .places .facts { margin: 8px 0 0; font-size: 15px; color: var(--ink2); }
  .places .facts b { color: var(--ink); font-weight: 600; }
  .places .note { margin: 6px 0 0; font-size: 15px; color: var(--ink2); }
  .places .fine { margin: 6px 0 0; }
  .places .link { font-size: 14px; margin: 6px 0 0; }
  .tag { display: inline-block; font-size: 12px; font-weight: 700; letter-spacing: .05em; text-transform: uppercase; background: var(--lime); color: #0b3c49; border-radius: 6px; padding: 1px 6px; margin: 0 4px 2px 0; }
  .tag-mi { background: #0b3c49; color: #fff; }
  .tag-jb { background: #006d77; color: #fff; }
  .tag-plain { background: var(--soft); color: #0b3c49; }
  .toc { columns: 2; padding-left: 20px; margin: 0; }
  table { border-collapse: collapse; width: 100%; font-size: 15px; }
  th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid var(--rule); vertical-align: top; }
  td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
  .tbl { overflow-x: auto; }
  .res { display: inline-block; font: 800 12px/1.4 -apple-system, system-ui, sans-serif; letter-spacing: .04em; text-transform: uppercase; padding: 2px 6px; border-radius: 6px; }
  .res-0 { background: #ddefe3; color: #0e5a2b; } .res-1 { background: #ffe9c2; color: #6b3a00; } .res-2 { background: #f9d5db; color: #7a0019; }
  .groups { list-style: none; padding: 0; margin: 0 0 18px; display: grid; gap: 12px; }
  .groups > li { background: var(--surface); border: 1px solid var(--rule); border-radius: 14px; padding: 14px 16px; }
  .groups ul { margin: 8px 0 0; padding-left: 20px; color: var(--ink2); font-size: 15px; }
  .groups .count { margin: 8px 0 0; font-weight: 600; }
  .fine { font-size: 14px; color: var(--muted); }
  .legal h2 { font-size: 26px; margin-top: 28px; }
  .legal p, .legal li { color: var(--ink2); }
  footer { padding: 32px 0 56px; color: var(--muted); font-size: 14px; border-top: 1px solid var(--rule); margin-top: 20px; }
  footer nav { display: flex; flex-wrap: wrap; gap: 8px 16px; }
  footer a { color: var(--muted); }
  footer p { margin: 12px 0 0; }
  @media (max-width: 600px) {
    .grid2 { grid-template-columns: 1fr; }
    .stats { grid-template-columns: 1fr 1fr; }
    .toc { columns: 1; }
    header.site { flex-direction: column; align-items: flex-start; }
    header.site nav { justify-content: flex-start; }
    header.site nav a, footer nav a, nav.crumbs a { display: inline-block; padding: 10px 0; }
    footer nav { gap: 0 18px; }
    th, td { padding: 8px 4px; font-size: 14px; }
    .tbl th, .tbl td { padding: 8px 3px; font-size: 13px; }
    .res { font-size: 11px; letter-spacing: .02em; padding: 2px 4px; }
    nav.crumbs ol { align-items: center; }
  }
"""


def jsonld(obj):
    big = obj.get("@type") == "ItemList"
    raw = json.dumps(obj, ensure_ascii=False, indent=None if big else 1, separators=(",", ":") if big else None)
    return '<script type="application/ld+json">\n' + raw.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026") + "\n</script>"


def crumbs(trail):
    """trail: [(name, url)] ending with the current page."""
    items = "".join(f'<li><a href="{u}">{e(n)}</a></li>' if i < len(trail) - 1 else f'<li aria-current="page">{e(n)}</li>'
                    for i, (n, u) in enumerate(trail))
    ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": DOMAIN + u} for i, (n, u) in enumerate(trail)]}
    return f'<nav class="crumbs" aria-label="Breadcrumb"><ol>{items}</ol></nav>', ld


def store_button(label="Get early access"):
    # A plain mailto button until launch: no Apple logo (Apple's marketing rules allow it only in the official badge). When
    # APP_STORE_URL is set in page() below, swap this for Apple's "Download on the App Store" badge artwork.
    return (f'<a class="btn store-btn" href="mailto:{EMAIL}?subject=Florida%20Eats%20early%20access&amp;body=Send%20me%20the%20TestFlight%20link.">'
            f'<span class="store-label">{label}</span></a>')


STORE_NOTE = "Free iPhone and iPad app, coming soon to the App Store."


def sha256_src(s):
    return "'sha256-" + base64.b64encode(hashlib.sha256(s.encode("utf-8")).digest()).decode() + "'"


def csp_for(doc):
    """A strict policy for one finished page: only its own inline <script>/<style> blocks (by hash), same-origin data and images."""
    scripts = re.findall(r"<script>(.*?)</script>", doc, re.S)          # executable inline scripts (JSON-LD blocks are data, not run)
    styles = re.findall(r"<style>(.*?)</style>", doc, re.S)
    return ("default-src 'none'; "
            f"script-src {' '.join(sha256_src(s) for s in scripts) or chr(39) + 'none' + chr(39)}; "
            f"style-src {' '.join(sha256_src(s) for s in styles) or chr(39) + 'none' + chr(39)}; "
            "img-src 'self' data:; connect-src 'self'; manifest-src 'self'; base-uri 'none'; form-action 'none'")


CSP_SLOT = "__CSP__"
written, noindexed = [], []
NAV = [("/florida-cuban-sandwiches-cafecito.html", "Cuban"), ("/florida-stone-crab.html", "Stone crab"),
       ("/florida-oyster-bars.html", "Oysters"), ("/cities/", "Cities"), ("/explore/", "Search")]


def page(path, title, desc, body, lds=(), robots="index,follow,max-image-preview:large", og_alt=None, extra_css="", og_type="article"):
    assert 50 <= len(title) <= 60 or path == "404.html", (path, len(title), title)
    assert 140 <= len(desc) <= 160 or path == "404.html", (path, len(desc), desc)
    assert body.count("<h1") == 1, path
    assert 'style="' not in body, f"{path}: inline style attributes break the CSP"
    url = DOMAIN + "/" + ("" if path == "index.html" else path.removesuffix("index.html"))
    indexed = "noindex" not in robots
    og_alt = og_alt or f"{BRAND}: {TAGLINE}. Florida restaurants, with hand-checked Cuban sandwiches, stone crabs, oyster bars and the state's oldest places."
    ld = "\n".join(jsonld(x) for x in lds)
    canon = f'<link rel="canonical" href="{url}">\n' if indexed else ""
    og_url = f'<meta property="og:url" content="{url}">\n' if indexed else ""
    nav = "\n".join(f'      <a href="{u}">{t}</a>' for u, t in NAV)
    doc = f"""<!DOCTYPE html>
<html lang="en" data-base="{BASE}">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="{CSP_SLOT}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
{canon}<meta name="robots" content="{robots}">
<meta name="theme-color" content="#006d77">
<!-- Smart App Banner: once the App Store Connect record exists, replace APP_ID with the numeric Apple ID and uncomment.
<meta name="apple-itunes-app" content="app-id=APP_ID">
-->
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
{og_url}<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{BRAND}">
<meta property="og:locale" content="en_US">
<meta property="og:image" content="{DOMAIN}/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{e(og_alt)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{DOMAIN}/og.png">
<link rel="icon" type="image/svg+xml" href="{FAVICON}">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<style>{CSS}{extra_css}</style>
{ld}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<div class="wrap">
  <header class="site">
    <a class="logo" href="/" aria-label="{BRAND} home">{LOGO}{BRAND}</a>
    <nav aria-label="Main">
{nav}
    </nav>
  </header>
{body}
  <footer>
    <nav aria-label="Footer">
      <a href="/">{BRAND} app</a>
      <a href="/explore/">Search Florida restaurants</a>
{chr(10).join(f'      <a href="{u}">{e(t)}</a>' for u, t in GUIDE_LINKS)}
      <a href="/cities/">Cities and towns</a>
      <a href="/privacy.html">Privacy policy</a>
      <a href="/terms.html">Terms of use</a>
      <a href="mailto:{EMAIL}">Email us</a>
    </nav>
    <p>{SOURCES_LINE}</p>
    <p>© 2026 {BRAND}.</p>
  </footer>
</div>
<script>
  // Once the App Store listing exists, paste its URL here (looks like https://apps.apple.com/app/id123456789).
  // Every button switches from "Get early access" to "Download on the App Store" automatically (then use Apple's badge artwork,
  // see store_button() in scripts/make-site.py). Also fill in the apple-itunes-app meta tag in <head> on every page, and put the
  // MobileApplication "offers" back in the landing page's JSON-LD (re-run scripts/make-site.py after editing it there).
  var APP_STORE_URL = "";
  if (APP_STORE_URL) {{
    document.querySelectorAll(".store-btn").forEach(function (b) {{ b.href = APP_STORE_URL; b.rel = "noopener"; }});
    document.querySelectorAll(".store-label").forEach(function (l) {{ l.textContent = "Download on the App Store"; }});
    document.querySelectorAll(".store-note").forEach(function (n) {{ n.textContent = "Free for iPhone and iPad."; }});
  }}
</script>
</body>
</html>
"""
    if BASE:   # served under /florida-eats/: every root-relative link and asset gets the prefix
        doc = re.sub(r'(href|src|srcset)="/', rf'\1="{BASE}/', doc)
    doc = doc.replace(CSP_SLOT, csp_for(doc), 1)   # hashed last, over the exact bytes the browser will see
    os.makedirs(os.path.dirname(f"{DOCS}/{path}"), exist_ok=True)
    open(f"{DOCS}/{path}", "w").write(doc)
    (written if indexed else noindexed).append(path)
    return path


class Anchors:
    """Gives each place an id (name-zip) the first time it appears on a page, so ItemList items can point to page#id."""
    RESERVED = {"main", "about", "list", "honors", "oldest", "inspections", "cuisines", "more", "towns", "how", "what", "guides", "cities",
                "faq", "download", "screens", "pricing", "privacy", "groups", "counties", "lookup", "closures", "tiers", "lg-r", "lg-f", "lg-p",
                "cities-list"} | {k for k, _ in GUIDE_TAGS}

    def __init__(self, page_url):
        self.page_url, self.used, self.of = page_url, set(self.RESERVED), {}

    def take(self, p):
        if id(p) in self.of:
            return None
        base = slug(p.name + (" " + p.zip if p.zip else "")) or "place"
        a, n = base, 2
        while a in self.used:
            a, n = f"{base}-{n}", n + 1
        self.used.add(a)
        self.of[id(p)] = a
        return a

    def url(self, p):
        return f"{self.page_url}#{self.of[id(p)]}"


CHIPS = [(CUBAN, "Cuban &amp; cafecito"), (STONECRAB, "Stone crab"), (GROUPER, "Grouper &amp; seafood"), (KEYS, "Keys classic"),
         (OYSTER, "Oyster bar"), (FISHCAMP, "Fish camp"), (LATIN, "Latin &amp; Caribbean")]


def place_item(p, anchors=None, show_fn=False, honors=False):
    facts = []
    if p.dishes:
        facts.append(f"<b>On the menu:</b> {e(p.dishes)}")
    if p.founded:
        facts.append(f"<b>Since</b> {e(str(p.founded))}")
    if p.season:
        facts.append(f"<b>Season:</b> {e(p.season)}")
    kinds = []
    if p.mi:
        kinds.append(('<span class="tag tag-mi">', e(MI[p.mi])))
    if p.gs:
        kinds.append(('<span class="tag tag-mi">', "MICHELIN Green Star"))
    if p.jb_label():
        kinds.append(('<span class="tag tag-jb">', e(p.jb_label())))
    if p.hc:
        kinds += [('<span class="tag">', k) for t, k in CHIPS if p.tags & t]
    if p.mouse:
        kinds.append(('<span class="tag tag-plain">', "Disney/Universal"))
    where = ", ".join(x for x in (p.addr, p.city) if x)
    aid = anchors.take(p) if anchors else None
    out = [f'<li id="{e(aid)}">' if aid else "<li>", f"<h3>{e(p.name)}</h3>", f'<p class="where">{e(where)}</p>']
    if kinds or facts:
        out.append('<p class="facts">' + "".join(f"{tag}{k}</span>" for tag, k in kinds) + (" " + " · ".join(facts) if facts else "") + "</p>")
    if p.note:
        out.append(f'<p class="note">{e(p.note)}</p>')
    if show_fn and p.fn:
        out.append(f'<p class="fine">{e(p.fn)}</p>')
    if honors and p.jbf:   # restaurateur-level honors have no chip, so say what the honor is
        out.append('<p class="fine">' + e("; ".join("James Beard: " + x for x in p.jbf.split("; "))) + "</p>")
    if p.mouse:
        out.append('<p class="fine">Run by Walt Disney World or Universal Orlando; some of their restaurants are inside ticketed parks.</p>')
    if p.site:
        host = re.sub(r"^https?://(www\.)?", "", p.site, flags=re.I).split("/")[0]
        out.append(f'<p class="link"><a href="{e(p.site)}" rel="noopener nofollow">{e(host)}</a></p>')
    out.append("</li>")
    return "".join(out)


def restaurant_ld(p, item_url):
    addr = {"@type": "PostalAddress"}
    if p.addr:
        addr["streetAddress"] = p.addr
    if p.city:
        addr["addressLocality"] = p.city
    addr["addressRegion"] = "FL"
    if p.zip:
        addr["postalCode"] = p.zip
    addr["addressCountry"] = "US"
    x = {"@type": "Restaurant", "name": p.name, "url": item_url, "address": addr}
    if p.lat is not None and p.lon is not None:
        x["geo"] = {"@type": "GeoCoordinates", "latitude": p.lat, "longitude": p.lon}
    if p.site:
        x["sameAs"] = p.site
    if p.founded:
        x["foundingDate"] = str(p.founded)
    if p.cuisine and p.cuisine not in ("Other", "Restaurant", "American & Other"):
        x["servesCuisine"] = p.cuisine
    return x


def item_list(name, places, url, anchors):
    """An all-on-one-page list: each item's url is its anchor on this page; the restaurant's own site goes in sameAs."""
    return {"@context": "https://schema.org", "@type": "ItemList", "name": name, "url": url, "numberOfItems": len(places),
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "item": restaurant_ld(p, anchors.url(p))} for i, p in enumerate(places)]}


def article_ld(url, headline, desc):
    return {"@context": "https://schema.org", "@type": "Article", "headline": headline, "description": desc,
            "datePublished": PUBLISHED, "dateModified": TODAY, "inLanguage": "en", "mainEntityOfPage": url,
            "image": f"{DOMAIN}/og.png", "author": {"@type": "Organization", "name": BRAND, "url": DOMAIN + "/"},
            "publisher": {"@type": "Organization", "name": BRAND, "url": DOMAIN + "/", "logo": {"@type": "ImageObject", "url": f"{DOMAIN}/icon-512.png"}}}


# ---------------------------------------------------------------- counts shared by several pages
N_REST = len(REST)
N_TOWNS = len({p.city for p in REST if p.city})
N_COUNTIES = len({p.county for p in REST if p.county})
N_LICENSED = sum(1 for p in REST if p.r.get("t") == 2)
N_HC = len(HC_ANY)
MI_N = Counter(p.mi for p in HON_L if p.mi)
MI_COUNT = {MI[k]: v for k, v in sorted(MI_N.items())}
N_JBF = sum(1 for p in HON_L if p.jbf)
N_CLASSICS = sum(1 for p in HON_L if p.h & 1)
N_GREEN = sum(1 for p in HON_L if p.gs)
GROUP_N = Counter(p.group for p in INS_L)
DISP_N = Counter(DISP[p.ins["dp"]] for p in INS_L if p.ins.get("dp") is not None and 0 <= p.ins["dp"] < len(DISP))
TYPE_N = Counter(ITYPES[p.ins["t"]] for p in INS_L if p.ins.get("t") is not None and 0 <= p.ins["t"] < len(ITYPES))
INS_SINCE = min((v[0] for p in INS_L for v in (p.ins.get("h") or []) if v and v[0]), default="")
CL_PLACES = [p for p in REST if p.cl]
CL_DATES = sorted(c[0] for p in CL_PLACES for c in p.cl if c and c[0])
CL_ALL = [c for p in CL_PLACES for c in p.cl if c and c[0]]
CL_QUICK = sum(1 for c in CL_ALL if len(c) > 2 and c[2] and (dt.date.fromisoformat(c[2][:10]) - dt.date.fromisoformat(c[0][:10])).days <= 3)
CL_REASONS = [r for r, _ in Counter(str(c[1]).strip() for c in CL_ALL if len(c) > 1 and c[1]).most_common(3)]
CL_NOREOPEN = sum(1 for c in CL_ALL if len(c) < 3 or not c[2])
INS_PATH = "florida-restaurant-inspections.html"
HON_PATH = "florida-michelin-james-beard.html"
OLD_PATH = "florida-oldest-restaurants.html"
GUIDE_PATH = {"cuban": "florida-cuban-sandwiches-cafecito.html", "stonecrab": "florida-stone-crab.html",
              "grouper": "florida-grouper-sandwiches-seafood-shacks.html", "keys": "florida-keys-key-lime-pie-conch.html",
              "oyster": "florida-oyster-bars.html", "fishcamp": "florida-fish-camps-smoked-fish.html",
              "latin": "florida-latin-caribbean-restaurants.html"}
GUIDE_NAME = {"cuban": "Cuban sandwiches & cafecito", "stonecrab": "Stone crabs", "grouper": "Grouper & seafood shacks",
              "keys": "Keys classics", "oyster": "Oyster bars", "fishcamp": "Fish camps & smoked fish", "latin": "Latin & Caribbean"}
GUIDE_LINKS = ([("/" + GUIDE_PATH[k], GUIDE_NAME[k]) for k, _ in GUIDE_TAGS]
               + [("/" + OLD_PATH, "Oldest restaurants"), ("/" + HON_PATH, "MICHELIN & James Beard"), ("/" + INS_PATH, "Restaurant inspections")])

SOURCES_LINE = (f"Place data: hand-checked research by {BRAND} ({CHECKED}); Florida Department of Business and Professional Regulation, "
                "Division of Hotels and Restaurants: food service licenses, inspections and emergency closure reports (public records, "
                "Chapter 119, Florida Statutes); Overture Maps Foundation places (CDLA Permissive 2.0) and addresses (open address sources "
                "under permissive licenses, docs.overturemaps.org/attribution); map outlines © OpenStreetMap contributors, Overture Maps "
                "Foundation (ODbL); U.S. Census Bureau Geocoder (public domain). Not affiliated with or endorsed by the State of Florida, "
                "DBPR, any restaurant or chain, Walt Disney World, Universal Orlando, the MICHELIN Guide or the James Beard Foundation. "
                "MICHELIN and the MICHELIN Guide are trademarks of Michelin; James Beard Foundation and James Beard Award are trademarks "
                "of the James Beard Foundation. Places open and close, so check before you go.")


def by_region(places, key=lambda p: (p.city, p.name.lower())):
    groups = defaultdict(list)
    for p in places:
        groups[p.region or "Elsewhere"].append(p)
    order = REGION_ORDER + ["Elsewhere"]
    return [(REGION_NAME.get(r, "Elsewhere in Florida"), sorted(groups[r], key=key)) for r in order if groups.get(r)]


def region_sections(places, noun, plural_noun, anchors, **item_kw):
    toc = '<ul class="toc">' + "".join(f'<li><a href="#{slug(r)}">{e(r)}</a> ({len(ps)})</li>' for r, ps in by_region(places)) + "</ul>"
    secs = []
    for r, ps in by_region(places):
        anchors.used.update({slug(r), "h-" + slug(r)})
        secs.append(f'<section id="{slug(r)}" aria-labelledby="h-{slug(r)}"><h2 id="h-{slug(r)}">{e(r)}</h2>'
                    f'<p class="sub">{plural(len(ps), noun, plural_noun)}, by town.</p><ol class="places">'
                    + "".join(place_item(p, anchors, **item_kw) for p in ps) + "</ol></section>")
    return toc, "\n".join(secs)


# ---------------------------------------------------------------- city pages: which towns get one
CITY_WANTED = ["Miami", "Miami Beach", "Tampa", "Orlando", "Jacksonville", "St. Petersburg", "Fort Lauderdale", "Key West", "Tallahassee",
               "Gainesville", "Sarasota", "Naples", "Pensacola", "St. Augustine", "Fort Myers", "West Palm Beach", "Clearwater",
               "Daytona Beach", "Apalachicola", "Islamorada", "Kissimmee", "Coral Gables", "Key Largo", "Winter Park", "Destin"]
MIN_LISTED = 5   # hand-checked, honored or oldest places in the town itself: fewer, and the town gets no page yet


def town_listed(c):
    return [p for p in REST if p.city == c and ((p.hc and p.tags) or p.mi or p.jbf)]


CITY_PAGES = [c for c in CITY_WANTED if any(p.city == c and p.lat is not None for p in REST) and len(town_listed(c)) >= MIN_LISTED]
CITY_SKIPPED = {c: len(town_listed(c)) for c in CITY_WANTED if c not in CITY_PAGES}


def city_url(c):
    return f"/cities/{slug(c)}.html"


def city_links(current=None):
    return '<ul class="cities">' + "".join(f'<li><a href="{city_url(c)}"{" aria-current=" + chr(34) + "page" + chr(34) if c == current else ""}>{e(c)}</a></li>'
                                           for c in CITY_PAGES) + "</ul>"


def other_guides(skip):
    return "Other guides: " + ", ".join(f'<a href="{u}">{e(t)}</a>' for u, t in GUIDE_LINKS if u != skip) + "."


def guide_page(path, h1, kicker, title_opts, desc_opts, lede, about_html, places, noun, plural_noun, list_name, region=True, **item_kw):
    url = f"{DOMAIN}/{path}"
    title, desc = fit(title_opts, 50, 60, path + " title"), fit(desc_opts, 140, 160, path + " description")
    nav, bc = crumbs([("Home", "/"), (h1, "/" + path)])
    anchors = Anchors(url)
    if region:
        toc, secs = region_sections(places, noun, plural_noun, anchors, **item_kw)
        jump = f"<h2>Jump to a region</h2>\n    {toc}"
    else:
        secs = (f'<section id="list" aria-labelledby="h-list"><h2 id="h-list">Oldest first</h2><ol class="places">'
                f'{"".join(place_item(p, anchors, **item_kw) for p in places)}</ol></section>')
        jump = ""
    body = f"""{nav}
  <main id="main">
  <section class="hero">
    <p class="kicker">{kicker}</p>
    <h1>{e(h1)}</h1>
    <p class="lede">{lede}</p>
    <div class="cta-row">{store_button()}<span class="pill store-note">{STORE_NOTE}</span></div>
  </section>
  <section id="about">
    {about_html}
    <p class="fine">{other_guides("/" + path)} City pages: {", ".join(f'<a href="{city_url(c)}">{e(c)}</a>' for c in CITY_PAGES)}.</p>
    {jump}
  </section>
{secs}
  </main>"""
    page(path, title, desc, body, [article_ld(url, h1, desc), bc, item_list(list_name, places, url, anchors)])


def towns_text(places, k):
    return join_words([t for t, _ in Counter(p.city for p in places).most_common(k)])


def towns_counts(places, k=8):
    return ", ".join(f"{t} ({n})" for t, n in Counter(p.city for p in places).most_common(k))


def top_dishes(places, k=6, skip=()):
    c = Counter()
    for p in places:
        for d in {x.strip().lower() for x in re.split(r"[;,]", p.r.get("dish") or "") if x.strip()}:
            if d not in skip:
                c[d] += 1
    return ", ".join(f"{d} ({n})" for d, n in c.most_common(k) if n > 1)


HOW_BUILT = ("How the list was built: each place was checked against a 2025 or 2026 source, such as its own website or menu, recent local "
             "news or an official tourism listing, with the address checked. Places with no current source or a dead website were left "
             "out. Nothing here comes from review sites, and the order is by region and town, not by anyone's rating. Menus change, so "
             "check before you go.")
APP_LINE = f"In the {BRAND} app, the same list sorts by distance from you, and each place opens Apple Maps' own card for live hours, photos and directions."


def checked_kicker():
    return f"{BRAND} guide · checked {CHECKED}"


def seasonal_line(places):
    n = sum(1 for p in places if p.season)
    return f" {plural(n, 'place')} on this list {'notes a season' if n == 1 else 'note a season'}; seasonal is not closed." if n else ""


# ---------------------------------------------------------------- the seven themed guides
assert all(len(v) > 1 for v in L.values()), "the guide copy writes plural nouns"
G = L["cuban"]
n_tampa = sum(1 for p in G if p.county == "Hillsborough")
n_mdade = sum(1 for p in G if p.county == "Miami-Dade")
guide_page(GUIDE_PATH["cuban"], "Florida Cuban sandwiches & cafecito", checked_kicker(),
           [f"Florida Cuban Sandwiches & Cafecito: {len(G)} Checked Places", f"Cuban Sandwiches & Cafecito in Florida: {len(G)} Places",
            f"Florida Cuban Sandwiches & Cafecito | {BRAND}"],
           [f"{plural(len(G), 'Florida place')} for Cuban sandwiches, cafecito and coffee-window colada, checked in {CHECKED} against a 2025–26 source, by region and town.",
            f"{plural(len(G), 'Florida place')} for Cuban sandwiches, bakeries and cafecito, each checked in {CHECKED} against a 2025–26 source, listed by region and town.",
            f"{plural(len(G), 'Florida spot')} for a Cuban sandwich, pastelitos or a cafecito, hand-checked in {CHECKED} against a 2025–26 source, by region and town."],
           f"{plural(len(G), 'restaurant')}, bakeries and coffee windows across Florida known for Cuban sandwiches and Cuban coffee, each checked in {CHECKED} against a 2025–26 source: its own menu or site, recent local news or an official tourism listing. {n_mdade:,} are in Miami-Dade County and {n_tampa:,} in Hillsborough (Tampa).",
           f"""<h2>The sandwich and the coffee window</h2>
    <p>A Cuban sandwich is roast pork, ham, Swiss cheese, pickles and mustard on Cuban bread, pressed flat and hot. Tampa's version, from the Ybor City cigar-factory days, usually adds Genoa salami. The coffee comes strong and sweet: a cafecito is a single shot of Cuban espresso, and a colada is a bigger cup poured into thimble-sized cups to share, often from a walk-up window, the ventanita.</p>
    <h2>What's on the list</h2>
    <p>Towns with the most: {e(towns_counts(G))}. The dishes we found most often: {e(top_dishes(G))}.</p>
    <p>{HOW_BUILT}</p>
    <p>{APP_LINE}</p>""",
           G, "place", "places", "Florida Cuban sandwich and cafecito spots")

G = L["stonecrab"]
guide_page(GUIDE_PATH["stonecrab"], "Florida stone crab", f"{checked_kicker()} · season Oct 15 – May 1",
           [f"Florida Stone Crab: {len(G)} Checked Places, In Season Oct–May", f"Florida Stone Crab Claws: {len(G)} Checked Places | {BRAND}",
            f"Where to Eat Florida Stone Crab: {len(G)} Checked Places"],
           [f"{plural(len(G), 'Florida place')} for stone crab claws, checked in {CHECKED} against a 2025–26 source. The FWC season runs October 15 to May 1. By region and town.",
            f"{plural(len(G), 'Florida place')} serving stone crab claws in season (October 15 to May 1), each checked in {CHECKED} against a 2025–26 source, by region.",
            f"{plural(len(G), 'Florida restaurant')} and fish markets for stone crab claws, in season October 15 to May 1, checked in {CHECKED}, by region and town."],
           f"{plural(len(G), 'restaurant')}, fish houses and markets across Florida that serve stone crab claws in season, each checked in {CHECKED} against a 2025–26 source. Florida's stone crab season, set by the Florida Fish and Wildlife Conservation Commission (FWC), runs from October 15 to May 1: out of season, these places are open but the claws aren't on the menu.",
           f"""<h2>A claw, not a crab</h2>
    <p>Florida stone crab is sold as claws: harvesters take the claws and return the crab to the water, where it can grow them back. They're served chilled and cracked, usually with a mustard sauce. The commercial and recreational season set by the FWC runs from October 15 to May 1, so a stone crab place is seasonal, not closed, the rest of the year.{seasonal_line(G)}</p>
    <h2>What's on the list</h2>
    <p>Towns with the most: {e(towns_counts(G))}.</p>
    <p>{HOW_BUILT}</p>
    <p>{APP_LINE}</p>""",
           G, "place", "places", "Florida stone crab restaurants")

G = L["grouper"]
n_gulf = sum(1 for p in G if p.region in ("Panhandle", "Tampa Bay", "Southwest"))
guide_page(GUIDE_PATH["grouper"], "Florida grouper sandwiches & seafood shacks", checked_kicker(),
           [f"Florida Grouper Sandwiches & Seafood Shacks: {len(G)} Places", f"Florida Grouper Sandwiches: {len(G)} Checked Seafood Shacks",
            f"Grouper Sandwiches & Seafood Shacks in Florida | {BRAND}"],
           [f"{len(G):,} Florida seafood shacks, docks and waterfront fish houses for a grouper sandwich, each checked in {CHECKED} against a 2025–26 source, by region and town.",
            f"{plural(len(G), 'Florida place')} for a fried, grilled or blackened grouper sandwich and the day's catch, each checked in {CHECKED} against a 2025–26 source, by region.",
            f"{len(G):,} Florida seafood shacks and fish houses for a grouper sandwich, checked in {CHECKED} against a 2025–26 source, by region and town.",
            f"{plural(len(G), 'Florida place')} for a fried, grilled or blackened grouper sandwich, each checked in {CHECKED} against a 2025–26 source, by region.",
            f"{plural(len(G), 'Florida seafood shack')} and waterfront fish houses for grouper sandwiches, hand-checked in {CHECKED}, listed by region and town."],
           f"{plural(len(G), 'seafood shack')}, fish houses and waterfront grills across Florida for a grouper sandwich and the day's catch, each checked in {CHECKED} against a 2025–26 source. {n_gulf:,} of them are in the Panhandle, Tampa Bay and Southwest Florida.",
           f"""<h2>The grouper sandwich</h2>
    <p>A Florida grouper sandwich is a thick fillet, fried, grilled or blackened, on a bun with lettuce, tomato and tartar sauce, and it's on the menu at most seafood shacks on both coasts. The list adds the docks, fish markets with kitchens and beach grills where it's served, along with shrimp, mullet and the day's catch.</p>
    <h2>What's on the list</h2>
    <p>Towns with the most: {e(towns_counts(G))}. The dishes we found most often: {e(top_dishes(G))}.</p>
    <p>{HOW_BUILT}</p>
    <p>{APP_LINE}</p>""",
           G, "place", "places", "Florida grouper sandwich and seafood shack restaurants")

G = L["keys"]
n_monroe = sum(1 for p in G if p.county == "Monroe")
guide_page(GUIDE_PATH["keys"], "Florida Keys classics: key lime pie & conch", checked_kicker(),
           [f"Florida Keys Classics: Key Lime Pie & Conch, {len(G)} Places", f"Key Lime Pie & Conch Fritters: {len(G)} Checked Keys Places",
            f"Florida Keys Food: Key Lime Pie & Conch | {BRAND}"],
           [f"{plural(len(G), 'place')} for key lime pie, conch fritters and Keys seafood, checked in {CHECKED} against a 2025–26 source, from Key Largo to Key West.",
            f"{plural(len(G), 'place')} for key lime pie, conch fritters and Florida Keys seafood, each checked in {CHECKED} against a 2025–26 source, by region and town."],
           f"{plural(len(G), 'place')} for the Keys' classics, key lime pie, conch fritters and chowder and Keys seafood, each checked in {CHECKED} against a 2025–26 source. {n_monroe:,} are in the Keys themselves (Monroe County); the rest are mainland places known for the same dishes.",
           f"""<h2>What the Keys eat</h2>
    <p>Key lime pie is made with the small, tart key lime, sweetened condensed milk and egg yolks. Conch comes as fritters and chowder, and the Keys' seafood houses cook the local catch, such as hogfish, yellowtail snapper, mahi and pink shrimp.</p>
    <h2>What's on the list</h2>
    <p>Towns with the most: {e(towns_counts(G))}. The dishes we found most often: {e(top_dishes(G))}.</p>
    <p>{HOW_BUILT}</p>
    <p>{APP_LINE}</p>""",
           G, "place", "places", "Florida Keys classic restaurants")

G = L["oyster"]
guide_page(GUIDE_PATH["oyster"], "Florida oyster bars & raw bars", checked_kicker(),
           [f"Florida Oyster Bars & Raw Bars: {len(G)} Checked Places", f"Florida Oyster Bars: {len(G)} Checked Raw Bars | {BRAND}",
            f"Florida Oyster Bars and Raw Bars | {BRAND}"],
           [f"{len(G):,} Florida oyster bars and raw bars, checked in {CHECKED} against a 2025–26 source: raw, steamed and baked oysters, by region and town.",
            f"{plural(len(G), 'Florida oyster bar')} and raw bars, each checked in {CHECKED} against a 2025–26 source, from the Panhandle to the Keys, by region and town.",
            f"{plural(len(G), 'Florida place')} for oysters raw, steamed or baked, hand-checked in {CHECKED} against a 2025–26 source, by region and town."],
           f"{plural(len(G), 'oyster bar')}, raw bars and seafood houses across Florida where oysters are the main event, raw on the half shell, steamed or baked, each checked in {CHECKED} against a 2025–26 source.",
           f"""<h2>Oysters, Florida style</h2>
    <p>Florida's oyster bars run from Panhandle shacks with a shucking counter to raw bars on the Atlantic and the Keys. Oysters come raw on the half shell with saltines and cocktail sauce, steamed by the bucket, or baked with toppings. Where the oysters come from changes with the season and the harvest, so ask; we name a source only when the place itself does.</p>
    <h2>What's on the list</h2>
    <p>Towns with the most: {e(towns_counts(G))}. The dishes we found most often: {e(top_dishes(G))}.</p>
    <p>{HOW_BUILT}</p>
    <p>{APP_LINE}</p>""",
           G, "place", "places", "Florida oyster bars and raw bars")

G = L["fishcamp"]
guide_page(GUIDE_PATH["fishcamp"], "Florida fish camps & smoked fish", checked_kicker(),
           [f"Florida Fish Camps & Smoked Fish Dip: {len(G)} Checked Places", f"Old Florida Fish Camps & Smoked Fish: {len(G)} Places",
            f"Florida Fish Camps and Smoked Fish | {BRAND}"],
           [f"{len(G):,} Old Florida fish camps and smoked fish spots, checked in {CHECKED} against a 2025–26 source: fried fish, fish dip, smoked mullet, by region.",
            f"{plural(len(G), 'Florida fish camp')} and smoked fish spots on rivers, lakes and the coast, each checked in {CHECKED} against a 2025–26 source, by region and town.",
            f"{plural(len(G), 'Florida fish camp')}, river restaurants and smoked fish spots, hand-checked in {CHECKED} against a 2025–26 source, listed by region and town."],
           f"{plural(len(G), 'fish camp')}, river and lake restaurants and smoked fish spots across Florida, many of them Old Florida places on the water, each checked in {CHECKED} against a 2025–26 source.",
           f"""<h2>Old Florida on the water</h2>
    <p>Fish camps started as bait shops and boat ramps on rivers, lakes and the Intracoastal, and many grew kitchens: fried catfish and mullet, shrimp, hush puppies and a view of the water. Smoked fish dip, made from smoked mullet, mackerel or other local fish, is the snack of both coasts.</p>
    <h2>What's on the list</h2>
    <p>Towns with the most: {e(towns_counts(G))}. The dishes we found most often: {e(top_dishes(G))}.</p>
    <p>{HOW_BUILT}</p>
    <p>{APP_LINE}</p>""",
           G, "place", "places", "Florida fish camps and smoked fish restaurants")

G = L["latin"]
latin_kinds = Counter(p.cuisine for p in G if p.cuisine)
guide_page(GUIDE_PATH["latin"], "Florida Latin & Caribbean restaurants", checked_kicker(),
           [f"Florida Latin & Caribbean Restaurants: {len(G)} Checked Places", f"Latin & Caribbean Food in Florida: {len(G)} Checked Places",
            f"Florida Latin and Caribbean Restaurants | {BRAND}"],
           [f"{plural(len(G), 'Florida restaurant')} for Haitian, Venezuelan, Colombian, Puerto Rican, Peruvian and Dominican food, checked in {CHECKED}, by region and town.",
            f"{len(G):,} Florida restaurants and bakeries for Haitian, Venezuelan, Colombian, Puerto Rican, Peruvian and Dominican food, checked in {CHECKED}, by region.",
            f"{plural(len(G), 'Florida place')} for Haitian, Venezuelan, Colombian, Puerto Rican and Peruvian food, each checked in {CHECKED} against a 2025–26 source, by region.",
            f"{plural(len(G), 'Latin and Caribbean restaurant')} and bakeries in Florida, each checked in {CHECKED} against a 2025–26 source, listed by region and town.",
            f"{plural(len(G), 'Florida place')} for Haitian, Venezuelan, Colombian, Puerto Rican and Peruvian food, each checked in {CHECKED} against a 2025–26 source.",
            f"{plural(len(G), 'Latin and Caribbean restaurant')} in Florida, each checked in {CHECKED} against a 2025–26 source, listed by region and town."],
           f"{plural(len(G), 'restaurant')}, bakeries and cafés across Florida for the Latin American and Caribbean cooking beyond Cuban, each checked in {CHECKED} against a 2025–26 source. Towns with the most: {e(towns_counts(G, 5))}.",
           f"""<h2>Beyond the Cuban sandwich</h2>
    <p>Florida eats the whole region: Haitian griot and pikliz, Venezuelan arepas and cachapas, Colombian bandeja paisa, Puerto Rican mofongo and pernil, Peruvian ceviche, Nicaraguan fritanga and Dominican mangú. The dish line under each place says what it serves, from its own menu or a recent source.</p>
    <h2>What's on the list</h2>
    <p>The dishes we found most often: {e(top_dishes(G))}.</p>
    <p>{HOW_BUILT}</p>
    <p>{APP_LINE}</p>""",
           G, "place", "places", "Florida Latin and Caribbean restaurants")

# ---------------------------------------------------------------- MICHELIN & James Beard
MI_SHORT = {5: "3-Star", 4: "2-Star", 3: "1-Star", 2: "Bib Gourmand", 1: "Recommended"}
mi_parts = [f"{words_num(MI_N[k])} {MI_SHORT[k]}" for k in (5, 4, 3, 2, 1) if MI_N.get(k)]
N_MI = sum(MI_N.values())
mi_line = (join_words(mi_parts) + (" restaurants" if N_MI != 1 else " restaurant")) if mi_parts else ""
green = (f" {plural(N_GREEN, 'restaurant')} also {'holds' if N_GREEN == 1 else 'hold'} a MICHELIN Green Star from the 2026 selection, an "
         "honor MICHELIN is phasing out during 2026.") if N_GREEN else ""
guide_page(HON_PATH, "Florida MICHELIN & James Beard restaurants", f"{BRAND} guide · honors as of {CHECKED}",
           [f"Florida MICHELIN & James Beard Restaurants | {BRAND}", "Florida MICHELIN Guide & James Beard Restaurants List",
            f"MICHELIN & James Beard Restaurants in Florida | {BRAND}"],
           [f"{plural(len(HON_L), 'Florida restaurant')} in the MICHELIN Guide Florida 2026 or honored by the James Beard Foundation from 2023 to 2026, by region and town.",
            f"{plural(len(HON_L), 'Florida restaurant')} in the MICHELIN Guide Florida 2026 or honored by the James Beard Foundation, 2023 to 2026, listed by region and town.",
            f"{plural(len(HON_L), 'Florida restaurant')} with a MICHELIN Guide Florida 2026 distinction or a James Beard honor, listed by region and town."],
           f"{plural(len(HON_L), 'Florida restaurant')} with an honor: {plural(N_MI, 'place')} from the MICHELIN Guide Florida 2026 selection ({e(mi_line)}), and {plural(N_JBF, 'place')} with a James Beard Foundation award, finalist or semifinalist nod from 2023 to 2026 or an America's Classics award.",
           f"""<h2>What's here, and what isn't</h2>
    <p>These are facts from the honoring organizations, not ratings: a distinction in MICHELIN's first statewide Florida selection (announced May 28, 2026), or a James Beard Foundation award, finalist or semifinalist recognition from 2023 to 2026, or an America's Classics award from any year ({plural(N_CLASSICS, 'place')}). A finalist or semifinalist is listed as one, never as a winner. Restaurants that have closed since their honor are left out, and a few honors belong to a chef or restaurant group rather than the restaurant itself; the line under the place says so. Readers' polls, "best of" lists and star ratings from review sites are never included.{green}</p>
    <p class="fine">MICHELIN and the MICHELIN Guide are trademarks of Michelin. James Beard Foundation and James Beard Award are trademarks of the James Beard Foundation. {BRAND} is not affiliated with either.</p>""",
           HON_L, "restaurant", "restaurants", "Florida MICHELIN Guide and James Beard restaurants", honors=True)

# ---------------------------------------------------------------- oldest
oldest_named = next((p for p in OLD_L if p.promo_ok()), None)
assert all(p.founded <= 1960 for p in OLD_L), "the oldest-places copy says 'since 1960 or earlier'"
old_pre1950 = sum(1 for p in OLD_L if p.founded < 1950)
from_line = f" The oldest, {e(oldest_named.name)} in {e(oldest_named.city)}, dates from {oldest_named.founded}." if oldest_named else ""
guide_page(OLD_PATH, "Florida's oldest restaurants", checked_kicker(),
           [f"Florida's Oldest Restaurants: {len(OLD_L)} Places, Oldest First", f"Oldest Restaurants in Florida: {len(OLD_L)} Places | {BRAND}",
            "Florida's Oldest Restaurants, Year by Year | Florida Eats"],
           [f"{plural(len(OLD_L), 'Florida restaurant')} and bars open at the same address since 1960 or earlier, oldest first, each with a note on what its founding year rests on.",
            f"Florida's oldest restaurants and bars: {plural(len(OLD_L), 'place')} open at the same address since 1960 or earlier, oldest first, with the source behind each year.",
            f"Florida's oldest restaurants: {plural(len(OLD_L), 'place')} open at the same address since 1960 or earlier, oldest first, with the source behind each year.",
            f"Florida's oldest restaurants and bars: {plural(len(OLD_L), 'place')} with a documented founding year at their current address, oldest first, sources noted."],
           f"{plural(len(OLD_L), 'Florida restaurant')}, bars and lunch counters open at their current address since 1960 or earlier, oldest first, each checked in {CHECKED} against a 2025–26 source. {old_pre1950:,} opened before 1950.{from_line} Under each one, a note says what the year rests on.",
           f"""<h2>How a founding year is chosen</h2>
    <p>A founding year here means the year the place opened at this address in its present form, as the place itself or a published history documents it. It is never the year a brand started elsewhere, and never a year before a move. When sources disagree we use the later date. Several places call themselves the oldest in their town or county, and one calls itself Florida's oldest restaurant; those are their own claims, and the note under each place attributes them as written. A place that isn't here may simply not have been documented yet: email us with a source.</p>""",
           OLD_L, "place", "places", "Florida's oldest restaurants", region=False, show_fn=True)

# ---------------------------------------------------------------- the inspections explainer (counts only: no place is named here)
url = f"{DOMAIN}/{INS_PATH}"
n_ins = len(INS_L)
INS_DATE = hdate(INS_THROUGH)
nav, bc = crumbs([("Home", "/"), ("Florida restaurant inspections", "/" + INS_PATH)])
title = fit(["Florida Restaurant Inspections, Explained: DBPR Results", "Florida Restaurant Inspections: How DBPR Results Work",
             f"Florida Restaurant Inspections Explained | {BRAND}"], 50, 60, "inspections title")
desc = fit([f"How Florida's DBPR inspects restaurants, what its three results mean, and how {n_ins:,} licensed places stood at their latest visit. Florida gives no grade.",
            f"How Florida's DBPR inspects restaurants, what Met Inspection Standards and Follow-Up Inspection Required mean, and the latest results for {n_ins:,} places.",
            f"How Florida's DBPR inspects restaurants and what its three results mean, with the latest results for {n_ins:,} licensed places. Florida gives no grade."],
           140, 160, "inspections description")
grp_items = []
for g in (0, 1, 2):
    disps = [d for d, gg in DBPR_GROUP.items() if gg == g]
    lis = "".join(f"<li>“{e(d)}”" + (f" ({plural(DISP_N[d], 'place')})" if DISP_N.get(d) else "") + "</li>" for d in disps)
    grp_items.append(f'<li><span class="res res-{g}">{e(GROUPS[g])}</span><ul>{lis}</ul>'
                     f'<p class="count">{plural(GROUP_N.get(g, 0), "place")} at their latest visit.</p></li>')
ungrouped = GROUP_N.get(None, 0)
ungrouped_line = (f" For {plural(ungrouped, 'place')} the latest visit ended in a disposition DBPR doesn't put in a group "
                  f"({e(join_words(['“' + d + '”' for d in sorted(d for d in DISP_N if d not in DBPR_GROUP)]))}), so no group is shown.") if ungrouped else ""
type_line = join_words([f"{t} ({n:,})" for t, n in TYPE_N.most_common()])
county_rows = []
for co in sorted({p.county for p in INS_L if p.county}):
    ps = [p for p in INS_L if p.county == co]
    gc = Counter(p.group for p in ps)
    county_rows.append(f'<tr><th scope="row">{e(co)}</th><td class="n">{len(ps):,}</td><td class="n">{gc.get(0, 0):,}</td>'
                       f'<td class="n">{gc.get(1, 0):,}</td><td class="n">{gc.get(2, 0):,}</td></tr>')
cl_line = (f"<p>DBPR also publishes a weekly report of emergency closures, with the reason in its own words (the most common in our data: "
           f"{e(join_words(['“' + r + '”' for r in CL_REASONS]))}) "
           f"and the date the place was allowed to reopen. {plural(len(CL_PLACES), 'place')} in our data had at least one emergency closure in the reports "
           f"from {e(hdate(CL_DATES[0]))} to {e(hdate(CL_DATES[-1]))}. Between them they had {plural(len(CL_ALL), 'closure')}: {CL_QUICK:,} list a reopening within three days, "
           f"and {CL_NOREOPEN:,} list no reopening date. The {BRAND} app and the "
           f"<a href=\"/explore/#g=inspections\">web search</a> show each place's closures with DBPR's reason and reopening date.</p>") if CL_DATES else ""
body = f"""{nav}
  <main id="main">
  <section class="hero">
    <p class="kicker">{BRAND} guide · records through {e(INS_DATE)}</p>
    <h1>Florida restaurant inspections, explained</h1>
    <p class="lede">Florida's Department of Business and Professional Regulation (DBPR) licenses the state's restaurants and inspects them, and it publishes every visit's result. It doesn't grade them: in DBPR's words, “{NO_GRADE}.” Here is how an inspection works, what DBPR's three result groups mean, and where the {n_ins:,} DBPR-licensed places in our data stood at their latest visit, with records through {e(INS_DATE)}.</p>
  </section>
  <section id="how">
    <h2>How DBPR inspects</h2>
    <p>Inspectors from DBPR's Division of Hotels and Restaurants make routine, unannounced inspections, and visit after a complaint, before a new license and on callbacks that check whether violations were fixed. At the latest visit to the places in our data, the visit types were: {e(type_line)}.</p>
    <p>DBPR sorts violations into three kinds. High-priority violations are the ones it says could contribute directly to a foodborne illness or injury, such as cooking, cooling and hand-washing problems. Intermediate violations could lead to those risks if they aren't corrected, and basic violations are best practices. DBPR publishes the count of each kind for every visit; the {BRAND} app shows DBPR's counts from each place's latest routine inspection, never a score of ours.</p>
  </section>
  <section id="groups">
    <h2>DBPR's three result groups</h2>
    <p class="sub">Every visit ends in a disposition, which DBPR's records spell out (“Warning Issued”). DBPR's inspections page sorts the dispositions into three groups. Here they are, with the dispositions DBPR puts in each and how many places in our data had each one at their latest visit:</p>
    <ul class="groups">{"".join(grp_items)}</ul>
    <p>A Follow-Up Inspection Required result means the inspector will come back to check that violations were corrected; the place stays open. Facility Temporarily Closed means DBPR recommended an emergency order (or found the place operating without a license); a closed place reopens after a callback inspection, which DBPR records as “Emergency Order Callback Complied.”{ungrouped_line}</p>
    {cl_line}
    <p>One visit is a snapshot of one day, and conditions can change quickly; that's why DBPR doesn't grade restaurants, and why this site doesn't rank them by inspections. We don't list places by their results here.</p>
  </section>
  <section id="lookup">
    <h2>Look up a restaurant</h2>
    <p>Search for a place in the <a href="/explore/">{BRAND} web app</a>: its panel shows DBPR's result group and disposition for the latest visit, with the date, the counts from the latest routine inspection, up to eight recent visits and any emergency closures, plus the DBPR license number. For the inspector's full report, with each violation as written, search that license number in DBPR's <a href="{e(DBPR_SEARCH)}" rel="noopener">View Food &amp; Lodging Inspections</a> search. DBPR's bulk files are on its <a href="{e(DBPR_RECORDS)}" rel="noopener">public records page</a>, and its own explanation of the results is on its <a href="{e(DBPR_INSPECTIONS)}" rel="noopener">inspections page</a>.</p>
    <p class="fine">Our data: DBPR's food service licenses, inspections since {e(hmonth(INS_SINCE)) if INS_SINCE else "July 2023"} and emergency closure reports, downloaded {e(hdate(DBPR_FETCHED))}. DBPR publishes inspections with a lag, so we use records through {e(INS_DATE)}. Places licensed by another agency, such as coffee shops and bakeries the Department of Agriculture licenses, have no DBPR results here.</p>
  </section>
  <section id="counties" aria-labelledby="h-counties">
    <h2 id="h-counties">Latest results by county</h2>
    <p class="sub">Places in our data with a DBPR result, by DBPR's group at the latest visit, counties A to Z. Counts, not a ranking: a county with more restaurants has more of every result.</p>
    <div class="tbl" role="region" aria-labelledby="h-counties" tabindex="0"><table><thead><tr><th scope="col">County</th><th scope="col" class="n">Places</th><th scope="col" class="n">Met standards</th><th scope="col" class="n">Follow-up</th><th scope="col" class="n">Closed</th></tr></thead><tbody>{"".join(county_rows)}</tbody></table></div>
    <p class="fine">{other_guides("/" + INS_PATH)}</p>
  </section>
  </main>"""
page(INS_PATH, title, desc, body, [article_ld(url, "Florida restaurant inspections, explained", desc), bc])

# ---------------------------------------------------------------- city pages
city_stats = {}
SEC_DEFS = [  # key, long title phrase, short title phrase, h1 phrase, description phrase builder
    ("cuban", "Cuban Sandwiches & Cafecito", "Cuban Food", "Cuban sandwiches & cafecito", lambda n: plural(n, "hand-checked Cuban sandwich or cafecito spot", "hand-checked Cuban sandwich and cafecito spots")),
    ("stonecrab", "Stone Crabs", "Stone Crab", "stone crabs", lambda n: plural(n, "stone crab spot")),
    ("grouper", "Grouper & Seafood Shacks", "Grouper", "grouper & seafood shacks", lambda n: plural(n, "grouper and seafood shack", "grouper and seafood shacks")),
    ("keys", "Key Lime Pie & Conch", "Keys Classics", "key lime pie & conch", lambda n: plural(n, "key lime pie and conch spot")),
    ("oyster", "Oyster Bars", "Oyster Bars", "oyster bars", lambda n: plural(n, "oyster bar")),
    ("fishcamp", "Fish Camps & Smoked Fish", "Fish Camps", "fish camps & smoked fish", lambda n: plural(n, "fish camp or smoked fish spot", "fish camps and smoked fish spots")),
    ("latin", "Latin & Caribbean Food", "Latin Food", "Latin & Caribbean food", lambda n: plural(n, "Latin or Caribbean restaurant", "Latin and Caribbean restaurants")),
]
SEC_ORDER = [k for k, *_ in SEC_DEFS] + ["hon", "oldest"]
CITY_INFO = {}
for c in CITY_PAGES:
    here = [p for p in REST if p.city == c]
    info = {k: sorted([p for p in L[k] if p.city == c], key=P.featured_key) for k, _ in GUIDE_TAGS}
    info["hon"] = sorted([p for p in HON_L if p.city == c], key=P.featured_key)
    info["oldest"] = [p for p in OLD_L if p.city == c]
    info["insp"] = Counter(p.group for p in INS_L if p.city == c)
    info["n_ins"] = sum(1 for p in INS_L if p.city == c)
    info["cuis"] = Counter(p.cuisine for p in here if p.cuisine and p.cuisine not in ("Other", "American & Other")).most_common(10)
    info["n_town"] = len(here)
    listed, seen = [], set()
    for k in SEC_ORDER:
        for p in info[k]:
            if id(p) not in seen:
                seen.add(id(p)); listed.append(p)
    info["listed"] = listed
    CITY_INFO[c] = info
    city_stats[c] = {"restaurants": len(here), "listed": len(listed), **{k: len(info[k]) for k in SEC_ORDER},
                     "dbpr_results": info["n_ins"], "dbpr_by_group": {GROUPS[g] if g is not None else "not grouped": n for g, n in info["insp"].items()}}


def city_sections(info):
    """The sections a city page has, biggest first: (key, long, short, h1 phrase, description phrase)."""
    out = [(k, lt, st, h1p, dp(len(info[k]))) for k, lt, st, h1p, dp in SEC_DEFS if info[k]]
    if info["hon"]:
        has_mi, has_jb = any(p.mi for p in info["hon"]), any(p.jbf for p in info["hon"])
        long = "MICHELIN & James Beard" if has_mi and has_jb else "MICHELIN" if has_mi else "James Beard"
        out.append(("hon", long, "MICHELIN" if has_mi else "James Beard", long if long != "James Beard" else "James Beard honorees",
                    plural(len(info["hon"]), "MICHELIN or James Beard honoree")))
    if info["oldest"]:
        out.append(("oldest", "Oldest Restaurants", "Oldest Places", "oldest restaurants", f"the oldest restaurants (back to {info['oldest'][0].founded})"))
    return sorted(out, key=lambda s: (-len(info[s[0]]), SEC_ORDER.index(s[0])))


def tjoin(xs):
    if len(xs) == 1:
        return xs[0]
    conj = " and " if any("&" in x for x in xs) else " & "
    return ", ".join(xs[:-1]) + conj + xs[-1]


def city_title(c, secs):
    cands = []
    for k in range(min(len(secs), 3), 0, -1):
        for col in (1, 2):
            J = tjoin([s[col] for s in secs[:k]])
            forms = [f"{c} {J} | {BRAND}", f"{c}, FL {J} | {BRAND}", f"{c}, Florida {J}", f"{c}, FL {J}", f"{c} {J}"]
            if "Restaurant" not in J:
                forms += [f"{c} Restaurants: {J}", f"{c}, FL Restaurants: {J}", f"{c} Restaurants: {J} | {BRAND}", f"{c}, Florida Restaurants: {J}",
                          f"{c} {J} & Restaurants", f"{c} {J} & Restaurants | {BRAND}", f"{c}, Florida {J} & Restaurants"]
            cands += forms
    cands += [f"{c} Restaurants: What {c} Eats | {BRAND}", f"{c}, Florida Restaurants by Kind | {BRAND}", f"{c}, FL Restaurants, Cafés & Bars | {BRAND}",
              f"{c}, Florida Restaurants, Cafés and Bars", f"{c} Restaurants, Cafés & Bars | {BRAND}"]
    return fit(cands, 50, 60, c + " title")


def city_desc(c, info, secs):
    n_town = info["n_town"]
    leads = [f"In {c}, Florida", f"{c}, Florida", f"{c}, FL"]
    tails = [f". Search {n_town:,} {c} restaurants, cafés and bars", f". Search {n_town:,} local places to eat",
             f", plus {n_town:,} local places to eat on a searchable map", f", plus {n_town:,} more local places to eat", ""]
    extras = ["", f" Checked in {CHECKED}.", " Free iPhone app coming soon.", f" Checked in {CHECKED}. Free iPhone app coming soon."]

    def gen():
        for k in range(len(secs), 0, -1):
            J = join_words([s[4] for s in secs[:k]])
            for lead in leads:
                for tail in tails:
                    for x in extras:
                        yield f"{lead}: {J}{tail}.{x}"
    return fit(list(dict.fromkeys(s.replace("..", ".") for s in gen())), 140, 160, c + " description")


SEC_HEAD = {"cuban": ("Cuban sandwiches & cafecito", "cuban"), "stonecrab": ("Stone crabs", "stonecrab"), "grouper": ("Grouper & seafood shacks", "grouper"),
            "keys": ("Keys classics: key lime pie & conch", "keys"), "oyster": ("Oyster bars & raw bars", "oyster"),
            "fishcamp": ("Fish camps & smoked fish", "fishcamp"), "latin": ("Latin & Caribbean", "latin")}
GUIDE_COUNT_NOUN = {"cuban": "Florida Cuban sandwich and cafecito spots", "stonecrab": "Florida stone crab spots", "grouper": "Florida grouper and seafood shacks",
                    "keys": "Keys classics", "oyster": "Florida oyster bars", "fishcamp": "Florida fish camps and smoked fish spots",
                    "latin": "Florida Latin and Caribbean restaurants"}

for c in CITY_PAGES:
    info = CITY_INFO[c]
    path = f"cities/{slug(c)}.html"
    url = DOMAIN + "/" + path
    anchors = Anchors(url)
    secs = city_sections(info)
    title = city_title(c, secs)
    desc = city_desc(c, info, secs)
    k = 3
    while k > 1 and len(join_words([s[3] for s in secs[:k]])) > 48:   # a heading, not the whole table of contents
        k -= 1
    h1_bits = [s[3] for s in secs[:k]] + (["restaurants"] if len(secs) == 1 and "restaurant" not in secs[0][3] else [])
    h1 = f"{c} " + (join_words(h1_bits) + (", and more" if len(secs) > k else "") if secs else "restaurants")
    nav, bc = crumbs([("Home", "/"), ("Cities", "/cities/"), (c, "/" + path)])
    counts = [s[4] for s in secs]
    n_hc = sum(1 for p in info["listed"] if p.hc and p.tags)
    lede = (f"In {e(c)}: {e(join_words(counts))}. "
            + (f"The hand-checked lists were checked in {CHECKED} against 2025–26 sources. " if n_hc else "")
            + f"The {BRAND} app lists {info['n_town']:,} restaurants, cafés, bars and bakeries in {e(c)} and sorts them by distance from you.")
    parts = [f"""{nav}
  <main id="main">
  <section class="hero">
    <p class="kicker">{BRAND} · {e(c)}, Florida</p>
    <h1>{e(h1)}</h1>
    <p class="lede">{lede}</p>
    <div class="cta-row">{store_button()}<span class="pill store-note">{STORE_NOTE}</span></div>
  </section>"""]
    for s in secs:
        key = s[0]
        if key in SEC_HEAD:
            head, gk = SEC_HEAD[key]
            parts.append(f'<section id="{key}" aria-labelledby="h-{key}"><h2 id="h-{key}">{e(head)} in {e(c)}</h2><p class="sub">Hand-checked in {CHECKED} against a 2025–26 source. Statewide: <a href="/{GUIDE_PATH[gk]}">{plural(len(L[gk]), GUIDE_COUNT_NOUN[gk][:-1], GUIDE_COUNT_NOUN[gk])}</a>.</p><ol class="places">'
                         + "".join(place_item(p, anchors) for p in info[key]) + "</ol></section>")
        elif key == "hon":
            parts.append(f'<section id="honors" aria-labelledby="h-honors"><h2 id="h-honors">MICHELIN &amp; James Beard in {e(c)}</h2><p class="sub">MICHELIN Guide Florida 2026 and James Beard Foundation honorees. Honors are facts, not ratings. Statewide: <a href="/{HON_PATH}">{plural(len(HON_L), "Florida MICHELIN and James Beard restaurant")}</a>.</p><ol class="places">'
                         + "".join(place_item(p, anchors, honors=True) for p in info["hon"]) + "</ol></section>")
        elif key == "oldest":
            parts.append(f'<section id="oldest" aria-labelledby="h-oldest"><h2 id="h-oldest">Oldest restaurants in {e(c)}</h2><p class="sub">Open at the same address since 1960 or earlier, as each place or a published history documents it, oldest first. The note under each says what the year rests on. Statewide: <a href="/{OLD_PATH}">Florida\'s oldest restaurants</a>.</p><ol class="places">'
                         + "".join(place_item(p, anchors, show_fn=True) for p in info["oldest"]) + "</ol></section>")
    if info["n_ins"]:
        ig = info["insp"]
        ins_bits = join_words([f"{plural(ig.get(g, 0), 'place')} {GROUPS[g]}" for g in (0, 1, 2) if ig.get(g)])
        parts.append(f'<section id="inspections" aria-labelledby="h-inspections"><h2 id="h-inspections">Inspections in {e(c)}</h2><p class="sub">Florida DBPR has an inspection on record for {plural(info["n_ins"], "place")} we list in {e(c)}. At their latest visit, by DBPR\'s own result groups: {e(ins_bits)}. Florida doesn\'t grade restaurants, and neither do we. Records through {e(hdate(INS_THROUGH))}. Each place\'s results are in the <a href="/explore/#g=inspections&amp;town={e(urllib.parse.quote(c))}">web search</a>; what the results mean: <a href="/{INS_PATH}">Florida restaurant inspections, explained</a>.</p></section>')
    if info["cuis"]:
        rows = "".join(f'<tr><td>{e(k)}</td><td class="n">{n:,}</td></tr>' for k, n in info["cuis"])
        parts.append(f'<section id="cuisines" aria-labelledby="h-cuisines"><h2 id="h-cuisines">What {e(c)} eats</h2><p class="sub">The most common kinds of restaurant among the {info["n_town"]:,} we list in {e(c)}, from DBPR\'s licenses and open map data.</p><table><thead><tr><th scope="col">Kind of place</th><th scope="col" class="n">Places</th></tr></thead><tbody>{rows}</tbody></table></section>')
    parts.append(f'<section id="more" aria-labelledby="h-more"><h2 id="h-more">More Florida cities and towns</h2>{city_links(current=c)}<p class="fine"><a href="/cities/">All city pages</a></p></section>\n  </main>')
    lds = [article_ld(url, h1, desc), bc]
    if info["listed"]:
        lds.append(item_list(f"{c}: " + join_words([s[3] for s in secs]), info["listed"], url, anchors))
    page(path, title, desc, "\n".join(parts), lds)


# ---------------------------------------------------------------- cities index
url = f"{DOMAIN}/cities/"
nav, bc = crumbs([("Home", "/"), ("Cities", "/cities/")])
cards = []
for c in CITY_PAGES:
    info = CITY_INFO[c]
    bits = [f"{s[3]} ({len(info[s[0]])})" for s in city_sections(info)]
    line = (join_words(bits) + ". " if bits else "") + f"{info['n_town']:,} places to eat in all."
    cards.append(f'<a class="card" href="{city_url(c)}"><h3>{e(c)}</h3><p>{e(line[0].upper() + line[1:])}</p></a>')
first, last = CITY_PAGES[:2], CITY_PAGES[-2:]
title = fit([f"Florida Cities & Towns: Restaurant Guides | {BRAND}", f"Florida City Restaurant Guides: {len(CITY_PAGES)} Towns | {BRAND}"], 50, 60, "cities title")
desc = fit([f"Restaurant guides for {len(CITY_PAGES)} Florida cities and beach towns, from {join_words(first)} to {join_words(last)}: Cuban food, seafood and honors.",
            f"Restaurant guides for {len(CITY_PAGES)} Florida cities and towns, from {join_words(first)} to {join_words(last)}: Cuban sandwiches, seafood and more.",
            f"City-by-city Florida restaurant guides for {len(CITY_PAGES)} cities and towns: Cuban sandwiches, stone crabs, oyster bars, MICHELIN and the oldest places."],
           140, 160, "cities description")
skipped_line = (f" Other towns get a page once they have at least {MIN_LISTED} hand-checked or honored places; until then, "
                f'<a href="/explore/">search them</a>.')
body = f"""{nav}
  <main id="main">
  <section class="hero">
    <p class="kicker">{BRAND} · cities and towns</p>
    <h1>Florida cities and towns</h1>
    <p class="lede">A page for Florida's biggest cities and most-visited towns that have enough hand-checked or honored places to say something real: the Cuban sandwiches, stone crabs, seafood shacks, oyster bars, MICHELIN and James Beard honorees and oldest restaurants that are actually there, and how the town did at its DBPR inspections.{skipped_line}</p>
  </section>
  <section id="cities-list">
    <h2>Pick a town</h2>
    <div class="grid2">{"".join(cards)}</div>
  </section>
  </main>"""
page("cities/index.html", title, desc, body, [bc], og_type="website")

# ---------------------------------------------------------------- web app (docs/explore/): data split + page
# The web app lists restaurants only (the venues the app hides by default, such as stadium stands and gas-station counters, stay out).
# Three kinds of file, to keep the first load small for ~52,000 places:
# - core.json: the list, search and map columns. Places are ordered by region, county, town, zip and street, so neighbouring rows
#   share their town, zip and street words and gzip well; coordinates are integer steps of 0.0001° from the previous row ("dla"/"dlo"),
#   and the latest DBPR visit is a day number from 2000-01-01 ("idn").
# - ids.json: each place's stable id (the app's id), in core order. Fetched right after the list renders; saved places and shared
#   #p= links wait for it.
# - detail-<county>.json: phones, websites, notes, licenses, inspection histories and closures, keyed by core index, one file per
#   county (Miami-Dade's is the biggest), fetched when someone opens (or points at) a place there.
os.makedirs(f"{DOCS}/data", exist_ok=True)
DFILES = [slug(c) for c in COUNTIES] + ["other"]   # detail file per county index; "other" for a place with no county
CAL = (D.get("calibration") or {}).get("statewide") or {}
DAY0 = "2000-01-01"


def day_num(iso):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    return (dt.date(int(m[1]), int(m[2]), int(m[3])) - dt.date(2000, 1, 1)).days if m else None


def street_key(a):
    m = re.match(r"\s*(\d+)\s*(.*)", a or "")
    return (m[2].lower(), int(m[1]) if len(m[1]) < 9 else 0) if m else ((a or "").lower(), 0)


def web_order(p):
    rg = list(REGIONS).index(p.region) if p.region else len(REGIONS)
    return (rg, p.county or "", p.city or "", p.zip, street_key(p.addr), p.name.lower(), p.r["id"])


WEB = sorted(REST, key=web_order)
CORE_KEYS = ["n", "c", "co", "cu", "t", "s", "a", "z", "b", "ch", "g", "hc", "ip", "f", "h", "mi", "dish", "dw"]
cols = {k: [] for k in CORE_KEYS + ["dla", "dlo", "jb", "gs", "ig", "idn", "ihp", "ims"]}
ids, shards = [], defaultdict(dict)
prev = [0, 0]
for i, p in enumerate(WEB):
    r = p.r
    ids.append(r["id"])
    for k in CORE_KEYS:
        v = r.get(k)
        if k == "a" and v:
            v = p.addr
        cols[k].append(v)
    for k, j, v in (("dla", 0, p.lat), ("dlo", 1, p.lon)):
        if v is None:
            cols[k].append(None)
        else:
            q = round(v * 10000)
            cols[k].append(q - prev[j])
            prev[j] = q
    dk = r["co"] if r.get("co") is not None else len(COUNTIES)   # the detail file this place's extras go in
    if r.get("co") is None:
        cols["co"][-1] = len(COUNTIES)
    cols["jb"].append(1 if r.get("jbf") else None)
    cols["gs"].append(1 if p.gs else None)
    ins = p.ins or {}
    cols["ig"].append(p.group)
    cols["idn"].append(day_num(ins.get("d")))
    cols["ihp"].append(ins.get("hp"))
    cols["ims"].append((ins.get("im") or 0) + (ins.get("bs") or 0) if ins.get("hp") is not None else None)
    d = {k: r[k] for k in ("ph", "note", "seas", "fn", "jbf", "lic", "cl") if r.get(k)}
    if p.site:
        d["w"] = p.site
    if ins:
        d["in"] = ins
    if d:
        shards[dk][str(i)] = d
assert len(set(ids)) == len(ids), "place ids must be unique (saved places and #p= links use them)"
for f in glob.glob(f"{DOCS}/data/detail*.json"):   # files from an older layout or a region that emptied
    os.remove(f)
DETAIL_FILES = {}
for dk, d in sorted(shards.items()):
    fn = f"detail-{DFILES[dk]}.json"
    json.dump(d, open(f"{DOCS}/data/{fn}", "w"), separators=(",", ":"), ensure_ascii=False)
    DETAIL_FILES[fn] = len(d)
# columns that are mostly empty (hand-checked and honored facts) go as [[index, value], ...] instead of 52,000 nulls
sparse = {k: [[i, v] for i, v in enumerate(cols.pop(k)) if v is not None]
          for k in list(cols) if sum(v is not None for v in cols[k]) < len(WEB) * 0.05}
core = {"generated": D["generated"], "inspections_through": INS_THROUGH, "dbpr_fetched": DBPR_FETCHED, "ins_since": INS_SINCE, "day0": DAY0,
        "n": len(WEB), "cities": CITIES, "cuisines": CUISINES, "counties": COUNTIES + ["Florida"], "brands": D["brands"], "srcs": D["srcs"],
        "dispositions": DISP, "itypes": ITYPES, "groups": GROUPS, "dfiles": DFILES, "calibration": CAL, "cols": cols, "sparse": sparse}
json.dump(core, open(f"{DOCS}/data/core.json", "w"), separators=(",", ":"), ensure_ascii=False)
json.dump(ids, open(f"{DOCS}/data/ids.json", "w"), separators=(",", ":"))
json.dump(json.load(open(f"{ROOT}/data/fl/fl_shapes.json")), open(f"{DOCS}/data/fl_shapes.json", "w"), separators=(",", ":"))


def sizes(path):
    raw = open(path, "rb").read()
    return len(raw), len(gzip.compress(raw, 9))


SIZES = {os.path.relpath(f, DOCS): sizes(f) for f in sorted(glob.glob(f"{DOCS}/data/*.json"))}

EXPLORE_CSS = """
  [hidden] { display: none !important; }
  .ex-hero { padding: 28px 0 8px; }
  .ex-hero h1 { font-size: clamp(30px, 6vw, 44px); }
  .ex-controls { background: var(--bg); padding: 10px 0 8px; border-bottom: 1px solid var(--rule); }
  .ex-guides { display: flex; gap: 6px; overflow-x: auto; padding-bottom: 8px; scrollbar-width: none; }
  @media (min-width: 601px) { .ex-guides { flex-wrap: wrap; overflow: visible; } }
  @media (max-width: 600px) { .ex-guides { padding-right: 32px; -webkit-mask-image: linear-gradient(to right, #000 calc(100% - 32px), transparent); mask-image: linear-gradient(to right, #000 calc(100% - 32px), transparent); } }
  .ex-guides button, .ex-view button, .ex-small { flex: 0 0 auto; border: 1px solid var(--rule); background: var(--surface); color: var(--accent); border-radius: 999px; padding: 7px 12px; font: 600 14px/1.2 system-ui, sans-serif; font-family: inherit; cursor: pointer; }
  .ex-guides button[aria-pressed="true"], .ex-view button[aria-pressed="true"] { background: var(--accent); color: var(--on-accent); border-color: var(--accent); }
  .ex-row1 { display: flex; gap: 8px; align-items: center; }
  .ex-row1 input[type=search] { flex: 1; min-width: 0; font: 16px/1.3 system-ui, sans-serif; font-family: inherit; padding: 10px 12px; border: 2px solid var(--accent); border-radius: 12px; background: var(--surface); color: var(--ink); }
  .ex-row2 { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 8px; font-size: 14px; }
  .ex-row2 select { font: 14px system-ui, sans-serif; font-family: inherit; padding: 6px 8px; border: 1px solid var(--rule); border-radius: 8px; background: var(--surface); color: var(--ink); max-width: 46vw; }
  .ex-view { margin-left: auto; display: flex; gap: 4px; }
  #ex-count { margin: 8px 0 0; font-size: 14px; color: var(--muted); }
  #ex-sub { margin: 4px 0 0; font-size: 14px; color: var(--ink2); }
  #ex-locmsg { font-size: 13px; color: var(--muted); margin: 4px 0 0; }
  .ex-list { list-style: none; padding: 0; margin: 10px 0; }
  .ex-list li + li { border-top: 1px solid var(--rule); }
  .ex-row { width: 100%; display: flex; gap: 12px; align-items: center; text-align: left; background: none; border: 0; padding: 12px 4px; cursor: pointer; color: var(--ink); font: inherit; }
  .ex-row:hover { background: var(--surface2); }
  .ex-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; overflow-wrap: anywhere; }
  .ex-main b { font-weight: 650; }
  .ex-town { font-size: 14px; color: var(--muted); }
  .tag-dash { background: transparent; color: var(--muted); border: 1px dashed var(--rule); }
  .ex-metric { text-align: right; display: flex; flex-direction: column; align-items: flex-end; max-width: 46%; }
  .ex-metric b { font: 800 22px/1 var(--display); color: var(--accent); }
  .ex-metric small { font-size: 11px; color: var(--muted); }
  .ex-rank { flex: 0 0 34px; height: 34px; display: grid; place-items: center; font: 800 20px var(--display); color: var(--accent); border-radius: 8px; }
  .ex-rank.top { background: var(--orange); color: #0b3c49; }
  .ex-empty { padding: 24px 4px; color: var(--muted); }
  #ex-more { display: block; margin: 8px auto 24px; }
  #ex-mapwrap { position: relative; height: min(72vh, 720px); margin: 10px 0 20px; border: 1px solid var(--rule); border-radius: 16px; overflow: hidden; background: #cfe6e8; }
  #ex-map { width: 100%; height: 100%; display: block; touch-action: none; cursor: grab; }
  .ex-zoom { position: absolute; right: 10px; top: 10px; display: flex; flex-direction: column; gap: 6px; }
  .ex-zoom button { width: 44px; height: 44px; border-radius: 10px; border: 1px solid #e6dccb; background: #fff; color: #006d77; font: 700 22px/1 system-ui, sans-serif; cursor: pointer; }
  #ex-maphint { position: absolute; left: 10px; top: 10px; margin: 0; font-size: 13px; background: #fff; padding: 3px 8px; border-radius: 999px; color: #24505c; }
  #ex-mapattr { position: absolute; right: 0; bottom: 0; margin: 0; font-size: 11px; background: rgba(255,255,255,.85); padding: 2px 6px; border-radius: 6px 0 0 0; color: #24505c; }
  .ex-panel { position: fixed; z-index: 20; right: 0; top: 0; bottom: 0; width: min(440px, 100%); overflow-y: auto; background: var(--surface); border-left: 1px solid var(--rule); box-shadow: -8px 0 24px rgba(0,0,0,.12); padding: 18px 20px 40px; }
  @media (max-width: 600px) { .ex-panel { top: auto; height: 86vh; border-left: 0; border-top: 4px solid var(--orange); border-radius: 18px 18px 0 0; } }
  .ex-close { position: sticky; top: 0; float: right; width: 44px; height: 44px; border-radius: 50%; border: 1px solid var(--rule); background: var(--surface); font-size: 24px; line-height: 1; cursor: pointer; color: var(--ink); }
  .ex-kicker { margin: 0; font-size: 12px; font-weight: 700; letter-spacing: .1em; color: var(--accent2); }
  .ex-panel h2 { font-size: 34px; margin: 4px 0 6px; text-transform: uppercase; overflow-wrap: anywhere; }
  .ex-addr, .ex-dist { margin: 0 0 4px; color: var(--ink2); font-size: 15px; }
  .ex-actions { margin: 14px 0 8px; display: grid; gap: 8px; }
  .ex-apple { justify-content: center; }
  .ex-act-row { display: flex; gap: 8px; flex-wrap: wrap; }
  .ex-act-row a, .ex-act-row button { flex: 1; min-width: 88px; text-align: center; padding: 10px; border: 1px solid var(--rule); border-radius: 12px; text-decoration: none; color: var(--accent); font: 600 14px system-ui, sans-serif; font-family: inherit; background: var(--surface); cursor: pointer; }
  .ex-act-row button[aria-pressed="true"] { background: var(--soft); color: #0b3c49; }
  .ex-sec { margin-top: 18px; }
  .ex-sec h3 { font-size: 12px; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); border-bottom: 1px solid var(--rule); padding-bottom: 6px; margin-bottom: 8px; }
  .ex-sec p, .ex-sec li { font-size: 15px; color: var(--ink2); margin: 6px 0; }
  .ex-sec ul { padding-left: 18px; }
  .ex-kv { display: flex; justify-content: space-between; gap: 12px; font-size: 15px; padding: 3px 0; }
  .ex-kv span { color: var(--ink2); flex: 0 0 auto; max-width: 40%; }
  .ex-kv b { text-align: right; overflow-wrap: anywhere; }
  .ex-fine { font-size: 13px !important; color: var(--muted) !important; }
  .ex-result { display: flex; align-items: center; gap: 10px; font-weight: 600; flex-wrap: wrap; }
  .ex-app { margin-top: 22px; font-size: 14px; color: var(--muted); }
  body.ex-open { overflow: hidden; }
  @media (min-width: 601px) { body.ex-open { overflow: auto; } }
  .ex-res { display: inline-block; font: 800 12px/1.4 -apple-system, system-ui, sans-serif; letter-spacing: .04em; text-transform: uppercase; padding: 3px 8px; border-radius: 6px; text-align: center; }
  .ex-res-0 { background: #ddefe3; color: #0e5a2b; } .ex-res-1 { background: #ffe9c2; color: #6b3a00; } .ex-res-2 { background: #f9d5db; color: #7a0019; } .ex-res-x { background: var(--surface2); color: var(--ink2); }
"""
url = f"{DOMAIN}/explore/"
N_HC_GUIDES = len(HC_ANY)
title = fit(["Search Florida Restaurants: Cuban, Seafood & Inspections", "Florida Restaurant Search & Map | Florida Eats"], 50, 60, "explore title")
desc = fit([f"Search {N_REST:,} Florida restaurants by name, town, street or dish, map {N_HC_GUIDES} hand-checked places and see DBPR's inspection results. Free.",
            f"Search {N_REST:,} Florida restaurants by name, town, street or dish, map {N_HC_GUIDES} hand-checked places and see Florida DBPR's latest inspection results.",
            f"Search {N_REST:,} Florida restaurants by name, town, street or dish, browse {N_HC_GUIDES} hand-checked places on a map and read DBPR's inspection results."],
           140, 160, "explore description")
nav, bc = crumbs([("Home", "/"), ("Search", "/explore/")])
guide_buttons = "".join(f'<button type="button" data-g="{k}" aria-pressed="false">{e(t)}</button>' for k, t in
                        (("cuban", "Cuban & cafecito"), ("stonecrab", "Stone crabs"), ("grouper", "Grouper"), ("keys", "Keys classics"),
                         ("oyster", "Oyster bars"), ("fishcamp", "Fish camps"), ("latin", "Latin & Caribbean"),
                         ("honors", "MICHELIN & James Beard"), ("oldest", "Oldest"), ("inspections", "Inspections"),
                         ("all", "All restaurants"), ("saved", "Saved")))
explore_js = open(f"{ROOT}/scripts/explore.js").read()
assert "</script" not in explore_js.lower()
assert f'"{STORAGE_PREFIX}"' in explore_js, "explore.js must keep its localStorage keys under " + STORAGE_PREFIX
body = f"""{nav}
  <main id="main">
  <section class="ex-hero">
    <p class="kicker">{BRAND} · on the web</p>
    <h1>Search Florida restaurants</h1>
    <p class="sub">{N_REST:,} restaurants, cafés, bars and bakeries, with {N_HC_GUIDES} hand-checked places on the Cuban, stone crab, grouper, Keys, oyster bar, fish camp and Latin lists, {len(HON_L)} MICHELIN and James Beard honorees and Florida DBPR's own inspection results. The same data as the iPhone and iPad app, which is coming soon. Nothing about you is stored anywhere but this browser.</p>
  </section>
  <p id="ex-loading" hidden>Loading the restaurant list…</p>
  <noscript><p>The search needs JavaScript. The guides work without it: <a href="/{GUIDE_PATH['cuban']}">Cuban sandwiches</a>, <a href="/{GUIDE_PATH['stonecrab']}">stone crabs</a>, <a href="/{GUIDE_PATH['oyster']}">oyster bars</a>, <a href="/{INS_PATH}">inspections explained</a>.</p></noscript>
  <div id="ex-app" hidden>
    <div class="ex-controls">
      <div class="ex-guides" role="group" aria-label="Guides">{guide_buttons}</div>
      <div class="ex-row1">
        <label class="skip" for="ex-q">Search</label>
        <input id="ex-q" type="search" placeholder="Name, town, street, zip or dish" autocomplete="off" enterkeyhint="search">
        <button type="button" id="ex-locate" class="ex-small">Near me</button>
      </div>
      <div class="ex-row2">
        <label>Sort <select id="ex-sort" aria-label="Sort"></select></label>
        <select id="ex-town" aria-label="Town"></select>
        <select id="ex-cuisine" aria-label="Kind of place"></select>
        <label><input type="checkbox" id="ex-chains"> Hide chains</label>
        <button type="button" id="ex-clear" class="ex-small" hidden>Clear filters</button>
        <div class="ex-view" role="group" aria-label="View"><button type="button" data-v="list" aria-pressed="true">List</button><button type="button" data-v="map" aria-pressed="false">Map</button></div>
      </div>
      <p id="ex-sub"></p>
      <p id="ex-count" aria-live="polite"></p>
      <p id="ex-locmsg"></p>
    </div>
    <div id="ex-listwrap"><ol id="ex-list" class="ex-list"></ol><button type="button" id="ex-more" class="ex-small" hidden></button></div>
    <div id="ex-mapwrap" hidden>
      <canvas id="ex-map" aria-label="Map of Florida with a dot for each place in the list. The list view has the same places."></canvas>
      <div class="ex-zoom"><button type="button" id="ex-zin" aria-label="Zoom in">+</button><button type="button" id="ex-zout" aria-label="Zoom out">−</button></div>
      <p id="ex-maphint"></p>
      <p id="ex-mapattr">Outlines © OpenStreetMap contributors, Overture Maps Foundation</p>
    </div>
  </div>
  <aside id="ex-panel" class="ex-panel" hidden aria-labelledby="ex-pname"></aside>
  </main>
<script>
{explore_js}
</script>"""
webapp_ld = {"@context": "https://schema.org", "@type": "WebApplication", "name": f"{BRAND} web app", "url": url,
             "applicationCategory": "TravelApplication", "operatingSystem": "Any", "browserRequirements": "Requires JavaScript",
             "description": desc, "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
             "publisher": {"@type": "Organization", "@id": f"{DOMAIN}/#org", "name": BRAND, "url": f"{DOMAIN}/"}}
page("explore/index.html", title, desc, body, [webapp_ld, bc], extra_css=EXPLORE_CSS, og_type="website")

# ---------------------------------------------------------------- landing page
shots = [("home", "Florida Eats home screen with guide cards for Cuban sandwiches and cafecito, stone crabs, grouper and seafood shacks, Keys classics, oyster bars, fish camps, Latin and Caribbean food, MICHELIN and James Beard, the oldest places and inspections.", "A guide for each Florida craving."),
         ("cuban", "The hand-checked Cuban sandwich and cafecito list in Florida Eats, nearest first.", "Cuban sandwiches and coffee windows nearest you."),
         ("detail", "A place in Florida Eats: address, a button for Apple Maps' ratings, hours and photos, what's on the menu and Florida DBPR's latest inspection result.", "Each place, with DBPR's own inspection results."),
         ("map", "The Florida Eats map of Florida with pins for hand-checked places.", "The map, by guide."),
         ("honors", "The MICHELIN and James Beard list in Florida Eats.", "MICHELIN Guide and James Beard honorees.")]
shot_html = []
for i, (name, alt, cap) in enumerate(shots):
    png = f"{DOCS}/img/screen-{name}.png"
    if not os.path.exists(png):
        continue
    w, h = png_size(png)
    lazy = ' loading="lazy"' if i > 1 else ""
    webp = os.path.exists(f"{DOCS}/img/screen-{name}.webp")
    src = (f'<source srcset="/img/screen-{name}.webp" type="image/webp">' if webp else "")
    shot_html.append(f'<li><picture>{src}<img src="/img/screen-{name}.png" alt="{e(alt)}" width="{w}" height="{h}"{lazy} decoding="async"></picture><p>{e(cap)}</p></li>')

g_ins = GROUP_N
faq = [
    ("Is Florida Eats free?", "Yes. The app is free, with no ads, no in-app purchases and no account. It's coming soon to the App Store; the web search works today."),
    ("Where do the lists come from?", f"We checked the themed lists by hand in {CHECKED}: each place on the Cuban, stone crab, grouper, Keys, oyster bar, fish camp, Latin and oldest-places lists has a 2025 or 2026 source, such as its own website or menu, a dated local news story or an official tourism listing. The rest of the {N_REST:,} restaurants come from the Florida Department of Business and Professional Regulation's list of current food service licenses ({N_LICENSED:,} places) and Overture Maps' open place data, placed on the map with Overture's address points and the U.S. Census Bureau Geocoder."),
    ("Does the app show ratings and reviews?", "Not its own. Tap a place and Apple Maps' own place card opens inside the app with Apple's current ratings, hours, photos and directions. Our lists are never ordered by ratings."),
    ("What are the inspection results?", f"Florida's DBPR inspects licensed restaurants and publishes each visit's result. Florida doesn't grade restaurants (in DBPR's words, “{NO_GRADE}”), and neither do we: the app shows DBPR's own result group for the latest visit (Met Inspection Standards, Follow-Up Inspection Required or Facility Temporarily Closed), DBPR's disposition and the date, with DBPR's violation counts. Records through {hdate(INS_THROUGH)}."),
    ("When is stone crab season?", "October 15 to May 1, set by the Florida Fish and Wildlife Conservation Commission. Out of season, the places on our stone crab list are open; the claws just aren't on the menu."),
    ("Does it need my location?", "Only if you want lists sorted by distance. Your location stays on your iPhone or iPad and is never sent to us. Everything else works without it. On the website, Near me uses your location only inside your browser."),
    ("A place closed or is missing. How do I tell you?", f"Email {EMAIL} with the name and town. Corrections go into the next update."),
    ("Is there an Android version?", f"Not yet. Florida Eats is for iPhone and iPad. If enough people ask at {EMAIL}, it moves up the list."),
]
faq_html = "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in faq)
faq_ld = {"@context": "https://schema.org", "@type": "FAQPage", "@id": f"{DOMAIN}/#faq",
          "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
app_ld = {"@context": "https://schema.org", "@graph": [
    # No "offers" until the app is on the App Store (put it back with the listing URL: price 0, USD).
    {"@type": "MobileApplication", "@id": f"{DOMAIN}/#app", "name": APP_NAME,
     "alternateName": ["Florida Eats", "FL Eats", "Florida Eats: Cuban, Seafood & More"],
     "description": f"A free guide to {N_REST:,} Florida restaurants, with hand-checked lists of Cuban sandwiches and cafecito, stone crabs, grouper and seafood shacks, Keys classics, oyster bars, fish camps, Latin and Caribbean food and the state's oldest places, {len(HON_L)} MICHELIN and James Beard honorees, and Florida DBPR's own inspection results. Sort by distance, open Apple Maps' live place card for hours and photos, and save places for your next trip.",
     "url": f"{DOMAIN}/", "image": f"{DOMAIN}/og.png", "operatingSystem": "iOS, iPadOS", "applicationCategory": "TravelApplication",
     "applicationSubCategory": "Food & Drink", "inLanguage": "en", "publisher": {"@id": f"{DOMAIN}/#org"}},
    {"@type": "Organization", "@id": f"{DOMAIN}/#org", "name": BRAND, "url": f"{DOMAIN}/",
     "logo": {"@type": "ImageObject", "url": f"{DOMAIN}/icon-512.png", "width": 512, "height": 512}, "email": EMAIL,
     "contactPoint": {"@type": "ContactPoint", "contactType": "customer support", "email": EMAIL, "availableLanguage": "en"}},
    {"@type": "WebSite", "@id": f"{DOMAIN}/#website", "name": BRAND, "alternateName": ["FL Eats", "Florida Eats app"], "url": f"{DOMAIN}/",
     "inLanguage": "en", "publisher": {"@id": f"{DOMAIN}/#org"}}]}
if shot_html:
    app_ld["@graph"][0]["screenshot"] = f"{DOMAIN}/img/screen-{next(n for n, *_ in shots if os.path.exists(f'{DOCS}/img/screen-{n}.png'))}.png"
title = fit(["Florida Eats: Cuban, Seafood & Restaurant Guide App", "Florida Eats: Cuban Food, Seafood & Restaurant App"], 50, 60, "landing title")
desc = fit([f"Free iPhone and iPad guide to {N_REST:,} Florida restaurants, with hand-checked Cuban sandwiches, stone crabs, oyster bars and DBPR inspection results.",
            f"A free iPhone and iPad guide to {N_REST:,} Florida restaurants, with hand-checked Cuban sandwiches, stone crabs and oyster bars, plus DBPR inspections."],
           140, 160, "landing description")
city_cards = "".join(f'<li><a href="{city_url(c)}">{e(c)}</a></li>' for c in CITY_PAGES)
screens = f"""
  <section id="screens">
    <h2>What it looks like</h2>
    <ul class="shots" tabindex="0" aria-label="Florida Eats app screenshots">
      {"".join(shot_html)}
    </ul>
  </section>""" if shot_html else ""
guide_cards = "".join(f'<a class="card" href="/{GUIDE_PATH[k]}"><h3>{e(GUIDE_NAME[k])}</h3><p>{plural(len(L[k]), "hand-checked place")}{line}.</p></a>'
                      for k, line in (("cuban", ", from Calle Ocho to Ybor City"), ("stonecrab", ", in season Oct 15 – May 1"),
                                      ("grouper", " on the docks and beaches"), ("keys", " for key lime pie and conch"),
                                      ("oyster", ", raw, steamed and baked"), ("fishcamp", " on rivers, lakes and the coast"),
                                      ("latin", ": Haitian, Venezuelan, Colombian and more")))
body = f"""  <main id="main">
  <section class="hero">
    <p class="kicker">{BRAND}: {TAGLINE} for iPhone and iPad</p>
    <h1>Florida's restaurants, from cafecito to stone crab</h1>
    <p class="lede">{BRAND} is a free Florida restaurant guide. Find a coffee window pouring cafecito near you, stone crab claws in season, a grouper sandwich on the dock and an oyster bar on the Panhandle, from hand-checked lists, the MICHELIN Guide and James Beard honorees and the state's own inspection records, plus {N_REST:,} restaurants, cafés, bars and bakeries in {N_TOWNS:,} towns.</p>
    <div class="cta-row">{store_button()}<a class="btn btn-ghost" href="/explore/">Search on the web</a><span class="pill store-note">Free. No ads, no account. Coming soon to the App Store.</span></div>
    <ul class="stats" aria-label="What's in the app">
      <li><b>{N_HC_GUIDES}</b><span>hand-checked places</span></li>
      <li><b>{len(HON_L)}</b><span>MICHELIN &amp; James Beard</span></li>
      <li><b>{len(INS_L):,}</b><span>with DBPR inspection results</span></li>
      <li><b>{N_REST:,}</b><span>restaurants</span></li>
    </ul>
  </section>

  <section id="what">
    <h2>A Florida guide that knows what's in season</h2>
    <p class="sub">General restaurant apps rank by star ratings and can't tell you which window pours the colada. {BRAND} starts from what people here look for: a Cuban sandwich and a cafecito, stone crab claws from October to May, a grouper sandwich, key lime pie, an oyster bar, an Old Florida fish camp and the Latin and Caribbean kitchens beyond Cuban. The hand-checked lists were checked in {CHECKED} against 2025–26 sources. Licensed places show Florida DBPR's own latest inspection result, never a grade of ours. For ratings, hours and photos, each place opens Apple Maps' own live card.</p>
  </section>

  <section id="how">
    <h2>How it works</h2>
    <ol class="steps">
      <li class="step"><div class="n" aria-hidden="true">1</div><div><h3>Pick a guide.</h3><p>Cuban &amp; Cafecito, Stone Crabs, Grouper &amp; Seafood Shacks, Keys Classics, Oyster Bars, Fish Camps, Latin &amp; Caribbean, MICHELIN &amp; James Beard, Oldest Places, Inspections, or search {N_REST:,} restaurants by name, town, street or dish.</p></div></li>
      <li class="step"><div class="n" aria-hidden="true">2</div><div><h3>See what's near you.</h3><p>Sort by distance, filter by town or cuisine, or browse the map.</p></div></li>
      <li class="step"><div class="n" aria-hidden="true">3</div><div><h3>Go.</h3><p>Open Apple Maps' place card for live hours and photos, call, get directions, or save it for your next trip.</p></div></li>
    </ol>
  </section>
{screens}
  <section id="guides">
    <h2>Florida food guides</h2>
    <p class="sub">The app's lists, readable on the web.</p>
    <div class="grid2">
      {guide_cards}
      <a class="card" href="/{OLD_PATH}"><h3>Florida's oldest restaurants</h3><p>{plural(len(OLD_L), "place")} open at the same address since 1960 or earlier.</p></a>
      <a class="card" href="/{HON_PATH}"><h3>MICHELIN &amp; James Beard</h3><p>{plural(len(HON_L), "honored Florida restaurant")}.</p></a>
      <a class="card" href="/{INS_PATH}"><h3>Restaurant inspections, explained</h3><p>DBPR's three result groups and the latest results for {plural(len(INS_L), "place")}, records through {e(hdate(INS_THROUGH))}.</p></a>
    </div>
  </section>

  <section id="cities">
    <h2>Cuban food, seafood and more by city</h2>
    <p class="sub">The guides for Florida's biggest cities and most-visited towns. <a href="/cities/">See what each city page has</a>.</p>
    <ul class="cities">{city_cards}</ul>
  </section>

  <section id="pricing">
    <h2>Free, and staying that way</h2>
    <p class="sub">No ads, no subscription, no in-app purchases, no account. The whole guide is built into the app, so lists open instantly and work with a weak signal on the water.</p>
  </section>

  <section id="privacy">
    <h2>Your plans are your business</h2>
    <p class="sub">{BRAND} collects nothing. If you allow location, it only sorts lists by distance on your device. Saved places stay on your device. This website sets no cookies and runs no trackers. <a href="/privacy.html">Read the privacy policy</a>.</p>
  </section>

  <section id="faq">
    <h2>Questions</h2>
    {faq_html}
  </section>

  <section id="download" class="final">
    <h2>Find your next cafecito</h2>
    <p class="sub">{BRAND} is coming soon to the App Store for iPhone and iPad. Free.</p>
    <div class="cta-row">{store_button()}</div>
  </section>
  </main>"""
page("index.html", title, desc, body, [app_ld, faq_ld], og_type="website")

# ---------------------------------------------------------------- privacy and terms
nav, bc = crumbs([("Home", "/"), ("Privacy policy", "/privacy.html")])
body = f"""{nav}
  <main id="main" class="legal">
  <section class="hero">
    <h1>Privacy policy</h1>
    <p class="lede">Short version: the {BRAND} app collects nothing about you, and this website doesn't track you. Last updated {POLICY_UPDATED}.</p>
  </section>
  <section>
    <h2>The app</h2>
    <ul>
      <li><b>No account, no analytics, no ads.</b> The app has no sign-in, no advertising and no analytics or crash-reporting code. We receive no data from it.</li>
      <li><b>Location.</b> If you allow it, your location is used on your device to sort places by distance and show where you are on the map. It is never sent to us. You can turn it off in Settings at any time.</li>
      <li><b>Saved places and filters</b> are stored only on your device and are deleted when you delete the app.</li>
      <li><b>Apple Maps.</b> When you open a place's ratings, hours and photos, or ask for directions, the app asks Apple Maps for that place. Apple handles that request under <a href="https://www.apple.com/legal/privacy/" rel="noopener">Apple's privacy policy</a>, as it does for any app that shows a map.</li>
      <li><b>Spotlight.</b> The app adds its hand-checked and honored places to your device's search index so you can find them from Spotlight. That index stays on your device.</li>
      <li><b>Calls, websites and email</b> you start from a place open in the Phone app, your browser or Mail, and are handled by them.</li>
    </ul>
    <p>When the app is on the App Store, its privacy label will be "Data Not Collected".</p>
    <h2>This website</h2>
    <p>The site is static pages hosted on GitHub Pages. It sets no cookies and loads no analytics, fonts or scripts from anyone else.</p>
    <ul>
      <li><b>Saved places and your last guide.</b> The search page (<a href="/explore/">/explore/</a>) keeps the places you save and the last guide you opened in your browser's local storage, on this device only. Nothing is sent to us. Clearing this site's data in your browser removes them.</li>
      <li><b>Location.</b> If you tap Near me or choose the Nearest sort, your browser asks whether to share your location. If you allow it, the location is used only inside your browser to sort places by distance and is never sent to us or anyone else.</li>
    </ul>
    <p>GitHub may keep standard server logs, such as IP addresses, for security; see <a href="https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement" rel="noopener">GitHub's privacy statement</a>.</p>
    <h2>Email</h2>
    <p>If you email us, we use your message and address only to reply and to fix the listing you told us about. We don't add you to a mailing list or share your address.</p>
    <h2>Children</h2>
    <p>The app collects no personal information from anyone, including children.</p>
    <h2>Changes and contact</h2>
    <p>If this policy changes, the new version will be posted here with a new date. Questions: <a href="mailto:{EMAIL}">{EMAIL}</a>.</p>
  </section>
  </main>"""
page("privacy.html", "Privacy Policy: Florida Eats, a Free Florida Restaurant App",
     fit(["The Florida Eats privacy policy: the app collects no data, keeps your location and saved places on your device, and this website sets no cookies at all."], 140, 160),
     body, [bc])

nav, bc = crumbs([("Home", "/"), ("Terms of use", "/terms.html")])
body = f"""{nav}
  <main id="main" class="legal">
  <section class="hero">
    <h1>Terms of use</h1>
    <p class="lede">The plain-language terms for the {BRAND} app and this website. Last updated {POLICY_UPDATED}.</p>
  </section>
  <section>
    <h2>What the app is</h2>
    <p>{BRAND} is a free guide to restaurants in Florida. It is provided as is, for personal use, without charge and without warranties of any kind.</p>
    <h2>Check before you go</h2>
    <p>Restaurants open, close, change their hours and change their menus; stone crab claws are only served in season (October 15 to May 1), and some places close for part of the year. Dishes, seasons and founding years are what each place or a named source said when we checked in {CHECKED}. We work to keep the lists right, but we can't promise that any listing is current or complete. Call the restaurant before you make the trip.</p>
    <h2>Inspection results</h2>
    <p>The app and this site show the Florida Department of Business and Professional Regulation's own inspection records: each visit's disposition as DBPR wrote it, DBPR's own result group for it (Met Inspection Standards, Follow-Up Inspection Required or Facility Temporarily Closed), DBPR's violation counts and its emergency closure reports. Florida doesn't grade restaurants (“{NO_GRADE}”), and we compute no grade of our own. An inspection is a snapshot of one day, and the published records lag by about a week. For DBPR's own records, use its <a href="{e(DBPR_SEARCH)}" rel="noopener">license and inspection search</a>.</p>
    <h2>Other people's content</h2>
    <p>Ratings, reviews, hours and photos in each place card come from Apple Maps and are Apple's and its providers', under Apple's terms. Restaurant names and trademarks belong to their owners. MICHELIN and the MICHELIN Guide are trademarks of Michelin; James Beard Foundation and James Beard Award are trademarks of the James Beard Foundation. {BRAND} is not affiliated with any restaurant, chain, award body, theme park or government agency.</p>
    <h2>Data sources and licenses</h2>
    <ul>
      <li>Florida Department of Business and Professional Regulation, Division of Hotels and Restaurants: food service licenses, inspections, emergency closure reports and disciplinary reports, from its public records downloads (Chapter 119, Florida Statutes), modified for use here.</li>
      <li>Overture Maps Foundation places data, under the Community Data License Agreement, Permissive 2.0, including data from Meta, Microsoft, DAC, BrightQuery, AllThePlaces (CC0 1.0) and Foursquare (Apache 2.0).</li>
      <li>Overture Maps Foundation divisions, used for the state and county outlines on the map, under the Open Database License: © OpenStreetMap contributors, Overture Maps Foundation.</li>
      <li>Overture Maps Foundation addresses data, compiled from open address sources under permissive licenses (see docs.overturemaps.org/attribution), used to place license records on the map.</li>
      <li>U.S. Census Bureau Geocoder (public domain), used for addresses Overture's address points don't cover.</li>
      <li>The MICHELIN Guide Florida 2026 selection and the James Beard Foundation's awards, finalists, semifinalists and America's Classics: honors reported as facts.</li>
      <li>Cuban sandwiches and cafecito, stone crabs, grouper and seafood shacks, Keys classics, oyster bars, fish camps, Latin and Caribbean food and founding years: our own research, with a source recorded for every place.</li>
    </ul>
    <h2>Corrections</h2>
    <p>If a listing is wrong, or you own a restaurant and want something fixed, email <a href="mailto:{EMAIL}">{EMAIL}</a>. We fix mistakes in the next update.</p>
    <h2>Liability</h2>
    <p>To the extent the law allows, we are not liable for any loss arising from use of the app or site, including a wasted drive to a closed restaurant.</p>
    <h2>Changes</h2>
    <p>We may update these terms; the current version and its date are always on this page. See also the <a href="/privacy.html">privacy policy</a>.</p>
  </section>
  </main>"""
page("terms.html", "Terms of Use: Florida Eats, a Free Florida Restaurant App",
     fit(["The Florida Eats terms of use: a free Florida restaurant guide, provided as is. Check before you go, and see where each listing and result comes from."], 140, 160),
     body, [bc])

body = f"""  <main id="main">
  <section class="hero">
    <h1>Page not found</h1>
    <p class="lede">That page isn't here. Try the <a href="/">{BRAND} home page</a>, the <a href="/{GUIDE_PATH['cuban']}">Cuban sandwich guide</a> or the <a href="/explore/">restaurant search</a>.</p>
  </section>
  </main>"""
page("404.html", f"Page not found | {BRAND}", "This page doesn't exist.", body, robots="noindex,follow")
noindexed.remove("404.html")


# ---------------------------------------------------------------- plumbing
for f in os.listdir(f"{DOCS}/cities"):   # a city the data lost: drop its old page instead of leaving it live and stale
    if f.endswith(".html") and f"cities/{f}" not in written + noindexed:
        os.remove(f"{DOCS}/cities/{f}")
        print("removed stale", f"cities/{f}")
urls = ["" if w == "index.html" else w.replace("index.html", "") for w in written]
urls.sort(key=lambda u: (u != "", u.startswith("cities/"), u))
open(f"{DOCS}/sitemap.xml", "w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                       + "".join(f"  <url><loc>{DOMAIN}/{u}</loc><lastmod>{TODAY}</lastmod></url>\n" for u in urls) + "</urlset>\n")
open(f"{DOCS}/robots.txt", "w").write(f"User-agent: *\nAllow: /\n\nSitemap: {DOMAIN}/sitemap.xml\n")
json.dump({"name": BRAND, "short_name": "FL Eats", "description": f"{TAGLINE[0].upper() + TAGLINE[1:]}: a guide to {N_REST:,} Florida restaurants.",
           "start_url": f"{BASE}/", "display": "browser", "background_color": "#fbf5ea", "theme_color": "#006d77",
           "icons": [{"src": f"{BASE}/icon-192.png", "sizes": "192x192", "type": "image/png"}, {"src": f"{BASE}/icon-512.png", "sizes": "512x512", "type": "image/png"}]},
          open(f"{DOCS}/site.webmanifest", "w"), indent=2)
if CUSTOM_DOMAIN:
    open(f"{DOCS}/CNAME", "w").write(CUSTOM_DOMAIN + "\n")
elif os.path.exists(f"{DOCS}/CNAME"):
    os.remove(f"{DOCS}/CNAME")   # no custom domain yet: GitHub serves the project address
open(f"{DOCS}/.nojekyll", "w").write("")
os.makedirs(f"{ROOT}/playbook", exist_ok=True)
json.dump({"generated": TODAY, "domain": DOMAIN, "restaurants": N_REST, "places_incl_hidden": len(PLACES), "towns": N_TOWNS, "counties": N_COUNTIES,
           "dbpr_licensed": N_LICENSED, "hand_checked_on_a_guide": N_HC, **{"guide_" + k: len(v) for k, v in L.items()},
           "oldest": len(OLD_L), "honors": len(HON_L), "michelin": MI_COUNT, "michelin_green_star": N_GREEN, "james_beard": N_JBF,
           "americas_classics": N_CLASSICS, "dbpr_results": len(INS_L),
           "dbpr_latest_group": {GROUPS[g] if g is not None else "not grouped by DBPR": n for g, n in sorted(GROUP_N.items(), key=lambda x: (x[0] is None, x[0] or 0))},
           "dbpr_latest_disposition": dict(DISP_N.most_common()), "inspections_through": INS_THROUGH, "dbpr_fetched": DBPR_FETCHED,
           "inspections_since": INS_SINCE, "emergency_closure_places": len(CL_PLACES), "closure_reports": [CL_DATES[0], CL_DATES[-1]] if CL_DATES else None,
           "city_pages": city_stats, "cities_without_a_page": CITY_SKIPPED, "noindex_pages": noindexed,
           "web_app_data_bytes": {k: {"raw": r, "gzip": g} for k, (r, g) in SIZES.items()}},
          open(f"{ROOT}/playbook/site-numbers.json", "w"), indent=1, ensure_ascii=False)
print("wrote", len(written) + len(noindexed) + 1, "pages:", ", ".join(written))
if noindexed:
    print("noindex:", ", ".join(noindexed))
print(f"restaurants {N_REST:,} in {N_TOWNS} towns | licensed {N_LICENSED:,} | hand-checked on a guide {N_HC} | "
      + " | ".join(f"{k} {len(v)}" for k, v in L.items()) + f" | oldest {len(OLD_L)} | honors {len(HON_L)} | DBPR results {len(INS_L):,} {dict(GROUP_N)}")
print("city pages:", ", ".join(CITY_PAGES), "| no page (listed places):", CITY_SKIPPED)
for k, (r, g) in SIZES.items():
    print(f"  {k}: {r / 1024:,.0f} KB raw, {g / 1024:,.0f} KB gzip")
