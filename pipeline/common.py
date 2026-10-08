"""Shared helpers: name keys, casing, name matching, town names, cuisine rules and money benchmarks.

Adapted from co-eats/pipeline/common.py (itself from wi-eats and chi-eats): Colorado-only words out, Florida ones in.
"""
import os, re
from rapidfuzz import fuzz

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(ROOT, "data")
RAW = os.path.join(DATA, "raw")
FL = os.path.join(DATA, "fl")

STOP = {"THE", "INC", "LLC", "CO", "CORP", "RESTAURANT", "RESTAURANTS", "AND", "OF", "LTD", "CAFE", "#"}


def norm_name(s):
    s = (s if isinstance(s, str) else "").upper().replace("&", " AND ").replace("'S", "S").replace("’S", "S").replace("¿S", "S")
    s = re.sub(r"[ÁÀÂÄ]", "A", s); s = re.sub(r"[ÉÈÊË]", "E", s); s = re.sub(r"[ÍÌÎÏ]", "I", s)
    s = re.sub(r"[ÓÒÔÖ]", "O", s); s = re.sub(r"[ÚÙÛÜ]", "U", s); s = s.replace("Ñ", "N").replace("Ç", "C")
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"\b\d{2,}\b", " ", s)  # store numbers like "#1234"
    return " ".join(w for w in s.split() if w not in STOP)


SMALL = {"of", "and", "the", "on", "at", "in", "de", "la", "el", "y", "du", "del", "da", "di", "los", "las", "by"}
NOT_ACRONYM = {"mr", "mrs", "ms", "st", "dr", "jr", "sr", "pl", "ct", "rd", "ln", "blvd", "pkwy", "hwy", "sq", "cr", "th", "nd", "mc",
               "cty", "hwy", "trl", "cir", "ste", "fl", "wy", "pkwy", "rr", "rt", "ne", "nw", "se", "sw", "bch", "pk", "pt", "ft", "mt"}
UNIT_TAIL = re.compile(r"(\s+(BLDG|BLD|STE|SUITE|FL|FLR|FLOOR|UNIT|RM|LOWER LEVEL|LL|APT|SPACE|SP|BAY|STALL|KIOSK|#)\b.*$)|(\s+#?\d+[A-Z]?\s*$)", re.I)


def _case(w, first, addr):
    lw = w.lower()
    if not lw:
        return w
    if first is False and lw in SMALL and not addr:
        return lw
    if lw == "bj's":
        return "BJ's"
    if lw in ("a1a", "i-95", "i-4", "i-75", "i-10"):
        return w.upper()
    core = re.sub(r"[^a-z']", "", lw)
    if re.fullmatch(r"(bbq|ii|iii|iv|usa|jj|kfc|ihop|tgi|atm|llc|bp|dj|pb|vfw|amvets|ymca|uf|fsu|ucf|usf|fiu|fau|[a-z])", core):
        return w.upper()
    if addr and re.fullmatch(r"(ne|nw|se|sw|us|sr|cr|a1a)", core):
        return w.upper()
    if re.fullmatch(r"(dj|bj|jj)'s", core):
        return core[:2].upper() + core[2:] + w[len(core):]
    if not addr and core not in NOT_ACRONYM and re.fullmatch(r"[b-df-hj-np-tv-xz]{2,4}", core) and not re.search(r"(.)\1\1", core):
        return w.upper()
    if re.match(r"^mc[a-z]{3}", lw):
        return "Mc" + lw[2].upper() + lw[3:]
    if re.match(r"^o'[a-z]{2}", lw):
        return "O'" + lw[2].upper() + lw[3:]
    t = lw[:1].upper() + lw[1:]
    return re.sub(r"([-(.&])([a-z])", lambda m: m.group(1) + m.group(2).upper(), t)


