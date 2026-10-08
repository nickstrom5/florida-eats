import SwiftUI

struct AboutView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        List {
            Section {
                VStack(alignment: .leading, spacing: 8) {
                    Text("FLORIDA EATS").displayFont(30).foregroundStyle(Theme.green)
                    Text("A free guide to \(model.restaurantCount.formatted()) Florida restaurants, with hand-checked lists of Cuban sandwiches and coffee windows, stone crabs, grouper and seafood shacks, Keys classics, oyster bars, fish camps and the state's oldest places, MICHELIN and James Beard honors, and the state's own inspection results. No account, no ads, no tracking.")
                        .font(.subheadline).foregroundStyle(Theme.ink2)
                    Text("Florida Eats (\u{201C}FL Eats\u{201D}) is an independent app by Nicholas Soderstrom. It is not affiliated with, endorsed by or operated by the State of Florida, the Florida Department of Business and Professional Regulation, the Florida Department of Agriculture and Consumer Services, VISIT FLORIDA, the MICHELIN Guide, the James Beard Foundation, Walt Disney World, Universal Orlando, Apple, or any restaurant, team or chain.")
                        .font(.footnote).foregroundStyle(Theme.muted)
                }
                .padding(.vertical, 4)
            }
            Section("How the lists are built") {
                Text("The Cuban, stone crab, grouper, Keys, oyster bar, fish camp, Latin and oldest-places lists are hand-checked: each place was checked against a 2025 or 2026 source (the place's own website or menu, local news or an official tourism listing), with the address checked. Founding years mean the year it opened at this address. Seasonal places aren't closed: stone crab claws are in season Oct 15 – May 1.")
                Text("Honors are the MICHELIN Guide Florida 2026 selection and James Beard Foundation awards and nominations from 2023 to 2026, plus America's Classics.")
                Text("Florida's Department of Business and Professional Regulation (DBPR) licenses and inspects every restaurant in the state. Every current seating and non-seating food service license is here, placed on its street address. Open map listings (Overture Maps) add map points, websites and phone numbers, and a few places DBPR doesn't license, such as coffee shops and bakeries, which the Department of Agriculture often licenses. Checked against DBPR's licenses statewide, high-confidence restaurant listings matched a current license \(rate("meta_high")) of the time. Website links are checked, and any that no longer belong to the place are left out.")
                Text("Inspection results are DBPR's: each visit's official disposition (such as \u{201C}Inspection Completed - No Further Action\u{201D} or \u{201C}Warning Issued\u{201D}), DBPR's own result group for it (Met Inspection Standards, Follow-Up Inspection Required or Facility Temporarily Closed) and DBPR's violation counts. Florida doesn't grade restaurants, and this app computes no grade.")
                Text("Ratings, reviews, hours and photos are Apple Maps' own, shown live in Apple's place card. This app doesn't store or rank by them.")
            }
            .font(.subheadline).foregroundStyle(Theme.ink2)
            Section("Sources") {
                source("Florida DBPR, Division of Hotels and Restaurants", "Food service licenses, inspections (July 2023 through \(DayFormat.text(model.inspectionsThrough) ?? model.inspectionsThrough)), emergency closure reports and disciplinary reports, from DBPR's public records downloads (Chapter 119, Florida Statutes), downloaded \(DayFormat.text(model.dbprFetched) ?? model.dbprFetched) and modified for use in this app. DBPR says its data is refreshed weekly; for up-to-the-minute license verification, use DBPR's license search. Each inspection report is a snapshot of conditions at the time of the inspection.", Links.dbprRecords.absoluteString)
                source("Overture Maps Foundation", "Restaurant listings and websites come from Overture Maps Foundation places data (overturemaps.org)\(model.overtureRelease.map { ", release \($0)" } ?? ""), filtered and reformatted for this app.\n• Data from Meta, Microsoft, DAC and BrightQuery. Available under CDLA Permissive 2.0.\n• Data from Foursquare. \(foursquareCopyright) Available under Apache 2.0. Foursquare data was transformed to the Overture schema; this app further filtered and reformatted it. See the NOTICE below.\n• Data from AllThePlaces. Available under CC0 1.0.\nLicense records are placed on the map with Overture Maps addresses data (open address sources under permissive licenses, docs.overturemaps.org/attribution).", "https://overturemaps.org")
                source("U.S. Census Bureau Geocoder", "Puts license records on the map where Overture's address points don't reach. Public domain.", "https://geocoding.geo.census.gov")
                source("Honors", "The MICHELIN Guide Florida 2026 selection and James Beard Foundation awards, finalists, semifinalists and America's Classics are reported as facts and checked by hand against the official announcements. MICHELIN and the MICHELIN Guide are trademarks of Michelin. James Beard Foundation and James Beard Award are trademarks of the James Beard Foundation. Other names belong to their owners.", "https://guide.michelin.com/us/en/florida/restaurants")
                source("Maps", "Maps, place cards and directions by Apple Maps.", nil)
            }
            Section("Licenses") {
                NavigationLink("Community Data License Agreement – Permissive 2.0") { LicenseText(file: "CDLA-Permissive-2.0", title: "CDLA Permissive 2.0") }
                NavigationLink("Apache License 2.0") { LicenseText(file: "Apache-2.0", title: "Apache License 2.0") }
                NavigationLink("Foursquare OS Places NOTICE") { LicenseText(file: "Foursquare-NOTICE", title: "Foursquare NOTICE") }
            }
            Section("Privacy") {
                Text("The app collects nothing. Your location, if you allow it, only sorts lists by distance and shows where you are on the map, on this device. Saved places stay on this device.")
                    .font(.subheadline).foregroundStyle(Theme.ink2)
                Link("Privacy policy", destination: Links.privacy)
                Link("Terms of use", destination: Links.terms)
            }
            Section("Help") {
                Link("Report a missing or closed place", destination: Links.correctionEmail)
                Link("Email \(Links.supportEmail)", destination: URL(string: "mailto:\(Links.supportEmail)")!)
                Link("Website", destination: Links.site)
                Text("Data as of \(DayFormat.text(model.generated) ?? model.generated). Places open and close; check before you go. Version \(Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "1.0")")
                    .font(.footnote).foregroundStyle(Theme.muted)
            }
        }
        .navigationTitle("About")
        .tint(Theme.green)
    }

    /// the copyright line exactly as the bundled Foursquare NOTICE has it, so the two can't disagree
    private var foursquareCopyright: String {
        guard let url = Bundle.main.url(forResource: "Foursquare-NOTICE", withExtension: "txt"),
              let text = try? String(contentsOf: url, encoding: .utf8),
              let line = text.split(separator: "\n").first(where: { $0.hasPrefix("©") }) else { return "© Foursquare Labs, Inc. All rights reserved." }
        return line.trimmingCharacters(in: .whitespaces)
    }

    private func rate(_ group: String) -> String {
        guard let v = model.calibration.statewide?.groups["\(group)|restaurant/bar"]?.current else { return "most" }
        return "\(Int((v * 100).rounded()))%"
    }

    @ViewBuilder
    private func source(_ name: String, _ detail: String, _ url: String?) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            if let url, let u = URL(string: url) { Link(name, destination: u).font(.subheadline.weight(.semibold)) }
            else { Text(name).font(.subheadline.weight(.semibold)) }
            Text(detail).font(.caption).foregroundStyle(Theme.muted)
        }
    }
}

