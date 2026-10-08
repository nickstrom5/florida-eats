# Website: florida.eatsranked.com (for now nickstrom5.github.io/florida-eats/)

Built 2026-10-07. The site in `docs/` is **generated**: never hand-edit `docs/*.html` or `docs/data/*`; change
`scripts/make-site.py` (pages, data split) or `scripts/explore.js` (the web app) and re-run.

## Regenerate and check

```bash
.venv/bin/python scripts/make-site.py          # writes docs/ and playbook/site-numbers.json (github.io address, BASE /florida-eats)
.venv/bin/python scripts/qa-site.py --static   # a few seconds
.venv/bin/python scripts/qa-site.py            # + headless Chrome at 375 and 1280 px, about 3 minutes
```

Run it after every data rebuild (`FL_APP=1 pipeline/florida.py`, which writes `data/app/places.json` and `data/app/detail-*.json`;
the generator reads both, and also accepts the older single-file format). Every number on the site is counted from that data at
build time; `playbook/site-numbers.json` records them, plus the web app's file sizes.

Once `dig florida.eatsranked.com` shows the CNAME: `FL_DOMAIN=florida.eatsranked.com .venv/bin/python scripts/make-site.py` (writes
`docs/CNAME`, drops the `/florida-eats` prefix from every link), QA, push. Without `FL_DOMAIN` the generator deletes `docs/CNAME`.

## What each page holds

