// Regenerates the brand images: the app icon, playbook/brand/, and the site's og.png, favicons and manifest icons.
// The icon (Nick's approval 2026-10-09, the Eats Ranked icon style shared by every state): a flat, level stone crab claw with its
// black-tipped pincer wide open, centred on flat Gulf teal, no wave and no tilt. `claw` is copied from
// ../state-prompts/icon-style/approved/fl/icon.swift; check the 1024 with ../state-prompts/icon-style/check.swift.
// It replaced the 2026-10-07 tilted claw over a wave (concept A of scripts/icon-concepts.swift).
// Usage: swift scripts/make-brand.swift ["50,000+"]   (run from fl-eats/; the argument is the restaurant count on the share image)
import AppKit
import CoreGraphics

let root = FileManager.default.currentDirectoryPath
func rgb(_ hex: UInt32, _ a: CGFloat = 1) -> CGColor {
    CGColor(srgbRed: CGFloat((hex >> 16) & 255) / 255, green: CGFloat((hex >> 8) & 255) / 255, blue: CGFloat(hex & 255) / 255, alpha: a)
}
let teal = rgb(0x006D77), white = rgb(0xFFFFFF), ink = rgb(0x0B3C49), sand = rgb(0xFBF5EA)
let orange = rgb(0xF28C28), lime = rgb(0xB5D46A)

func canvas(_ w: Int, _ h: Int, _ draw: (CGContext) -> Void) -> CGImage {
    let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0,
                        space: CGColorSpace(name: CGColorSpace.sRGB)!, bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
    ctx.setShouldAntialias(true); ctx.interpolationQuality = .high
    draw(ctx)
    return ctx.makeImage()!
}
func save(_ img: CGImage, _ path: String) {
    let url = URL(fileURLWithPath: root + "/" + path)
    try? FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
    try! NSBitmapImageRep(cgImage: img).representation(using: .png, properties: [:])!.write(to: url)
    print("wrote", path)
}

/// Florida's food: a stone crab claw. Draws inside (0,0)-(s,s), centred, and paints no background (the og.png call
/// `claw(c, 420)` keeps working). Design units are px of a 1024 canvas with the origin at the centre, y up.
func claw(_ c: CGContext, _ s: CGFloat) {
    let teal = rgb(0x006D77), orange = rgb(0xE8572A), cream = rgb(0xF7E4C8), black = rgb(0x17191A)
    func p(_ x: CGFloat, _ y: CGFloat) -> CGPoint { CGPoint(x: x, y: y) }
    func beyond(_ a: CGPoint, _ b: CGPoint) -> CGPath {   // the half-plane to the right of the line a -> b
        let m = CGMutablePath(); let dx = b.x - a.x, dy = b.y - a.y
        m.move(to: a); m.addLine(to: b); m.addLine(to: p(b.x + dy, b.y - dx)); m.addLine(to: p(a.x + dy, a.y - dx))
        m.closeSubpath(); return m
    }
    c.saveGState()
    c.translateBy(x: s / 2, y: s / 2); c.scaleBy(x: s / 1024, y: s / 1024)
    c.setLineJoin(.round); c.setLineCap(.round)

    // Palm: a small, squarish soft block.
    let palm = CGPath(roundedRect: CGRect(x: -370, y: -238, width: 338, height: 436), cornerWidth: 120, cornerHeight: 120, transform: nil)
    // Fixed (lower) finger: leaves the palm's flat underside and curls up to a point.
    let fixed = CGMutablePath()
    fixed.move(to: p(-272, -238))
    fixed.addCurve(to: p(80, -199), control1: p(-153, -247), control2: p(-33, -235))
    fixed.addCurve(to: p(237, -128), control1: p(135, -181), control2: p(188, -158))
    fixed.addCurve(to: p(360, -6), control1: p(281, -98), control2: p(349, -62))
    fixed.addCurve(to: p(-232, -13), control1: p(172, -78), control2: p(-42, -84))
    fixed.closeSubpath()
    // Movable (upper) finger: hinged at the palm's top front, opened wide, curling down to a point.
    let dactyl = CGMutablePath()
    dactyl.move(to: p(-202, 89))
    dactyl.addCurve(to: p(86, 236), control1: p(-124, 166), control2: p(-23, 219))
    dactyl.addCurve(to: p(240, 232), control1: p(137, 243), control2: p(190, 243))
    dactyl.addCurve(to: p(370, 149), control1: p(285, 220), control2: p(361, 202))
    dactyl.addCurve(to: p(-35, -51), control1: p(210, 169), control2: p(42, 93))
    dactyl.closeSubpath()
    // Black tips: each finger beyond a cut straight across it, about 63% of the way out.
    let fixedBlack = beyond(p(293, -677), p(-20, 481))
    let dactylBlack = beyond(p(261, -432), p(65, 751))
    // Cream underside: below one hard curve across the palm and the fixed finger.
    let belly = CGMutablePath()
    belly.move(to: p(-500, -75)); belly.addCurve(to: p(491, -195), control1: p(-206, -118), control2: p(99, -200))
    belly.addLine(to: p(491, -512)); belly.addLine(to: p(-500, -512)); belly.closeSubpath()

    // 1. The palm and the fixed finger (one piece of shell): orange, the cream underside, the fixed finger's black tip.
    c.setFillColor(orange); c.addPath(palm); c.fillPath(); c.addPath(fixed); c.fillPath()
    c.setFillColor(cream)
    for part in [palm, fixed as CGPath] { c.saveGState(); c.addPath(part); c.clip(); c.addPath(belly); c.fillPath(); c.restoreGState() }
    c.saveGState(); c.addPath(fixed); c.clip(); c.setFillColor(black); c.addPath(fixedBlack); c.fillPath(); c.restoreGState()
    // 2. A 13 px Gulf-teal ring around the movable finger where it overlaps the palm (STYLE R7), so it reads as a hinged part.
    c.saveGState(); c.addPath(palm); c.clip()
    c.setStrokeColor(teal); c.setLineWidth(26); c.addPath(dactyl); c.strokePath()
    c.restoreGState()
    // 3. The movable finger on top, with its black tip.
    c.setFillColor(orange); c.addPath(dactyl); c.fillPath()
    c.saveGState(); c.addPath(dactyl); c.clip(); c.setFillColor(black); c.addPath(dactylBlack); c.fillPath(); c.restoreGState()
    c.restoreGState()
}

