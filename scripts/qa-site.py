"""QA for the website in docs/: static checks on every generated page, then every page in headless Chrome at phone and desktop widths.

Static (no browser):
- no "every restaurant" / "all N restaurants"-style overclaims, "worst"/"dirtiest" lists or grades anywhere (text, meta, alt text,
  JSON-LD, the web app's strings)
- a Content-Security-Policy meta on every page whose hashes match each inline <script>/<style>; no inline style or on* attributes
- titles 50-60 and descriptions 140-160 characters, unique across indexable pages; one <h1>; sitemap = the indexable pages
- city pages: the title, h1 and description name only sections the page has
- JSON-LD parses; ItemList items point to an anchor on the same page; no aggregateRating/review; no empty streetAddress
- promotional spots (title, description, og/twitter, h1, kicker, lede, Article headline) never name a place whose latest DBPR result
  is Follow-Up Inspection Required or Facility Temporarily Closed; the inspections page names no place at all and lists none
- the hand-checked guide pages list only hand-checked places with that guide's tag (matched to core.json by name and address)
- the honors page never calls a finalist or semifinalist a winner; MICHELIN and James Beard trademark lines on every page
- no "Apalachicola oysters" claim outside a place's own researched text; the stone crab season (Oct 15 - May 1) is stated
- the inspections page quotes DBPR's "not graded or rated", names its three result groups and links DBPR's search
- the web app keeps its localStorage under "fleats-"; its map credits OpenStreetMap and Overture; its Inspections guide has no
  "most violations" order (no worst list)
- data: ids unique and as many as places; detail files keyed inside core and in the right county; websites are http(s); no
  Google-derived field (rating, reviews, price) anywhere in the published data
Browser (Playwright, channel="chrome"): no horizontal scroll, no console errors, no CSP violations, no broken internal links or
images; the web app loads, searches (dishes, Miami's "southwest 8th street" quadrant words), opens a place with DBPR's results and
license search, Back closes it, the phone panel is a modal dialog, a #p= link opens that place, the map draws, a hostile #g= doesn't
break it, and saved places use the fleats- prefix.

Usage: .venv/bin/python scripts/qa-site.py            (serves docs/ itself on a free localhost port; exits 1 on any problem)
       .venv/bin/python scripts/qa-site.py --static   (static checks only, a few seconds)
Adapted from co-eats/scripts/qa-site.py. Until the custom domain is live the site sits under /florida-eats/ on github.io, so the pages
are served under that same path here (a temporary folder with docs/ linked in as florida-eats/).
"""
import base64
import functools
import glob
import hashlib
import html
import html.parser
import http.server
import json
import os
import re
import sys
import tempfile
import threading
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET

ROOT = os.path.join(os.path.dirname(__file__), "..")
DOCS = os.environ.get("QA_DOCS") or os.path.join(ROOT, "docs")   # QA_DOCS: check a copy (used to mutation-test these checks)
DOMAIN = open(os.path.join(DOCS, "CNAME")).read().strip() if os.path.exists(os.path.join(DOCS, "CNAME")) else "nickstrom5.github.io"
BASE = re.search(r'data-base="([^"]*)"', open(os.path.join(DOCS, "index.html")).read()).group(1)
STORAGE_PREFIX = "fleats-"
OTHER_PREFIXES = ("coeats-", "ce-", "wieats-")
INS_PAGE = "florida-restaurant-inspections.html"
HON_PAGE = "florida-michelin-james-beard.html"
GUIDE_PAGES = {"florida-cuban-sandwiches-cafecito.html": 1, "florida-stone-crab.html": 2, "florida-grouper-sandwiches-seafood-shacks.html": 4,
               "florida-keys-key-lime-pie-conch.html": 8, "florida-oyster-bars.html": 16, "florida-fish-camps-smoked-fish.html": 32,
               "florida-latin-caribbean-restaurants.html": 64, "florida-oldest-restaurants.html": 128}
TM_MICHELIN = "MICHELIN and the MICHELIN Guide are trademarks of Michelin"
TM_JBF = "James Beard Foundation and James Beard Award are trademarks of the James Beard Foundation"