/// A bundled license text (Resources/Licenses), reflowed rather than shown as raw 80-column lines.
struct LicenseText: View {
    let file: String
    let title: String

    var body: some View {
        ScrollView {
            Text(text).font(.footnote).foregroundStyle(Theme.ink).textSelection(.enabled)
                .frame(maxWidth: .infinity, alignment: .leading).padding()
        }
        .inlineTitle(title)
    }

    private var text: String {
        guard let url = Bundle.main.url(forResource: file, withExtension: "txt"),
              let raw = try? String(contentsOf: url, encoding: .utf8) else { return "License text missing." }
        // join hard-wrapped lines into paragraphs; keep blank lines and list items as breaks
        var out: [String] = []
        for para in raw.components(separatedBy: "\n\n") {
            let lines = para.components(separatedBy: "\n").map { $0.trimmingCharacters(in: .whitespaces) }
            var joined = ""
            for l in lines where !l.isEmpty {
                let startsItem = l.hasPrefix("–") || l.hasPrefix("-") || l.range(of: #"^\(?[a-z0-9]{1,3}[.)]\s"#, options: .regularExpression) != nil
                joined += joined.isEmpty ? l : (startsItem ? "\n" + l : " " + l)
            }
            if !joined.isEmpty { out.append(joined) }
        }
        return out.joined(separator: "\n\n")
    }
}
