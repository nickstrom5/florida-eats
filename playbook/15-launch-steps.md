# Launch steps (each one needs Nick's explicit yes; none has been done)

## 0. Before anything public: the name
"Florida Eats" is Nick's pick. Search USPTO (tmsearch.uspto.gov) for FLORIDA EATS in classes 9, 35, 39 and 43. "EAT LOCAL FLORIDA" is a
registered mark for a restaurant guide website: different wording, but take a look before launch.

## 1. Public website repo + GitHub Pages
Only `docs/`, the app source, scripts and playbook go public. `.gitignore` keeps out `data/` (DBPR files, research, the Google 2021
snapshot), `site/` (the Google-derived leaderboard), build output, every `DerivedData*` folder and the generated Xcode project. Run `git status`
before the first commit to confirm.
```bash
cd fl-eats   # from the claudecode folder
git init -b main
git config user.name "Nick Soderstrom" && git config user.email "329204362+nickstrom5@users.noreply.github.com"
git add -A && git status --short | head -60          # confirm: no data/, site/, .venv/, DerivedData/, build/
git commit -m "Florida Eats: app, website and pipeline"
gh repo create nickstrom5/florida-eats --public --source . --push
gh api -X POST repos/nickstrom5/florida-eats/pages -f "source[branch]=main" -f "source[path]=/docs"
```
Then check that https://nickstrom5.github.io/florida-eats/, `/privacy.html`, `/terms.html` and `/explore/` return 200.

## 2. florida.eatsranked.com (Nick, in Cloudflare)
Add `CNAME florida → nickstrom5.github.io`, **DNS only** (grey cloud). When `dig +short florida.eatsranked.com CNAME` shows it:
```bash
FL_DOMAIN=florida.eatsranked.com .venv/bin/python scripts/make-site.py && .venv/bin/python scripts/qa-site.py
git commit -am "Serve from florida.eatsranked.com" && git push
gh api -X PUT repos/nickstrom5/florida-eats/pages -f cname=florida.eatsranked.com
# once the certificate is issued (minutes):
gh api -X PUT repos/nickstrom5/florida-eats/pages -F https_enforced=true
gh repo edit nickstrom5/florida-eats --homepage https://florida.eatsranked.com/
```
The app's links (`FloridaEats/App/Links.swift`) stay github.io for build 1 (GitHub forwards them); switch them in the next update.
Change the website line in `13-app-review-reply.md` too.

## 3. eatsranked.com hub
`playbook/hub/`: the Florida entry and icon for `../eatsranked/`, with the steps.

## 4. App Store Connect (Nick creates the record in the web UI; the API can't)
- Register the App ID `com.floridaeats.ios` (Certificates, Identifiers & Profiles), or let Xcode's automatic signing do it on the
  first signed archive.
- New app: name "Florida Eats: Restaurants", bundle `com.floridaeats.ios`, SKU `floridaeats-ios`, primary language English (U.S.).
- Fill it in from `06-app-store-listing.md`. Put the privacy policy URL on the App Privacy page and choose "Data Not Collected". Untick
  "Sign-in required" and add a reviewer phone number. Price $0.00, availability United States. Age rating answers are in the listing file
  (13+).
- The version number must be 1.0.0 to match the build.
- Paste `13-app-review-reply.md`'s reply into App Review Information → Notes, and record the screen recording before submitting.
- Promotional text: switch to the stone crab season line on Oct 15 (no review needed).

## 5. Archive and upload (public Xcode only)
```bash
cd fl-eats && xcodegen generate   # from the claudecode folder
DEVELOPER_DIR="/Applications/Xcode 1.app/Contents/Developer" xcodebuild archive -project FloridaEats.xcodeproj -scheme FloridaEats \
  -destination 'generic/platform=iOS' -derivedDataPath ./DerivedData-xc27.0 -archivePath build/FloridaEats.xcarchive -allowProvisioningUpdates
/usr/libexec/PlistBuddy -c "Print :DTXcodeBuild" build/FloridaEats.xcarchive/Products/Applications/FloridaEats.app/Info.plist   # 27A…, not a beta build
DEVELOPER_DIR="/Applications/Xcode 1.app/Contents/Developer" xcodebuild -exportArchive -archivePath build/FloridaEats.xcarchive \
  -exportOptionsPlist scripts/ExportOptions-AppStore.plist -exportPath build/export -allowProvisioningUpdates
```
`scripts/ExportOptions-AppStore.plist` exports locally; set `destination` to `upload` to send the build (Nick's yes first). Bump
`CURRENT_PROJECT_VERSION` in `project.yml` for every upload. TestFlight: an internal group with Nick in it, using the Apple ID signed in on
his phone (see `13-app-review-reply.md`).

## 6. Before submitting (never submit without Nick's yes)
- Refresh DBPR (weekly files): `bash data/raw/dbpr/fetch.sh`, then `dbpr.py`, `geocode.py`, `calibrate.py` (see `CLAUDE.md`).
- Re-run `pipeline/check_websites.py`, rebuild with `FL_APP=1`, copy `places.json` and the `detail-*.json` files, rebuild the app.
- Unit tests, then the UI smoke test on "FL Eats 6.9" and "FL Eats iPad 13" (one simulator at a time).
- Screenshots: `docs/screenshots/` (iPhone 1320×2868) and `docs/screenshots/ipad-*` (2064×2752). Upload them one at a time in the order in
  `06-app-store-listing.md`. No Follow-Up or Closed result, and no inspections board, in any image.
- Recount the numbers in `06-app-store-listing.md`, `13-app-review-reply.md` and `hub/eatsranked-entry.json` from `site-numbers.json`.
