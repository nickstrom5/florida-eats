import Foundation
import CoreLocation
import SwiftUI

// MARK: - The bundled data (Resources/places.json + Resources/detail-<region>.json), written by pipeline/florida.py with FL_APP=1
// places.json is the statewide core every screen needs at launch; a region's detail file (inspection history, closures, license,
// phone, website) is read only when one of its places opens. One statewide file with everything was 24 MB.

/// The core file's header (everything but the places). Read with JSONSerialization, not Codable: 57,000 keyed records through
/// JSONDecoder kept a Debug launch on a busy Mac at 18 s.
struct DataFile {
    let generated: String
    /// the Overture Maps release the listings come from ("2026-09-23.1")
    let overture_release: String?
    /// DBPR's files were downloaded on this day; inspections and closures are cut a week earlier (publication lag)
    let dbpr_fetched: String
    let inspections_through: String
    /// the first day of the inspection records kept ("2023-07-01": three DBPR fiscal years plus this one)
    let inspections_since: String?
    let cities: [String]
    let cuisines: [String]
    let brands: [String]
    let counties: [String]
    /// the eight regions the detail files are split by ("South Florida", "Keys", ...); a place's `rg` indexes this
    let regions: [String]
    let srcs: [String]
    /// DBPR's dispositions, verbatim ("Inspection Completed - No Further Action"), and visit types ("Routine - Food")
    let dispositions: [String]
    let itypes: [String]
    /// DBPR's violation category names (since 2013), keyed "1"..."58"
    let catnames: [String: String]?
    let count_restaurants: Int
    let calibration: Calibration

    struct Malformed: LocalizedError { let field: String; var errorDescription: String? { "the data file is missing \(field)" } }

    init(json r: [String: Any]) throws {
        func str(_ k: String) throws -> String { guard let v = r[k] as? String else { throw Malformed(field: k) }; return v }
        func list(_ k: String) throws -> [String] { guard let v = r[k] as? [String] else { throw Malformed(field: k) }; return v }
        generated = try str("generated")
        overture_release = r["overture_release"] as? String
        dbpr_fetched = try str("dbpr_fetched")
        inspections_through = try str("inspections_through")
        inspections_since = r["inspections_since"] as? String
        cities = try list("cities"); cuisines = try list("cuisines"); brands = try list("brands"); counties = try list("counties")
        regions = (r["regions"] as? [String]) ?? []
        srcs = try list("srcs"); dispositions = try list("dispositions"); itypes = try list("itypes")
        catnames = r["catnames"] as? [String: String]
        guard let n = r["count_restaurants"] as? Int else { throw Malformed(field: "count_restaurants") }
        count_restaurants = n
        let cal = (r["calibration"] as? [String: Any]).flatMap { try? JSONSerialization.data(withJSONObject: $0) }
        calibration = cal.flatMap { try? JSONDecoder().decode(Calibration.self, from: $0) } ?? Calibration(statewide: nil)
    }
}

/// How often listings of one kind matched a current DBPR license, statewide (pipeline/calibrate.py).
struct Calibration: Decodable, Hashable {
    let statewide: CalibrationScope?
}

struct CalibrationScope: Decodable, Hashable {
    /// keyed "meta_high|restaurant/bar", "meta_high|cafe-type", ...
    let groups: [String: CalibrationGroup]
}

struct CalibrationGroup: Decodable, Hashable {
    let n: Int
    let current: Double
}

/// DBPR's own result group for a visit (www2.myfloridalicense.com/hotels-restaurants/inspections/). Read from the record's
/// disposition, never computed from violation counts.
enum InspectionResult: Int, Decodable, Hashable {
    case met = 0, followUp = 1, closed = 2

