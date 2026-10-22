import XCTest
import CoreLocation
@testable import FloridaEats

@MainActor
final class FloridaEatsTests: XCTestCase {

    /// A tiny core file and two region detail files with the same shape as Resources/places.json and Resources/detail-*.json.
    private func sampleModel() async throws -> AppModel {
        let json = """
        {"v":2,"generated":"2026-10-07","overture_release":"2026-09-23.1","inspections_through":"2026-09-30","inspections_since":"2023-07-01","dbpr_fetched":"2026-10-07",
         "cities":["Miami","Tampa","Key West","St. Petersburg","Apalachicola","Orlando","Miami Beach"],
         "cuisines":["Latin & Caribbean","Seafood","Bar & Pub","Burgers","American & Other","Coffee & Café"],
         "brands":["Pollo Tropical"],"counties":["Miami-Dade","Hillsborough","Monroe","Pinellas","Franklin","Orange"],
         "regions":["South Florida","Keys","Space & Treasure Coast","Central","Tampa Bay","Southwest","Northeast","Panhandle"],
         "srcs":["official","meta","AllThePlaces","DAC","research"],
         "dispositions":["Call Back - Complied","Emergency order recommended","Inspection Completed - No Further Action","Warning Issued"],
         "itypes":["Complaint Full","Routine - Food"],"catnames":{"35":"No presence or breeding of insects/rodents/pests"},
         "count":10,"count_restaurants":9,
         "calibration":{"statewide":{"groups":{"meta_high|restaurant/bar":{"n":37023,"current":0.763,"any":0.771},
                                               "meta_high|cafe-type":{"n":3774,"current":0.407,"any":0.413}}}},
         "places":[
          {"id":"a","n":"Versailles Restaurant Cuban Cuisine","c":0,"co":0,"rg":0,"cu":0,"t":2,"s":1,"hc":1,"a":"3555 SW 8th St","z":"33135","la":25.7653,"lo":-80.2526,
           "g":1,"h":1,"ip":60,"jbf":"America's Classics 2001","dish":"Cuban sandwich; cafecito; croquetas","in":[0,"2026-08-01",1,2,3]},
          {"id":"b","n":"Joe's Stone Crab","c":6,"co":0,"rg":0,"cu":1,"t":2,"s":1,"hc":1,"a":"11 Washington Ave","la":25.7690,"lo":-80.1342,
           "g":130,"h":17,"mi":1,"ip":75,"f":1918,"seas":"Stone crab claws Oct 15 – May 1 (FWC season)","in":[0,"2026-05-08",1,1,4]},
          {"id":"c","n":"Pollo Tropical","c":0,"co":0,"rg":0,"cu":0,"t":2,"s":0,"b":0,"ch":120,"la":25.70,"lo":-80.30},
          {"id":"d","n":"Cuban Corner Cafe","c":1,"co":1,"rg":4,"cu":0,"t":0,"s":1,"a":"100 E 7th Ave","la":27.96,"lo":-82.44},
          {"id":"e","n":"Wawa","c":5,"co":5,"rg":3,"cu":4,"t":1,"s":1,"v":1,"la":28.54,"lo":-81.38},
          {"id":"f","n":"Hole in the Wall Seafood","c":4,"co":4,"rg":7,"cu":1,"t":2,"s":1,"hc":1,"a":"23 Avenue D","la":29.7255,"lo":-84.9830,"g":16,
           "dish":"Apalachicola oysters (in season)"},
          {"id":"g","n":"Ybor Grill","c":1,"co":1,"rg":4,"cu":4,"t":2,"s":0,"a":"1600 E 7th Ave","la":27.960,"lo":-82.437,"in":[2,"2026-09-10",2,1,1]},
          {"id":"h","n":"Kona Coffee Window","c":0,"co":0,"rg":0,"cu":5,"t":1,"s":1,"a":"200 SW 8th St","la":25.765,"lo":-80.199},
          {"id":"i","n":"Cinderella Castle Snacks","c":5,"co":5,"rg":3,"cu":4,"t":2,"s":0,"v":1,"dw":1,"la":28.4195,"lo":-81.5812},
          {"id":"j","n":"Blue Heaven","c":2,"co":2,"rg":1,"cu":1,"t":2,"s":1,"hc":1,"a":"729 Thomas St","la":24.5507,"lo":-81.8001,"g":8,
           "dish":"key lime pie; conch fritters","seas":"Closed Sept 8 – Oct 15 for its seasonal break","in":[1,"2026-07-15",3,0,6]}
         ]}
        """
        let south = """
        {"a":{"lic":"SEA2300001","ph":"(305) 444-0240","w":"versaillesrestaurant.com","in":{"dp":2,"t":1,"n":3,"eo":0,"rd":"2026-08-01","h":[["2026-08-01",1,2,1,2,3],["2026-02-01",1,3,4,1,2]]}},
         "b":{"lic":"SEA2300002","w":"javascript:alert(1)","in":{"dp":2,"t":1,"n":2,"eo":0,"rd":"2026-05-08","h":[["2026-05-08",1,2,1,1,4]]}},
         "c":{"lic":"SEA2300003"}}
        """
        let tampa = """
        {"g":{"lic":"SEA3900007","in":{"dp":1,"t":0,"n":2,"eo":1,"rd":"2026-03-01","h":[["2026-09-10",0,1,9,2,5],["2026-03-01",1,2,2,1,1]]},
              "cl":[["2026-09-10","Roach activity","2026-09-11"]]}}
        """
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("fl-test-\(UUID().uuidString)")
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let url = dir.appendingPathComponent("places.json")
        try json.data(using: .utf8)!.write(to: url)
        try south.data(using: .utf8)!.write(to: dir.appendingPathComponent("detail-south-florida.json"))
        try tampa.data(using: .utf8)!.write(to: dir.appendingPathComponent("detail-tampa-bay.json"))
        let model = AppModel(defaults: UserDefaults(suiteName: "test-\(UUID().uuidString)")!)
        await model.load(from: url, detailFolder: dir)
        XCTAssertTrue(model.isLoaded, model.loadError ?? "")
        return model
    }

