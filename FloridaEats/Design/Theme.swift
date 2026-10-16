import SwiftUI
import UIKit
import CoreText

/// Florida landscape palette (Nick's pick, 2026-10-07), light only: Gulf teal #006D77 (6.1:1 on white), citrus orange #F28C28 and
/// key lime #B5D46A (fills only: as text on white they fail contrast), ink #0B3C49, sand #FBF5EA. No team colors: Florida's loyalties split.
/// The names `green`/`gold` are kept from Wisconsin Eats so the shared views read the same; here `green` is the Gulf teal and `gold` the orange.
enum Theme {
    static let green = Color(hex: 0x006D77)      // Gulf teal: titles, tint, primary text accents
    static let green2 = Color(hex: 0x0B5961)
    static let gold = Color(hex: 0xF28C28)       // citrus orange: fills only
    static let goldSoft = Color(hex: 0xFDE3C6)
    static let lime = Color(hex: 0xB5D46A)       // key lime: fills only
    static let limeSoft = Color(hex: 0xE9F3CF)
    static let sand = Color(hex: 0xFBF5EA)
    static let red = Color(hex: 0xB3261E)        // MICHELIN chips and Facility Temporarily Closed results only
    static let ink = Color(hex: 0x0B3C49)
    static let ink2 = Color(hex: 0x28525E)
    static let muted = Color(hex: 0x4A666D)
    static let surface = Color.white
    static let surface2 = Color(hex: 0xF4F8F7)
    static let surface3 = Color(hex: 0xE2ECEA)
    static let rule = Color(hex: 0xD9E5E3)
    static let rule2 = Color(hex: 0xB0C7C5)
}

extension Color {
    init(hex: UInt32) {
        self.init(red: Double((hex >> 16) & 0xFF) / 255, green: Double((hex >> 8) & 0xFF) / 255, blue: Double(hex & 0xFF) / 255)
    }
}

/// A small uppercase label: "STONE CRAB", "1 MICHELIN STAR".
struct Chip: View {
    enum Style { case gold, green, red, plain, dashed }
    let text: String
    var style: Style = .plain

    var body: some View {
        Text(text.uppercased())
            .font(.caption2.weight(.bold))
            .tracking(0.4)
            .padding(.horizontal, 7).padding(.vertical, 3)
            .foregroundStyle(style == .green || style == .red ? Color.white : style == .dashed ? Theme.muted : style == .gold ? Theme.ink : Theme.green)
            .background {
                RoundedRectangle(cornerRadius: 5).fill(style == .gold ? Theme.goldSoft : style == .green ? Theme.green : style == .red ? Theme.red
                                                       : style == .dashed ? .clear : Theme.surface2)
            }
            .overlay {
                if style == .dashed { RoundedRectangle(cornerRadius: 5).strokeBorder(Theme.rule2, style: StrokeStyle(lineWidth: 1, dash: [3, 2])) }
            }
            .accessibilityLabel(text)
    }
}

/// DBPR's own result group for a visit, as recorded: Met Inspection Standards, Follow-Up Inspection Required or Facility Temporarily
/// Closed. Florida doesn't grade restaurants ("establishments are not graded or rated") and the app computes no grade.
struct ResultBadge: View {
    let result: InspectionResult
    var large = false

    var body: some View {
        Text(result.label.uppercased())
            .font(large ? .footnote.weight(.heavy) : .caption2.weight(.heavy))
            .tracking(0.4)
            .multilineTextAlignment(.leading)
            .padding(.horizontal, large ? 10 : 7).padding(.vertical, large ? 6 : 3)
            .foregroundStyle(result.ink)
            .background(RoundedRectangle(cornerRadius: 6).fill(result.fill))
            .accessibilityLabel("DBPR result: \(result.label)")
    }
}

/// Florida Eats' lettering (Nick's pick, 2026-10-09: the Postcard setup with the Gulf Chart lettering). Archivo, a variable grotesque,
/// drawn condensed and heavy for titles and guide names; IBM Plex Mono for numbers, dates and small labels. Both SIL OFL 1.1, bundled in
/// Resources/Fonts (licenses in Resources/Licenses, listed on About).
enum BrandFont {
    /// Archivo at a weight (100–900) and width (62–125) from its variable axes; the default instance is "Archivo-SemiBold".
    static func archivo(_ size: CGFloat, weight: CGFloat, width: CGFloat = 68) -> Font {
        let axes: [NSNumber: CGFloat] = [NSNumber(value: 0x7767_6874): weight, NSNumber(value: 0x7764_7468): width]   // 'wght', 'wdth'
        let d = UIFontDescriptor(name: "Archivo-SemiBold", size: size)
            .addingAttributes([UIFontDescriptor.AttributeName(rawValue: kCTFontVariationAttribute as String): axes])
        return Font(UIFont(descriptor: d, size: size) as CTFont)
    }

    static func wght(_ w: Font.Weight) -> CGFloat {
        switch w {
        case .black: 850
        case .heavy: 780
        case .bold: 700
        case .semibold: 620
        case .medium: 540
        default: 460
        }
    }
}

/// Condensed, heavy display type for titles and guide names (Archivo). It scales with the reader's text size, capped at 1.6× so a big
/// title can't swallow its row.
struct DisplayFont: ViewModifier {
    let size: CGFloat
    var weight: Font.Weight = .black
    @ScaledMetric(relativeTo: .body) private var scale: CGFloat = 1

    func body(content: Content) -> some View {
        content.font(BrandFont.archivo(size * min(scale, 1.6), weight: BrandFont.wght(weight)))
    }
}

/// Numbers, dates and small labels in IBM Plex Mono, scaled like DisplayFont.
struct MonoFont: ViewModifier {
    let size: CGFloat
    var weight: Font.Weight = .semibold
    @ScaledMetric(relativeTo: .body) private var scale: CGFloat = 1

    func body(content: Content) -> some View {
        content.font(.custom(weight == .medium || weight == .regular ? "IBMPlexMono-Medium" : "IBMPlexMono-SemiBold", fixedSize: size * min(scale, 1.6)))
    }
}

extension View {
    func displayFont(_ size: CGFloat, weight: Font.Weight = .black) -> some View {
        modifier(DisplayFont(size: size, weight: weight))
    }

    func monoFont(_ size: CGFloat, weight: Font.Weight = .semibold) -> some View {
        modifier(MonoFont(size: size, weight: weight))
    }
}

/// The Postcard setup's three stripes (teal, orange, key lime) under the Home title, like an old motel sign.
struct Stripes: View {
    var height: CGFloat = 6

    var body: some View {
        VStack(spacing: 3) {
            ForEach([Theme.green, Theme.gold, Theme.lime], id: \.self) { c in Capsule().fill(c).frame(height: height) }
        }
        .accessibilityHidden(true)
    }
}

extension View {
    /// An inline navigation title in the display type. UINavigationBar.appearance() didn't reach every SwiftUI bar on iOS 27
    /// (the Map title went from compressed blue to plain black after a push and pop; place titles were always plain), so the
    /// title is our own view in the bar. The navigation title is still set, for the back button and VoiceOver.
    func inlineTitle(_ title: String) -> some View {
        navigationTitle(title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .principal) {
                    Text(title).displayFont(19, weight: .heavy).foregroundStyle(Theme.green)
                        .lineLimit(1).minimumScaleFactor(0.7)
                        .accessibilityAddTraits(.isHeader)
                }
            }
    }
}
