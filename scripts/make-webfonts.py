"""The site's two fonts, self-hosted in docs/fonts/ (the pages' CSP allows only same-origin fonts):
- Archivo (variable weight and width), subset to Latin and saved as WOFF2. Archivo has no Reserved Font Name, so a subset is allowed.
- IBM Plex Mono Medium and SemiBold, copied unmodified: "Plex" is a Reserved Font Name under its SIL OFL 1.1, so no subset.
Sources: data/raw/fonts/ (github.com/google/fonts, ofl/archivo and ofl/ibmplexmono). Run once, and again only when the fonts change.
"""
import os, shutil
from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC, OUT = f"{ROOT}/data/raw/fonts", f"{ROOT}/docs/fonts"
os.makedirs(OUT, exist_ok=True)

LATIN = "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD"
opts = subset.Options()
opts.flavor = "woff2"
opts.layout_features = ["*"]
opts.name_IDs = ["*"]
opts.notdef_outline = True
font = TTFont(f"{SRC}/Archivo-Variable.ttf")
s = subset.Subsetter(opts)
s.populate(unicodes=subset.parse_unicodes(LATIN))
s.subset(font)
subset.save_font(font, f"{OUT}/archivo-latin.woff2", opts)

for f in ("IBMPlexMono-Medium.ttf", "IBMPlexMono-SemiBold.ttf"):
    shutil.copy(f"{SRC}/{f}", f"{OUT}/{f}")
shutil.copy(f"{SRC}/Archivo-OFL.txt", f"{OUT}/OFL-Archivo.txt")
shutil.copy(f"{SRC}/IBMPlexMono-OFL.txt", f"{OUT}/OFL-IBM-Plex-Mono.txt")
print({f: os.path.getsize(f"{OUT}/{f}") // 1024 for f in sorted(os.listdir(OUT))}, "KB")