    var label: String {
        switch self {
        case .met: "Met Inspection Standards"
        case .followUp: "Follow-Up Inspection Required"
        case .closed: "Facility Temporarily Closed"
        }
    }
    var fill: Color {
        switch self {
        case .met: Color(hex: 0xDDEFE3)
        case .followUp: Color(hex: 0xFFE9C2)
        case .closed: Color(hex: 0xF9D5DB)
        }
    }
    var ink: Color {
        switch self {
        case .met: Color(hex: 0x0E5A2B)
        case .followUp: Color(hex: 0x6B3A00)
        case .closed: Color(hex: 0x7A0019)
        }
    }
}

/// One DBPR visit: [date, visit type index, disposition index, high-priority, intermediate, basic] (counts are DBPR's).
struct InspectionVisit: Decodable, Hashable {
    let d: String
    let t: Int
    let dp: Int
    let hp: Int?
    let im: Int?
    let bs: Int?

    init(from decoder: Decoder) throws {
        var c = try decoder.unkeyedContainer()
        d = try c.decode(String.self)
        t = try c.decode(Int.self)
        dp = try c.decode(Int.self)
        hp = try c.decodeIfPresent(Int.self)
        im = try c.decodeIfPresent(Int.self)
        bs = try c.decodeIfPresent(Int.self)
    }
}

/// What a list row shows and sorts by (core file): DBPR's result group at the latest visit, its date, and DBPR's counts at the latest
/// routine inspection. Stored as a compact array, [g, d] or [g, d, hp, im, bs].
struct InspectionRecord: Decodable, Hashable {
    let g: InspectionResult?  // DBPR's result group at the latest visit (nil for a disposition DBPR doesn't group)
    let d: String             // latest visit date
    let hp: Int?
    let im: Int?
    let bs: Int?

    init(g: InspectionResult?, d: String, hp: Int?, im: Int?, bs: Int?) {
        self.g = g; self.d = d; self.hp = hp; self.im = im; self.bs = bs
    }

    /// From the JSONSerialization array (the launch path); nil without a date.
    init?(array a: [Any]) {
        guard a.count >= 2, let d = a[1] as? String else { return nil }
        func n(_ i: Int) -> Int? { i < a.count ? a[i] as? Int : nil }
        self.init(g: n(0).flatMap(InspectionResult.init(rawValue:)), d: d, hp: n(2), im: n(3), bs: n(4))
    }

    init(from decoder: Decoder) throws {
        var c = try decoder.unkeyedContainer()
        g = try c.decodeIfPresent(Int.self).flatMap(InspectionResult.init(rawValue:))
        d = try c.decode(String.self)
        hp = c.isAtEnd ? nil : try c.decodeIfPresent(Int.self)
        im = c.isAtEnd ? nil : try c.decodeIfPresent(Int.self)
        bs = c.isAtEnd ? nil : try c.decodeIfPresent(Int.self)
    }
}

/// The rest of a place's DBPR inspections (detail file): the latest visit's disposition and type, the history, latest first.
struct InspectionDetail: Decodable, Hashable {
    let dp: Int               // disposition at the latest visit (index into DataFile.dispositions)
    let t: Int                // latest visit type
    let n: Int                // visits since Jul 2023
    let eo: Int               // of those, "Emergency order recommended"
    let rd: String?           // latest routine inspection date
    let h: [InspectionVisit]
}

/// A place's detail record, from its region's detail file.
struct PlaceDetail: Decodable, Hashable {
    let lic: String?
    let ph: String?
    let w: String?
    let inspection: InspectionDetail?
    let cl: [Closure]?

    enum CodingKeys: String, CodingKey {
        case lic, ph, w, cl
        case inspection = "in"
    }

    /// web links only: a bare host gets https://, and any other scheme (javascript:, tel:, a custom app URL) is dropped
    var website: URL? {
        w.flatMap { URL(string: $0.contains("://") ? $0 : "https://" + $0) }
            .flatMap { ["http", "https"].contains($0.scheme?.lowercased() ?? "") && $0.host != nil ? $0 : nil }
    }
    var closures: [Closure] { cl ?? [] }
}