# claims the lists can't back up: the app lists what was checked or matched, never "every"/"all N" restaurants
OVERCLAIMS = [
    r"\bevery\s+(?:single\s+)?(?:florida\s+|local\s+|licensed\s+)?(?:restaurant|bar|caf[eé]|place to eat|eatery|oyster bar|fish camp)",
    r"\bevery\s+place\s+in\s+(?:florida|the\s+state)",
    r"\ball\s+(?:of\s+the\s+)?\d[\d,]*\s+(?:\w+\s+){0,2}(?:restaurants|places|spots|caf[eé]s|bars)\b",
    r"\b(?:all|every)\s+(?:the\s+)?(?:restaurants|places)\s+in\s+(?:the\s+state|florida|town)\b",
    r"\b(?:all|every)\s+(?:of\s+)?florida'?s\s+(?:restaurants|bars)\b",
    r"\b(?:confirmed|checked|verified)\s+open\b",            # the research dates show when we checked a source, not that it's open now
    r"\b(?:worst|dirtiest|grossest|filthiest)\b",            # no worst lists, anywhere
    r"(?-i:\b[Gg]rade\s+[A-F]\b|\b[A-F][+-]?\s+grade\b)|\b(?:health|safety|inspection)\s+score\b|\bletter\s+grade\b",
]
# city-page words -> the section that backs them
GENERIC = set("""the and of a an at on in by to la el le los las de del da di du restaurant restaurants cafe café cafes grill grille bar bars pub
kitchen local cuban latin food foods deli bakery market house fish seafood oyster oysters raw tavern diner pizza pizzeria taqueria tacos
burger burgers bbq sushi wings coffee tea juice bistro cantina eatery shack hut express company co inn lounge club station dock docks
grill bay beach island key keys florida miami tampa orlando main street corner new old original famous best little big great first
american italian mexican chinese thai japanese indian greek french spanish caribbean haitian sandwich sandwiches subs chicken steak
steakhouse crab crabs camp mama papa joe joes""".split())
CITY_KEYWORDS = [(r"cuban|cafecito", "cuban"), (r"stone crab", "stonecrab"), (r"grouper|seafood shack", "grouper"),
                 (r"key lime|conch|keys classic", "keys"), (r"oyster", "oyster"), (r"fish camp|smoked fish", "fishcamp"),
                 (r"latin|caribbean", "latin"), (r"michelin|james beard|honoree", "honors"), (r"\boldest\b", "oldest"),
                 (r"inspection", "inspections")]


class Page(html.parser.HTMLParser):
    """The facts the static checks need from one HTML file."""

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.title, self.desc, self.robots, self.canonical, self.csp = "", None, "", None, None
        self.h1s, self.ids, self.section_ids, self.alts, self.metas = [], [], set(), [], []
        self.scripts, self.styles, self.ldjson, self.bad_attrs = [], [], [], []
        self.promo = []        # text of the kicker and lede paragraphs
        self._in, self._buf, self._h1, self._promo = None, [], None, None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for k, v in attrs:
            if k == "style" or k.startswith("on"):
                self.bad_attrs.append(f"<{tag} {k}=…>")
        if "id" in a:
            self.ids.append(a["id"])
            if tag == "section":
                self.section_ids.add(a["id"])
        if tag == "img":
            self.alts.append(a.get("alt"))
        if tag == "meta":
            if a.get("name") == "description":
                self.desc = a.get("content", "")
            elif a.get("name") == "robots":
                self.robots = a.get("content", "")
            elif (a.get("http-equiv") or "").lower() == "content-security-policy":
                self.csp = a.get("content", "")
            if (a.get("property") or a.get("name") or "").startswith(("og:", "twitter:")):
                self.metas.append(a.get("content", ""))
        if tag == "link" and a.get("rel") == "canonical":
            self.canonical = a.get("href")
        if tag in ("script", "style", "title"):
            self._in, self._buf = (tag, a.get("type")), []
        if tag == "h1":
            self._h1 = []
        if tag == "p" and set((a.get("class") or "").split()) & {"lede", "kicker"}:
            self._promo = []

    def handle_endtag(self, tag):
        if self._in and tag == self._in[0]:
            text = "".join(self._buf)
            kind, typ = self._in
            if kind == "title":
                self.title = text
            elif kind == "style":
                self.styles.append(text)
            elif typ == "application/ld+json":
                self.ldjson.append(text)
            elif typ in (None, "", "text/javascript", "module"):
                self.scripts.append(text)
            self._in = None
        if tag == "h1" and self._h1 is not None:
            self.h1s.append("".join(self._h1).strip())
            self._h1 = None
        if tag == "p" and self._promo is not None:
            self.promo.append("".join(self._promo))
            self._promo = None

    def handle_data(self, data):
        if self._in:
            self._buf.append(data)
        if self._h1 is not None:
            self._h1.append(data)
        if self._promo is not None:
            self._promo.append(data)


def sha(s):
    return "'sha256-" + base64.b64encode(hashlib.sha256(s.encode("utf-8")).digest()).decode() + "'"


def walk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield path + "." + k, k, v
            yield from walk(v, path + "." + k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, f"{path}[{i}]")