def nice(s, addr=False):
    s = re.sub(r"\s+", " ", (s or "").strip())
    s = re.sub(r"(?i)\b(\w+)IES'S\b", r"\1IE'S", s)
    s = re.sub(r"(?i)'S\s+'S\b", "'S", s)
    s = re.sub(r"(?i)\bMC\s+([A-Z]{2,})", r"MC\1", s)
    if addr:   # "55 E MAIN ST STE 4" -> drop the dangling unit / stray number
        s = re.sub(r"[\s,]+$", "", s)                                   # "151 NE 41 St,"
        s = re.sub(r"\b(\w{3,})\s+\1\b", r"\1", s, flags=re.I)       # "4525 Collins Collins Ave"
        s = re.sub(r"(?<=\S)\s+(?:STE|SUITE|UNIT|APT|#)\s*[\w-]*$", "", s, flags=re.I)
        m = re.match(r"^(\d+[A-Z]?(?:\s*-\s*\d+)?\s+.+?\b(?:ST|AVE|BLVD|DR|RD|PL|CT|PKWY|TER|WAY|LN|HWY|PLZ|SQ|CIR|TRL|CSWY|PIKE|LOOP|PL)\b(?:\s+(?:N|S|E|W|NE|NW|SE|SW)\b)?)", s, re.I)
        numbered = re.search(r"\b(?:HWY|HIGHWAY|US|SR|CR|RTE|ROUTE|ROAD|RD)\s*$", m.group(1), re.I) if m else None
        if m and UNIT_TAIL.search(s[m.end():]) and not (numbered and re.match(r"\s*\d", s[m.end():])):
            s = m.group(1)
    if not s:
        return s
    out = []
    words = s.split(" ")
    for i, w in enumerate(words):
        parts = re.split(r"([/@&])", w)
        cased = "".join(p if p in "/@&" else _case(p, None if i == 0 and j == 0 else False, addr) for j, p in enumerate(parts))
        out.append(cased)
    s = " ".join(out).replace("Chick-Fil-A", "Chick-fil-A")
    if addr:   # "27 Ave" stays as written; ordinal casing "27Th" -> "27th"
        s = re.sub(r"\b(\d+)(St|Nd|Rd|Th)\b", lambda m: m.group(1) + m.group(2).lower(), s)
    return s


# ---------------------------------------------------------------- towns
_ABBR = [(r"\bBCH\b", "BEACH"), (r"\bBCHS\b", "BEACHES"), (r"\bSPGS?\b|\bSPRGS?\b|\bSPRINGS?\b", "SPRINGS"), (r"\bGDNS?\b|\bGARDEN\b(?=$)", "GARDENS"),
         (r"\bHTS\b", "HEIGHTS"), (r"\bLK\b", "LAKE"), (r"\bPK\b", "PARK"), (r"\bPT\b", "PORT"), (r"\bFT\b", "FORT"), (r"\bMT\b", "MOUNT"),
         (r"\bVLG\b", "VILLAGE"), (r"\bSHRS\b", "SHORES"), (r"\bIS\b|\bISL\b", "ISLAND"), (r"\bCV\b", "COVE"), (r"\bPNTE\b", "PONTE"),
         (r"\bVDRA\b", "VEDRA"), (r"\bJAX\b", "JACKSONVILLE")]


def canon_city(c):
    """One spelling per town: BCH -> Beach, FT -> Fort, PT -> Port, SPGS -> Springs, ST/Saint -> St., N/S/E/W -> North/..., case fixes."""
    if not isinstance(c, str) or not c.strip():
        return None
    c = c.strip().strip(",").strip()
    c = re.sub(r",?\s*(?:FL|Fla\.?|Florida)(?:\s+\d{5}(?:-\d{4})?)?$", "", c, flags=re.I).strip()
    c = re.sub(r"^(?:City|Town|Village)\s+of\s+", "", c, flags=re.I)
    u = re.sub(r"\.", ". ", c.upper()); u = re.sub(r"\s+", " ", u).strip()
    for pat, rep in _ABBR:
        u = re.sub(pat, rep, u)
    u = re.sub(r"^(N|S|E|W)\.?\s+", lambda m: {"N": "NORTH ", "S": "SOUTH ", "E": "EAST ", "W": "WEST "}[m.group(1)], u)
    u = re.sub(r"\b(?:SAINT|ST)\b\.?\s*", "ST. ", u)
    u = re.sub(r"\s+", " ", u).strip()
    key = re.sub(r"[^A-Z]", "", u)
    fix = {"STPETE": "St. Petersburg", "STPETERSBURG": "St. Petersburg", "STPETESBURG": "St. Petersburg", "STPETETRSBURG": "St. Petersburg",
           "STPETEBEACH": "St. Pete Beach", "STPETERSBURGBEACH": "St. Pete Beach", "STJOHNS": "St. Johns", "STJOHNSCOUNTY": "St. Johns",
           "STAUGUSTINE": "St. Augustine", "STAUGUSTINEBEACH": "St. Augustine Beach", "PORTSTLUCIE": "Port St. Lucie", "PORTSTJOE": "Port St. Joe",
           "PORTSTJOHN": "Port St. John", "DEFUNIAKSPRINGS": "DeFuniak Springs", "DELAND": "DeLand", "DEBARY": "DeBary", "LABELLE": "LaBelle",
           "MCINTOSH": "McIntosh", "MIAMIDADE": "Miami", "HALLANDALE": "Hallandale Beach", "SUNNYISLES": "Sunny Isles Beach",
           "LAUDERDALEBYTHESEA": "Lauderdale-by-the-Sea", "LAUDERDALEBYSEA": "Lauderdale-by-the-Sea", "PONTEVEDRE": "Ponte Vedra",
           "PONTEVEDREBEACH": "Ponte Vedra Beach", "INDIANHARBORBEACH": "Indian Harbour Beach", "TOWNNCOUNTRY": "Town 'n' Country",
           "TOWNANDCOUNTRY": "Town 'n' Country", "FORTWALTON": "Fort Walton Beach", "DAYTONABEACHSHORES": "Daytona Beach Shores",
           "OPALOCKA": "Opa-locka", "OPALOCKS": "Opa-locka", "HOWEYINTHEHILLS": "Howey-in-the-Hills", "CAPECANAVERAL": "Cape Canaveral",
           "LAKEBUENAVISTA": "Lake Buena Vista", "ALTAMONTESPRINGS": "Altamonte Springs", "STTEAUGUSTINE": "St. Augustine",
           "WESTPALMBEACH": "West Palm Beach", "NORTHPALMBEACH": "North Palm Beach", "PALMBEACHGARDENS": "Palm Beach Gardens",
           "MIAMIBEACH": "Miami Beach", "NORTHMIAMIBEACH": "North Miami Beach", "FORTLAUDERDALE": "Fort Lauderdale", "FORTMYERS": "Fort Myers",
           "FORTMYERSBEACH": "Fort Myers Beach", "NORTHFORTMYERS": "North Fort Myers", "FORTPIERCE": "Fort Pierce", "FORTWALTONBEACH": "Fort Walton Beach",
           "FORTMEADE": "Fort Meade", "WINTERGARDENS": "Winter Garden", "KISSIMEE": "Kissimmee", "HIALIAH": "Hialeah", "FORTWHITE": "Fort White", "KEYWEST": "Key West", "KEYLARGO": "Key Largo", "KEYBISCAYNE": "Key Biscayne"}
    if key in fix:
        return fix[key]
    out = []
    for i, w in enumerate(u.split(" ")):
        lw = w.lower()
        if i and lw in ("of", "the", "by", "in", "on", "de", "del", "la"):
            out.append(lw)
        elif w == "ST.":
            out.append("St.")
        else:
            out.append(re.sub(r"(^|[-'])([a-z])", lambda m: m.group(1) + m.group(2).upper(), lw))
    return " ".join(out)