func icon(_ size: Int) -> CGImage {
    canvas(size, size) { c in let s = CGFloat(size); c.setFillColor(teal); c.fill(CGRect(x: 0, y: 0, width: s, height: s)); claw(c, s) }
}

func text(_ c: CGContext, _ str: String, font: NSFont, color: CGColor, at p: CGPoint) {
    let attr = NSAttributedString(string: str, attributes: [.font: font, .foregroundColor: NSColor(cgColor: color)!])
    c.textPosition = p
    CTLineDraw(CTLineCreateWithAttributedString(attr), c)
}
func heavy(_ size: CGFloat) -> NSFont {
    NSFont(name: "HelveticaNeue-CondensedBlack", size: size) ?? NSFont.systemFont(ofSize: size, weight: .black)
}

let appIcon = icon(1024)
save(appIcon, "FloridaEats/Resources/Assets.xcassets/AppIcon.appiconset/icon-1024.png")
save(appIcon, "playbook/brand/icon-1024.png")
save(icon(512), "docs/icon-512.png")
save(icon(192), "docs/icon-192.png")
save(icon(180), "docs/apple-touch-icon.png")
save(icon(32), "docs/favicon-32.png")

let count = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "50,000+"
let og = canvas(1200, 630) { c in
    c.setFillColor(teal); c.fill(CGRect(x: 0, y: 0, width: 1200, height: 630))
    c.setFillColor(orange); c.fill(CGRect(x: 72, y: 470, width: 90, height: 12))
    text(c, "FLORIDA", font: heavy(128), color: white, at: CGPoint(x: 66, y: 322))
    text(c, "EATS", font: heavy(128), color: sand, at: CGPoint(x: 66, y: 204))
    text(c, "Cuban, seafood & more · \(count) Florida restaurants", font: NSFont.systemFont(ofSize: 32, weight: .semibold), color: white, at: CGPoint(x: 70, y: 150))
    text(c, "Free for iPhone and iPad", font: NSFont.systemFont(ofSize: 30, weight: .regular), color: sand, at: CGPoint(x: 70, y: 96))
    c.saveGState(); c.translateBy(x: 760, y: 120); claw(c, 420); c.restoreGState()
    for (k, col) in [(0, orange), (1, lime)] { c.setFillColor(col); c.fill(CGRect(x: 0, y: CGFloat(k) * 6, width: 1200, height: 6)) }
}
save(og, "docs/og.png")
