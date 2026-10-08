import SwiftUI

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

/// Florida's one header element: a low coast-to-coast wave in orange, key lime and teal under the Home header.
struct WaveLine: View {
    var body: some View {
        Canvas { ctx, size in
            let w = size.width, h = size.height
            for (k, color) in [(0, Theme.gold), (1, Theme.lime), (2, Theme.green)] {
                let top = h * (0.18 + 0.26 * CGFloat(k)), amp = h * 0.16
                var p = Path()
                p.move(to: CGPoint(x: 0, y: h))
                p.addLine(to: CGPoint(x: 0, y: top))
                let n = 4
                for i in 0..<n {
                    let x0 = w * CGFloat(i) / CGFloat(n), x1 = w * CGFloat(i + 1) / CGFloat(n)
                    p.addCurve(to: CGPoint(x: x1, y: top), control1: CGPoint(x: x0 + (x1 - x0) / 3, y: top - amp),
                               control2: CGPoint(x: x0 + 2 * (x1 - x0) / 3, y: top + amp))
                }
                p.addLine(to: CGPoint(x: w, y: h)); p.closeSubpath()
                ctx.fill(p, with: .color(color))
            }
        }
        .accessibilityHidden(true)
    }
}

/// Condensed, heavy display type for titles and big numbers (the system font's compressed width). It scales with the
/// reader's text size, capped at 1.6× so a big number can't swallow its row.
struct DisplayFont: ViewModifier {
    let size: CGFloat
    var weight: Font.Weight = .black
    @ScaledMetric(relativeTo: .body) private var scale: CGFloat = 1

    func body(content: Content) -> some View {
        content.font(.system(size: size * min(scale, 1.6), weight: weight).width(.compressed))
    }
}

extension View {
    func displayFont(_ size: CGFloat, weight: Font.Weight = .black) -> some View {
        modifier(DisplayFont(size: size, weight: weight))
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