| Page | What's on it |
|---|---|
| `index.html` | Hero, four counted stats, how it works, screenshots (only once `docs/img/screen-{home,cuban,detail,map,honors}.png` exist; `.webp` twins are used when present), guide cards, city links, FAQ (FAQPage JSON-LD), early-access mailto button |
| 7 themed guides | `florida-cuban-sandwiches-cafecito.html`, `florida-stone-crab.html` (FWC season Oct 15 – May 1 in kicker, lede and copy), `florida-grouper-sandwiches-seafood-shacks.html`, `florida-keys-key-lime-pie-conch.html`, `florida-oyster-bars.html` (names an oyster's source only where the place's own researched text does), `florida-fish-camps-smoked-fish.html`, `florida-latin-caribbean-restaurants.html`. Hand-checked places only (`hc` + the guide's tag bit), by region (the pipeline's eight regions, by county) and town, with ItemList JSON-LD |
| `florida-oldest-restaurants.html` | Hand-checked places with the oldest tag and a founding year at this address, oldest first, each with its `fn` note (self-claims such as Columbia's "Florida's Oldest Restaurant℠" stay attributed as written) |
| `florida-michelin-james-beard.html` | MICHELIN Guide Florida 2026 distinctions and James Beard honors (2023–26, plus America's Classics), the honor text under each place; finalists and semifinalists never called winners; Green Star noted as being phased out; trademark lines |
| `florida-restaurant-inspections.html` | How DBPR inspects, its three result groups with DBPR's dispositions verbatim under each and counts at the latest visit, emergency closures (counts, DBPR's most common reasons), how to look a place up (web app panel + DBPR's license search), counts by county A to Z. **Names no place and lists none**; no ranking |
| `cities/*.html` (19) + `cities/index.html` | Towns with at least 5 hand-checked or honored places (`MIN_LISTED`): that town's guide places, honorees and oldest places, a counts-only DBPR line, and what the town eats (top cuisines). Title, h1 and description name only sections the page has |
| `explore/` | The web app (below) |
| `privacy.html`, `terms.html`, `404.html` | Policy text; terms list every source and license |
| `sitemap.xml`, `robots.txt`, `site.webmanifest`, `.nojekyll` | Plumbing; the sitemap lists the indexable pages |

Every page: hash-pinned Content-Security-Policy (`default-src 'none'`), no third-party scripts, fonts or analytics, no cookies, no
`aggregateRating`/reviews, the footer's source and trademark lines, Gulf teal / citrus orange / key lime / sand palette with a
light and dark scheme, and an inline SVG of the stone crab claw icon (same geometry as `scripts/make-brand.swift`).

## The web app (`docs/explore/`, source `scripts/explore.js`)

Guides as in `Guide.swift` (Cuban & cafecito, stone crabs, grouper, Keys, oysters, fish camps, Latin & Caribbean, MICHELIN & James
Beard, oldest, inspections, all, saved), a port of `Search.swift` (street-type and Miami quadrant synonyms: "southwest 8th street"
finds "SW 8th St"; "cuban sandwich", "stone crab", "oyster bar", "fish camp" act as guide words; dishes search the hand-checked
places), town/kind/chain filters, distance sort from the browser's location, a canvas map of the county outlines from
`data/fl/fl_shapes.json` credited "© OpenStreetMap contributors, Overture Maps Foundation", a place panel with DBPR's result group,
disposition, date, latest routine counts, up to 8 visits, emergency closures and the license number to search on DBPR's site, and
`#g=…&p=<id>` URLs. localStorage (keys `fleats-…`) holds only saved places and the last guide.

Deliberate differences from the app: the Inspections guide has no "most violations" order (the site keeps no worst list), and the
web app leaves out the non-restaurant venues the app hides by default.

Data files (sizes on 2026-10-07, 52,387 restaurants; GitHub Pages serves them gzipped):

| File | Raw | Gzip | Loaded |
|---|---|---|---|
| `data/core.json` | 4.7 MB | 0.96 MB | on page load: list, search and map columns, ordered by region/county/town/zip/street so they compress; coordinates delta-coded in 0.0001° steps; latest visit as a day number; mostly-empty columns as `[index, value]` pairs |
| `data/ids.json` | 0.79 MB | 0.41 MB | right after the list renders (saved places and `#p=` links wait for it) |
| `data/detail-<county>.json` (67) | 0.5 KB – 2.0 MB | up to 0.35 MB (Miami-Dade); 2.5 MB for all 67 | when a place in that county is opened or pointed at: phone, website, notes, license, inspection history, closures |
| `data/fl_shapes.json` | 0.29 MB | 0.07 MB | when the map opens |

## QA (`scripts/qa-site.py`)

Static: overclaims ("every restaurant", "all N", "checked open", worst/dirtiest, letter grades or "inspection score"), CSP hashes,
title 50–60 / description 140–160 and unique, one h1, sitemap = indexable pages, canonical, alt text, duplicate ids, JSON-LD
validity and ItemList anchors, no ratings in JSON-LD, promotional spots (title, description, og/twitter, h1, kicker, lede, Article
headline) never name a place whose latest DBPR group is Follow-Up or Closed, the inspections page names and lists no place and
quotes DBPR, every hand-checked guide item is a hand-checked place with that tag in `core.json`, no finalist shown as a winner,
no "Apalachicola oysters" outside a place's own text, attributed "Florida's oldest restaurant", trademark lines, the stone crab
season, the web app's storage prefix, map credit and sort list, and the published data (ids unique, detail files per county,
http(s) websites, no rating/review/price fields). Browser (Python Playwright, `channel="chrome"`, served under `/florida-eats/`):
no sideways scroll at 375/1280, no console errors or CSP violations, no broken links or images, dish searches, the quadrant search,
the place panel's DBPR section and license link, Back closing the panel, the phone sheet as a modal dialog, `#p=` links, the map
drawing, hostile hashes, and storage keys. Every check was mutation-tested on a copy of `docs/` (`QA_DOCS=<copy>`): 18 static and
9 browser faults, all caught.

## What Nick needs to do (each needs his explicit yes)

1. **Cloudflare DNS**: `CNAME florida → nickstrom5.github.io`, **DNS only** (grey cloud), in the `eatsranked.com` zone.
2. **GitHub**: create the public repo `nickstrom5/florida-eats`, push `docs/`, the app source and `scripts/` (never `data/` or
   `site/`), and turn on Pages from `main` / `docs`. Public commits use
   `git -c user.name="Nick Soderstrom" -c user.email="329204362+nickstrom5@users.noreply.github.com" commit`.
3. After the CNAME resolves: regenerate with `FL_DOMAIN=florida.eatsranked.com`, QA, push; turn on Enforce HTTPS
   (`gh api -X PUT repos/nickstrom5/florida-eats/pages -F https_enforced=true`); set the repo's Website field; point the App Store
   privacy, support and marketing URLs and `FloridaEats/App/Links.swift` at the new domain in the next build; add Florida to the
   `eatsranked.com` hub.
4. Once the App Store listing exists: set `APP_STORE_URL` in `page()` (footer script) and the Smart App Banner `app-id`, swap the
   mailto button for Apple's unmodified badge, and put the MobileApplication `offers` back in the landing page JSON-LD.
5. Optional: site screenshots in `docs/img/` (480 px copies of `docs/screenshots/{home,cuban,detail,map,honors}.png`, quantized PNG
   plus `cwebp -q 84`); the landing page picks them up on the next run.

## Not yet covered

- Tallahassee (4 listed places), Islamorada (3), Fort Myers (2), Clearwater (2), Gainesville (1) and Daytona Beach (0) have no city
  page until the research adds places there (`cities_without_a_page` in `site-numbers.json`).
- No per-place pages (Wisconsin has them); the web app's `#p=` links are the shareable place URLs.
