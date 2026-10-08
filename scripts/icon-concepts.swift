// Icon concepts for the Florida app (2026-10-07), flat (no gloss, no gradients), drawn in code, food only, no text.
// A: stone crab claw · B: pressed Cuban sandwich cut on the diagonal · C: key lime pie slice with a lime wheel.
// Ground: Gulf teal with a low wave. Palette: teal #006D77, citrus orange #F28C28, key-lime #B5D46A, ink #0B3C49, sand #FBF5EA.
// Usage: swift scripts/icon-concepts.swift   (run from fl-eats/) -> playbook/brand/concepts.png and concept-<x>-1024.png
import AppKit
import CoreGraphics

let root = FileManager.default.currentDirectoryPath
func rgb(_ hex: UInt32, _ a: CGFloat = 1) -> CGColor {
    CGColor(srgbRed: CGFloat((hex >> 16) & 255) / 255, green: CGFloat((hex >> 8) & 255) / 255, blue: CGFloat(hex & 255) / 255, alpha: a)
}
let teal = rgb(0x006D77), teal2 = rgb(0x0B7F89), white = rgb(0xFFFFFF), ink = rgb(0x0B3C49), sand = rgb(0xFBF5EA)

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
func poly(_ c: CGContext, _ s: CGFloat, _ pts: [(CGFloat, CGFloat)], _ color: CGColor) {
    let p = CGMutablePath(); p.move(to: P(s, pts[0].0, pts[0].1)); for q in pts.dropFirst() { p.addLine(to: P(s, q.0, q.1)) }; p.closeSubpath()
    c.setFillColor(color); c.addPath(p); c.fillPath()
}

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

/// B: a pressed Cuban sandwich cut on the diagonal: two flat halves, staggered, the front one showing its layers.
func half(_ c: CGContext, _ s: CGFloat, _ dx: CGFloat, _ dy: CGFloat) {
    let crust = rgb(0xC98532), crustTop = rgb(0xE0A048), press = rgb(0x9A5E1E), crumb = rgb(0xF3DDB0)
    let ham = rgb(0xE77F8B), pork = rgb(0xC98A5E), swiss = rgb(0xF4D35E), pickle = rgb(0x5E8C31), mustard = rgb(0xE5B000)
    let x0: CGFloat = 0.10 + dx, x1: CGFloat = 0.68 + dx, y0: CGFloat = 0.24 + dy, sk: CGFloat = 0.12, dep: (CGFloat, CGFloat) = (0.15, 0.09)
    let layers: [(CGFloat, CGColor)] = [(0.04, crust), (0.018, crumb), (0.014, mustard), (0.035, pork), (0.035, ham), (0.022, swiss), (0.02, pickle), (0.018, crumb), (0.04, crust)]
    var y = y0
    for (h, col) in layers {
        poly(c, s, [(x0, y), (x1, y + sk), (x1, y + sk + h), (x0, y + h)], col)
        y += h
    }
    poly(c, s, [(x1, y0 + sk), (x1 + dep.0, y0 + sk + dep.1), (x1 + dep.0, y + sk + dep.1), (x1, y + sk)], crust)   // far end
    poly(c, s, [(x0, y), (x1, y + sk), (x1 + dep.0, y + sk + dep.1), (x0 + dep.0, y + dep.1)], crustTop)          // pressed top
    c.setStrokeColor(press); c.setLineWidth(s * 0.016); c.setLineCap(.round)
    for k in 1..<5 {
        let f = CGFloat(k) / 5
        c.move(to: P(s, x0 + f * (x1 - x0) + 0.02, y + f * sk + 0.012)); c.addLine(to: P(s, x0 + f * (x1 - x0) + dep.0 - 0.02, y + f * sk + dep.1 - 0.012)); c.strokePath()
    }
}
func cuban(_ c: CGContext, _ s: CGFloat) {
    half(c, s, 0.10, 0.20)   // the back half
    half(c, s, 0.0, 0.0)     // the front half
}

