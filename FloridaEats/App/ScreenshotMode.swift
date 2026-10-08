import Foundation
import CoreLocation
import UIKit

/// `-screenshot <name>` opens one screen with fixed state for App Store screenshots (scripts/capture-screenshots.sh).
/// Names: home, cuban, stonecrab, keys, detail, map, honors, oldest, saved, about.
enum ScreenshotMode {
    /// Debug builds only: an App Store build ignores the launch argument, so no one can reach seeded screens or fake locations.
    static var name: String? {
        #if DEBUG
        let args = ProcessInfo.processInfo.arguments
        guard let i = args.firstIndex(of: "-screenshot"), i + 1 < args.count else { return nil }
        return args[i + 1]
        #else
        return nil
        #endif
    }
    static var isActive: Bool { name != nil }

    @MainActor
    static func apply(to model: AppModel) {
        guard let name, model.isLoaded else { return }
        model.filters = Filters()
        // downtown Miami, so "nearest" lists have distances without a permission prompt
        model.screenshotLocation = CLLocation(latitude: 25.7743, longitude: -80.1937)
        // by name, ignoring case, so a rebuild with a slightly different casing still finds the place
        let pick = { (n: String) in model.places.first { $0.name.caseInsensitiveCompare(n) == .orderedSame } }
        // Columbia Restaurant has five locations: the saved one is the 1905 original in Ybor City
        let columbia = model.places.first { $0.name == "Columbia Restaurant" && $0.city == "Tampa" }
        for p in [pick("Versailles"), pick("Joe's Stone Crab"), columbia, pick("Ted Peters' Famous Smoked Fish")].compactMap({ $0 }) where !model.isSaved(p) {
            model.toggleSaved(p)
        }
        let open = { (g: Guide) in model.tab = .guides; model.selectedGuide = g; model.guidesPath = [.guide(g)] }
        switch name {
        case "cuban": open(.cuban)
        case "stonecrab": open(.stoneCrab)
        case "keys": open(.keys)
        case "honors": open(.honors)
        case "oldest": open(.oldest)
        case "detail":
            // a place with only "Inspection Completed - No Further Action" visits: no warning in an App Store image
            open(.stoneCrab)
            if let p = pick("Joe's Stone Crab") ?? model.places.first { model.selectedPlace = p; model.guidesPath.append(.place(p)) }
        case "map": model.tab = .map
        case "saved": model.tab = .saved
        case "about": model.tab = .about
        default: model.tab = .guides; model.selectedGuide = nil
        }
        // iPad shows the place column next to every list, so give each shot a place instead of "Pick a place": famous ones whose
        // inspection history is spotless, since the iPad column shows it all.
        guard UIDevice.current.userInterfaceIdiom == .pad, model.selectedPlace == nil else { return }
        let place: Place? = switch name {
        case "cuban": pick("Sanguich De Miami")
        case "honors": pick("Stubborn Seed")
        case "stonecrab", "keys": pick("Joe's Stone Crab")
        case "saved": pick("Ted Peters' Famous Smoked Fish")
        case "about": nil
        default: pick("Joe's Stone Crab")
        }
        model.selectedPlace = place
    }
}
