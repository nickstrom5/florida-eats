# Adding Florida to the eatsranked.com hub (not done: needs Nick's OK, and it's another repo)

The hub lives in `../eatsranked/` (repo nickstrom5/eatsranked). This session only worked in `fl-eats/`, so the change is prepared here:
1. Append `eatsranked-entry.json` to `"states"` in `eatsranked/tools/site-data.json`.
2. Copy `florida.png` (256×256, the stone crab claw icon) to `eatsranked/docs/icons/florida.png`.
3. Run `eatsranked/tools/build.py`, check, then commit and push with the no-reply email (Nick's yes first).
When florida.eatsranked.com resolves, change the three github.io URLs to https://florida.eatsranked.com/.
Check the counts in the tagline against `playbook/site-numbers.json` after a data refresh.
