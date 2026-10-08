"""Street address keys for Florida, so a DBPR license ("10775 NW 27 AVE"), an Overture place ("10775 Northwest 27th Avenue") and an
Overture address point ("10775 NW 27TH AVE") land on the same key.

street_key("10775 NW 27TH AVE STE 4") -> ("10775", "NW 27 AVE")   (number, street with directions and type)
core_key(...)                          -> ("10775", "27")          (fallback: no directions, no type)
Miami-Dade's grid repeats a number on NW/SW and ST/AVE/CT/TER streets, so the full key always comes first and the core key is only used
when it is unique within the zip.
"""
import re

DIRW = {"NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W", "NORTHWEST": "NW", "NORTHEAST": "NE", "SOUTHWEST": "SW", "SOUTHEAST": "SE",
        "N.": "N", "S.": "S", "E.": "E", "W.": "W", "N.W.": "NW", "N.E.": "NE", "S.W.": "SW", "S.E.": "SE"}
DIRS = {"N", "S", "E", "W", "NW", "NE", "SW", "SE"}
TYPEW = {"STREET": "ST", "STR": "ST", "AVENUE": "AVE", "AV": "AVE", "AVN": "AVE", "BOULEVARD": "BLVD", "BLV": "BLVD", "BL": "BLVD", "ROAD": "RD",
         "DRIVE": "DR", "DRV": "DR", "LANE": "LN", "COURT": "CT", "PLACE": "PL", "PARKWAY": "PKWY", "PKY": "PKWY", "PKWAY": "PKWY",
         "TERRACE": "TER", "TERR": "TER", "TRAIL": "TRL", "TR": "TRL", "HIGHWAY": "HWY", "HWAY": "HWY", "CIRCLE": "CIR", "CAUSEWAY": "CSWY",
         "PLAZA": "PLZ", "PZ": "PLZ", "SQUARE": "SQ", "EXPRESSWAY": "EXPY", "TURNPIKE": "TPKE", "CROSSING": "XING", "POINT": "PT",
         "PIKE": "PIKE", "LOOP": "LOOP", "WAY": "WAY", "ROW": "ROW", "RUN": "RUN", "PASS": "PASS", "PATH": "PATH", "WALK": "WALK",
         "MALL": "MALL", "CENTER": "CTR", "CENTRE": "CTR", "CTR": "CTR", "ISLE": "ISLE", "KEY": "KEY", "COVE": "CV", "BEND": "BND",
         "ALLEY": "ALY", "HARBOR": "HBR", "LANDING": "LNDG", "ESTATES": "ESTS", "PROMENADE": "PROM", "BYPASS": "BYP", "EXTENSION": "EXT"}
TYPES = set(TYPEW.values()) | {"ST", "AVE", "BLVD", "RD", "DR", "LN", "CT", "PL", "PKWY", "TER", "TRL", "HWY", "CIR", "CSWY", "PLZ", "SQ", "XING"}
ORD = {"FIRST": "1", "SECOND": "2", "THIRD": "3", "FOURTH": "4", "FIFTH": "5", "SIXTH": "6", "SEVENTH": "7", "EIGHTH": "8", "NINTH": "9",
       "TENTH": "10", "ELEVENTH": "11", "TWELFTH": "12"}
UNIT = re.compile(r"\s(?:(?:STE|SUITE|UNIT|APT|PMB|DEPT|TRLR)\b|#|(?:BLDG|BLD|BUILDING|SPACE|SP|SPC|BAY|LOT|KIOSK|FLOOR|FL|FLR|RM|ROOM|STALL|SHOP|BOOTH)\s*#?\s*[A-Z]?-?\d).*$")


def road(a):
    """One spelling for numbered roads: US HWY 1 = US-1 = U.S. 1 -> 'US 1'; STATE ROAD 70 = SR-70 = FL-70 -> 'SR 70'; COUNTY ROAD 581 -> 'CR 581'."""
    a = a.upper()
    a = re.sub(r"\bU\.?\s?S\.?(?=\s|-)", "US", a)
    a = re.sub(r"\b(US|SR|CR|FL|I)-(\w)", r"\1 \2", a)
    a = re.sub(r"\bUS\s+(?:HIGHWAY|HWY|ROUTE|RTE|RT)\b", "US", a)
    a = re.sub(r"\b(?:STATE\s+(?:ROAD|RD|HIGHWAY|HWY|ROUTE|RT|RTE)|ST\s+RD|FL\s+(?:HWY|HIGHWAY|STATE ROAD)|FLORIDA\s+(?:HWY|HIGHWAY|STATE ROAD)|FL(?=\s+\d)|SR)\b", "SR", a)
    a = re.sub(r"\b(?:COUNTY\s+(?:ROAD|RD|HIGHWAY|HWY|ROUTE)|CO\s+(?:RD|ROAD|HWY)|CTY\s+(?:RD|ROAD|HWY)|CR)\b", "CR", a)
    a = re.sub(r"\b(?:HIGHWAY|HWY|SR|STATE ROAD)\s+A\s?1\s?A\b|\bA\s1\sA\b", "A1A", a)
    a = re.sub(r"\bINTERSTATE\b", "I", a)
    # a bare "HWY 98" is US 98 for Florida's US highway numbers (Red Pirate's license says "236 HWY 98", its listing "236 US Highway 98");
    # other bare numbers ("HWY 50", "HWY 60") are state roads and stay as they are
    a = re.sub(r"(?<!US )(?<!SR )(?<!CR )\b(?:HWY|HIGHWAY)\s+(?=(?:1|17|19|27|29|41|90|92|98|129|221|231|301|319|331|441)\b)", "US ", a)
    a = re.sub(r"(?<!US )(?<!SR )(?<!CR )(?<!I )\b(?:HWY|HIGHWAY)\s+(?=\d)", "SR ", a)
    # one spelling for compound names: OCEAN SHORE = OCEANSHORE, BAY SHORE = BAYSHORE, GULF VIEW = GULFVIEW (Flagler Fish Company's
    # listing says "1224 S Ocean Shore Blvd", its license "1224 S OCEANSHORE BLVD")
    a = re.sub(r"\b(OCEAN|BAY|LAKE|SEA|RIVER|GULF|CREEK|HARBOR|PALM)\s+(SHORE|SHORES|VIEW|BREEZE|SIDE|FRONT|WAY)\b", r"\1\2", a)
    return a