def town_key(c):
    k = c.lower().replace(".", " ")
    k = re.sub(r"^(e|n|s|w)\s+", lambda m: {"e": "east ", "n": "north ", "s": "south ", "w": "west "}[m.group(1)], k)
    k = re.sub(r"\bmt\b", "mount", k); k = re.sub(r"\bhts\b", "heights", k); k = re.sub(r"\bft\b", "fort", k)
    k = re.sub(r"\bpt\b", "port", k); k = re.sub(r"\bbch\b", "beach", k); k = re.sub(r"\bsaint\b", "st", k)
    return re.sub(r"[^a-z]", "", k)


# words that don't identify a business on their own: a name match needs a shared word outside this list
GENERIC = set("""PIZZA PIZZERIA PHO TACO TACOS TAQUERIA GRILL GRILLE KITCHEN EXPRESS HOUSE COFFEE BAR PUB TAVERN FOOD FOODS STORE SHOP MARKET
DELI BAKERY CHICKEN FISH BBQ SUSHI THAI CHINESE MEXICAN INDIAN ITALIAN GYROS BURGER BURGERS WINGS DONUTS DONUT BEEF TEA JUICE
NORTH SOUTH EAST WEST PARK SQUARE STATION UNION TOWN VILLAGE STREET AVE AVENUE CENTER PLAZA LAKE LAKES RIVER BAY
NEW OLD BEST GOLDEN LITTLE BIG KING STAR ORIGINAL FAMOUS FRESH HOT GRAND LA EL LOS LAS DE DEL ON THE Y AT OF LOUNGE SNACK SNACKS
NOODLE NOODLES ASIAN SHRIMP PATIO CLUB INN LODGE SALOON RESORT BREWING BREWERY COMPANY BREW HALL FROZEN CHEESE
FRY BAKE CAFETERIA CORNER SPOT STOP PLACE ROOM SPORTS FAMILY STEAKHOUSE STEAK DINER CREAMERY ICE CREAM
HUT WOK MEAL FUSION BUFFET CUISINE EATS EATERY BISTRO TAPROOM TAPHOUSE DEN TRADING POST
FLORIDA FLA KEY KEYS BEACH BEACHES OCEAN OCEANFRONT TROPICAL TROPICS ISLAND ISLANDS PALM PALMS SUNSHINE GULF COAST COASTAL BAYSIDE MARINA DOCK
DOCKSIDE HARBOR HARBOUR SUNSET SUNRISE PIER CRAB CRABS OYSTER OYSTERS STONE SEAFOOD RAW CUBAN CUBANA LATIN LATINO CARIBBEAN SANDWICH SANDWICHES
SUBS CANTINA RESTAURANTE COCINA PANADERIA FRITANGA VENTANITA SABOR SABORES CASA MI TU SU MAR SOL LUNA COCINA HOGAR TIPICO TIPICA CRIOLLA""".split())


