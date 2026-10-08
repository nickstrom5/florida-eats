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
3. Tap **Cuban & Cafecito**, then tap any place.
4. On the place: tap **Ratings, hours & photos**. Apple's place card opens. Close it.
5. Scroll to **Inspections · Florida DBPR**, then tap the **heart** (Save) and go back.
6. Back on Home, tap the search box and type `stone crab`. Open one result.
7. Tap the **Map** tab, then **Florida picks**, then a pin and its name.
8. Tap the **Saved** tab, where the saved place shows. Then tap **About** and scroll to the sources.

## Reply text (under 4,000 characters)

```
Thank you. Here is the information requested. A screen recording from an iPhone running the latest iOS is attached. It starts at launch and shows the full flow.

1. Screen recording: attached. There is no account, login, user-generated content or paid content.

2. Purpose and audience: Florida Eats is a free guide to restaurants in Florida. Its focus is the state's food traditions: Cuban sandwiches and coffee windows, stone crabs, grouper sandwiches, Keys classics, oyster bars and Old Florida fish camps. 467 places were checked by hand in October 2026 against a 2025 or 2026 source (the restaurant's own website or menu, local news, or an official tourism listing). It also lists 52,790 restaurants, cafés, bars and bakeries statewide, with the State of Florida's own inspection result for each licensed place. It is for Florida residents and visitors deciding where to eat. It shows sourced facts and the state's records, with no ads, account or tracking.

3. How to use it (no login, no setup, no sample files needed):
- Home → any guide card (Cuban & Cafecito, Stone Crabs, Oyster Bars, Inspections...) → tap any place.
- On a place, tap "Ratings, hours & photos" to open Apple Maps' own place card through MapKit. Directions, Call and Website are below it.
- Search from the Home search box by name, town, street or dish ("cuban sandwich ybor", "stone crab").
- The Map tab shows the guides as pins. "My location" and the Nearest sort use location only if allowed, on the device.
- The heart saves a place on the device (Saved tab). About lists sources, licenses and the independence statement. On iPad a sidebar replaces the tabs.
- Location: if you're outside Florida (as App Review usually is), the map says so and stays on Florida, and distance sorting still works from where you are.
- "FL Eats" is the short Home Screen name of "Florida Eats: Restaurants".

4. External services and data:
- Apple MapKit: maps, local search to find a place's Apple Maps listing, and Apple's place card for live hours, photos and ratings.
- Core Location: optional, on-device only, for distance sorting.
- Core Spotlight: on-device indexing so places appear in iPhone search.
- No backend, accounts, analytics, advertising, payments or AI services. The restaurant data is bundled in the app.
- Bundled data sources: the Florida Department of Business and Professional Regulation's public records (food service licenses, inspections, emergency closure and disciplinary reports, published under Chapter 119, Florida Statutes); Overture Maps Foundation open place data (CDLA Permissive 2.0, with Foursquare-sourced records under Apache 2.0 and AllThePlaces under CC0; license texts are in the app); the MICHELIN Guide Florida 2026 selection and James Beard Foundation award records (facts only); and our own research of restaurants' public websites, menus and local news.
- The website with the privacy policy and support page is static and hosted on GitHub Pages: https://nickstrom5.github.io/florida-eats/

5. Regional differences: none. The content covers Florida; the app is offered in the United States and works the same everywhere.

6. Regulated or protected material: the app is not in a regulated industry and includes no protected third-party material. The data is open-licensed or public record, with attribution and licenses on the About tab. Ratings, hours and photos are shown only inside Apple's own place card through MapKit, under Apple's terms; the app stores no ratings or reviews. Inspection results are shown exactly as the State of Florida records them (its disposition, its own result group and its violation counts, with dates); Florida doesn't grade restaurants and the app computes no grade. Every website link was checked before release, and adult venues are excluded. The app is independent and not affiliated with any restaurant, agency, the MICHELIN Guide or the James Beard Foundation.

Support: work-with-nick@gmail.com
```

Before pasting: if the site has moved to https://florida.eatsranked.com (Cloudflare record live, `FL_DOMAIN` set), change the website line.
Recount the numbers from `playbook/site-numbers.json` after any data refresh.
