import Foundation
import CoreLocation

/// The lists the app is built around. Each is a filter plus an order; none uses ratings (the app only publishes data it may).
enum Guide: String, CaseIterable, Identifiable, Hashable {
    case cuban, stoneCrab, grouper, keys, oyster, fishCamp, latin, honors, oldest, inspections, nearMe, all

    var id: String { rawValue }

    var title: String {
        switch self {
        case .cuban: "Cuban & Cafecito"
        case .stoneCrab: "Stone Crabs"
        case .grouper: "Grouper & Seafood Shacks"
        case .keys: "Keys Classics"
        case .oyster: "Oyster Bars"
        case .fishCamp: "Fish Camps & Smoked Fish"
        case .latin: "Latin & Caribbean"
        case .honors: "MICHELIN & James Beard"
        case .oldest: "Oldest Places"
        case .inspections: "Inspections"
        case .nearMe: "Near Me"
        case .all: "All Restaurants"
        }
    }

    var subtitle: String {
        switch self {
        case .cuban: "Hand-checked Cuban sandwiches, bakeries and coffee windows"
        case .stoneCrab: "Hand-checked stone crab spots; claws are in season Oct 15 – May 1"
        case .grouper: "Hand-checked grouper sandwiches and Gulf and Atlantic seafood shacks"
        case .keys: "Hand-checked key lime pie, conch fritters and Keys seafood"
        case .oyster: "Hand-checked oyster bars and raw bars"
        case .fishCamp: "Hand-checked Old Florida fish camps, fish dip and smoked mullet"
        case .latin: "Hand-checked Haitian, Venezuelan, Colombian, Puerto Rican and more"
        case .honors: "MICHELIN Guide Florida 2026 and James Beard honorees"
        case .oldest: "Founding years checked at the same address, oldest first"
        case .inspections: "Florida DBPR's official inspection results"
        case .nearMe: "Everything around you, closest first"
        case .all: "Restaurants, cafés, bars and bakeries statewide"
        }
    }

    var systemImage: String {
        switch self {
        case .cuban: "cup.and.saucer"
        case .stoneCrab: "snowflake"
        case .grouper: "fish"
        case .keys: "sun.horizon"
        case .oyster: "drop"
        case .fishCamp: "water.waves"
        case .latin: "flame"
        case .honors: "star.circle"
        case .oldest: "clock.arrow.circlepath"
        case .inspections: "checkmark.seal"
        case .nearMe: "location"
        case .all: "fork.knife"
        }
    }

    /// The Florida guides get the orange card on Home.
    var isFlorida: Bool { [.cuban, .stoneCrab, .grouper, .keys, .oyster, .fishCamp, .latin].contains(self) }

    /// Guides whose order is a ranking worth numbering.
    var isRanked: Bool { [.oldest].contains(self) }

    var sortOptions: [SortOrder] {
        switch self {
        case .cuban, .stoneCrab, .grouper, .keys, .oyster, .fishCamp, .latin: [.featured, .nearest, .name]
        case .honors: [.iconic, .nearest]
        case .oldest: [.oldest]
        case .inspections: [.recent, .fewestHighPriority, .mostHighPriority, .nearest]
        case .nearMe: [.nearest]
        case .all: [.name, .nearest]
        }
    }

    var defaultSort: SortOrder { sortOptions[0] }

    /// The tag behind a hand-checked guide.
    var tag: PlaceTags? {
        switch self {
        case .cuban: .cuban
        case .stoneCrab: .stoneCrab
        case .grouper: .grouper
        case .keys: .keys
        case .oyster: .oyster
        case .fishCamp: .fishCamp
        case .latin: .latin
        default: nil
        }
    }

    func includes(_ p: Place) -> Bool {
        if let tag {   // the guides that promise "hand-checked" list only places checked open with a 2025–26 source
            return p.handChecked && p.tags.contains(tag)
        }
        switch self {
        case .honors: return p.michelin != .none || p.jamesBeard != nil
        case .oldest: return p.founded != nil && p.tags.contains(.oldest)
        case .inspections: return p.inspection != nil
        default: return true
        }
    }
}

