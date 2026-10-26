import Foundation

/// The app's web pages and support address, in one place.
/// The site is GitHub Pages at the project address until florida.eatsranked.com resolves (Nick adds a Cloudflare CNAME
/// florida -> nickstrom5.github.io, DNS only; then scripts/make-site.py sets CUSTOM_DOMAIN). GitHub forwards these github.io
/// links to the custom domain after the switch, so a shipped build keeps working; point them at the new domain in the next update.
enum Links {
    static let site = URL(string: "https://nickstrom5.github.io/florida-eats/")!
    /// The app's data updates: scripts/publish_app_data.py writes docs/data/app/ (OTA-DATA.md).
    static let appData = URL(string: site.absoluteString + "data/app/")!
    static let privacy = URL(string: "https://nickstrom5.github.io/florida-eats/privacy.html")!
    static let terms = URL(string: "https://nickstrom5.github.io/florida-eats/terms.html")!
    /// DBPR's inspection search: a form, so no per-license link exists; the place shows its license number to search for
    static let dbprSearch = URL(string: "https://www.myfloridalicense.com/portalsearches/VerifyLicensee?Mode=0&BoardType=H")!
    static let dbprRecords = URL(string: "https://www2.myfloridalicense.com/hotels-restaurants/public-records/")!
    static let supportEmail = "nick@eatsranked.com"

    static var correctionEmail: URL {
        URL(string: "mailto:\(supportEmail)?subject=Florida%20Eats%20correction")!
    }

    // MARK: Share

    /// The web app. It opens a place's panel from the hash, explore/#p=<id> (readHash in scripts/explore.js), using the app's ids.
    static let explore = URL(string: site.absoluteString + "explore/")!

    /// What Share sends: the place's own page in the web app, never an Apple Maps or Google link (Apple Maps has its own button).
    /// The id is escaped the way the page's encodeURIComponent would escape it. A place the web app leaves out
    /// gets the web app's front page instead of a link that opens nothing.
    static func share(_ place: Place) -> URL {
        guard onWeb(place), let id = place.id.addingPercentEncoding(withAllowedCharacters: uriComponent),
              let url = URL(string: explore.absoluteString + "#p=" + id) else { return explore }
        return url
    }

    /// The text that goes with the link: the place, its town and the app. No street address, which Messages turns into a Maps link.
    static func shareMessage(_ place: Place) -> String {
        [place.name, place.city ?? ""].filter { !$0.isEmpty }.joined(separator: ", ") + ", on Florida Eats"
    }

    /// Whether the web app lists the place: make-site.py's ids.json (restaurants only: stadium stands and gas-station counters stay out).
    static func onWeb(_ place: Place) -> Bool { !place.isVenue }

    /// What encodeURIComponent leaves as is.
    private static let uriComponent = CharacterSet(charactersIn: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.!~*'()")
}