def doc_files():
    return sorted(f for f in glob.glob(os.path.join(DOCS, "**", "*.html"), recursive=True) if "/screenshots/" not in f)


def rel(f):
    return os.path.relpath(f, DOCS)


def page_url(path):
    full = f"https://{DOMAIN}{BASE}" if DOMAIN.endswith("github.io") else f"https://{DOMAIN}"
    return full + "/" + ("" if path == "index.html" else path.removesuffix("index.html"))


def sitemap_paths():
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [e.text for e in ET.parse(os.path.join(DOCS, "sitemap.xml")).getroot().findall("s:url/s:loc", ns)]
    out = []
    for u in locs:
        p = urllib.parse.urlparse(u).path
        if BASE and p.startswith(BASE):
            p = p[len(BASE):]
        p = p.lstrip("/")
        out.append(p + "index.html" if p == "" or p.endswith("/") else p)
    return out


def norm(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return " " + re.sub(r"[^a-z0-9]+", " ", s.replace("'", "").replace("’", "")).strip() + " "


def load_core():
    """core.json with its sparse columns expanded and its coordinates and dates decoded: a list of dicts, in core order."""
    core = json.load(open(os.path.join(DOCS, "data", "core.json")))
    n, C = core["n"], dict(core["cols"])
    for k, pairs in (core.get("sparse") or {}).items():
        col = [None] * n
        for i, v in pairs:
            col[i] = v
        C[k] = col
    rows, la, lo = [], 0, 0
    for i in range(n):
        r = {k: C[k][i] for k in C}
        if r.get("dla") is not None:
            la += r["dla"]; lo += r["dlo"]
            r["la"], r["lo"] = la / 10000, lo / 10000
        r["city"] = core["cities"][r["c"]] if r.get("c") is not None else ""
        rows.append(r)
    return core, rows


def static_checks():
    problems = []
    pages = {rel(f): open(f, encoding="utf-8").read() for f in doc_files()}
    parsed = {p: Page(t) for p, t in pages.items()}
    in_sitemap = set(sitemap_paths())
    titles, descs = {}, {}
    try:
        core, rows = load_core()
    except (OSError, ValueError, KeyError) as ex:
        return [f"data: couldn't read core.json ({ex})"], len(pages)
    # names a promotional spot must never carry: places whose latest DBPR group is 1 or 2, when no place of the same name is fine
    bad, fine = set(), set()
    for r in rows:
        (bad if r.get("ig") in (1, 2) else fine).add(norm(r["n"]))
    # a name made only of everyday words ("Local", "Cuban Cafe") can't be told from the copy around it, so only distinctive names count
    distinctive = lambda k: len(k.strip()) >= 6 and any(w not in GENERIC for w in k.split())
    promo_bad = sorted(k for k in bad - fine if distinctive(k))
    any_bad = sorted(k for k in bad if distinctive(k))
    by_key = {}
    for r in rows:
        by_key.setdefault((norm(r["n"]), norm(r.get("a")), r.get("z")), []).append(r)
    for path, text in pages.items():
        pg = parsed[path]
        where = path
        indexed = "noindex" not in pg.robots
        # --- overclaims: everything a reader or a crawler sees (CSS aside)
        visible = html.unescape(re.sub(r"<style>.*?</style>", " ", text, flags=re.S))
        visible = re.sub(r"\s+", " ", visible.replace("\\u003c", "<").replace("\\u003e", ">").replace("\\u0026", "&"))
        for rx in OVERCLAIMS:
            for m in re.finditer(rx, visible, re.I):
                problems.append(f"{where}: overclaim \"{m.group(0)}\" (…{visible[max(0, m.start() - 40):m.end() + 20]}…)")
        # --- CSP
        if not pg.csp:
            problems.append(f"{where}: no Content-Security-Policy meta")
        else:
            pol = {d.split()[0]: d.split()[1:] for d in (x.strip() for x in pg.csp.split(";")) if d}
            if pol.get("default-src") != ["'none'"]:
                problems.append(f"{where}: CSP default-src isn't 'none'")
            for name, blocks in (("script-src", pg.scripts), ("style-src", pg.styles)):
                allowed = pol.get(name, [])
                if any(x in allowed for x in ("'unsafe-inline'", "'unsafe-eval'", "*", "https:", "data:")):
                    problems.append(f"{where}: CSP {name} is loose: {allowed}")
                for b in blocks:
                    if sha(b) not in allowed:
                        problems.append(f"{where}: an inline {name.split('-')[0]} block isn't in the CSP (hash {sha(b)[:20]}…)")
            for need in ("base-uri", "form-action", "connect-src", "img-src"):
                if need not in pol:
                    problems.append(f"{where}: CSP has no {need}")
        if pg.bad_attrs:
            problems.append(f"{where}: inline style/event attributes break the CSP: {pg.bad_attrs[:3]}")
        if re.search(r"<script[^>]+src=|<link[^>]+rel=\"stylesheet\"", text):
            problems.append(f"{where}: loads an external script or stylesheet")
        # --- titles, descriptions, headings, sitemap
        if len(pg.h1s) != 1:
            problems.append(f"{where}: {len(pg.h1s)} <h1>")
        if path != "404.html":
            if not 50 <= len(pg.title) <= 60:
                problems.append(f"{where}: title is {len(pg.title)} characters: {pg.title}")
            if pg.desc is None or not 140 <= len(pg.desc) <= 160:
                problems.append(f"{where}: description is {len(pg.desc or '')} characters")
        if indexed and path != "404.html":
            if pg.title in titles:
                problems.append(f"{where}: same title as {titles[pg.title]}")
            if pg.desc in descs:
                problems.append(f"{where}: same description as {descs[pg.desc]}")
            titles[pg.title], descs[pg.desc] = path, path
            if path not in in_sitemap:
                problems.append(f"{where}: indexable but not in sitemap.xml")
            if pg.canonical != page_url(path):
                problems.append(f"{where}: canonical {pg.canonical} != {page_url(path)}")
        elif path in in_sitemap:
            problems.append(f"{where}: noindex page is in sitemap.xml")
        for a in pg.alts:
            if not a:
                problems.append(f"{where}: an <img> has no alt text")
        dup_ids = {i for i in pg.ids if pg.ids.count(i) > 1}
        if dup_ids:
            problems.append(f"{where}: duplicate ids {sorted(dup_ids)[:5]}")
        # --- trademark lines (the footer carries them on every page)
        for tm in (TM_MICHELIN, TM_JBF):
            if tm not in visible:
                problems.append(f"{where}: missing the trademark line \"{tm[:40]}…\"")
        # --- promotional spots never name a place with a Follow-Up or Closed latest result
        lds = []
        for raw in pg.ldjson:
            try:
                lds.append(json.loads(raw))
            except ValueError:
                pass
        headlines = [x.get("headline", "") + " " + x.get("description", "") for x in lds if isinstance(x, dict) and x.get("@type") == "Article"]
        promo_text = norm(" ".join([pg.title, pg.desc or ""] + pg.metas + pg.h1s + pg.promo + headlines))
        for k in promo_bad:
            if k in promo_text:
                problems.append(f"{where}: a promotional spot names{k}, whose latest DBPR result is Follow-Up or Closed")
        # --- city pages: the title, h1 and description promise only what's on the page
        if path.startswith("cities/") and path != "cities/index.html":
            promise = " ".join([pg.title, pg.h1s[0] if pg.h1s else "", pg.desc or ""]).lower()
            for rx, sec in CITY_KEYWORDS:
                if re.search(rx, promise) and sec not in pg.section_ids:
                    problems.append(f"{where}: title/h1/description mention {rx!r} but the page has no #{sec} section")
        # --- no "Apalachicola oysters" claim outside a place's own researched text
        outside = re.sub(r"<li id=\"[^\"]*\">.*?</li>", " ", text, flags=re.S)
        outside = re.sub(r"<script.*?</script>", " ", outside, flags=re.S)
        if re.search(r"apalachicola\s+(?:bay\s+)?oysters?(?!\s+(?:bars?|houses?|pubs?)\b)", html.unescape(outside), re.I):
            problems.append(f"{where}: claims Apalachicola oysters outside a place's own researched text")
        # --- a self-claim of "Florida's oldest restaurant" is always attributed
        for m in re.finditer(r"florida'?s oldest restaurant(?!s)", visible, re.I):
            before = visible[max(0, m.start() - 40):m.start()].lower()
            if not re.search(r"calls itself|its own|service mark|claim", before):
                problems.append(f"{where}: unattributed \"{m.group(0)}\" (…{visible[max(0, m.start() - 40):m.end() + 10]}…)")
        # --- JSON-LD
        for raw in pg.ldjson:
            try:
                ld = json.loads(raw)
            except ValueError as ex:
                problems.append(f"{where}: bad JSON-LD ({ex})")
                continue
            if "</" in raw:
                problems.append(f"{where}: JSON-LD contains a raw '</'")
            for p, k, v in walk(ld):
                if k in ("aggregateRating", "review", "reviewRating", "ratingValue", "reviewCount"):
                    problems.append(f"{where}: JSON-LD has {k} at {p}")
                if k == "streetAddress" and not str(v).strip():
                    problems.append(f"{where}: empty streetAddress at {p}")
            for block in ([ld] + ld.get("@graph", [])) if isinstance(ld, dict) else []:
                if block.get("@type") != "ItemList":
                    continue
                own_url = pg.canonical or page_url(path)
                items = block.get("itemListElement", [])
                if block.get("numberOfItems") != len(items):
                    problems.append(f"{where}: ItemList numberOfItems {block.get('numberOfItems')} != {len(items)}")
                for li in items:
                    it = li.get("item", {})
                    u = it.get("url", "")
                    if not u.startswith(own_url + "#"):
                        problems.append(f"{where}: ItemList item {it.get('name')!r} url {u!r} isn't on this page")
                    elif u.split("#", 1)[1] not in pg.ids:
                        problems.append(f"{where}: ItemList item {it.get('name')!r} points to #{u.split('#', 1)[1]}, which isn't on the page")
                    s = it.get("sameAs")
                    if s and not re.match(r"https?://", s):
                        problems.append(f"{where}: sameAs {s!r} isn't http(s)")
                # --- a hand-checked guide lists only hand-checked places with its tag
                if path in GUIDE_PAGES:
                    tag = GUIDE_PAGES[path]
                    for li in items:
                        it = li.get("item", {})
                        a = it.get("address", {})
                        key = (norm(it.get("name")), norm(a.get("streetAddress")), a.get("postalCode") or None)
                        hits = by_key.get(key, [])
                        if not any(r.get("hc") == 1 and (r.get("g") or 0) & tag for r in hits):
                            problems.append(f"{where}: lists {it.get('name')!r}, which isn't a hand-checked place with this guide's tag")
        # --- links: only http(s), mailto and tel leave the site
        for href in re.findall(r'href="([^"]*)"', text):
            if re.match(r"\s*(javascript|data|vbscript):", href, re.I) and not href.startswith("data:image/svg+xml"):
                problems.append(f"{where}: unsafe link {href[:40]}")
        # --- the App Store button has no Apple logo until it's Apple's own badge
        for m in re.finditer(r'<a class="btn store-btn"[^>]*>(.*?)</a>', text, re.S):
            if "<svg" in m.group(1):
                problems.append(f"{where}: the early-access button carries an Apple logo")
    # --- the inspections page: DBPR's words and groups, DBPR's search, and no place named or listed
    ins = pages.get(INS_PAGE)
    if not ins:
        problems.append(f"{INS_PAGE} is missing")
    else:
        vis = norm(html.unescape(re.sub(r"<(script|style)\b.*?</\1>", " ", ins, flags=re.S)))
        for need in ("establishments are not graded or rated", "Met Inspection Standards", "Follow-Up Inspection Required", "Facility Temporarily Closed"):
            if norm(need) not in vis:
                problems.append(f"{INS_PAGE}: doesn't say \"{need}\"")
        if "VerifyLicensee" not in ins:
            problems.append(f"{INS_PAGE}: doesn't link DBPR's license and inspection search")
        if 'class="places"' in ins or '"ItemList"' in ins:
            problems.append(f"{INS_PAGE}: lists places")
        named = [k for k in any_bad if k in vis]
        if named:
            problems.append(f"{INS_PAGE}: names places with a Follow-Up or Closed result: {named[:5]}")
    # --- the stone crab season is stated
    sc = pages.get("florida-stone-crab.html", "")
    if not ("October 15" in sc and "May 1" in sc):
        problems.append("florida-stone-crab.html: doesn't state the October 15 – May 1 season")
    # --- the honors page never calls a finalist or semifinalist a winner
    hon = pages.get(HON_PAGE, "")
    for li in re.findall(r"<li id=\"[^\"]*\">.*?</li>", hon, re.S):
        t = html.unescape(re.sub(r"<[^>]+>", " ", li))
        if "James Beard winner" in t and not re.search(r"James Beard: [^;]*\bwinner\b", t):
            problems.append(f"{HON_PAGE}: a place carries 'James Beard winner' without a winning honor: {t[:80]}")
        if re.search(r"(?:semi)?finalist\s+winner|winner\s+\(?(?:semi)?finalist", t, re.I):
            problems.append(f"{HON_PAGE}: mixes finalist and winner: {t[:80]}")
    # --- the web app
    ex = parsed.get("explore/index.html")
    if ex:
        js = "\n".join(ex.scripts)
        if f'"{STORAGE_PREFIX}"' not in js:
            problems.append(f"explore/index.html: localStorage prefix {STORAGE_PREFIX!r} not found")
        for m in re.finditer(r"""localStorage\.(?:get|set|remove)Item\(\s*(["'`])([^"'`]*)\1""", js):
            if not m.group(2).startswith(STORAGE_PREFIX):
                problems.append(f"explore/index.html: localStorage key {m.group(2)!r} doesn't start with {STORAGE_PREFIX!r}")
        for other in OTHER_PREFIXES:
            if re.search(rf"""["'`]{re.escape(other)}["'`]""", js):
                problems.append(f"explore/index.html: uses another state's storage prefix {other!r}")
        if not re.search(r'id="ex-mapattr"[^>]*>[^<]*© OpenStreetMap contributors, Overture Maps Foundation', pages["explore/index.html"]):
            problems.append("explore/index.html: the map doesn't credit OpenStreetMap contributors and Overture Maps Foundation")
        if re.search(r"""\bmost\s*:\s*["']Most|sorts:\s*\[[^\]]*["']most["']""", js):
            problems.append("explore/index.html: the Inspections guide has a 'most violations' order (a worst list)")
    else:
        problems.append("explore/index.html is missing")
    # --- published data
    try:
        ids = json.load(open(os.path.join(DOCS, "data", "ids.json")))
        if len(ids) != core["n"] or len(set(ids)) != len(ids):
            problems.append(f"data: ids.json has {len(ids)} ids ({len(set(ids))} unique) for {core['n']} places")
        for f in sorted(glob.glob(os.path.join(DOCS, "data", "detail-*.json"))):
            slug_ = os.path.basename(f)[len("detail-"):-len(".json")]
            co = core["dfiles"].index(slug_) if slug_ in core["dfiles"] else None
            det = json.load(open(f))
            for k, d in det.items():
                i = int(k)
                if not 0 <= i < core["n"] or rows[i].get("co") != co:
                    problems.append(f"data: {os.path.basename(f)} has place {k}, which isn't in that county")
                    break
                w = d.get("w")
                if w and not re.match(r"https?://", w):
                    problems.append(f"data: website {w!r} for {rows[i]['n']!r} isn't http(s)")
            for p_, k, v in walk(det):
                if k.lower() in ("rating", "ratings", "reviews", "review_count", "price", "price_level", "gmap_id", "stars"):
                    problems.append(f"data: {os.path.basename(f)} has a Google-style field {k!r}")
                    break
        for k in list(core["cols"]) + list(core.get("sparse") or {}):
            if k.lower() in ("rating", "ratings", "reviews", "rv", "rt", "price", "pr", "gmap_id", "stars"):
                problems.append(f"data: core.json has a Google-style column {k!r}")
    except (OSError, ValueError, KeyError) as ex:
        problems.append(f"data: couldn't read the published data ({ex})")
    return problems, len(pages)


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve():
    root = DOCS
    if BASE:   # serve docs/ at /florida-eats/, the path GitHub Pages will use
        root = tempfile.mkdtemp()
        os.symlink(os.path.abspath(DOCS), os.path.join(root, BASE.strip("/")))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=root))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_address[1]}"