def _stems(s):
    return {w if w in GENERIC else (w[:-1] if len(w) > 3 and w.endswith("S") else w) for w in s.split()} - GENERIC


# what a name says the place serves: two names that each say it, and disagree, are two businesses ("Flagler Fish Company" and
# "Flagler Tea Company" share only the town's name, since FISH, TEA and COMPANY are generic)
KIND_WORDS = {**dict.fromkeys(["PIZZA", "PIZZERIA"], "pizza"), **dict.fromkeys(["SUSHI", "JAPANESE", "HIBACHI", "RAMEN"], "japanese"),
              **dict.fromkeys(["TEA", "BOBA"], "tea"), **dict.fromkeys(["FISH", "SEAFOOD", "OYSTER", "OYSTERS", "CRAB", "CRABS", "SHRIMP"], "seafood"),
              **dict.fromkeys(["TACO", "TACOS", "TAQUERIA", "MEXICAN", "CANTINA"], "mexican"), **dict.fromkeys(["CHINESE", "WOK"], "chinese"),
              "THAI": "thai", "INDIAN": "indian", "ITALIAN": "italian", "BBQ": "bbq", "PHO": "vietnamese", "GYROS": "greek",
              **dict.fromkeys(["BURGER", "BURGERS"], "burger"), **dict.fromkeys(["CHICKEN", "WINGS"], "chicken"),
              **dict.fromkeys(["DONUT", "DONUTS"], "donut"), **dict.fromkeys(["BAKERY", "PANADERIA"], "bakery"),
              **dict.fromkeys(["STEAKHOUSE", "STEAK"], "steak"), **dict.fromkeys(["CREAMERY", "FROZEN", "YOGURT"], "icecream"),
              "JUICE": "juice", "COFFEE": "coffee"}


def kinds(s):
    return {KIND_WORDS[w] for w in s.split() if w in KIND_WORDS}


def kind_conflict(a, b):
    """Both names say what they serve, and they disagree ("FLAGLER FISH COMPANY" / "FLAGLER TEA COMPANY")."""
    ka, kb = kinds(a), kinds(b)
    return bool(ka and kb and not ka & kb)


_TOWN_WORDS = None
FILLER = {"RESTAURANT", "RESTAURANTS", "CAFE", "CO", "INC", "LLC", "CORP", "AND"}   # for the town-only tests: "HAVANA RESTAURANT" is "HAVANA"


def town_words():
    """Words of Florida's town names (from DBPR's license file): "MIAMI", "CLERMONT", "FLAGLER", "BELL", "HAVANA", plus islands and
    neighborhoods that aren't towns. Stemmed too, as _stems does ("MYERS" -> "MYER")."""
    global _TOWN_WORDS
    if _TOWN_WORDS is None:
        import pandas as pd
        cities = pd.read_parquet(f"{FL}/licenses.parquet", columns=["city_raw"]).city_raw.dropna().unique()
        words = {w for c in cities for w in norm_name(canon_city(c) or c).split() if len(w) >= 4}
        words |= set("""AMELIA SIESTA CAPTIVA LONGBOAT BRICKELL WYNWOOD YBOR KENDALL COCONUT DOWNTOWN MIDTOWN UPTOWN SOBE OLAS ANNA MARIA
                        HUTCHINSON PERDIDO OKALOOSA SANTA ROSA DESTIN WALTON BAYSHORE""".split())
        _TOWN_WORDS = (words | {w[:-1] for w in words if len(w) > 3 and w.endswith("S")}) - GENERIC
    return _TOWN_WORDS


def real_share(a, b):
    """Distinctive name words in common (stem sets). A town's name alone counts only when it is the whole distinctive name on both
    sides ("HAVANA" / "HAVANA RESTAURANT"): "MIAMI SUBS" and "WOK N ROLL MIAMI" share only MIAMI, "CEDAR GRILL CLERMONT" and
    "EPIC THEATRES OF CLERMONT" only CLERMONT. (Chains like "TACO BELL" / "TACO BELL AMERICA" match on name similarity instead.)"""
    a, b = a - FILLER, b - FILLER
    both = a & b
    if not both:
        return False
    return bool(both - town_words()) or both == a == b