/// An emergency closure from DBPR's weekly closure reports: [date, reason in DBPR's words, reopened date].
struct Closure: Decodable, Hashable {
    let date: String
    let reason: String?
    let reopened: String?

    init(from decoder: Decoder) throws {
        var c = try decoder.unkeyedContainer()
        date = try c.decode(String.self)
        reason = try c.decodeIfPresent(String.self)
        reopened = try c.decodeIfPresent(String.self)
    }
}

struct PlaceRecord: Decodable {
    // the memberwise initializer is used by init?(_ d:) below
    let id: String
    let n: String
    let c: Int?
    let cu: Int
    let t: Int
    let s: Int
    let co: Int?
    let rg: Int?
    let a: String?
    let z: String?
    let la: Double?
    let lo: Double?
    let b: Int?
    let ch: Int?
    let v: Int?
    let bar: Int?
    let dw: Int?
    let g: Int?
    let hc: Int?
    let h: Int?
    let mi: Int?
    let jbf: String?
    let ip: Double?
    let f: Int?
    let fn: String?
    let note: String?
    let dish: String?
    let seas: String?
    /// the listing's other name when a hand-checked place shows its verified one ("Cafe Versailles Calle 8"): searchable, shown small
    let aka: String?
    let inspection: InspectionRecord?

    enum CodingKeys: String, CodingKey {
        case id, n, c, cu, t, s, co, rg, a, z, la, lo, b, ch, v, bar, dw, g, hc, h, mi, jbf, ip, f, fn, note, dish, seas, aka
        case inspection = "in"
    }
}

extension PlaceRecord {
    /// From one JSONSerialization dictionary (the fast path); nil when the required fields are missing.
    init?(_ d: [String: Any]) {
        guard let id = d["id"] as? String, let n = d["n"] as? String, let cu = d["cu"] as? Int, let t = d["t"] as? Int, let s = d["s"] as? Int else { return nil }
        func i(_ k: String) -> Int? { d[k] as? Int }
        func str(_ k: String) -> String? { d[k] as? String }
        self.init(id: id, n: n, c: i("c"), cu: cu, t: t, s: s, co: i("co"), rg: i("rg"), a: str("a"), z: str("z"), la: d["la"] as? Double,
                  lo: d["lo"] as? Double, b: i("b"), ch: i("ch"), v: i("v"), bar: i("bar"), dw: i("dw"), g: i("g"), hc: i("hc"), h: i("h"),
                  mi: i("mi"), jbf: str("jbf"), ip: d["ip"] as? Double, f: i("f"), fn: str("fn"), note: str("note"), dish: str("dish"),
                  seas: str("seas"), aka: str("aka"),
                  inspection: (d["in"] as? [Any]).flatMap { InspectionRecord(array: $0) })
    }
}

// MARK: - The model the views use

struct PlaceTags: OptionSet, Hashable {
    let rawValue: Int
    static let cuban = PlaceTags(rawValue: 1)       // hand-checked Cuban sandwich or cafecito window
    static let stoneCrab = PlaceTags(rawValue: 2)   // hand-checked stone crab (seasonal)
    static let grouper = PlaceTags(rawValue: 4)     // hand-checked grouper sandwiches and seafood shacks
    static let keys = PlaceTags(rawValue: 8)        // hand-checked Keys classics: key lime pie, conch
    static let oyster = PlaceTags(rawValue: 16)     // hand-checked oyster and raw bars
    static let fishCamp = PlaceTags(rawValue: 32)   // hand-checked fish camps and smoked fish
    static let latin = PlaceTags(rawValue: 64)      // hand-checked Haitian, Venezuelan, Colombian, Puerto Rican...
    static let oldest = PlaceTags(rawValue: 128)    // hand-checked, open at this address since 1960 or earlier
}

/// How a place got on the list. The share that matched a license comes from calibration.
enum Tier: Int, Comparable {
    case listing = 0        // one map listing
    case confirmed = 1      // a high-confidence Meta listing, or a hand-checked place
    case licensed = 2       // on a current Florida DBPR food service license