enum SortOrder: String, CaseIterable, Identifiable {
    case featured, nearest, oldest, name, iconic, recent, fewestHighPriority, mostHighPriority
    var id: String { rawValue }
    var label: String {
        switch self {
        case .featured: "Featured first"
        case .nearest: "Nearest"
        case .oldest: "Oldest first"
        case .name: "A to Z"
        case .iconic: "MICHELIN, then James Beard"
        case .recent: "Latest inspection first"
        case .fewestHighPriority: "Fewest high-priority violations"
        case .mostHighPriority: "Most high-priority violations"
        }
    }
}

/// Filters shared by every list. Search text lives with each list.
struct Filters: Equatable, Codable {
    var town: String?
    var cuisine: String?
    var hideChains = false
    var confirmedOnly = false
    var includeNonRestaurants = false

    var activeCount: Int {
        [town != nil, cuisine != nil, hideChains, confirmedOnly, includeNonRestaurants].filter { $0 }.count
    }

    func allows(_ p: Place) -> Bool {
        if !includeNonRestaurants && p.isVenue { return false }
        if let town, p.city != town { return false }
        if let cuisine, p.cuisine != cuisine { return false }
        if hideChains && p.isChain { return false }
        if confirmedOnly && p.tier == .listing { return false }
        return true
    }
}

enum Ranking {
    static func sort(_ places: [Place], by order: SortOrder, from here: CLLocation?) -> [Place] {
        // Keys come from fields made once at load: a localized compare, or a new CLLocation per comparison, made a 16,000-place
        // sort take most of a second (AR-13). sortKey is the normalized name, so case, accents and punctuation don't change the order.
        func name(_ a: Place, _ b: Place) -> Bool { a.sortKey != b.sortKey ? a.sortKey < b.sortKey : a.id < b.id }
        switch order {
        case .nearest where here != nil:
            // each distance once, not four times per comparison
            let from = here!
            return places.map { p in (p, p.location.map { $0.distance(from: from) } ?? .greatestFiniteMagnitude) }
                .sorted { $0.1 != $1.1 ? $0.1 < $1.1 : name($0.0, $1.0) }
                .map(\.0)
        case .featured, .nearest:
            // honored places first, then verified founding year, then name
            return places.sorted {
                let a = $0.iconicPoints ?? -1, b = $1.iconicPoints ?? -1
                if a != b { return a > b }
                let fa = $0.founded ?? 9999, fb = $1.founded ?? 9999
                return fa != fb ? fa < fb : name($0, $1)
            }
        case .oldest:
            return places.sorted { ($0.founded ?? 9999) != ($1.founded ?? 9999) ? ($0.founded ?? 9999) < ($1.founded ?? 9999) : name($0, $1) }
        case .name:
            return places.sorted(by: name)
        case .iconic:
            // an order anyone can check: MICHELIN distinction, then the James Beard honor (America's Classic, winner, finalist, semifinalist), then name
            func jb(_ p: Place) -> Int { p.honorFlags & 1 != 0 ? 4 : p.honorFlags & 2 != 0 ? 3 : p.honorFlags & 4 != 0 ? 2 : p.honorFlags & 8 != 0 ? 1 : 0 }
            return places.sorted {
                if $0.michelin.rawValue != $1.michelin.rawValue { return $0.michelin.rawValue > $1.michelin.rawValue }
                if jb($0) != jb($1) { return jb($0) > jb($1) }
                return name($0, $1)
            }
        case .recent:
            return places.sorted {
                let a = $0.inspection?.d ?? "", b = $1.inspection?.d ?? ""
                return a != b ? a > b : name($0, $1)
            }
        case .fewestHighPriority, .mostHighPriority:
            // DBPR's own counts at the latest routine inspection; places without one go last either way
            let few = order == .fewestHighPriority
            return places.sorted {
                let a = $0.inspection?.hp, b = $1.inspection?.hp
                if (a == nil) != (b == nil) { return a != nil }
                let x = a ?? 0, y = b ?? 0
                if x != y { return few ? x < y : x > y }
                let ra = ($0.inspection?.im ?? 0) + ($0.inspection?.bs ?? 0), rb = ($1.inspection?.im ?? 0) + ($1.inspection?.bs ?? 0)
                if ra != rb { return few ? ra < rb : ra > rb }
                return name($0, $1)
            }
        }
    }
}