    func testDecodesAndHidesNonRestaurantsByDefault() async throws {
        let m = try await sampleModel()
        XCTAssertEqual(m.places.count, 10)
        XCTAssertEqual(m.inspectionsThrough, "2026-09-30")
        XCTAssertEqual(m.dbprFetched, "2026-10-07")
        let all = m.list(.all, sort: .name, search: "", here: nil)
        XCTAssertFalse(all.contains { $0.name == "Wawa" }, "gas-station counters are hidden unless asked for")
        XCTAssertFalse(all.contains { $0.name == "Cinderella Castle Snacks" }, "theme-park carts are hidden with the non-restaurants")
        m.filters.includeNonRestaurants = true
        XCTAssertTrue(m.list(.all, sort: .name, search: "", here: nil).contains { $0.name == "Wawa" })
        XCTAssertTrue(m.place(id: "i")!.isThemePark)
    }

    func testGuidesListOnlyWhatTheyPromise() async throws {
        let m = try await sampleModel()
        XCTAssertEqual(m.list(.cuban, sort: .name, search: "", here: nil).map(\.id), ["a"],
                       "a listing merely named \u{201C}Cuban\u{201D} isn't hand-checked, so it stays out of the guide")
        XCTAssertEqual(m.list(.all, sort: .name, search: "cuban corner", here: nil).map(\.id), ["d"], "but it's still in the directory")
        XCTAssertEqual(m.list(.stoneCrab, sort: .name, search: "", here: nil).map(\.id), ["b"])
        XCTAssertEqual(m.list(.oyster, sort: .name, search: "", here: nil).map(\.id), ["f"])
        XCTAssertEqual(m.list(.keys, sort: .name, search: "", here: nil).map(\.id), ["j"])
        XCTAssertEqual(Set(m.list(.honors, sort: .iconic, search: "", here: nil).map(\.id)), ["a", "b"])
        XCTAssertEqual(m.list(.oldest, sort: .oldest, search: "", here: nil).map(\.id), ["b"])
        XCTAssertEqual(m.list(.nearMe, sort: .nearest, search: "", here: nil), [], "near me needs a location")
        for g in Guide.allCases where g.tag != nil {
            XCTAssertTrue(m.places.filter(g.includes).allSatisfy(\.handChecked), "\(g.title) lists only hand-checked places")
        }
    }

    /// DBPR's own result group is read from the record; a high violation count never turns into a computed result.
    func testInspectionResultsAreDBPRsAsRecorded() async throws {
        let m = try await sampleModel()
        let grill = m.place(id: "g")!.inspection!
        XCTAssertEqual(grill.g, .closed, "an emergency order is DBPR's Facility Temporarily Closed")
        XCTAssertEqual(grill.hp, 2, "the high-priority count shown is the latest ROUTINE inspection's")
        let grillDetail = await m.detail(for: m.place(id: "g")!)
        XCTAssertEqual(m.disposition(grillDetail!.inspection!.dp), "Emergency order recommended")
        XCTAssertEqual(m.visitType(grillDetail!.inspection!.t), "Complaint Full")
        XCTAssertEqual(grillDetail!.inspection!.h.count, 2)
        let heaven = m.place(id: "j")!.inspection!
        XCTAssertEqual(heaven.g, .followUp)
        XCTAssertEqual(InspectionResult.met.label, "Met Inspection Standards")
        XCTAssertEqual(InspectionResult.followUp.label, "Follow-Up Inspection Required")
        XCTAssertEqual(InspectionResult.closed.label, "Facility Temporarily Closed")
        XCTAssertEqual(m.list(.inspections, sort: .recent, search: "", here: nil).map(\.id), ["g", "a", "j", "b"])
        XCTAssertEqual(m.list(.inspections, sort: .mostHighPriority, search: "", here: nil).map(\.id), ["j", "g", "b", "a"])
        XCTAssertEqual(m.list(.inspections, sort: .fewestHighPriority, search: "", here: nil).map(\.id), ["b", "a", "g", "j"],
                       "equal high-priority counts break on intermediate + basic (5 and 5 here), then name")
        XCTAssertEqual(grillDetail!.closures.first?.reason, "Roach activity", "the closure reason is DBPR's own words")
        XCTAssertEqual(grillDetail!.closures.first?.reopened, "2026-09-11")
    }