def _words(street):
    s = road(street)
    s = re.sub(r"[.,]", " ", s.replace("N.W.", "NW").replace("N.E.", "NE").replace("S.W.", "SW").replace("S.E.", "SE"))
    s = re.sub(r"[^A-Z0-9 /&-]", " ", s)
    out = []
    for w in s.split():
        w = DIRW.get(w, w)
        w = TYPEW.get(w, w)
        w = ORD.get(w, w)
        w = re.sub(r"^(\d+)(?:ST|ND|RD|TH)$", r"\1", w)
        out.append(w)
    return out


def split_num(a):
    """'10775 NW 27 AVE STE 4' -> ('10775', 'NW 27 AVE'). Ranges '157-159 Main St' -> ('157', ...). Grid-style '7S 100E' kept whole."""
    if not isinstance(a, str):
        return None, None
    a = re.sub(r"\s+", " ", a.upper()).strip()
    a = UNIT.sub("", " " + a).strip()
    m = re.match(r"^(\d+)[A-Z]?(?:\s*-\s*\d+[A-Z]?)?(?:\s+1/2)?\s+(.+)$", a)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def street_key(a):
    num, rest = split_num(a)
    if not num:
        return None, None
    w = _words(rest)
    # cut anything after the street type (e.g. "MAIN ST BUILDING 4", "OCEAN DR SOUTH TOWER")
    for i, x in enumerate(w):
        if x in TYPES and i > 0:
            w = w[: i + 1] + ([w[i + 1]] if i + 1 < len(w) and w[i + 1] in DIRS else [])
            break
    return num, " ".join(w[:6]) or None


def core_key(a):
    num, st = street_key(a)
    if not st:
        return None, None
    w = [x for x in st.split() if x not in DIRS and x not in TYPES]
    return num, " ".join(w) or None


def street_nums(a):
    """'157-159 W Main St' -> {'157', '159'}; '2505 Monroe St' -> {'2505'}."""
    if not isinstance(a, str):
        return set()
    m = re.match(r"^\s*(\d+)[A-Z]?(?:\s*-\s*(\d+)[A-Z]?)?\s", a.upper() + " ")
    if not m:
        return set()
    lo = int(m.group(1)); hi = int(m.group(2)) if m.group(2) else lo
    if hi < lo:   # "1500-02"
        hi = int(str(lo)[: len(str(lo)) - len(m.group(2))] + m.group(2)) if m.group(2) else lo
    return {str(x) for x in range(lo, hi + 1, 2 if (hi - lo) % 2 == 0 else 1)} if 0 <= hi - lo <= 12 else {str(lo)}


def street_compat(a, b):
    """Same street key, or the same core words (directions/type differ or are missing on one side)."""
    if not isinstance(a, str) or not isinstance(b, str) or not a or not b:
        return False
    if a == b:
        return True
    ca = [x for x in a.split() if x not in DIRS and x not in TYPES]
    cb = [x for x in b.split() if x not in DIRS and x not in TYPES]
    if not ca or ca != cb:
        return False
    # quadrant directions that disagree are different streets in a grid (NW 27 AVE vs SW 27 AVE)
    da = {x for x in a.split() if x in DIRS}; db = {x for x in b.split() if x in DIRS}
    if da and db and not (da & db):
        return False
    ta = {x for x in a.split() if x in TYPES}; tb = {x for x in b.split() if x in TYPES}
    if ta and tb and not (ta & tb) and ca[-1].isdigit():
        return False   # NW 27 AVE vs NW 27 ST
    return True


if __name__ == "__main__":
    for t in ["10775 NW 27 AVE STE 4", "10775 Northwest 27th Avenue", "5003 US HWY 301 N", "5003 U.S. 301 North", "1000 UNIVERSAL STUDIOS PLZ",
              "1000 Universal Studios Plaza", "2101 N EPCOT RESORT BLVD", "3304 NW FEDERAL HWY", "11380 BEACH BLVD  STE 12", "1 STATE ROAD A1A",
              "250 N Highway A1A", "8190 PARADISE BAY AVE", "157-159 W MAIN ST", "2700 SR-70 E", "2700 State Road 70 East", "3280 CORAL WAY"]:
        print(f"{t!r:42} {street_key(t)} {core_key(t)}")
    print(street_compat("NW 27 AVE", "27 AVE"), street_compat("NW 27 AVE", "SW 27 AVE"), street_compat("NW 27 AVE", "NW 27 ST"))