def name_sim(a, b):
    ours, theirs = set(a.split()), set(b.split())
    distinct = (_stems(a) - GENERIC) & (_stems(b) - GENERIC)
    joined = a.replace(" ", "") == b.replace(" ", "") or fuzz.ratio(a.replace(" ", ""), b.replace(" ", "")) >= 92
    if joined:
        return 96
    if not distinct and fuzz.ratio(a, b) < 95:   # nothing but generic words in common: not the same business
        return 60
    if not (distinct - town_words()) and _stems(a) - FILLER != _stems(b) - FILLER and fuzz.ratio(a, b) < 95:
        return 60   # only a town's name in common: "CUCINA DANIA BEACH" / "PB DANIA BEACH" (a legal name), "BREWSKIS SOUTH MIAMI" / "SUSHI SAKE SOUTH MIAMI"
    ka, kb = kinds(a), kinds(b)
    if ka and kb and not ka & kb:   # each name says what it serves, and they disagree
        return 70
    s_set = fuzz.token_set_ratio(a, b)
    # token_set_ratio is 100 whenever one name's words are a subset of the other's: cap it unless the overlap is a real share of both
    if len(ours & theirs) < 0.5 * min(len(ours), len(theirs)) + 0.5 or len(ours & theirs) < 0.4 * max(len(ours), len(theirs)):
        s_set = min(s_set, 72)
    return max(s_set, fuzz.ratio(a, b), fuzz.token_sort_ratio(a, b))


FOODCAT = re.compile(r"\b(restaurant|cafe|coffee|bakery|pizza|bar|pub|diner|deli|taco|ice cream|donut|dessert|sandwich|food court|caterer|tea house|bistro|brewpub|brewery|juice|grill|takeout|buffet|bagel|chicken|seafood|steak|hot dog|tavern|lounge|gastropub|snack|yogurt|creperie|patisserie|chocolate|confectionery|bubble tea|night club|beer|wine|bbq|barbecue|pie|pastry|popcorn|tamale|churro|takeaway|tortilleria|fish & chips|cheesesteak|oyster|raw bar|cuban|empanada)\b", re.I)
NOTFOOD = re.compile(r"^(?:Tower|Museum|Stadium|Convention|Hotel|Performing|Theater|Hospital|University|Corporate|Observation|Tourist|Airport|Casino|Gas station|Grocery|Supermarket|Convenience|Liquor store|Event|Banquet|Park|Arena)\b")