    static func < (a: Tier, b: Tier) -> Bool { a.rawValue < b.rawValue }

    var label: String {
        switch self {
        case .licensed: "Licensed by the state"
        case .confirmed: "Confirmed listing"
        case .listing: "Listing only"
        }
    }
}

enum Michelin: Int {
    case none = 0, recommended = 1, bib = 2, oneStar = 3, twoStars = 4, threeStars = 5
    var label: String? {
        switch self {
        case .none: nil
        case .recommended: "MICHELIN Recommended"
        case .bib: "Bib Gourmand"
        case .oneStar: "1 MICHELIN Star"
        case .twoStars: "2 MICHELIN Stars"
        case .threeStars: "3 MICHELIN Stars"
        }
    }
}

struct Place: Identifiable, Hashable {
    let id: String
    let name: String
    let address: String?
    let city: String?
    let county: String?
    /// the region whose detail file holds this place's inspection history, license, phone and website
    let region: String?
    let zip: String?
    let coordinate: CLLocationCoordinate2D?
    let cuisine: String
    let brand: String?
    let chainCount: Int
    let tier: Tier
    let source: String
    let isVenue: Bool
    let isBar: Bool
    /// run by Walt Disney World or Universal Orlando (some of these are inside ticketed parks)
    let isThemePark: Bool
    let tags: PlaceTags
    /// On our hand-checked list (data/research): confirmed open with a 2025–26 source.
    let handChecked: Bool
    let honorFlags: Int
    let michelin: Michelin
    let iconicPoints: Double?
    let jamesBeard: String?
    let founded: Int?
    let foundedNote: String?
    let note: String?
    let dishes: String?
    let seasonal: String?
    let inspection: InspectionRecord?
    /// normalized text for search: name, town, county, zip, cuisine, brand, dishes, then the address with street words abbreviated
    let searchText: String
    let nameText: String
    /// the A-to-Z key, worked out once at load: the normalized name ("por wine house" for "/pôr/ Wine House"), so case, accents
    /// and leading punctuation don't change the order, and a sort never runs a localized compare per comparison
    let sortKey: String
    /// made once at load: a new CLLocation per comparison made a Nearest sort of 16,000 places take seconds
    let location: CLLocation?

    static func == (a: Place, b: Place) -> Bool { a.id == b.id }
    func hash(into h: inout Hasher) { h.combine(id) }

    /// MICHELIN, James Beard or a verified founding year: what the map and Spotlight put first
    var isHonored: Bool { honorFlags != 0 || michelin != .none }
    /// what the Honors section lists: a MICHELIN distinction or a James Beard honor ("oldest" alone isn't an honor)
    var hasHonors: Bool { michelin != .none || jamesBeard != nil }
    var isChain: Bool { chainCount >= 5 }
    var jamesBeardLabel: String? {
        if honorFlags & 1 != 0 { return "America's Classic" }
        if honorFlags & 2 != 0 { return "James Beard winner" }
        if honorFlags & 4 != 0 { return "James Beard finalist" }
        if honorFlags & 8 != 0 { return "James Beard semifinalist" }
        return nil
    }
    /// The chip for a James Beard line: the place's own honor, or a restaurateur (group) honor when that's the only one.
    var jamesBeardChip: String? { jamesBeardLabel ?? (jamesBeard != nil ? "James Beard (restaurateur)" : nil) }
    /// a hand-checked Florida pick: the orange pins
    var isClassic: Bool { handChecked && !tags.isEmpty }
    var townLine: String { [city, cuisine].compactMap { $0 }.joined(separator: " · ") }
    var fullAddress: String {
        [address, [city, zip].compactMap { $0 }.joined(separator: " ")].compactMap { $0 }.filter { !$0.isEmpty }.joined(separator: ", ")
    }