def local_exists(path):
    path = urllib.parse.unquote(path.split("#")[0].split("?")[0])
    if BASE and path.startswith(BASE + "/"):
        path = path[len(BASE):]
    f = os.path.join(DOCS, path.lstrip("/"))
    return os.path.isfile(f) or os.path.isfile(os.path.join(f, "index.html"))


def expected_hits(rows, guide_tag, word):
    """Places on a hand-checked guide whose name, dishes, town or address contain the word (what a search for it should list)."""
    return sum(1 for r in rows if r.get("hc") == 1 and (r.get("g") or 0) & guide_tag
               and f" {word}" in norm(" ".join(str(x) for x in (r["n"], r.get("dish"), r.get("a"), r["city"], r.get("z")) if x)))


CSP_PROBE = """window.__csp = []; document.addEventListener("securitypolicyviolation",
  e => window.__csp.push(e.violatedDirective + " " + (e.blockedURI || "inline") + " @" + (e.sourceFile || "") + ":" + e.lineNumber));"""


def browser_checks(problems):
    from playwright.sync_api import sync_playwright
    base = serve()
    paths = [rel(f) for f in doc_files()]
    urls = [base + BASE + "/" + ("" if p == "index.html" else p.removesuffix("index.html")) for p in paths]
    core, rows = load_core()
    ids = json.load(open(os.path.join(DOCS, "data", "ids.json")))
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome")
        for width in (375, 1280):
            ctx = browser.new_context(viewport={"width": width, "height": 900})
            ctx.add_init_script(CSP_PROBE)
            page = ctx.new_page()
            errors = []
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(str(e)))
            for url in urls:
                errors.clear()
                page.goto(url, wait_until="networkidle")
                where = f"{urllib.parse.urlparse(url).path} @{width}"
                over = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                if over > 1:
                    problems.append(f"{where}: scrolls sideways by {over}px")
                if page.locator("h1").count() != 1:
                    problems.append(f"{where}: {page.locator('h1').count()} <h1>")
                problems += [f"{where}: CSP violation: {v}" for v in page.evaluate("window.__csp || []")]
                if width == 1280:   # links are the same at both widths
                    refs = page.evaluate("""[...document.querySelectorAll('a[href],img[src],link[href],script[src]')]
                        .map(e => e.getAttribute('href') || e.getAttribute('src'))""")
                    for ref in refs:
                        full = urllib.parse.urljoin(url, ref)
                        p = urllib.parse.urlparse(full)
                        if p.scheme in ("mailto", "tel", "data"):
                            continue
                        if p.netloc in (urllib.parse.urlparse(base).netloc, DOMAIN) and not local_exists(p.path):
                            problems.append(f"{where}: broken link {ref}")
                        if p.fragment and "=" not in p.fragment and p.netloc == urllib.parse.urlparse(base).netloc and p.path == urllib.parse.urlparse(url).path:
                            if not page.evaluate("(id) => !!document.getElementById(id)", urllib.parse.unquote(p.fragment)):
                                problems.append(f"{where}: link to missing #{p.fragment}")
                    imgs = page.evaluate("[...document.images].filter(i => i.complete && i.naturalWidth === 0).map(i => i.src)")
                    problems += [f"{where}: image didn't load {s}" for s in imgs]
                problems += [f"{where}: console error: {e}" for e in errors]
            # ------------------------------------------------ the web app
            errors.clear()
            ex = base + BASE + "/explore/"
            page.goto(base + BASE + "/", wait_until="networkidle")             # a page before it, so Back has somewhere to leave to
            page.goto(ex + "#g=cuban", wait_until="networkidle")
            page.wait_for_function("document.querySelectorAll('.ex-row').length > 0", timeout=30000)
            search = page.locator('#ex-q').first
            for word in ("croquetas", "pastelitos"):
                search.fill(word)
                page.wait_for_timeout(500)
                want, got = expected_hits(rows, 1, word), page.locator(".ex-row").count()
                if got != want or not want:
                    problems.append(f"explore @{width}: '{word}' listed {got} Cuban places, expected the {want} that serve it")
            # Miami's quadrant words: "southwest 8th street" finds SW 8th St addresses
            page.goto(ex + "#g=all", wait_until="networkidle")
            page.wait_for_function("document.querySelectorAll('.ex-row').length > 0", timeout=30000)
            search.fill("southwest 8th street")
            page.wait_for_timeout(700)
            sw8 = sum(1 for r in rows if " sw 8th st " in norm(r.get("a")))
            count_text = page.locator("#ex-count").inner_text()
            got = int(re.match(r"([\d,]+)", count_text).group(1).replace(",", "")) if re.match(r"[\d,]+", count_text) else 0
            if not sw8 or got < sw8:
                problems.append(f"explore @{width}: 'southwest 8th street' listed {got} places, but {sw8} have an SW 8th St address")
            page.goto(ex + "#g=cuban", wait_until="networkidle")
            page.wait_for_function("document.querySelectorAll('.ex-row').length > 0", timeout=30000)
            search.fill("versailles")
            page.wait_for_timeout(500)
            if not page.locator(".ex-row").count():
                problems.append(f"explore @{width}: search 'versailles' found nothing")
            else:
                page.locator(".ex-row").first.click()
                page.wait_for_timeout(1500)
                panel = page.locator("#ex-panel")
                if not panel.is_visible() or not panel.locator("a", has_text="Directions").count():
                    problems.append(f"explore @{width}: opening a place showed no details")
                else:
                    ptxt = panel.inner_text()
                    if "Inspections · Florida DBPR".upper() not in ptxt.upper() or not re.search(r"Met Inspection Standards|Follow-Up Inspection Required|Facility Temporarily Closed", ptxt, re.I):
                        problems.append(f"explore @{width}: the panel doesn't show DBPR's result group: {ptxt[:200]!r}")
                    if not panel.locator(f'a[href*="VerifyLicensee"]', has_text="search license").count():
                        problems.append(f"explore @{width}: the panel has no DBPR license search link")
                    if width == 375:
                        modal = page.evaluate("""[document.querySelector('#ex-panel').getAttribute('role'),
                            document.querySelector('#ex-panel').getAttribute('aria-modal'), document.querySelector('#ex-app').inert,
                            document.querySelector('footer').inert]""")
                        if modal != ["dialog", "true", True, True]:
                            problems.append(f"explore @{width}: the open place sheet isn't a modal dialog with the page behind it inert: {modal}")
                    page.locator("#ex-save").click()
                    keys = page.evaluate("Object.keys(localStorage)")
                    bad = [k for k in keys if not k.startswith(STORAGE_PREFIX)]
                    if bad or not keys:
                        problems.append(f"explore @{width}: localStorage keys {keys} (want all to start {STORAGE_PREFIX!r})")
                    page.locator("#ex-save").click()
                    page.go_back()
                    page.wait_for_timeout(600)
                    if not page.url.startswith(ex) or panel.is_visible():
                        problems.append(f"explore @{width}: Back with a place open didn't just close it (now at {page.url}, panel visible: {panel.is_visible()})")
                    elif width == 375 and page.evaluate("document.querySelector('#ex-app').inert"):
                        problems.append(f"explore @{width}: the page stayed inert after the sheet closed")
            search.fill("🍕")
            page.wait_for_timeout(400)
            if page.locator(".ex-row").count():
                problems.append(f"explore @{width}: an emoji search listed places")
            # a shared #p= link opens that place
            target = next((i for i, r in enumerate(rows) if r.get("hc") == 1 and r.get("ig") == 0 and (r.get("g") or 0) & 2), None)
            if target is not None:
                page.goto(ex + "#g=stonecrab&p=" + ids[target], wait_until="networkidle")
                page.reload(wait_until="networkidle")
                page.wait_for_timeout(1500)
                name = page.locator("#ex-pname").inner_text() if page.locator("#ex-pname").count() else ""
                if norm(name) != norm(rows[target]["n"]):
                    problems.append(f"explore @{width}: #p={ids[target]} opened {name!r}, not {rows[target]['n']!r}")
            # the map draws dots and credits its outlines
            page.goto(ex + "#g=oyster", wait_until="networkidle")
            page.reload(wait_until="networkidle")
            page.wait_for_function("document.querySelectorAll('.ex-row').length > 0", timeout=30000)
            page.locator('.ex-view button[data-v="map"]').click()
            page.wait_for_timeout(1200)
            painted = page.evaluate("""(() => { const c = document.querySelector('#ex-map'); const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
                let n = 0; for (let i = 0; i < d.length; i += 4) if (d[i] > 230 && d[i + 1] > 120 && d[i + 1] < 160 && d[i + 2] < 70) n++; return n; })()""")
            if painted < 20:
                problems.append(f"explore @{width}: the map drew no orange dots for the oyster bars ({painted} pixels)")
            if not page.locator("#ex-mapattr").is_visible():
                problems.append(f"explore @{width}: the map's OpenStreetMap/Overture credit isn't visible")
            for hostile in ("#g=constructor", "#g=__proto__&sort=toString", "#g=all&p=__proto__"):
                errors.clear()
                page.goto(ex + hostile, wait_until="networkidle")
                page.reload(wait_until="networkidle")
                page.wait_for_timeout(700)
                if not page.locator(".ex-row").count() or errors:
                    problems.append(f"explore @{width}: {hostile} broke the list ({errors[:1]})")
            page.goto(ex + "#g=honors&sort=nearest", wait_until="networkidle")
            page.reload(wait_until="networkidle")
            page.wait_for_function("document.querySelectorAll('.ex-row').length > 0", timeout=30000)
            if "Nearest" in page.locator("#ex-count").inner_text():
                problems.append(f"explore @{width}: says 'Nearest' with no location")
            page.goto(ex + "#g=inspections", wait_until="networkidle")
            page.reload(wait_until="networkidle")
            page.wait_for_function("document.querySelectorAll('.ex-row').length > 0", timeout=30000)
            opts = page.locator("#ex-sort option").all_inner_texts()
            if any(o.lower().startswith("most") for o in opts):
                problems.append(f"explore @{width}: the Inspections guide offers {opts} (no worst list)")
            problems += [f"explore @{width}: CSP violation: {v}" for v in page.evaluate("window.__csp || []")]
            problems += [f"explore @{width}: console error: {e}" for e in errors]
            ctx.close()
        browser.close()
    return len(urls)


def main():
    problems, n = static_checks()
    if "--static" in sys.argv:
        print(f"{n} pages, static checks")
    else:
        n = browser_checks(problems)
        print(f"{n} pages × 2 widths + the web app")
    for p in problems:
        print("  ✗", p)
    print("OK" if not problems else f"{len(problems)} problems")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