    /// Calendar days stay the same day in every time zone, and read as dates, not ISO strings.
    func testDatesAreCalendarDays() {
        var utc = Calendar(identifier: .gregorian)
        utc.timeZone = TimeZone(identifier: "UTC")!
        let d = DayFormat.date("2026-06-16")!
        XCTAssertEqual(utc.dateComponents([.year, .month, .day], from: d), DateComponents(year: 2026, month: 6, day: 16))
        let text = DayFormat.text("2026-06-16")!
        XCTAssertTrue(text.contains("16") && text.contains("2026") && !text.contains("2026-06"), text)
        XCTAssertTrue(DayFormat.monthYear("2023-07-01")!.contains("2023"))
        XCTAssertNil(DayFormat.text(nil))
        XCTAssertEqual(DayFormat.text("soon"), "soon", "a value that isn't a date is shown as it is")
        XCTAssertNil(DayFormat.date("2026-13-01"))
        let tampa = CLLocation(latitude: 27.9506, longitude: -82.4572), miami = CLLocation(latitude: 25.7743, longitude: -80.1937)
        let mi = Int((tampa.distance(from: miami) / 1609.344).rounded())
        XCTAssertEqual(tampa.milesText(to: miami), mi.formatted() + " mi")
    }

    func testHonorsAreFactsWithTheirOwnLabels() async throws {
        let m = try await sampleModel()
        let joes = m.place(id: "b")!
        XCTAssertEqual(joes.michelin.label, "MICHELIN Recommended")
        XCTAssertTrue(joes.isHonored)
        XCTAssertEqual(m.place(id: "a")!.jamesBeardLabel, "America's Classic")
        XCTAssertNil(m.place(id: "d")!.michelin.label)
        let noDetail = await m.detail(for: m.place(id: "d")!)
        XCTAssertNil(noDetail?.lic, "no license matched means unknown, never \u{201C}unlicensed\u{201D}")
        XCTAssertEqual(joes.seasonal, "Stone crab claws Oct 15 – May 1 (FWC season)", "a seasonal place says so instead of looking closed")
    }

    /// A region's detail file is read once, on demand; a place keeps its own record; unsafe links are dropped.
    func testRegionDetailsLoadOnDemand() async throws {
        let m = try await sampleModel()
        let v = await m.detail(for: m.place(id: "a")!)
        XCTAssertEqual(v?.lic, "SEA2300001")
        XCTAssertEqual(v?.website?.absoluteString, "https://versaillesrestaurant.com", "a bare host gets https://")
        XCTAssertEqual(v?.ph, "(305) 444-0240")
        let joes = await m.detail(for: m.place(id: "b")!)
        XCTAssertNil(joes?.website, "a javascript: link never becomes a website button")
        XCTAssertEqual(AppModel.regionSlug("Space & Treasure Coast"), "space-treasure-coast")
        let missing = await m.detail(for: m.place(id: "f")!)
        XCTAssertNil(missing, "a region with no detail file reads as no detail, not a crash")
    }

    func testNearestSort() async throws {
        let m = try await sampleModel()
        let littleHavana = CLLocation(latitude: 25.7655, longitude: -80.2500)
        let near = m.list(.nearMe, sort: .nearest, search: "", here: littleHavana)
        XCTAssertEqual(near.first?.id, "a", "Versailles is closest to Calle Ocho")
        let ids = near.map(\.id)
        XCTAssertLessThan(ids.firstIndex(of: "b")!, ids.firstIndex(of: "f")!, "Miami Beach comes before Apalachicola")
    }

    func testSearchWordStartsTownsGuidesAndDishes() async throws {
        let m = try await sampleModel()
        func ids(_ q: String) -> [String] { m.list(.all, sort: .name, search: q, here: nil).map(\.id) }
        XCTAssertEqual(ids("versail"), ["a"])
        XCTAssertTrue(ids("ersailles").isEmpty, "matches the start of words only")
        XCTAssertEqual(ids("joes"), ["b"], "apostrophes don't matter")
        XCTAssertEqual(ids("southwest 8th street"), ["a", "h"].sorted { m.place(id: $0)!.sortKey < m.place(id: $1)!.sortKey },
                       "southwest/street match the abbreviated address")
        XCTAssertEqual(ids("croquetas"), ["a"], "a hand-checked dish is searchable")
        XCTAssertEqual(Search.parse("cuban sandwich", towns: [:]).tag, .cuban)
        XCTAssertNil(Search.parse("croquetas", towns: [:]).tag, "\u{201C}croquetas\u{201D} is a dish, not the whole Cuban guide")
        XCTAssertEqual(ids("stone crab"), ["b"])
        XCTAssertEqual(ids("key west"), ["j"])
        XCTAssertEqual(ids("monroe"), ["j"], "the county is searchable")
        XCTAssertEqual(ids("🍕"), [], "nothing searchable typed means no results, not everything")
        XCTAssertEqual(ids("!!! ?"), [])
    }

    func testFiltersSavedPlacesAndMatchRates() async throws {
        let m = try await sampleModel()
        m.filters.hideChains = true
        XCTAssertFalse(m.list(.all, sort: .name, search: "", here: nil).contains { $0.name == "Pollo Tropical" })
        m.filters = Filters(confirmedOnly: true)
        XCTAssertFalse(m.list(.all, sort: .name, search: "", here: nil).contains { $0.id == "d" }, "single listings drop out")
        m.filters = Filters(town: "Tampa")
        XCTAssertEqual(Set(m.list(.all, sort: .name, search: "", here: nil).map(\.id)), ["d", "g"])
        m.filters = Filters()
        let p = m.place(id: "b")!
        m.toggleSaved(p)
        XCTAssertEqual(m.savedPlaces.map(\.id), ["b"])
        m.toggleSaved(p)
        XCTAssertTrue(m.savedPlaces.isEmpty)
        XCTAssertEqual(m.matchRate(for: m.place(id: "h")!), "41%", "a café cites the café-type rate (FDACS licenses many cafés)")
        XCTAssertNil(m.matchRate(for: m.place(id: "a")!), "licensed places don't cite a listing rate")
        XCTAssertEqual(m.place(id: "a")!.tier, .licensed)
    }

