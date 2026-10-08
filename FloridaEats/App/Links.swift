import Foundation

/// The app's web pages and support address, in one place.
/// The site is GitHub Pages at the project address until florida.eatsranked.com resolves (Nick adds a Cloudflare CNAME
/// florida -> nickstrom5.github.io, DNS only; then scripts/make-site.py sets CUSTOM_DOMAIN). GitHub forwards these github.io
/// links to the custom domain after the switch, so a shipped build keeps working; point them at the new domain in the next update.
enum Links {
    static let site = URL(string: "https://nickstrom5.github.io/florida-eats/")!
    static let privacy = URL(string: "https://nickstrom5.github.io/florida-eats/privacy.html")!
    static let terms = URL(string: "https://nickstrom5.github.io/florida-eats/terms.html")!
    /// DBPR's inspection search: a form, so no per-license link exists; the place shows its license number to search for
    static let dbprSearch = URL(string: "https://www.myfloridalicense.com/portalsearches/VerifyLicensee?Mode=0&BoardType=H")!
    static let dbprRecords = URL(string: "https://www2.myfloridalicense.com/hotels-restaurants/public-records/")!
    static let supportEmail = "work-with-nick@gmail.com"

    static var correctionEmail: URL {
        URL(string: "mailto:\(supportEmail)?subject=Florida%20Eats%20correction")!
    }
}
