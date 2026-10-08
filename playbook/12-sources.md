# Sources: Florida (checked 2026-10-07)

Every source the leaderboard, the app and the site use, with its terms, cadence and fields. Numbers that appear in copy are written
by the pipeline (`data/fl/calibration*.json`, later `playbook/site-numbers.json`); this file explains where they come from.

## Official: Florida DBPR, Division of Hotels and Restaurants

One agency licenses and inspects every public food service establishment in Florida. Its public-records page is
https://www2.myfloridalicense.com/hotels-restaurants/public-records/ (fetched 2026-10-07; HTTP 200 for every file below).

Terms: public records under Chapter 119, Florida Statutes, provided "through free download" (ReadMe/Disclaimer,
https://www2.myfloridalicense.com/public-records-read-medisclaimer/). The disclaimer says the data "is refreshed weekly" and that
"For up-to-the-minute license verification" people should use the license search. No reuse restriction is stated.

| File | What | Cadence | Rows (2026-10-07) |
|---|---|---|---|
| `sto/file_download/extracts/hrfood{1-7}.csv` | Every food service license by district: Business Name, Licensee Name (legal entity, never shown), location address/city/zip/county, rank (SEAT seating, NOST non-seating, MFDV mobile, CATR catering, PARK theme-park cart, HTDG, VEND, TEMP), primary status (20 Current, 45 Delinquent, 46 Voluntary Relinquishment), seats, base risk level, last inspection date, expiry. No coordinates. | weekly (files dated 2026-10-05) | 69,810 licenses; 53,489 current SEAT+NOST |
| `sto/file_download/extracts/{1-7}fdinspi.csv` | Inspections since July 1 (this fiscal year), one row per visit: license type + number (no rank prefix), DBA, address, inspection number, visit number, type (Routine - Food, Complaint Full/Partial, Food-Licensing), disposition, date, High Priority / Intermediate / Basic counts, counts per violation category 01–58 | weekly (2026-10-07; visits through 2026-10-06) | 42,398 visits, Jul 1 – Oct 6 2026 |
| `hr/inspections/fdinspi_2526.xlsx`, `_2425`, `_2324` | The same, statewide, per fiscal year (Jul–Jun). The 2024–25 and 2023–24 workbooks use database column names (LICENSE_NO, DISPOSITION, V_01…); `pipeline/dbpr.py` maps them. | yearly | 142,203 (FY25-26), 140,470 (FY24-25), FY23-24 |
| `hr/inspections/documents/EOS_Weekly_Extract_<date>.xlsx` | Emergency closures: license number, name, address, closure date and time, reopening ("order to vacate") date and time, the reason in DBPR's words ("Roach activity", "No potable water") | weekly, Jan–Oct 2026 posted | 40 files |
| `sto/file_download/extracts/rdarMMYY.csv` | Restaurant Disciplinary Activity Reports: case number, license, name, address, violation count, fine from the final order, order date, violation date | monthly | Oct 2025 – Oct 2026 used |
| Public-records layout section of the same page | Column definitions and the violation category names (pre-2013 critical/non-critical; since 1/1/2013 High Priority / Intermediate / Basic) | — | — |

**Florida has no official grade.** DBPR's inspections page (https://www2.myfloridalicense.com/hotels-restaurants/inspections/):
"Because conditions can change rapidly, establishments are not graded or rated." The same page groups the dispositions into three
results, which we show labeled as DBPR's:
- **Met Inspection Standards**: Inspection Completed – No Further Action; Callback – Complied; Admin. Complaint Callback Complied;
  Emergency Order Callback Complied.
- **Follow-Up Inspection Required**: Warning Issued; Callback – Extension given, pending; Callback – Administrative complaint recommended;
  Administrative complaint recommended; Admin. Complaint Callback Not Complied; Administrative Complaint Time Extension; Emergency Order
  Callback Time Extension.
- **Facility Temporarily Closed**: Emergency Order Recommended; Administrative Determination Recommended (operating without a license);
  Emergency Order Callback Not Complied.
We never compute a grade. The leaderboard's Inspections board sorts by DBPR's own count of high-priority violations at the latest routine
inspection and shows DBPR's result and date on every row.

**Reading the schema.** The files count violations per category, not citation text. Category 35 is "No presence or breeding of
insects/rodents/pests; no live animals, outer openings protected from insects/pests, rodent proof", so a 35 is not proof of pests; only
the closure file names a pest. Categories 45–49 are fire items "for reporting purposes only" and are left out of category lists.
Violation categories are shown with DBPR's own names.

**Publication lag.** Inspections and closures are cut at 7 days before the download (records through 2026-09-30 for the 2026-10-07
download). Every date shown comes from `data/fl/dbpr_meta.json`.

**Search-only portal: link, don't scrape.** "View Food & Lodging Inspections" (https://www.myfloridalicense.com/portalsearches/VerifyLicensee?Mode=0&BoardType=H)
is the only place with citation text. It's a POST form: a per-license GET link doesn't exist, so places link the search page (HTTP 200,
renders the search form) and show the license number to search for. The legacy wl11.asp was not used.

**Names.** The license's Business Name is preferred to the inspection DBA, and the Licensee Name is never shown. Both can hold a legal
entity ("MCDONALDS REST OF FLORIDA INC"), so `florida.py` strips corporate suffixes and store numbers, and replaces a name that is still
a legal entity with an inspection DBA that isn't, or the chain's brand. 21 business names arrive with "¿" for an apostrophe
("ADRIANO¿S"); `dbpr.py` repairs them.

**Not DBPR.** FDACS (Agriculture) licenses groceries, convenience stores and many bakeries, coffee shops and juice bars; the Department
of Health covers schools, some clubs, theaters and institutional kitchens. Their inspections are search-only
(foodpermit.fdacs.gov is a search form): not collected. For those places, no DBPR match means "—", not "unlicensed".

**Disney and Universal.** 358 current seating/non-seating licenses are held by Walt Disney or Universal Orlando entities (licensee name).
Restaurants stay and say "Disney/Universal" (some are inside ticketed parks); theme-park carts (rank PARK) and caterers are hidden with
the non-restaurants.

## Official, downloaded but not yet used

- DBPR Alcoholic Beverages and Tobacco retail licenses (`extracts/bd4006lic.csv`) and revocations (`bd400revok.csv`), and the license
  type list (`abt/rules_statutes/license_types.pdf`). Status codes from the ABT public-records page: 20 Current, 41 Escrow (not live),
  45 Delinquent, 46 Voluntary Relinquishment, 61 Revoked.
- Florida DOR NAL property rolls: not downloaded (owner names are personal data; not needed).

## Map listings and geocoding

| Source | Used for | License | URL |
|---|---|---|---|
| Overture Maps places, release 2026-09-23.1 | Map points, websites, phones and categories for licensed places; café-type places DBPR doesn't license | CDLA Permissive 2.0 (Meta, Microsoft, AllThePlaces CC0, Foursquare Apache 2.0 + NOTICE) | https://overturemaps.org |
| Overture divisions and base | State and county outlines (land only), for the map and county assignment | ODbL: "© OpenStreetMap contributors, Overture Maps Foundation" | same |
| Overture addresses (12.3M Florida points) | Placing DBPR licenses on their street address | Overture addresses: per-source open licenses (state/county address files) | same |
| US Census Bureau batch geocoder | Licenses the address points miss | Public domain | https://geocoding.geo.census.gov |

## Ratings (web leaderboard only)

UCSD Google Local 2021 (meta-Florida.json.gz, 86 MB; review-Florida.json.gz, 5.3 GB streamed, never stored): Google ratings, review
counts and price levels frozen in September 2021, labeled "2021 snapshot" everywhere. The app and the public site use none of it.

## Honors and hand-checked guides

`data/research/michelin.json`, `jbf.json`, `honors_notes.md` (MICHELIN Guide Florida 2026, James Beard Foundation), and
`data/research/app/*.json` (Cuban and Latin, stone crabs, grouper, Keys classics, oyster bars, fish camps and smoked fish, oldest
places), each place with a 2025–26 source. Leads the research couldn't verify: `data/research/app/LEADS_*.md`.
