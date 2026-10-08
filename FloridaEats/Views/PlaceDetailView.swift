import SwiftUI
import MapKit

struct PlaceDetailView: View {
    @Environment(AppModel.self) private var model
    @Environment(LocationService.self) private var location
    let place: Place

    @State private var mapItem: MKMapItem?
    @State private var lookingUp = false
    @State private var notOnAppleMaps = false
    @State private var appleMapsFailed = false
    /// inspection history, closures, license, phone and website, from the place's region file (read when the place opens)
    @State private var detail: PlaceDetail?
    @State private var detailLoaded = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                header
                actions
                if let c = place.coordinate { mapSnippet(c) }
                if place.handChecked && (place.note != nil || place.dishes != nil || place.founded != nil || place.seasonal != nil) { checked }
                if place.hasHonors { honors }
                if let i = place.inspection { inspections(i) }
                records
                listing
            }
            .padding(16)
        }
        .background(Theme.surface)
        .inlineTitle(place.name)
        .toolbar {
            ToolbarItemGroup(placement: .topBarTrailing) {
                Button { model.toggleSaved(place) } label: {
                    Label(model.isSaved(place) ? "Saved" : "Save", systemImage: model.isSaved(place) ? "heart.fill" : "heart")
                }
                .accessibilityIdentifier("saveHeart")   // the Saved tab is also a "Saved" button
                ShareLink(item: shareText) { Label("Share", systemImage: "square.and.arrow.up") }
            }
        }
        .task(id: place.id) {
            detailLoaded = false
            detail = await model.detail(for: place)
            detailLoaded = true
        }
        .mapItemDetailSheet(item: $mapItem)
        .alert("Not on Apple Maps", isPresented: $notOnAppleMaps) {
            Button("Open Apple Maps anyway") { AppleMaps.openInMaps(place) }
            Button("OK", role: .cancel) {}
        } message: {
            Text("Apple Maps doesn't have a listing for \(place.name) at this spot, so there are no ratings or hours to show here.")
        }
        .alert("Couldn't reach Apple Maps", isPresented: $appleMapsFailed) {
            Button("Try again") { lookUp() }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("Check your connection and try again.")
        }
    }

    /// Apple's place card for this place; "not on Apple Maps" only when Apple answered and had no listing here.
    private func lookUp() {
        lookingUp = true
        Task {
            let result = await AppleMaps.findItem(for: place)
            lookingUp = false
            switch result {
            case .found(let item): mapItem = item
            case .notListed: notOnAppleMaps = true
            case .failed: appleMapsFailed = true
            }
        }
    }

    // MARK: sections

    private var header: some View {
        VStack(alignment: .leading, spacing: 8) {
            // "MIAMI · MIAMI-DADE COUNTY"
            Text((place.city ?? "Florida").uppercased() + (place.county.map { " · " + $0.uppercased() + " COUNTY" } ?? ""))
                .font(.caption.weight(.bold)).tracking(1.2).foregroundStyle(Theme.green2)
            Text(place.name.uppercased())
                .displayFont(38).foregroundStyle(Theme.green)
                .fixedSize(horizontal: false, vertical: true)
                .accessibilityAddTraits(.isHeader)
            Text([place.fullAddress, place.cuisine].filter { !$0.isEmpty }.joined(separator: " · "))
                .font(.subheadline).foregroundStyle(Theme.ink2)
                .textSelection(.enabled)
            if let here = model.screenshotLocation ?? location.location, let l = place.location {
                Text("\(here.milesText(to: l)) away").font(.subheadline).foregroundStyle(Theme.muted)
            }
            PlaceChips(place: place)
        }
    }

    private var actions: some View {
        VStack(spacing: 10) {
            Button { lookUp() } label: {
                HStack {
                    if lookingUp { ProgressView().tint(Theme.green) } else { Image(systemName: "star.bubble") }
                    Text("Ratings, hours & photos").fontWeight(.semibold)
                    Spacer()
                    Text("Apple Maps").font(.caption).foregroundStyle(Theme.green2)
                }
                .padding(14)
                .foregroundStyle(Theme.green)
                .background(RoundedRectangle(cornerRadius: 12).fill(Theme.gold))
            }
            .disabled(place.coordinate == nil || lookingUp)
            .accessibilityHint("Opens the Apple Maps place card with current ratings and hours")

            HStack(spacing: 10) {
                actionButton("Directions", "arrow.triangle.turn.up.right.diamond") { AppleMaps.openInMaps(place, directions: true) }
                if let phone = detail?.ph, let url = URL(string: "tel:\(phone.filter { $0.isNumber || $0 == "+" })") {
                    actionButton("Call", "phone") { UIApplication.shared.open(url) }
                }
                if let web = detail?.website {
                    actionButton("Website", "safari") { UIApplication.shared.open(web) }
                }
            }
        }
    }

    private func actionButton(_ title: String, _ icon: String, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            VStack(spacing: 4) {
                Image(systemName: icon).font(.title3)
                Text(title).font(.caption.weight(.semibold))
            }
            .frame(maxWidth: .infinity, minHeight: 56)
            .foregroundStyle(Theme.green)
            .background(RoundedRectangle(cornerRadius: 12).strokeBorder(Theme.rule2))
        }
    }

    private func mapSnippet(_ c: CLLocationCoordinate2D) -> some View {
        Map(initialPosition: .region(MKCoordinateRegion(center: c, latitudinalMeters: 900, longitudinalMeters: 900)), interactionModes: []) {
            Marker(place.name, systemImage: place.tags.contains(.cuban) ? "cup.and.saucer.fill" : place.isClassic ? "fish.fill" : "fork.knife", coordinate: c).tint(Theme.green)
        }
        .frame(height: 170)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .onTapGesture { AppleMaps.openInMaps(place) }
        .accessibilityLabel("Map of \(place.name). Opens Apple Maps.")
        .accessibilityAddTraits(.isButton)
    }

    private var checked: some View {
        section("Hand-checked") {
            VStack(alignment: .leading, spacing: 8) {
                if let note = place.note { Text(note).font(.subheadline).foregroundStyle(Theme.ink2) }
                if let d = place.dishes { fact("On the menu", d.components(separatedBy: "; ").joined(separator: ", ")) }
                if let f = place.founded {
                    fact("Open here since", "\(f)")
                    // the note explains the year; without a year it only repeated the description above
                    if let fn = place.foundedNote { Text(fn).font(.caption).foregroundStyle(Theme.ink2) }
                }
                if let sea = place.seasonal { fact("Season", sea) }
                Text("Checked by hand against a 2025 or 2026 source: the place's own site or menu, local news or an official tourism listing. Menus and seasons change: stone crab claws are in season Oct 15 – May 1, some places close for part of the summer or after a storm, so check before you go.")
                    .font(.caption).foregroundStyle(Theme.ink2)
            }
        }
    }

    private var honors: some View {
        section("Honors") {
            VStack(alignment: .leading, spacing: 8) {
                if let m = place.michelin.label {
                    Label(m + " · MICHELIN Guide Florida 2026", systemImage: "rosette").font(.subheadline).foregroundStyle(Theme.ink)
                }
                ForEach(lines(place.jamesBeard, prefix: "James Beard: "), id: \.self) { l in
                    Label(l, systemImage: "rosette").font(.subheadline).foregroundStyle(Theme.ink)
                }
                Text("Honors are facts, not ratings. MICHELIN and the MICHELIN Guide are trademarks of Michelin; James Beard Foundation and James Beard Award are trademarks of the James Beard Foundation.")
                    .font(.caption).foregroundStyle(Theme.muted)
            }
        }
    }

    private func inspections(_ i: InspectionRecord) -> some View {
        section("Inspections · Florida DBPR") {
            VStack(alignment: .leading, spacing: 10) {
                HStack(alignment: .center, spacing: 12) {
                    if let g = i.g { ResultBadge(result: g, large: true) }
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Latest visit \(DayFormat.text(i.d) ?? i.d)").font(.headline).foregroundStyle(Theme.ink)
                        if let x = detail?.inspection {
                            Text("“\(model.disposition(x.dp))” · \(model.visitType(x.t))").font(.caption).foregroundStyle(Theme.ink2)
                        }
                    }
                }
                if let hp = i.hp {
                    Text("Latest routine inspection\(detail?.inspection?.rd.flatMap { DayFormat.text($0) }.map { " " + $0 } ?? ""): \(hp) high-priority, \(i.im ?? 0) intermediate and \(i.bs ?? 0) basic violations (DBPR's counts).")
                        .font(.subheadline).foregroundStyle(Theme.ink2)
                }
                if !detailLoaded { ProgressView().tint(Theme.green) }
                // by position: a routine inspection and its same-day callback are two entries
                ForEach(Array((detail?.inspection?.h ?? []).enumerated()), id: \.offset) { _, v in
                    VStack(alignment: .leading, spacing: 2) {
                        HStack(alignment: .firstTextBaseline) {
                            Text(DayFormat.text(v.d) ?? v.d).font(.subheadline).monospacedDigit().foregroundStyle(Theme.ink2)
                            Text(model.visitType(v.t)).font(.subheadline).foregroundStyle(Theme.muted)
                        }
                        Text(model.disposition(v.dp) + (v.hp.map { " · \($0) high-priority" } ?? ""))
                            .font(.subheadline.weight(.semibold)).foregroundStyle(Theme.ink)
                    }
                }
                if let x = detail?.inspection, x.n > x.h.count {
                    Text("The latest \(x.h.count) of \(x.n) visits since \(DayFormat.monthYear(model.inspectionsSince) ?? "July 2023").").font(.caption).foregroundStyle(Theme.muted)
                }
                ForEach(Array((detail?.closures ?? []).enumerated()), id: \.offset) { _, c in
                    fact("Emergency closure \(DayFormat.text(c.date) ?? c.date)",
                         [c.reason.map { "DBPR's reason: “\($0)”" }, c.reopened.flatMap { DayFormat.text($0) }.map { "reopened \($0)" }].compactMap { $0 }.joined(separator: " · "))
                }
                Text("Florida's Division of Hotels and Restaurants inspects every licensed restaurant. Florida doesn't grade restaurants (“establishments are not graded or rated”), and neither does this app: the result shown is DBPR's own group for the latest visit's disposition. Violation counts are DBPR's. One visit is a snapshot of one day. Records through \(DayFormat.text(model.inspectionsThrough) ?? model.inspectionsThrough).")
                    .font(.caption).foregroundStyle(Theme.muted)
                if let lic = detail?.lic {
                    Link(destination: Links.dbprSearch) {
                        Label("Full citations: search license \(lic) on DBPR's site", systemImage: "arrow.up.right.square").font(.subheadline.weight(.semibold))
                    }
                    .foregroundStyle(Theme.green)
                }
            }
        }
    }

    private var records: some View {
        section("Official records") {
            VStack(alignment: .leading, spacing: 8) {
                kv("DBPR food service license", detail?.lic.map(Self.unbroken) ?? (detailLoaded ? "— (no current license matched)" : "…"))
                Text(recordsNote).font(.caption).foregroundStyle(Theme.muted)
            }
        }
    }

    private var listing: some View {
        section("How we know it's here") {
            VStack(alignment: .leading, spacing: 8) {
                kv("Listed as", place.tier.label)
                if place.tier == .licensed { kv("Official record", "Florida DBPR food service licenses") }
                if place.isThemePark { kv("Operator", "Walt Disney World or Universal Orlando") }
                if place.chainCount >= 2 { kv("Locations in Florida", place.chainCount.formatted()) }
                Text(listingNote).font(.caption).foregroundStyle(Theme.muted)
            }
        }
    }

    /// "SEA2300159", never broken across lines
    private static func unbroken(_ id: String) -> String { id.replacingOccurrences(of: "-", with: "\u{2011}") }

    /// Where the license comes from; a missing license is unknown, not "unlicensed".
    private var recordsNote: String {
        if detail?.lic != nil || (!detailLoaded && place.tier == .licensed) {
            return "From the Florida Department of Business and Professional Regulation's list of current food service licenses (public records, downloaded \(DayFormat.text(model.dbprFetched) ?? model.dbprFetched))."
        }
        return "No current DBPR license matched this place. Coffee shops, bakeries, juice bars and grocery counters are often licensed by the Florida Department of Agriculture instead, and a place can be licensed under another name, so a missing license means unknown, not unlicensed."
    }

    private var listingNote: String {
        let checked = place.handChecked
        if place.source == "research" {
            return "On our hand-checked list (checked against a 2025 or 2026 source). The open map data didn't list it as a place to eat, so it's placed from its own map listing or street address."
        }
        switch place.tier {
        case .licensed:
            return place.source == "official"
                ? "From Florida's list of current food service licenses (DBPR). The open map data didn't have it, so its location comes from the license's street address."
                : "Matched to a current Florida DBPR food service license."
        case .confirmed, .listing:
            let rate = model.matchRate(for: place)
            let base = place.tier == .confirmed
                ? "A high-confidence listing in Overture's open map data."
                : "A single listing in Overture's open map data, so it may be closed or misfiled."
            let measured = rate.map { " Checked against Florida's restaurant licenses statewide, listings like this matched a current license \($0) of the time." } ?? ""
            return base + measured + (checked ? " It's also on our hand-checked list, checked against a 2025 or 2026 source." : "")
        }
    }

    // MARK: helpers

    private var shareText: String {
        [place.name, place.fullAddress, "via Florida Eats", Links.site.absoluteString].filter { !$0.isEmpty }.joined(separator: "\n")
    }

    private func lines(_ s: String?, prefix: String) -> [String] {
        (s ?? "").components(separatedBy: "; ").filter { !$0.isEmpty }.map { prefix + $0 }
    }

    private func section<Content: View>(_ title: String, @ViewBuilder _ content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(title.uppercased()).font(.caption.weight(.bold)).tracking(1).foregroundStyle(Theme.ink2)
            Divider()
            content()
        }
    }

    private func fact(_ label: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label).font(.subheadline.weight(.semibold)).foregroundStyle(Theme.ink)
            Text(value).font(.subheadline).foregroundStyle(Theme.ink2)
        }
    }

    @ViewBuilder
    private func kv(_ k: String, _ v: String?) -> some View {
        if let v {
            HStack(alignment: .firstTextBaseline) {
                Text(k).font(.subheadline).foregroundStyle(Theme.ink2)
                Spacer(minLength: 12)
                Text(v).font(.subheadline.weight(.semibold)).foregroundStyle(Theme.ink).multilineTextAlignment(.trailing)
            }
        }
    }
}

extension String {
    var nonEmpty: String? { isEmpty ? nil : self }
}