    /// Every place in the core file, built on all cores at once (each place's search text takes four normalizations).
    static func build(_ raw: [[String: Any]], file: DataFile) -> [Place] {
        var out = [Place?](repeating: nil, count: raw.count)
        let chunk = 2_000, chunks = (raw.count + chunk - 1) / chunk
        out.withUnsafeMutableBufferPointer { buf in
            let base = buf   // each chunk writes only its own slots
            DispatchQueue.concurrentPerform(iterations: chunks) { c in
                for k in (c * chunk)..<min(raw.count, (c + 1) * chunk) {
                    base[k] = PlaceRecord(raw[k]).map { Place($0, file: file) }
                }
            }
        }
        return out.compactMap { $0 }
    }

    init(_ r: PlaceRecord, file: DataFile) {
        let city = r.c.flatMap { $0 < file.cities.count ? file.cities[$0] : nil }
        let cuisine = r.cu < file.cuisines.count ? file.cuisines[r.cu] : "American & Other"
        let brand = r.b.flatMap { $0 < file.brands.count ? file.brands[$0] : nil }
        let county = r.co.flatMap { $0 < file.counties.count ? file.counties[$0] : nil }
        id = r.id
        name = r.n
        address = r.a
        self.city = city
        self.county = county
        region = r.rg.flatMap { $0 < file.regions.count ? file.regions[$0] : nil }
        zip = r.z
        if let la = r.la, let lo = r.lo { coordinate = CLLocationCoordinate2D(latitude: la, longitude: lo) } else { coordinate = nil }
        self.cuisine = cuisine
        self.brand = brand
        chainCount = r.ch ?? 1
        tier = Tier(rawValue: r.t) ?? .listing
        source = r.s < file.srcs.count ? file.srcs[r.s] : "meta"
        isVenue = r.v == 1
        isBar = r.bar == 1
        isThemePark = r.dw == 1
        tags = PlaceTags(rawValue: r.g ?? 0)
        handChecked = r.hc == 1
        honorFlags = r.h ?? 0
        michelin = Michelin(rawValue: r.mi ?? 0) ?? .none
        iconicPoints = r.ip
        jamesBeard = r.jbf
        founded = r.f
        foundedNote = r.fn
        note = r.note
        dishes = r.dish
        seasonal = r.seas
        inspection = r.inspection
        // the dishes a hand-checked place serves are searchable too: "cuban sandwich ybor", "smoked fish dip"
        searchText = " " + Search.normalize([r.n, r.aka, city, county, r.z, cuisine, brand, r.dish].compactMap { $0 }.joined(separator: " ")) + " "
            + Search.normalizeAddress(r.a ?? "") + " "
        nameText = " " + Search.normalize([r.n, brand].compactMap { $0 }.joined(separator: " ")) + " "
        sortKey = Search.normalize(r.n)
        location = coordinate.map { CLLocation(latitude: $0.latitude, longitude: $0.longitude) }
    }
}

/// The data's dates are calendar days ("2026-06-16"), not moments: read and shown in UTC, so no time zone can move one a day.
enum DayFormat {
    private static let utc = TimeZone(identifier: "UTC")!

    static func date(_ s: String?) -> Date? {
        guard let s, s.count >= 10 else { return nil }
        let parts = s.prefix(10).split(separator: "-").compactMap { Int($0) }
        guard parts.count == 3, (1...12).contains(parts[1]), (1...31).contains(parts[2]) else { return nil }
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = utc
        return cal.date(from: DateComponents(year: parts[0], month: parts[1], day: parts[2]))
    }

    /// "Jun 16, 2026" (in the reader's language); anything that isn't a date is shown as it is
    static func text(_ s: String?) -> String? {
        guard let s else { return nil }
        guard let d = date(s) else { return s }
        return d.formatted(Date.FormatStyle(date: .abbreviated, time: .omitted, timeZone: utc))
    }

    /// "Sep 2025"
    static func monthYear(_ s: String?) -> String? {
        guard let s else { return nil }
        guard let d = date(s) else { return s }
        return d.formatted(Date.FormatStyle(timeZone: utc).month(.abbreviated).year())
    }
}