# Name keywords -> cuisine. Whole words only, so HOSPITAL isn't "PITA", BREWING isn't "WING", BOWLING isn't "BOWL".
# Order matters: specific before general.
_W = lambda words: re.compile(r"\b(?:" + words + r")\b")
CUISINE_RULES = [
    ("Hot Dogs & Sausages", _W(r"HOT ?DOGS?|DOGS|WIENERS?|BRATS?|BRATWURST|SAUSAGES?|NATHANS")),
    ("Pizza", _W(r"PIZZA|PIZZAS|PIZZERIA|PIZZERIAS|DOMINOS|PAPA JOHNS|LITTLE CAESARS?|MELLOW MUSHROOM|HUNGRY HOWIES|MARCOS PIZZA|ANTHONYS COAL FIRED|SBARRO")),
    ("Korean", _W(r"KOREAN?|KOREA|KIMCHI|BIBIMBAP|SEOUL|GOGI|BULGOGI|KBBQ|CUPBOP|BONCHON")),
    ("Thai", _W(r"THAI|SIAM|BANGKOK|ISAAN|ISAN")),
    ("Vietnamese", _W(r"PHO|VIETNAMESE|VIETNAM|SAIGON|BANH MI|BANH|HANOI")),
    ("Coffee & Café", _W(r"COFFEE|ESPRESSO|STARBUCKS|DUNKIN|CAFFE|TEA|TEAS|TEAHOUSE|BOBA|LATTE|ROASTERS?|ROASTING|CAFECITO|COLADA|VENTANITA|BLACK RIFLE|DUTCH BROS|BIGGBY|SCOOTERS COFFEE|7 BREW")),
    ("Bakery & Sweets", _W(r"BAKERY|BAKERIES|BAKESHOP|BAKE SHOP|BAKEHOUSE|PASTRY|PASTRIES|PASTELITOS|PATISSERIE|DONUTS?|DOUGHNUTS?|PANADERIA|REPOSTERIA|CAKES?|CUPCAKES?|COOKIES?|DESSERTS?|ICE CREAM|GELATO|GELATERIA|PALETERIA|PALETAS|YOGURT|FROYO|CREPES?|CREPERIE|SWEETS|CHOCOLATE|CHOCOLATIER|CINNABON|BAGELS?|CREAMERY|CHURROS?|PIES|CONFECTIONS?|MICHOACANA|DAIRY QUEEN|BASKIN|KRISPY KREME|NOTHING BUNDT|CRUMBL|KEY LIME")),
    ("Latin & Caribbean", _W(r"CUBAN[AO]?|CUBA|HABANA|HAVANA|VERSAILLES|LA CARRETA|SEDANOS|PUERTO RICAN|BORICUA|BORINQUEN|CARIBBEAN|JAMAICAN?|JERK|HAITIAN?|HAITI|"
                              r"PERUVIAN|PERUAN[AO]|PERU|COLOMBIAN[AO]?|COLOMBIA|SALVADOREN[AO]|PUPUSAS?|PUPUSERIA|ARGENTIN[AE]|ARGENTINIAN|VENEZUELAN?|VENEZOLAN[AO]|AREPAS?|AREPERA|"
                              r"BRAZILIAN?|BRASIL|BRASILEIR[AO]|EMPANADAS?|DOMINICAN[AO]?|GUATEMALTEC[AO]|HONDUREN[AO]|NICARAGUAN?|NICARAGUENSE|FRITANGA|ECUADORIAN[AO]?|"
                              r"LATIN[AO]?|CEVICHE|CEVICHERIA|CVI CHE|MOFONGO|LECHONERA|CHURRASCO|CHURRASQUERIA|POLLO TROPICAL|POLLO CAMPERO|TRINIDAD|TRINI|BAHAMIAN|"
                              r"CRIOLL[AO]|TIPIC[AO]|ROTI|OXTAIL|GRIOT|CROQUETAS?|CAFETERIA LATINA|SANDWICH CUBANO")),
    ("Mexican", _W(r"TAQUERIA|TAQUERIAS|TACOS?|MEXICAN[AO]?|MEXICO|BURRITOS?|BIRRIA|BIRRIERIA|CARNITAS|TAMALES?|TORTAS?|ELOTES?|MARISCOS|CHIPOTLE|QDOBA|AZTECA|"
                    r"JALISCO|MICHOACAN|GUADALAJARA|OAXACA|GUERRERO|PUEBLA|TORTILLERIA|ANTOJITOS?|QUESADILLAS?|NACHOS?|HUARACHES?|FONDA|EL TORO|TIJUANA FLATS|"
                    r"TACO BELL|MOES SOUTHWEST|CHUYS|ON THE BORDER|CHILIS")),
    ("Japanese & Sushi", _W(r"SUSHI|RAMEN|JAPANESE|JAPAN|IZAKAYA|TERIYAKI|HIBACHI|OMAKASE|TOKYO|BENTO|UDON|YAKITORI|KATSU|SAKE|TEMPURA|SASHIMI|TEPPANYAKI|KYOTO|OSAKA|BENIHANA|KOBE|NARUTO|HIBACHI")),
    ("Chinese", _W(r"CHINA|CHINESE|EGG ROLLS?|WOK|DUMPLINGS?|DIM SUM|PANDA EXPRESS|HUNAN|SZECHUAN|SICHUAN|MANDARIN|CANTONESE|KUNG PAO|HONG KONG|BEIJING|SHANG ?HAI|HOT ?POT|CHOP SUEY|BAO|LO MEIN|WONTON|PEKING|YUNNAN|PF CHANGS|P F CHANGS")),
    ("South Asian", _W(r"INDIA|INDIAN|TANDOOR|TANDOORI|CURRY|CURRIES|MASALA|BIRYANI|NEPAL|NEPALI|NEPALESE|HIMALAYAN?|PAKISTANI?|BOMBAY|MUMBAI|DELHI|PUNJAB|PUNJABI|KATHMANDU|MOMOS?|CHAAT|SAMOSAS?|BENGALI|SRI LANKAN?|DOSA|TIKKA")),
    ("Mediterranean & Middle Eastern", _W(r"GREEK|GYROS?|MEDITERRANEAN|MEDITERANNEAN|FALAFEL|SHAWARMA|MIDDLE EASTERN|LEBANESE|HALAL|KABOBS?|KEBABS?|KABABS?|PERSIAN|TURKISH|ISRAELI|HUMMUS|PITA|PITAS|ZAATAR|SYRIAN|AFGHAN|ARABIC|ARABIAN|ATHENS|OLYMPIA|PARTHENON|AEGEAN|MEZZE|YEMENI|CAVA")),
    ("African", _W(r"AFRICAN?|AFRICA|ETHIOPIAN?|NIGERIAN?|ERITREAN?|GHANAIAN|SENEGALESE|SOMALI|MOROCCAN|EGYPTIAN|KENYAN|CAMEROONIAN|JOLLOF|SUYA")),
    ("Italian", _W(r"ITALIAN[AO]?|ITALIA|TRATTORIA|OSTERIA|PASTA|RISTORANTE|VINO|NONNA|CUCINA|ENOTECA|SPAGHETTI|NAPOLI|NAPOLETANA|SICILIAN|TUSCANY|TUSCAN|FORNO|MAGGIANOS|OLIVE GARDEN|CARRABBAS|BRAVO")),
    ("Burgers", _W(r"BURGERS?|HAMBURGERS?|CHEESEBURGERS?|MCDONALDS|MC DONALDS|WENDYS|WHITE CASTLE|FIVE GUYS|SHAKE SHACK|CULVERS|SMASHBURGER|PATTY|PATTIES|STEAK N SHAKE|SONIC|ARBYS|CHECKERS|RALLYS|JACK IN THE BOX|HARDEES|KRYSTAL|WHATABURGER|BURGERFI|BURGER KING|RED ROBIN")),
    ("Seafood", _W(r"SEAFOOD|FISH|FISHERIES|FISHERY|FISH CAMP|SHRIMP|OYSTERS?|CRABS?|CRAB|STONE CRAB|LOBSTER|CATFISH|CAJUN|BOIL|POKE|GROUPER|SNAPPER|MAHI|CONCH|RAW BAR|CLAMS?|MULLET|"
                     r"LONG JOHN SILVERS|CAPTAIN DS|RED LOBSTER|BONEFISH|SHELLS|JOES CRAB|DEEP SEA|SEA DOG|DOCKSIDE|FISH HOUSE|BOATHOUSE")),
    ("Chicken & Wings", _W(r"CHICKEN|WINGS|POPEYES|KFC|CHURCHS|RAISING CANES?|CHICK FIL A|BROASTED|WINGSTOP|NASHVILLE HOT|KRISPY KRUNCHY|ZAXBYS|BOJANGLES|HOOTERS|WINGHOUSE|PDQ")),
    ("BBQ", _W(r"BBQ|BAR B Q|BAR BQ|BAR B QUE|BAR BE CUE|BAR B CUE|BARBECUE|BARBEQUE|RIBS|SMOKEHOUSE|SMOKED|BRISKET|SONNYS|4 RIVERS|DICKEYS|SMOKEY BONES|FAMOUS DAVES")),
    ("Sandwiches & Deli", _W(r"SANDWICH|SANDWICHES|DELI|DELICATESSEN|SUBWAY|JIMMY JOHNS|POTBELLY|JERSEY MIKES|FIREHOUSE SUBS|SUBS|HOAGIES?|PANERA|CORNER BAKERY|CHEESE ?STEAKS?|PHILLY|CAPRIOTTIS|MIAMI SUBS|PUBLIX SUBS|WHICH WICH")),
    ("Steakhouse", _W(r"STEAK|STEAKS|STEAKHOUSE|STEAK HOUSE|CHOPHOUSE|CHOP HOUSE|RUTHS CHRIS|CAPITAL GRILLE|MORTONS|TEXAS ROADHOUSE|LONGHORN|OUTBACK|PRIME RIB|FLEMINGS|BERNS|SHULAS|CHURRASCARIA|FOGO DE CHAO|TEXAS DE BRAZIL")),
    ("Soul & Southern", _W(r"SOUL|SOUTHERN|CREOLE|GUMBO|BISCUITS?|GRITS|CHICKEN WAFFLES|CRACKER BARREL|CATFISH")),
    ("Healthy & Vegan", _W(r"VEGAN|VEGETARIAN|SALADS?|JUICE|JUICERY|SMOOTHIES?|SWEETGREEN|PLANT BASED|ACAI|HEALTHY|ORGANIC|JAMBA|TROPICAL SMOOTHIE|SMOOTHIE KING|BOLAY|PLAYA BOWLS|GREENS")),
    ("Breakfast & Diner", _W(r"BREAKFAST|PANCAKES?|DINER|BRUNCH|EGGS?|IHOP|DENNYS|PERKINS|YOLK|OMELETTES?|OMELETS?|SUNRISE|MORNING|WAFFLES?|GRIDDLE|SKILLETS?|FIRST WATCH|WAFFLE HOUSE|BOB EVANS|KEKES|BAGEL")),
    ("European", _W(r"POLISH|POLSKA|UKRAINIAN|GERMAN|BAVARIAN|SERBIAN|BOSNIAN|CROATIAN|RUSSIAN|FRENCH|BRASSERIE|IRISH|BRITISH|ENGLISH|SWEDISH|NORWEGIAN|DANISH|SPANISH|TAPAS|"
                               r"PORTUGUESE|EUROPEAN|LITHUANIAN|CZECH|HUNGARIAN|ROMANIAN|GEORGIAN|PIEROGI|PIEROGIES|HAUS|BIERGARTEN|BEER GARDEN|BIERHALLE|RATHSKELLER|SCHNITZEL|SWISS|FONDUE|BELGIAN|DUTCH|PELMENI")),
    ("Bar & Pub", _W(r"PUB|TAVERN|BAR|SALOON|LOUNGE|TAP|TAPS|TAPROOM|TAPHOUSE|BREWING|BREWERY|BREWPUB|BEER|ALE HOUSE|ALEHOUSE|GASTROPUB|COCKTAILS?|WINE|WINERY|DISTILLERY|DISTILLING|INN|PADDY|BARS|TIKI|SPORTS GRILL|ICEHOUSE|DUFFYS|FLANIGANS|MILLERS ALE")),
]
GCAT = [(c, re.compile(p)) for c, p in [
    ("Pizza", r"Pizza"), ("Coffee & Café", r"Coffee|Cafe|Espresso|Tea house|Bubble tea"),
    ("Bakery & Sweets", r"Bakery|Donut|Dessert|Ice cream|Pastry|Cake|Frozen yogurt|Chocolate|Bagel|Pie shop|Candy"),
    ("Latin & Caribbean", r"Latin|Caribbean|Cuban|Puerto Rican|Jamaican|Peruvian|Colombian|Salvadoran|Brazilian|Venezuelan|Argentin|Haitian|Dominican|Nicaraguan|Honduran|Ecuadorian|Guatemalan"),
    ("Mexican", r"Mexican|Taco|Burrito|Tex-Mex|Taqueria"),
    ("Japanese & Sushi", r"Japanese|Sushi|Ramen"), ("Chinese", r"Chinese|Cantonese|Dim sum|Szechuan|Dumpling|Hot pot"),
    ("Korean", r"Korean"), ("Thai", r"Thai"), ("Vietnamese", r"Vietnamese|Pho"), ("South Asian", r"Indian|Pakistani|Nepal|Bangladeshi|Sri Lankan"),
    ("Mediterranean & Middle Eastern", r"Mediterranean|Middle Eastern|Greek|Lebanese|Falafel|Halal|Turkish|Persian|Israeli|Afghan|Shawarma"),
    ("African", r"African|Ethiopian|Nigerian|Moroccan|Eritrean|Somali"), ("Italian", r"Italian"),
    ("Hot Dogs & Sausages", r"Hot dog|Bratwurst"), ("Burgers", r"Hamburger|Burger"), ("Seafood", r"Seafood|Fish|Oyster|Poke|Cajun|Crab"),
    ("Chicken & Wings", r"Chicken"), ("BBQ", r"Barbecue"), ("Steakhouse", r"Steak"),
    ("Soul & Southern", r"Soul food|Southern"), ("Sandwiches & Deli", r"Sandwich|Deli|Cheesesteak"),
    ("Healthy & Vegan", r"Vegan|Vegetarian|Health food|Salad|Juice"), ("Breakfast & Diner", r"Breakfast|Brunch|Diner|Pancake"),
    ("European", r"French|German|Polish|Ukrainian|Spanish|Tapas|Irish|European|Eastern European|Serbian|Russian|Bistro|Scandinavian|Swiss|Belgian|Dutch|Fondue|Portuguese"),
    ("Bar & Pub", r"Bar\b|Pub|Brewpub|Brewery|Tavern|Gastropub|Wine bar|Cocktail|Beer"),
    # a primary "American" category is an answer too, so a later "Bar" tag doesn't turn a family restaurant into a pub
    ("American & Other", r"American restaurant|Eclectic restaurant|Fine dining restaurant|Family restaurant|Southwestern"),
]]