    func testNearMeIsntASearchWord() {
        let q = Search.parse("stone crab near me", towns: ["melbourne": "Melbourne"])
        XCTAssertEqual(q.tag, .stoneCrab)
        XCTAssertNil(q.town)
        XCTAssertTrue(q.tokens.isEmpty, "\"me\" mustn't match Melbourne or Mexican places")
    }

    /// The one-pass normalize must agree with the regex version it replaced, on tricky strings and every bundled name and address.
    func testNormalizeMatchesTheRegexVersion() async throws {
        func reference(_ s: String) -> String {
            var t = s.folding(options: [.diacriticInsensitive, .caseInsensitive], locale: .init(identifier: "en_US")).lowercased()
            t = t.replacingOccurrences(of: #"\b([a-z0-9])\s*&\s*([a-z0-9])\b"#, with: "$1$2", options: .regularExpression)
            t = t.replacingOccurrences(of: "&", with: " and ")
            t = t.replacingOccurrences(of: #"['’`]"#, with: "", options: .regularExpression)
            t = t.replacingOccurrences(of: #"[^\p{L}\p{N}]+"#, with: " ", options: .regularExpression)
            return t.trimmingCharacters(in: .whitespaces)
        }
        for s in ["Joe's Stone Crab", "B&B Cafe", "Café La Trova", "  Phở 88!! ", "Ted Peters’", "Joe`s", "A&W", "½ Price",
                  "#vybe", "Doña Sofía", "3555 SW 8th St #100", "🍕 Pizza", "Ⅻ Club", "", "---"] {
            XCTAssertEqual(Search.normalize(s), reference(s), s)
        }
        let m = AppModel(defaults: UserDefaults(suiteName: "norm-\(UUID().uuidString)")!)
        await m.load()
        for p in m.places.prefix(20_000) {
            XCTAssertEqual(Search.normalize(p.name), reference(p.name), p.name)
            XCTAssertEqual(Search.normalize(p.fullAddress), reference(p.fullAddress), p.fullAddress)
        }
    }

    /// The real bundled file decodes and holds the guides the app promises.
    func testBundledData() async throws {
        let m = AppModel(defaults: UserDefaults(suiteName: "bundle-\(UUID().uuidString)")!)
        await m.load()
        XCTAssertTrue(m.isLoaded, m.loadError ?? "")
        XCTAssertGreaterThan(m.restaurantCount, 45_000)
        XCTAssertGreaterThan(m.count(.cuban), 40)
        XCTAssertGreaterThan(m.count(.oyster), 40)
        XCTAssertGreaterThan(m.count(.stoneCrab), 15)
        XCTAssertGreaterThan(m.count(.honors), 180)
        XCTAssertGreaterThan(m.count(.inspections), 40_000)
        XCTAssertEqual(Set(m.places.map(\.id)).count, m.places.count, "ids are unique")
        for g in Guide.allCases where g.tag != nil {
            XCTAssertTrue(m.places.filter(g.includes).allSatisfy(\.handChecked), "\(g.title) lists only hand-checked places")
        }
        XCTAssertTrue(m.places.contains { $0.name == "Joe's Stone Crab" && $0.jamesBeardLabel == "America's Classic" })
        XCTAssertTrue(m.places.contains { $0.michelin == .twoStars }, "two MICHELIN two-star places (L'Atelier de Joël Robuchon, Sorekara)")
        // a known hand-checked place survives duplicate merging with its check (Wisconsin lost a fish fry that way), and a chain store is
        // never renamed after a researched place at its address (the address-only match put "Paddy's Raw Bar" on a Subway)
        XCTAssertFalse(m.places.contains { $0.name == "Paddy's Raw Bar" && $0.brand != nil })
        XCTAssertTrue(m.list(.cuban, sort: .name, search: "versailles", here: nil).contains { $0.city == "Miami" })
        XCTAssertTrue(m.list(.all, sort: .name, search: "cafe versailles calle", here: nil).contains { $0.name == "Versailles" },
                      "the listing's old name still finds it")
        // verified closed places are gone, whatever the map listings say
        XCTAssertFalse(m.places.contains { $0.name.hasPrefix("Shuckers") && $0.city == "North Bay Village" })
        // no Google-derived data: the data file has no rating, review or price fields at all
        let raw = try String(contentsOf: Bundle.main.url(forResource: "places", withExtension: "json")!, encoding: .utf8)
        for key in ["\"rating\"", "\"reviews\"", "\"price\"", "\"gmap_id\""] { XCTAssertFalse(raw.contains(key), "\(key) must not ship") }
    }

    /// Stable ids: md5(license or name + ~100 m cell)[:12], never a row number, so saved places survive a rebuild; every bundled
    /// region detail file decodes and its ids are core ids.
    func testIdsAndBundledDetailFiles() async throws {
        let m = AppModel(defaults: UserDefaults(suiteName: "ids-\(UUID().uuidString)")!)
        await m.load()
        XCTAssertTrue(m.places.allSatisfy { $0.id.count >= 12 && $0.id.prefix(12).allSatisfy(\.isHexDigit) && $0.id.dropFirst(12).allSatisfy { $0 == "x" } })
        let ids = Set(m.places.map(\.id))
        var licensed = 0
        for region in Set(m.places.compactMap(\.region)) {
            let url = try XCTUnwrap(Bundle.main.url(forResource: "detail-" + AppModel.regionSlug(region), withExtension: "json"), region)
            let d = try JSONDecoder().decode([String: PlaceDetail].self, from: Data(contentsOf: url))
            XCTAssertTrue(Set(d.keys).isSubset(of: ids), "\(region) detail ids are core ids")
            licensed += d.values.filter { $0.lic != nil }.count
        }
        XCTAssertGreaterThan(licensed, 40_000, "most places carry their DBPR license number")
        let v = try XCTUnwrap(m.places.first { $0.name == "Versailles" && $0.city == "Miami" }, "the hand-checked name wins over a listing's")
        let detail = await m.detail(for: v)
        XCTAssertNotNil(detail?.lic)
        XCTAssertFalse((detail?.inspection?.h ?? []).isEmpty, "Versailles has DBPR inspections")
    }

    func testBundledDataGuards() async throws {
        let m = AppModel(defaults: UserDefaults(suiteName: "guards-\(UUID().uuidString)")!)
        await m.load()
        XCTAssertTrue(m.isLoaded, m.loadError ?? "")
        XCTAssertEqual(DataGuards.adultVenues(m.places), [], "no strip club under its name")
        XCTAssertEqual(DataGuards.adultLicensed(try DataGuards.bundledLicenses(m.places)), [], "no strip club under a plain trade name (data/research/adult_venues.json)")
        XCTAssertEqual(DataGuards.badWebsites(try DataGuards.bundledLinks(m.places)), [], "no directory, Google or news page as a restaurant's website")
        XCTAssertEqual(DataGuards.badNames(m.places), [], "no visible name ending in \u{201C} the\u{201D} or \u{201C} of\u{201D}, or just \u{201C}The\u{201D}")
        XCTAssertEqual(DataGuards.legalNames(m.places), [], "no licensee entity name (\u{201C}… LLC\u{201D}, \u{201C}… INC\u{201D}) shown as a place's name")
        XCTAssertEqual(DataGuards.nonRestaurants(m.places), [], "no nail salon, senior home, gun store or gas station among the restaurants")
    }

    /// Each guard above fires on a copy of the bundled data broken the way QA found it elsewhere: a guard that can't fail guards nothing.
    func testGuardsCatchABrokenCopy() async throws {
        let raw = try Data(contentsOf: Bundle.main.url(forResource: "places", withExtension: "json")!)
        var file = try XCTUnwrap(JSONSerialization.jsonObject(with: raw) as? [String: Any])
        var places = try XCTUnwrap(file["places"] as? [[String: Any]])
        let idx = places.indices.filter { places[$0]["v"] == nil }.prefix(6).map { $0 }
        places[idx[2]]["n"] = "Scores Gentlemen's Club"
        places[idx[3]]["n"] = "Kitchen the"
        places[idx[4]]["n"] = "SUNSHINE HOSPITALITY GROUP LLC"
        places[idx[5]]["n"] = "Tipsy Nails & Spa"
        file["places"] = places
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("places-broken.json")
        try JSONSerialization.data(withJSONObject: file).write(to: url)
        let m = AppModel(defaults: UserDefaults(suiteName: "broken-\(UUID().uuidString)")!)
        await m.load(from: url)
        XCTAssertTrue(m.isLoaded, m.loadError ?? "")
        let id = idx.map { places[$0]["id"] as? String }
        func caught(_ found: [String], _ i: Int, _ what: String) {
            XCTAssertTrue(found.contains { $0.contains("[\(id[i] ?? "?")]") }, "the guard missed \(what)")
        }
        let links = [(name: "A", id: "x1", url: "https://www.yelp.com/biz/some-place"), (name: "B", id: "x2", url: "https://www.miaminewtimes.com/restaurants/a-story-123"),
                     (name: "C", id: "x3", url: "https://smart.com/menu")]
        XCTAssertEqual(DataGuards.badWebsites(links).count, 2, "the guard catches a Yelp page and a news story, and not smart.com")
        XCTAssertEqual(DataGuards.adultLicensed(["x1": "SEA1102230", "x2": "SEA2300159"]), ["x1: SEA1102230"], "the guard catches Cafe Risque's license, and not Akashi's")
        caught(DataGuards.adultVenues(m.places), 2, "a gentlemen's club")
        caught(DataGuards.badNames(m.places), 3, "\u{201C}Kitchen the\u{201D}")
        caught(DataGuards.legalNames(m.places), 4, "a licensee entity name")
        caught(DataGuards.nonRestaurants(m.places), 5, "a nail salon shown as a restaurant")
    }
}

/// Checks on the bundled data, written as functions so testGuardsCatchABrokenCopy can prove each one fires.
enum DataGuards {
    /// directories, Google and news sites: matched on the link's host, so "smart.com" isn't "rt.com"
    static let badHosts = #"^https?://([^/?#]*\.)?(yelp\.com|business\.site|google\.com|groupon\.com|yellowpages\.com|tripadvisor\.com|miaminewtimes\.com|miamiherald\.com|tampabay\.com|orlandosentinel\.com|eater\.com|rt\.com)([:/?#]|$)"#

    static func badWebsites(_ links: [(name: String, id: String, url: String)]) -> [String] {
        links.compactMap { l in
            guard l.url.range(of: badHosts, options: [.regularExpression, .caseInsensitive]) != nil else { return nil }
            return "\(l.name) [\(l.id)]: \(l.url)"
        }
    }

    /// every website link in the bundled region detail files, with its place's name
    static func bundledLinks(_ places: [Place]) throws -> [(name: String, id: String, url: String)] {
        let names = Dictionary(places.map { ($0.id, $0.name) }, uniquingKeysWith: { a, _ in a })
        var out: [(name: String, id: String, url: String)] = []
        for region in Set(places.compactMap(\.region)) {
            guard let url = Bundle.main.url(forResource: "detail-" + AppModel.regionSlug(region), withExtension: "json") else { continue }
            for (id, d) in try JSONDecoder().decode([String: PlaceDetail].self, from: Data(contentsOf: url)) {
                if let w = d.website?.absoluteString { out.append((names[id] ?? "?", id, w)) }
            }
        }
        return out
    }

    static let adultNames = #"gentlem[ae]n['’]?s club|strip club|exotic dancer|cabaret|\bscores\b|^tootsies$|tootsie['’]?s cabaret|king of diamonds|booby trap|e11even|cafe risqu|diamond dolls|playmates|penthouse club|gold club|showgirls|pure nude|naturally nude|vixens|teasers|peppermint hippo|climaxxx|g5ive|mons venus|thee dollhouse"#

    /// strip clubs that hold an ordinary food service license under a plain trade name ("Sunset Eatery", "Italian beef"): their DBPR
    /// license numbers, from data/research/adult_venues.json (checked 2026-10-08)
    static let adultLicenses: Set<String> = ["NOS5816416", "SEA1102230", "SEA1305892", "SEA1506974", "SEA1600321", "SEA1608112", "SEA1608490", "SEA1609428", "SEA1617724", "SEA1621854", "SEA1621877", "SEA1622800", "SEA1623304", "SEA1624280", "SEA2315104", "SEA2322140", "SEA2323366", "SEA2325206", "SEA2326196", "SEA2328638", "SEA2333496", "SEA2334078", "SEA2334385", "SEA2335402", "SEA2336319", "SEA2336951", "SEA2609854", "SEA2612663", "SEA2614869", "SEA2706560", "SEA3901908", "SEA3911313", "SEA3918668", "SEA4606920", "SEA5807352", "SEA6008072", "SEA6013191", "SEA6020971", "SEA6100823", "SEA6102505", "SEA6211563", "SEA6214485", "SEA6217540", "SEA6218147", "SEA6218183", "SEA7407691"]

    static func adultLicensed(_ licByID: [String: String]) -> [String] {
        licByID.filter { adultLicenses.contains($0.value) }.map { "\($0.key): \($0.value)" }.sorted()
    }

    /// every DBPR license number in the bundled region detail files, by place id
    static func bundledLicenses(_ places: [Place]) throws -> [String: String] {
        var out: [String: String] = [:]
        for region in Set(places.compactMap(\.region)) {
            guard let url = Bundle.main.url(forResource: "detail-" + AppModel.regionSlug(region), withExtension: "json") else { continue }
            for (id, d) in try JSONDecoder().decode([String: PlaceDetail].self, from: Data(contentsOf: url)) {
                if let lic = d.lic { out[id] = lic }
            }
        }
        return out
    }

    static func adultVenues(_ places: [Place]) -> [String] {
        places.filter { $0.name.range(of: adultNames, options: [.regularExpression, .caseInsensitive]) != nil }.map { "\($0.name) [\($0.id)]" }
    }

    /// a name cut off after "the" or "of" ("Kitchen the", "Wines of") or nothing but "The", among the places shown by default
    static func badNames(_ places: [Place]) -> [String] {
        places.filter { p in
            let n = p.name.trimmingCharacters(in: .whitespaces).lowercased()
            return !p.isVenue && (n.hasSuffix(" the") || n.hasSuffix(" of") || n == "the")
        }.map { "\($0.name) [\($0.id)]" }
    }

    /// DBPR's licensee name is never shown; a business name that's still a legal entity shouldn't be either
    static let legalSuffix = #"\b(llc|l\.l\.c|inc|corp|corporation)\.?$"#

    static func legalNames(_ places: [Place]) -> [String] {
        places.filter { !$0.isVenue && $0.name.range(of: legalSuffix, options: [.regularExpression, .caseInsensitive]) != nil }
            .map { "\($0.name) [\($0.id)]" }
    }

    /// businesses that aren't places to eat, among the places shown by default
    static let nonRestaurantNames = #"\bnails?\b|assisted living|gun (?:club|range|shop|store)|shooting range|firearms|petroleum|\bauto (?:repair|parts)\b"#

    static func nonRestaurants(_ places: [Place]) -> [String] {
        places.filter { !$0.isVenue && $0.name.range(of: nonRestaurantNames, options: [.regularExpression, .caseInsensitive]) != nil }
            .map { "\($0.name) [\($0.id)]" }
    }
}

/// pipeline/website_blocklist.json (hacked, taken-over, expired or another business's sites, confirmed by hand in the link sweeps):
/// no link on it may ship in any field of any JSON file the app bundles. The 2026-10-19 QA found the export had only filtered the
/// website field, or nothing, so hijacked links were still in the bundle. Read from the repo, so a new entry needs no code change.
final class LinkBlocklistTests: XCTestCase {
    func testNoBlocklistedLinkInBundledData() throws {
        let entries = try LinkBlocklist.entries()
        XCTAssertFalse(entries.isEmpty, "the blocklist is missing or empty")
        let files = LinkBlocklist.bundledJSON()
        XCTAssertFalse(files.isEmpty, "no bundled JSON found")
        var hits: [String] = []
        for url in files {
            let text = try String(contentsOf: url, encoding: .utf8)
            hits += LinkBlocklist.hits(in: text, entries).map { "\(url.lastPathComponent): \($0)" }
        }
        XCTAssertEqual(hits, [], "blocklisted links in the app's bundled data")
    }

    /// The guard fires on a copy of the bundled data broken three ways: a blocklisted domain, its subdomain, and a "url" entry.
    func testBlocklistGuardCatchesABrokenCopy() throws {
        let entries = try LinkBlocklist.entries()
        let file = try XCTUnwrap(LinkBlocklist.bundledJSON().max { (try? $0.resourceValues(forKeys: [.fileSizeKey]).fileSize ?? 0) ?? 0 < (try? $1.resourceValues(forKeys: [.fileSizeKey]).fileSize ?? 0) ?? 0 })
        let text = try String(contentsOf: file, encoding: .utf8)
        let domain = try XCTUnwrap(entries.first { ($0["match"] as? String ?? "domain") == "domain" }?["domain"] as? String)
        let fake: [[String: Any]] = entries + [["match": "url", "url": "https://example.org/hacked-page"]]
        let before = LinkBlocklist.hits(in: text, fake).count
        let broken = text + "{\"w\":\"https://www.\(domain)/menu\"}{\"src\":\"http://shop.\(domain)/\"}{\"w\":\"https://example.org/hacked-page/\"}"
        XCTAssertEqual(LinkBlocklist.hits(in: broken, fake).count, before + 3, "a domain, a subdomain and a url entry are all caught")
        XCTAssertEqual(LinkBlocklist.hits(in: "{\"w\":\"https://not\(domain)/\"}", entries), [], "a host that only ends with the domain's letters isn't it")
    }
}

enum LinkBlocklist {
    static func entries() throws -> [[String: Any]] {
        let url = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("pipeline/website_blocklist.json")
        return try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [[String: Any]])
    }

    /// every .json file in the app bundle, subfolders included
    static func bundledJSON() -> [URL] {
        let root = Bundle.main.bundleURL
        let all = FileManager.default.enumerator(at: root, includingPropertiesForKeys: nil)?.allObjects as? [URL] ?? []
        return all.filter { $0.pathExtension == "json" && !$0.path.contains("/PlugIns/") }
    }

    private static func host(_ u: URLComponents) -> String {
        var h = (u.host ?? "").lowercased()
        if h.hasSuffix(".") { h.removeLast() }
        return h.hasPrefix("www.") ? String(h.dropFirst(4)) : h
    }

    private static func trimmedPath(_ p: String) -> String { p.hasSuffix("/") ? String(p.dropLast()) : p }

    /// the links in a JSON text that an entry covers: a "domain" entry its domain and subdomains, a "url" entry that page only
    static func hits(in text: String, _ entries: [[String: Any]]) -> [String] {
        let t = text.replacingOccurrences(of: "\\/", with: "/")
        let rx = try! NSRegularExpression(pattern: #"https?://[^"\s\\]+"#, options: [.caseInsensitive])
        return rx.matches(in: t, range: NSRange(t.startIndex..., in: t)).compactMap { m -> String? in
            let s = String(t[Range(m.range, in: t)!])
            guard let u = URLComponents(string: s) else { return nil }
            let h = host(u)
            for e in entries {
                if (e["match"] as? String ?? "domain") == "url" {
                    guard let v = URLComponents(string: e["url"] as? String ?? "") else { continue }
                    if !h.isEmpty && h == host(v) && trimmedPath(u.path) == trimmedPath(v.path) { return s }
                } else {
                    var d = (e["domain"] as? String ?? "").lowercased()
                    if let r = d.range(of: "://") { d = String(d[r.upperBound...]) }
                    d = String(d.split(separator: "/").first ?? "")
                    if d.hasPrefix("www.") { d = String(d.dropFirst(4)) }
                    if !d.isEmpty && (h == d || h.hasSuffix("." + d)) { return s }
                }
            }
            return nil
        }
    }
}

/// QA 2026-10-19, P1 3a: the support address is nick@eatsranked.com (Nick, 2026-10-12). The old Gmail address must not come back
/// anywhere in the app's source or bundled files.
final class SupportEmailTests: XCTestCase {
    func testSupportEmailIsEatsRanked() {
        XCTAssertEqual(Links.supportEmail, "nick@eatsranked.com")
    }

    func testNoGmailInAppSource() throws {
        let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("FloridaEats")
        XCTAssertGreaterThan(SupportEmailScan.textFiles(under: root).count, 5, "the app's source folder wasn't found")
        XCTAssertEqual(SupportEmailScan.hits(under: root), [], "the app's source still has a Gmail address")
    }

    /// The guard fires on a broken copy: a folder with one planted Gmail address.
    func testGmailGuardCatchesABrokenCopy() throws {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: dir.appendingPathComponent("App"), withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: dir) }
        try "static let supportEmail = \"someone@GMAIL.com\"\n".write(to: dir.appendingPathComponent("App/Links.swift"), atomically: true, encoding: .utf8)
        try "{\"ok\": \"nick@eatsranked.com\"}".write(to: dir.appendingPathComponent("App/data.json"), atomically: true, encoding: .utf8)
        XCTAssertEqual(SupportEmailScan.hits(under: dir), ["App/Links.swift"])
    }
}

enum SupportEmailScan {
    static let textExtensions: Set<String> = ["swift", "plist", "json", "strings", "xcstrings", "xcprivacy", "md", "txt", "html", "entitlements"]