/// C: a slice of key lime pie (graham crust, pale lime filling, whipped cream) with a lime wheel.
func pie(_ c: CGContext, _ s: CGFloat) {
    let crust = rgb(0xC98F4E), crust2 = rgb(0xAE7638), fill = rgb(0xEEF0A0), fillSide = rgb(0xDCE38A), cream = rgb(0xFFFFFF)
    // the lime wheel standing behind the slice
    let cx: CGFloat = 0.66, cy: CGFloat = 0.62, r: CGFloat = 0.20
    c.setFillColor(rgb(0x3F8A2A)); c.fillEllipse(in: CGRect(x: s * (cx - r), y: s * (cy - r), width: s * 2 * r, height: s * 2 * r))
    c.setFillColor(rgb(0xF4F7D8)); c.fillEllipse(in: CGRect(x: s * (cx - r * 0.86), y: s * (cy - r * 0.86), width: s * 1.72 * r, height: s * 1.72 * r))
    c.setFillColor(rgb(0xB5D46A))
    for k in 0..<8 {   // eight segments
        let a0 = CGFloat(k) * .pi / 4 + 0.07, a1 = CGFloat(k + 1) * .pi / 4 - 0.07
        let seg = CGMutablePath()
        seg.move(to: P(s, cx + 0.12 * r * cos((a0 + a1) / 2), cy + 0.12 * r * sin((a0 + a1) / 2)))
        seg.addArc(center: P(s, cx, cy), radius: s * r * 0.76, startAngle: a0, endAngle: a1, clockwise: false)
        seg.closeSubpath(); c.addPath(seg); c.fillPath()
    }
    // the slice: point at the lower left, back edge to the right; a side face shows filling over crust
    let tip = (0.10, 0.30), backL = (0.52, 0.52), backR = (0.80, 0.30)
    poly(c, s, [(tip.0, tip.1), (backR.0, backR.1), (backR.0, backR.1 - 0.10), (tip.0, tip.1 - 0.06)], fillSide)
    poly(c, s, [(tip.0, tip.1 - 0.06), (backR.0, backR.1 - 0.10), (backR.0, backR.1 - 0.16), (tip.0 + 0.01, tip.1 - 0.10)], crust)
    poly(c, s, [(tip.0 + 0.01, tip.1 - 0.10), (backR.0, backR.1 - 0.16), (backR.0, backR.1 - 0.18), (tip.0 + 0.03, tip.1 - 0.11)], crust2)
    poly(c, s, [(tip.0, tip.1), (backL.0, backL.1), (backR.0, backR.1)], fill)
    // the crust's rim along the back
    let rim = CGMutablePath()
    rim.move(to: P(s, backL.0 - 0.02, backL.1 + 0.005)); rim.addLine(to: P(s, backR.0 + 0.01, backR.1 - 0.005))
    c.setStrokeColor(crust); c.setLineWidth(s * 0.05); c.setLineCap(.round); c.addPath(rim); c.strokePath()
    // whipped cream: three overlapping puffs
    c.setFillColor(cream)
    for (x, y, rr) in [(0.50, 0.44, 0.065), (0.58, 0.47, 0.06), (0.54, 0.51, 0.05)] as [(CGFloat, CGFloat, CGFloat)] {
        c.fillEllipse(in: CGRect(x: s * (x - rr), y: s * (y - rr * 0.8), width: s * 2 * rr, height: s * 1.6 * rr))
    }
}

let concepts: [(String, String, (CGContext, CGFloat) -> Void)] = [("a", "A · Stone crab claw", claw), ("b", "B · Cuban sandwich", cuban), ("c", "C · Key lime pie", pie)]
func icon(_ size: Int, _ f: (CGContext, CGFloat) -> Void) -> CGImage {
    canvas(size, size) { c in let s = CGFloat(size); ground(c, s); f(c, s) }
}
let sheet = canvas(1060, 3 * 600 + 40) { c in
    c.setFillColor(white); c.fill(CGRect(x: 0, y: 0, width: 1060, height: 3 * 600 + 40))
    for (i, (_, label, f)) in concepts.enumerated() {
        let y0 = CGFloat(3 * 600 + 40 - (i + 1) * 600)
        let mask = CGPath(roundedRect: CGRect(x: 0, y: 0, width: 1, height: 1), cornerWidth: 0.225, cornerHeight: 0.225, transform: nil)
        for (sz, x) in [(512, 40), (180, 600), (60, 840)] {
            let img = icon(sz, f)
            c.saveGState()
            var t = CGAffineTransform(scaleX: CGFloat(sz), y: CGFloat(sz)).translatedBy(x: CGFloat(x) / CGFloat(sz), y: (y0 + 40) / CGFloat(sz))
            c.addPath(mask.copy(using: &t)!); c.clip()
            c.draw(img, in: CGRect(x: CGFloat(x), y: y0 + 40, width: CGFloat(sz), height: CGFloat(sz)))
            c.restoreGState()
        }
        let attr = NSAttributedString(string: label, attributes: [.font: NSFont.systemFont(ofSize: 30, weight: .bold), .foregroundColor: NSColor(cgColor: ink)!])
        c.textPosition = CGPoint(x: 600, y: y0 + 470); CTLineDraw(CTLineCreateWithAttributedString(attr), c)
        let sub = NSAttributedString(string: "512 · 180 · 60 px", attributes: [.font: NSFont.systemFont(ofSize: 22, weight: .regular), .foregroundColor: NSColor(cgColor: ink)!])
        c.textPosition = CGPoint(x: 600, y: y0 + 432); CTLineDraw(CTLineCreateWithAttributedString(sub), c)
    }
}
save(sheet, "playbook/brand/concepts.png")
for (k, _, f) in concepts { save(icon(1024, f), "playbook/brand/concept-\(k)-1024.png") }
