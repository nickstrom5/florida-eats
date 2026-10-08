"""Known chain brands in Florida: regex on normalized name -> brand label.

Adapted from co-eats/pipeline/brands.py (from wi-eats); Colorado-only brands dropped, Florida and Southeast chains added.
"""
import re

BRANDS = [
    ("Dunkin'", r"^DUNKIN"), ("Subway", r"^SUBWAY"), ("McDonald's", r"^MC ?DONALDS"), ("Starbucks", r"^STARBUCK"),
    ("Jimmy John's", r"^JIMMY JOHNS?\b"), ("Burger King", r"^BURGER KING"), ("Taco Bell", r"^TACO BELL"),
    ("Potbelly", r"^POTBELLY"), ("Wingstop", r"^WING ?STOP"), ("Chipotle", r"^CHIPOTLE"), ("Popeyes", r"^POPEYE"),
    ("Wendy's", r"^WENDYS"), ("Panda Express", r"^PANDA EXPRESS"), ("White Castle", r"^WHITE CASTLE"),
    ("Chick-fil-A", r"^CHICK FIL"), ("Domino's", r"^DOMINO"), ("Jersey Mike's", r"^JERSEY MIKE"),
    ("Panera Bread", r"^PANERA"), ("Jet's Pizza", r"^JETS PIZZA"), ("Little Caesars", r"^LITTLE CAESAR"),
    ("Papa John's", r"^PAPA JOHN"), ("KFC", r"^KFC|^KENTUCKY FRIED"), ("Tropical Smoothie Cafe", r"^TROPICAL SMOOTHIE"),
    ("Buffalo Wild Wings", r"^BUFFALO WILD"), ("Five Guys", r"^FIVE GUYS"), ("Raising Cane's", r"^RAISING CANE"),
    ("Portillo's", r"^PORTILLO"), ("Auntie Anne's", r"^AUNTIE ANNE"), ("Qdoba", r"^QDOBA"),
    ("Noodles & Company", r"^NOODLES (?:AND )?CO(?:MPANY)?\b"), ("Smoothie King", r"^SMOOTHIE KING"), ("Firehouse Subs", r"^FIREHOUSE SUB"),
    ("IHOP", r"^IHOP"), ("Denny's", r"^DENNYS"), ("Sonic", r"^SONIC DRIVE|^SONIC$"), ("Insomnia Cookies", r"^INSOMNIA COOKIE"),
    ("Crumbl", r"^CRUMBL\b"), ("Dairy Queen", r"^DAIRY QUEEN|^DQ GRILL|^DQ$"), ("Baskin-Robbins", r"^BASKIN"), ("Krispy Kreme", r"^KRISPY KREME"),
    ("Chuck E. Cheese", r"^CHUCK E CHEESE"), ("Rosati's", r"^ROSATI"), ("Nothing Bundt Cakes", r"^NOTHING BUNDT"),
    ("Hooters", r"^HOOTERS"), ("Cheesecake Factory", r"^CHEESECAKE FACTORY"), ("P.F. Chang's", r"^P ?F CHANG"), ("Maggiano's", r"^MAGGIANO"),
    ("Ruth's Chris", r"^RUTHS CHRIS"), ("Morton's", r"^MORTONS THE STEAK|^MORTONS STEAK"), ("Steak 'n Shake", r"^STEAK N SHAKE"),
    ("Applebee's", r"^APPLEBEE"), ("Chili's", r"^CHILIS"), ("Olive Garden", r"^OLIVE GARDEN"), ("Red Lobster", r"^RED LOBSTER"),
    ("Jamba", r"^JAMBA"), ("Cinnabon", r"^CINNABON"), ("Pizza Hut", r"^PIZZA HUT"), ("Arby's", r"^ARBYS"),
    ("Checkers", r"^CHECKERS DRIVE|^CHECKERS AND RALLY|^CHECKERS$"), ("MOD Pizza", r"^MOD PIZZA"), ("Tim Hortons", r"^TIM HORTON"),
    ("Peet's Coffee", r"^PEETS"), ("Colectivo", r"^COLECTIVO"), ("Cava", r"^CAVA$|^CAVA (?:MEDITERRANEAN|GRILL)"), ("Blaze Pizza", r"^BLAZE PIZZA"),
    # national chains common in the US
    ("Culver's", r"^CULVER"), ("Taco John's", r"^TACO JOHN"), ("Caribou Coffee", r"^CARIBOU COFFEE|^CARIBOU$"),
    ("Scooter's Coffee", r"^SCOOTERS COFFEE"), ("Dutch Bros", r"^DUTCH BRO"), ("7 Brew", r"^7 BREW"), ("The Human Bean", r"^(?:THE )?HUMAN BEAN"),
    ("Black Rock Coffee", r"^BLACK ROCK COFFEE"), ("Ziggi's Coffee", r"^ZIGGIS"), ("Dazbog Coffee", r"^DAZBOG"),
    ("Texas Roadhouse", r"^TEXAS ROADHOUSE"), ("Famous Dave's", r"^FAMOUS DAVE"), ("Red Robin", r"^RED ROBIN"),
    ("Freddy's", r"^FREDDYS FROZEN|^FREDDYS STEAKBURGER"), ("Papa Murphy's", r"^PAPA MURPH"), ("Marco's Pizza", r"^MARCOS PIZZA"),
    ("Cracker Barrel", r"^CRACKER BARREL"), ("Outback Steakhouse", r"^OUTBACK STEAK"), ("LongHorn Steakhouse", r"^LONGHORN STEAK"),
    ("Cold Stone Creamery", r"^COLD STONE"), ("Golden Corral", r"^GOLDEN CORRAL"),
    ("Old Chicago", r"^OLD CHICAGO$|^OLD CHICAGO (?:PASTA|PIZZA|TAPROOM)"), ("Rock Bottom", r"^ROCK BOTTOM"),
    ("Einstein Bros. Bagels", r"^EINSTEIN BRO"), ("Quiznos", r"^QUIZNO"), ("Fazoli's", r"^FAZOLI"), ("Dickey's Barbecue Pit", r"^DICKEYS"),
    ("HuHot Mongolian Grill", r"^HUHOT"), ("Blimpie", r"^BLIMPIE"), ("Dave's Hot Chicken", r"^DAVES HOT CHICKEN"), ("Sbarro", r"^SBARRO"),
    ("Great Harvest", r"^GREAT HARVEST"), ("Teriyaki Madness", r"^TERIYAKI MADNESS"), ("First Watch", r"^FIRST WATCH"),
    ("TGI Fridays", r"^TGI FRIDAY"), ("Mooyah", r"^MOOYAH"), ("Charleys Cheesesteaks", r"^CHARLEYS (?:PHILLY|CHEESESTEAK|GRILLED SUBS)"), ("Smashburger", r"^SMASHBURGER"),
    ("Hunt Brothers Pizza", r"^HUNT BROTHERS"), ("Hot Stuff Pizza", r"^HOT STUFF"), ("Krispy Krunchy Chicken", r"^KRISPY KRUNCHY"),
    ("Cheba Hut", r"^CHEBA HUT"), ("MrBeast Burger", r"^MR ?BEAST"), ("It's Just Wings", r"^ITS JUST WINGS"), ("7-Eleven", r"^7 ELEVEN"),
    ("Casey's", r"^CASEYS"), ("Pizza Ranch", r"^PIZZA RANCH"), ("Hardee's", r"^HARDEES"), ("Carl's Jr.", r"^CARLS JR"),
    ("Jack in the Box", r"^JACK IN THE BOX"), ("Del Taco", r"^DEL TACO"), ("Whataburger", r"^WHATABURGER"), ("In-N-Out Burger", r"^IN N OUT BURGER"),
    ("Café Rio", r"^CAFE RIO"), ("Costa Vida", r"^COSTA VIDA"), ("Cafe Yumm!", r"^CAFE YUMM"), ("Waffle House", r"^WAFFLE HOUSE"),
    ("Perkins", r"^PERKINS (?:RESTAURANT|BAKERY|AMERICAN|FAMILY)|^PERKINS$"), ("Bob Evans", r"^BOB EVANS"), ("Black Bear Diner", r"^BLACK BEAR DINER"),
    ("Native Grill & Wings", r"^NATIVE GRILL"), ("BJ's Restaurant", r"^BJS RESTAURANT|^BJS BREWHOUSE"), ("Twin Peaks", r"^TWIN PEAKS"),
    ("Kneaders", r"^KNEADERS"), ("Swig", r"^SWIG$"), ("Crave Cookies", r"^CRAVE COOKIE"), ("Paris Baguette", r"^PARIS BAGUETTE"),
    ("Sweetgreen", r"^SWEETGREEN"), ("Torchy's Tacos", r"^TORCHYS"), ("Velvet Taco", r"^VELVET TACO"), ("Fuzzy's Taco Shop", r"^FUZZYS TACO"),
    ("Slim Chickens", r"^SLIM CHICKENS"), ("Zaxby's", r"^ZAXBY"), ("Bojangles", r"^BOJANGLES"), ("Church's Chicken", r"^CHURCHS (?:TEXAS )?CHICKEN"),
    ("Hooters", r"^HOOTERS"), ("Dairy Queen", r"^DAIRY QUEEN|^DQ GRILL|^DQ$"),
    # Florida-born or Florida-heavy chains (and the Southeast's)
    ("Pollo Tropical", r"^POLLO TROPICAL"), ("Pollo Campero", r"^POLLO CAMPERO"), ("Tijuana Flats", r"^TIJUANA FLATS"), ("PDQ", r"^PDQ$|^PDQ (?:CHICKEN|RESTAURANT)"),
    ("Miami Subs", r"^MIAMI SUBS"), ("Hurricane Grill & Wings", r"^HURRICANE GRILL"), ("Duffy's Sports Grill", r"^DUFFYS SPORTS"),
    ("Miller's Ale House", r"^MILLERS ALE ?HOUSE|^MILLERS ALEHOUSE"), ("Flanigan's", r"^FLANIGANS"), ("Bonefish Grill", r"^BONEFISH GRILL"),
    ("Carrabba's Italian Grill", r"^CARRABBA"), ("Seasons 52", r"^SEASONS 52"), ("BurgerFi", r"^BURGER ?FI\b"), ("4 Rivers Smokehouse", r"^4 RIVERS"),
    ("Sonny's BBQ", r"^SONNYS (?:BBQ|BAR B Q|REAL PIT)|^SONNYS$"), ("Beef 'O' Brady's", r"^BEEF O BRADY"), ("Ker's WingHouse", r"^KERS WING"),
    ("Mellow Mushroom", r"^MELLOW MUSHROOM"), ("Hungry Howie's", r"^HUNGRY HOWIE"), ("Anthony's Coal Fired Pizza", r"^ANTHONYS COAL"),
    ("Bento Asian Kitchen", r"^BENTO (?:ASIAN|CAFE)|^BENTO$"), ("Shells Seafood", r"^SHELLS SEAFOOD"), ("Ford's Garage", r"^FORDS GARAGE"),
    ("Bubbakoo's Burritos", r"^BUBBAKOO"), ("Bolay", r"^BOLAY"), ("Gyro Shack", r"^GYRO SHACK"), ("Latin House Grill", r"^LATIN HOUSE (?:GRILL|PINES|SUNSET)\b"),
    ("La Carreta", r"^LA CARRETA"), ("Sergio's", r"^SERGIOS"), ("Vicky Bakery", r"^VICKY BAKERY"), ("Pinecrest Bakery", r"^PINECREST BAKERY"),
    ("Carvel", r"^CARVEL"), ("Kilwins", r"^KILWINS"), ("Hooters", r"^HOOTERS"), ("Twistee Treat", r"^TWISTEE"), ("Krystal", r"^KRYSTAL"),
    ("Steak 'n Shake", r"^STEAK N SHAKE"), ("Smokey Bones", r"^SMOKEY BONES"), ("Fuddruckers", r"^FUDDRUCKERS"), ("Shula's", r"^SHULAS"),
    ("Pincho", r"^PINCHO(?: FACTORY)?$"), ("Lime Fresh", r"^LIME FRESH"), ("Playa Bowls", r"^PLAYA BOWLS"), ("Clean Juice", r"^CLEAN JUICE"),
    ("Moe's Southwest Grill", r"^MOES SOUTHWEST|^MOES$"), ("Jason's Deli", r"^JASONS DELI"), ("McAlister's Deli", r"^MCALISTERS"),
    ("Which Wich", r"^WHICH WICH"), ("Chuy's", r"^CHUYS"), ("Bonchon", r"^BONCHON"), ("Ruby Tuesday", r"^RUBY TUESDAY"),
    ("Cheddar's", r"^CHEDDARS"), ("Bahama Breeze", r"^BAHAMA BREEZE"), ("Yard House", r"^YARD HOUSE"), ("Kona Grill", r"^KONA GRILL"),
    ("Twin Peaks", r"^TWIN PEAKS"), ("Tropical Smoothie Cafe", r"^TROPICAL SMOOTHIE"), ("Pollo Loco", r"^EL POLLO LOCO"),
    ("Taco Bus", r"^TACO BUS"), ("Big Cheese Pizza", r"^BIG CHEESE PIZZA"), ("Ci Ci's Pizza", r"^CICIS"), ("Jeremiah's Italian Ice", r"^JEREMIAHS (?:ITALIAN|ICE)"),
    ("Rita's Italian Ice", r"^RITAS (?:ITALIAN|ICE)"), ("Bagel Boss", r"^BAGEL BOSS"), ("Le Macaron", r"^LE MACARON"),
    ("Joe's Crab Shack", r"^JOES CRAB SHACK"), ("Hurricane Grill", r"^HURRICANE GRILL"), ("Whataburger", r"^WHATABURGER"),
    ("Buc-ee's", r"^BUC EES"), ("Wawa", r"^WAWA"), ("RaceTrac", r"^RACE ?TRAC"), ("Circle K", r"^CIRCLE K"), ("Sheetz", r"^SHEETZ"),
    ("Publix", r"^PUBLIX"), ("Winn-Dixie", r"^WINN ?DIXIE"), ("Sedano's", r"^SEDANOS"), ("Walmart", r"^WALMART|^WAL MART"), ("Target", r"^TARGET"),
    ("Kwik Stop", r"^KWIK STOP"), ("Love's", r"^LOVES TRAVEL"), ("Pilot", r"^PILOT TRAVEL|^PILOT FLYING"),
]
_C = [(b, re.compile(p)) for b, p in BRANDS]

# distinctive brands also recognized mid-name ("HALE FAMILY MCDONALDS", "SAII BABA DUNKIN")
_ANYWHERE = [(b, re.compile(p)) for b, p in [("McDonald's", r"\bMC ?DONALDS\b"), ("Dunkin'", r"\bDUNKIN\b"), ("Starbucks", r"\bSTARBUCKS\b"),
             ("Wingstop", r"\bWING ?STOP\b"), ("Culver's", r"\bCULVERS\b"), ("Popeyes", r"\bPOPEYES\b"), ("Chipotle", r"\bCHIPOTLE\b"),
             ("Jimmy John's", r"\bJIMMY JOHNS\b"), ("Taco Bell", r"\bTACO BELL\b"), ("Pollo Tropical", r"\bPOLLO TROPICAL\b")]]


def brand_of(nkey, *more):
    """Brand from the display name, else from Overture's brand label."""
    keys = [k for k in [nkey] + [m for m in more if isinstance(m, str)] if isinstance(k, str)]
    for k in keys:
        for part in [k or ""] + [p.strip() for p in (k or "").split("/")]:
            for b, p in _C:
                if p.search(part):
                    return b
    for k in keys:
        for b, p in _ANYWHERE:
            if p.search(k or ""):
                return b
    return None