    static func textFiles(under root: URL) -> [URL] {
        let all = FileManager.default.enumerator(at: root, includingPropertiesForKeys: nil)?.allObjects as? [URL] ?? []
        return all.filter { textExtensions.contains($0.pathExtension.lowercased()) }
    }

    /// paths (relative to root) of text files that mention gmail.com, in any case
    static func hits(under root: URL) -> [String] {
        let base = root.resolvingSymlinksInPath().path + "/"
        return textFiles(under: root).compactMap { url in
            guard let text = try? String(contentsOf: url, encoding: .utf8),
                  text.range(of: "gmail.com", options: .caseInsensitive) != nil else { return nil }
            return url.resolvingSymlinksInPath().path.replacingOccurrences(of: base, with: "")
        }.sorted()
    }
}

/// QA 2026-10-19, P1 #13: outbound links ship without tracking tags (ref=google, referrer=google_food_ordering, cn_channel, utm_* …).
/// pipeline/tracking_params.py strips them in the export; these are the same rules.
final class TrackingParamTests: XCTestCase {
    func testNoTrackingParametersInBundledLinks() throws {
        let files = TrackingParams.bundledJSON()
        XCTAssertFalse(files.isEmpty, "no bundled JSON found")
        var hits: [String] = []
        for url in files {
            let text = try String(contentsOf: url, encoding: .utf8)
            hits += TrackingParams.tracked(in: text).map { "\(url.lastPathComponent): \($0)" }
        }
        XCTAssertEqual(hits, [], "links with tracking parameters in the app's bundled data")
    }

