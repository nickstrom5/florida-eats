# App Review: Guideline 2.1 "Information Needed" (prepared before the first submission)

Wisconsin's first submission (2026-09-28) got a 2.1 "Information Needed" because the developer account has a limited review
history: Apple asked for a screen recording from a physical device, starting at launch, and six answers. Put the reply below into
**App Review Information → Notes** from the first submission, and keep the recording ready to attach if Apple asks.

## Screen recording (Nick, on his iPhone, latest iOS)

The app must be on the phone first, through TestFlight: an internal group with Nick in it. The tester email must be the Apple ID
signed in under Settings › your name › Media & Purchases on the phone (otherwise TestFlight says "not available").
Record with Control Center → Screen Recording, 60–120 seconds, no sound needed:

1. Start on the Home Screen and tap **FL Eats**. The recording must begin with the launch.
2. Home: scroll the guide cards a little.
3. Tap **Cuban & Cafecito**, then tap **Sanguich De Miami**.
4. On the place: tap **Ratings, hours & photos**. Apple's place card opens. Close it.
5. Scroll to **Inspections · Florida DBPR**, then tap the **heart** (Save) and go back.
6. Back on Home, tap the search box and type `stone crab`. Open one result.
7. Tap the **Map** tab, then **Florida picks**, then a pin and its name.
8. Tap the **Saved** tab, where the saved place shows. Then tap **About** and scroll to the sources.

## Reply text (under 4,000 characters)

```
A screen recording from an iPhone running the latest iOS is attached. It starts at launch and shows the full flow.

1. Screen recording: attached. There is no account, login, user-generated content or paid content.

2. Purpose and audience: Florida Eats is a free guide to restaurants in Florida. Its focus is the state's food traditions: Cuban sandwiches and coffee windows, stone crabs, grouper sandwiches, Keys classics, oyster bars and Old Florida fish camps. 252 places on its guides, plus 217 MICHELIN and James Beard honorees, were checked by hand in October 2026 against a 2025 or 2026 source (the restaurant's own website or menu, local news, or an official tourism listing). It also lists 52,573 restaurants, cafés, bars and bakeries statewide, with the State of Florida's own inspection result for 48,584 licensed places. It is for Florida residents and visitors deciding where to eat. It shows sourced facts and the state's records, with no ads, account or tracking.

3. How to use it (no login, no setup, no sample files needed):
- Home → any guide card (Cuban & Cafecito, Stone Crabs, Oyster Bars, Inspections...) → tap any place.
- On a place, tap "Ratings, hours & photos" to open Apple Maps' own place card through MapKit. Directions, Call and Website are below it.
- Search from the Home search box by name, town, street or dish ("cuban sandwich tampa", "stone crab").
- The Map tab shows the guides as pins. "My location" and the Nearest sort use location only if allowed, on the device.
- The heart saves a place on the device (Saved tab). About lists sources, licenses and the independence statement. On iPad a sidebar replaces the tabs.
- Location: if you're outside Florida (as App Review usually is), the map says so and stays on Florida, and distance sorting still works from where you are.
- "FL Eats" is the short Home Screen name of "Florida Eats: Restaurants".

4. External services and data:
- Apple MapKit: maps, local search to find a place's Apple Maps listing, and Apple's place card for live hours, photos and ratings.
- Core Location: optional, on-device only, for distance sorting.
- Core Spotlight: on-device indexing so places appear in iPhone search.
- No backend, accounts, analytics, advertising, payments or AI services. The restaurant data is bundled in the app.
- Bundled data sources: the Florida Department of Business and Professional Regulation's public records (food service licenses, inspections and emergency closure reports, published under Chapter 119, Florida Statutes); Overture Maps Foundation open place data (CDLA Permissive 2.0, with Foursquare-sourced records under Apache 2.0 and AllThePlaces under CC0; license texts are in the app); the MICHELIN Guide Florida 2026 selection and James Beard Foundation award records (facts only); and our own research of restaurants' public websites, menus and local news.
- The website with the privacy policy and support page is static and hosted on GitHub Pages: https://nickstrom5.github.io/florida-eats/

5. Regional differences: none. The content covers Florida; the app is offered in the United States and works the same everywhere.

6. Regulated or protected material: the app is not in a regulated industry and includes no protected third-party material. The data is open-licensed or public record, with attribution and licenses on the About tab. Ratings, hours and photos are shown only inside Apple's own place card through MapKit, under Apple's terms; the app stores no ratings or reviews. Inspection results are shown exactly as the State of Florida records them (its disposition, its own result group and its violation counts, with dates); Florida doesn't grade restaurants and the app computes no grade. Every website link was checked before release, and adult venues are excluded. The app is independent and not affiliated with any restaurant, agency, the MICHELIN Guide or the James Beard Foundation.

Support: work-with-nick@gmail.com
```

Before pasting: if the site has moved to https://florida.eatsranked.com (Cloudflare record live, `FL_DOMAIN` set), change the website line.
Recount the numbers from `playbook/site-numbers.json` after any data refresh.

## If App Review cites Guideline 4.3(a) (Resolution Center only; never in the Notes)

Nick's call (2026-10-07, STATE_EATS_PLAYBOOK): submit Florida Eats as its own app and keep this answer ready. Don't volunteer a
comparison with the other state apps. If Apple still asks for one app, the fallback is a single multi-state app with a state picker (Nick
decides then). Wisconsin's first app was still in App Review on 2026-10-09; Nick may want to submit Florida after Wisconsin clears.
Recount the numbers below from `playbook/site-numbers.json` before sending.

```
Thank you for the review. Florida Eats is not a repackaged copy of another app. It is a guide built for Florida, from Florida's own
sources:
- Its guides are Florida's food traditions, each place checked by hand against a 2025 or 2026 source: Cuban sandwiches and cafecito
  windows, stone crabs in their Oct 15 – May 1 season, grouper sandwiches and seafood shacks, Keys classics like key lime pie and conch
  fritters, oyster bars, Old Florida fish camps and smoked fish, and the state's oldest restaurants.
- It shows the State of Florida's own restaurant inspection results (the Department of Business and Professional Regulation's
  dispositions and result groups, with dates) for 48,000+ licensed places, and Florida's emergency closure reports. Florida doesn't grade restaurants, and the app computes no grade.
- Its directory is built from Florida's public records (DBPR's food service licenses), placed on Florida's county boundaries, with
  restaurants inside Walt Disney World and Universal Orlando labeled as such.
- None of its places, research, guides or text is shared with any other app; the people who use it are in Florida or traveling there.
We're glad to answer any question about how the app works.
```