def cuisine(name_key, gcats, raw=""):
    for c, pat in CUISINE_RULES:
        if pat.search(name_key or ""):
            return c
    cats = [x for x in (gcats or "").split("|") if x]
    for cat in cats:
        for c, pat in GCAT:
            if pat.search(cat):
                return c
    if re.search(r"\bCAF[EÉ]\b", (raw or "").upper()) and not cats:
        return "Coffee & Café"
    return "American & Other"


# Typical food-cost % by cuisine (industry rule-of-thumb ranges, midpoint)
FOOD_COST = {"Pizza": 26, "Coffee & Café": 24, "Bakery & Sweets": 25, "Mexican": 28, "Latin & Caribbean": 30,
             "Japanese & Sushi": 34, "Chinese": 30, "Korean": 32, "Thai": 30, "Vietnamese": 30, "South Asian": 28,
             "Mediterranean & Middle Eastern": 30, "African": 30, "Italian": 29, "Hot Dogs & Sausages": 31, "Burgers": 31,
             "Chicken & Wings": 33, "Seafood": 36, "BBQ": 34, "Steakhouse": 38, "Soul & Southern": 32,
             "Sandwiches & Deli": 30, "Healthy & Vegan": 32, "Breakfast & Diner": 27, "European": 30, "Bar & Pub": 27,
             "American & Other": 30}
# Pre-tax net margin benchmarks by segment
MARGIN = {1: 0.075, 2: 0.05, 3: 0.055, 4: 0.045}
MARGIN_CUISINE = {"Bar & Pub": 0.10, "Steakhouse": 0.09, "Pizza": 0.07, "Coffee & Café": 0.08}
SPEND = {1: 13, 2: 28, 3: 62, 4: 165}   # typical per-person spend by price tier