    /// The guard fires on a broken copy (four kinds of tracking tag, one in escaped JSON) and leaves a store's own parameters alone.
    func testTrackingGuardCatchesABrokenCopy() {
        let broken = #"[{"w":"https:\/\/places.example.com\/menu?ref=google"},{"w":"https://a.example/?utm_source=gmb&store=4"},"#
            + #"{"w":"https://b.example/x?referrer=google_food_ordering"},{"w":"https://c.example/order/1?cn_channel=cn_google"}]"#
        XCTAssertEqual(TrackingParams.tracked(in: broken).count, 4)
        let clean = #"[{"w":"https://order.example.com/menu?restaurantId=51&location=7"},{"w":"https://shop.example.com/?cid=12&ref=gs"}]"#
        XCTAssertEqual(TrackingParams.tracked(in: clean), [])
    }
}

enum TrackingParams {
    /// tracking by name, whatever the value
    static let keys = try! NSRegularExpression(pattern: #"^(?:utm[_-].*|gclid|gbraid|wbraid|dclid|fbclid|msclkid|mc_cid|mc_eid|_ga|_gl|igsh|"#
        + #"igshid|mibextid|srsltid|cn_channel|y_source|rwg_token|olonwp|ost_redirect_attribution|cmpid|yext_?.*)$"#, options: [.caseInsensitive])
    /// tracking only with these values
    static let values: [String: String] = ["ref": #"^(?:google|gmb|gbp|yext|bookmarks)\b"#, "referrer": "^google",
                                           "source": #"^(?:google|gmb|gbp|yext)\b"#, "cid": "^RF:YXT", "cmp": "^OKC-"]

    /// every .json file in the app bundle, subfolders included
    static func bundledJSON() -> [URL] {
        let all = FileManager.default.enumerator(at: Bundle.main.bundleURL, includingPropertiesForKeys: nil)?.allObjects as? [URL] ?? []
        return all.filter { $0.pathExtension == "json" && !$0.path.contains("/PlugIns/") }
    }

    static func isTracking(_ key: String, _ value: String) -> Bool {
        let k = key.trimmingCharacters(in: .whitespaces)
        if keys.firstMatch(in: k, range: NSRange(k.startIndex..., in: k)) != nil { return true }
        guard let pattern = values[k.lowercased()] else { return false }
        return value.trimmingCharacters(in: .whitespaces).range(of: pattern, options: [.regularExpression, .caseInsensitive]) != nil
    }

    /// links in a JSON text whose query carries a tracking parameter
    static func tracked(in text: String) -> [String] {
        let t = text.replacingOccurrences(of: "\\/", with: "/")
        let rx = try! NSRegularExpression(pattern: #"https?://[^\s"'<>\\]+"#)
        return rx.matches(in: t, range: NSRange(t.startIndex..., in: t)).compactMap { m -> String? in
            let s = String(t[Range(m.range, in: t)!])
            guard let q = s.split(separator: "?", maxSplits: 1).dropFirst().first else { return nil }
            let query = q.split(separator: "#", maxSplits: 1, omittingEmptySubsequences: false).first ?? ""
            for part in query.split(separator: "&") {
                let kv = part.split(separator: "=", maxSplits: 1, omittingEmptySubsequences: false)
                let k = String(kv[0]).replacingOccurrences(of: "+", with: " ").removingPercentEncoding ?? String(kv[0])
                let v = kv.count > 1 ? (String(kv[1]).replacingOccurrences(of: "+", with: " ").removingPercentEncoding ?? String(kv[1])) : ""
                if isTracking(k, v) { return s }
            }
            return nil
        }
    }
}
