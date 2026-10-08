// Regenerates the brand images: the app icon (a flat stone crab claw on Gulf teal with a low wave, Nick's pick 2026-10-07, concept A
// of scripts/icon-concepts.swift), playbook/brand/, and the site's og.png, favicons and manifest icons.
// Usage: swift scripts/make-brand.swift ["50,000+"]   (run from fl-eats/; the argument is the restaurant count on the share image)
import AppKit
import CoreGraphics

let root = FileManager.default.currentDirectoryPath
func rgb(_ hex: UInt32, _ a: CGFloat = 1) -> CGColor {
    CGColor(srgbRed: CGFloat((hex >> 16) & 255) / 255, green: CGFloat((hex >> 8) & 255) / 255, blue: CGFloat(hex & 255) / 255, alpha: a)
}
let teal = rgb(0x006D77), teal2 = rgb(0x0B7F89), white = rgb(0xFFFFFF), ink = rgb(0x0B3C49), sand = rgb(0xFBF5EA)
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
func P(_ s: CGFloat, _ x: CGFloat, _ y: CGFloat) -> CGPoint { CGPoint(x: x * s, y: y * s) }

/// The ground: Gulf teal with one low, lighter wave along the bottom.
func ground(_ c: CGContext, _ s: CGFloat) {
    c.setFillColor(teal); c.fill(CGRect(x: 0, y: 0, width: s, height: s))
    let w = CGMutablePath()
    w.move(to: P(s, 0, 0)); w.addLine(to: P(s, 0, 0.14))
    w.addCurve(to: P(s, 0.5, 0.14), control1: P(s, 0.16, 0.21), control2: P(s, 0.34, 0.21))
    w.addCurve(to: P(s, 1.0, 0.14), control1: P(s, 0.66, 0.07), control2: P(s, 0.84, 0.07))
    w.addLine(to: P(s, 1, 0)); w.closeSubpath()
    c.setFillColor(teal2); c.addPath(w); c.fillPath()
}

/// A: a stone crab claw, flat: orange palm with a cream underside, thick black-tipped pincers, a small joint at the base.
func claw(_ c: CGContext, _ s: CGFloat) {
    c.saveGState()
    c.translateBy(x: s * 0.53, y: s * 0.53); c.rotate(by: 0.70); c.scaleBy(x: s * 1.02, y: s * 1.02)   // local units: claw points along +x
    let orange = rgb(0xE8572A), orange2 = rgb(0xC4401A), cream = rgb(0xF7E4C8), black = rgb(0x17191A)
    c.setFillColor(orange2); c.fillEllipse(in: CGRect(x: -0.50, y: -0.10, width: 0.20, height: 0.20))   // the joint
    let lower = CGMutablePath()
    lower.move(to: CGPoint(x: -0.02, y: -0.18))
    lower.addCurve(to: CGPoint(x: 0.42, y: -0.015), control1: CGPoint(x: 0.18, y: -0.19), control2: CGPoint(x: 0.37, y: -0.12))
    lower.addCurve(to: CGPoint(x: 0.31, y: -0.035), control1: CGPoint(x: 0.40, y: 0.012), control2: CGPoint(x: 0.35, y: -0.02))
    lower.addCurve(to: CGPoint(x: 0.02, y: -0.005), control1: CGPoint(x: 0.21, y: -0.05), control2: CGPoint(x: 0.10, y: -0.03))
    lower.closeSubpath()
    let upper = CGMutablePath()
    upper.move(to: CGPoint(x: -0.06, y: 0.18))
    upper.addCurve(to: CGPoint(x: 0.42, y: 0.035), control1: CGPoint(x: 0.15, y: 0.23), control2: CGPoint(x: 0.37, y: 0.15))
    upper.addCurve(to: CGPoint(x: 0.31, y: 0.05), control1: CGPoint(x: 0.41, y: 0.012), control2: CGPoint(x: 0.35, y: 0.035))
    upper.addCurve(to: CGPoint(x: 0.02, y: 0.045), control1: CGPoint(x: 0.21, y: 0.07), control2: CGPoint(x: 0.10, y: 0.06))
    upper.closeSubpath()
    for f in [lower, upper] {
        c.saveGState(); c.addPath(f); c.clip()
        c.setFillColor(orange); c.fill(CGRect(x: -1, y: -1, width: 2, height: 2))
        c.setFillColor(black); c.fill(CGRect(x: 0.25, y: -1, width: 1, height: 2))   // the black tips
        c.restoreGState()
    }
    let palm = CGPath(ellipseIn: CGRect(x: -0.40, y: -0.20, width: 0.52, height: 0.40), transform: nil)
    c.saveGState(); c.addPath(palm); c.clip()
    c.setFillColor(orange); c.fill(CGRect(x: -1, y: -1, width: 2, height: 2))
    let belly = CGMutablePath()
    belly.move(to: CGPoint(x: -0.45, y: -0.08)); belly.addCurve(to: CGPoint(x: 0.16, y: -0.10), control1: CGPoint(x: -0.24, y: -0.15), control2: CGPoint(x: 0.0, y: -0.15))
    belly.addLine(to: CGPoint(x: 0.16, y: -0.3)); belly.addLine(to: CGPoint(x: -0.45, y: -0.3)); belly.closeSubpath()
    c.setFillColor(cream); c.addPath(belly); c.fillPath()
    c.restoreGState()
    c.setFillColor(orange2)
    for (x, y, r) in [(-0.20, 0.09, 0.024), (-0.07, 0.11, 0.018), (-0.27, 0.01, 0.016), (0.02, 0.05, 0.015)] as [(CGFloat, CGFloat, CGFloat)] {
        c.fillEllipse(in: CGRect(x: x - r, y: y - r, width: r * 2, height: r * 2))
    }
    c.restoreGState()
}

func icon(_ size: Int) -> CGImage {
    canvas(size, size) { c in let s = CGFloat(size); ground(c, s); claw(c, s) }
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
