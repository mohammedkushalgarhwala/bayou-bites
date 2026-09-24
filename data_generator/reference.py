"""Static reference data for the Bayou Bites generator.

Everything here is hand-written (not random) so the "shape" of the business
is easy to read and tweak: locations, menu, campaigns and name pools.
"""

# --------------------------------------------------------------------------
# Locations: 20 across Texas. Region = metro area used by campaigns/marts.
# Houston 7 (incl. Katy #20), Dallas 5, Austin 4, San Antonio 4.
# --------------------------------------------------------------------------
LOCATIONS = [
    # id, name,                         city,          region,        open_date,    seats, drive_thru, manager
    (1,  "Bayou Bites Montrose",        "Houston",     "Houston",     "2019-03-15", 90,  False, "Renee Boudreaux"),
    (2,  "Bayou Bites The Heights",     "Houston",     "Houston",     "2019-09-01", 110, False, "Marcus Villarreal"),
    (3,  "Bayou Bites Midtown",         "Houston",     "Houston",     "2020-06-20", 80,  False, "Tasha Nguyen"),
    (4,  "Bayou Bites Galleria",        "Houston",     "Houston",     "2021-02-10", 120, True,  "Luis Carrillo"),
    (5,  "Bayou Bites Clear Lake",      "Houston",     "Houston",     "2022-05-05", 100, True,  "Amber Thibodeaux"),
    (6,  "Bayou Bites Sugar Land",      "Sugar Land",  "Houston",     "2023-08-12", 95,  True,  "Kevin Patel"),
    (7,  "Bayou Bites Deep Ellum",      "Dallas",      "Dallas",      "2020-01-18", 85,  False, "Jasmine Ortiz"),
    (8,  "Bayou Bites Uptown",          "Dallas",      "Dallas",      "2020-11-07", 100, False, "Derek Landry"),
    (9,  "Bayou Bites Lakewood",        "Dallas",      "Dallas",      "2021-07-24", 90,  True,  "Brian Holloway"),
    (10, "Bayou Bites Plano",           "Plano",       "Dallas",      "2022-03-19", 115, True,  "Sofia Ramirez"),
    (11, "Bayou Bites Frisco",          "Frisco",      "Dallas",      "2024-04-06", 105, True,  "Tyler Guidry"),
    (12, "Bayou Bites South Congress",  "Austin",      "Austin",      "2019-12-01", 75,  False, "Maya Hernandez"),
    (13, "Bayou Bites East Austin",     "Austin",      "Austin",      "2021-04-17", 70,  False, "Jordan Fontenot"),
    (14, "Bayou Bites The Domain",      "Austin",      "Austin",      "2022-10-22", 110, True,  "Priya Shah"),
    (15, "Bayou Bites Round Rock",      "Round Rock",  "Austin",      "2024-01-13", 100, True,  "Carlos Mendoza"),
    (16, "Bayou Bites Riverwalk",       "San Antonio", "San Antonio", "2020-02-29", 95,  False, "Elena Garza"),
    (17, "Bayou Bites Pearl District",  "San Antonio", "San Antonio", "2021-09-11", 85,  False, "Nathan Broussard"),
    (18, "Bayou Bites Alamo Heights",   "San Antonio", "San Antonio", "2022-08-27", 90,  True,  "Gabriela Trevino"),
    (19, "Bayou Bites Stone Oak",       "San Antonio", "San Antonio", "2023-05-20", 105, True,  "Ryan Mouton"),
    (20, "Bayou Bites Katy",            "Katy",        "Houston",     "2026-04-01", 120, True,  "Dana LeBlanc"),
]

KATY_ID = 20          # story event 1: new location opens 2026-04-01
PROBLEM_ID = 9        # story event 3: Lakewood (Dallas) goes downhill from April

# DQ: messy city values written to the CSV (clean value lives in LOCATIONS)
CITY_DQ = {3: "houston", 5: " Houston ", 17: "SAN ANTONIO "}

AREA_CODES = {
    "Houston": ["713", "832", "281"],
    "Dallas": ["214", "469", "972"],
    "Austin": ["512", "737"],
    "San Antonio": ["210", "726"],
}

# --------------------------------------------------------------------------
# Menu: 35 items. `pop` is an internal popularity weight (not exported).
# --------------------------------------------------------------------------
MENU = [
    # id, name,                          category,  price, cost, spicy, launched,     pop
    (1,  "Brisket Street Tacos",         "Entree",  11.49, 3.95, False, "2019-03-15", 1.5),
    (2,  "Blackened Fish Tacos",         "Entree",  11.99, 4.10, True,  "2019-03-15", 1.3),
    (3,  "Chicken Fajita Tacos",         "Entree",  10.49, 3.20, False, "2019-03-15", 1.4),
    (4,  "Crawfish Etouffee",            "Entree",  14.99, 5.40, True,  "2019-03-15", 0.9),
    (5,  "Shrimp & Andouille Gumbo",     "Entree",  13.49, 4.60, True,  "2019-03-15", 1.0),
    (6,  "Chicken & Sausage Jambalaya",  "Entree",  12.99, 3.90, True,  "2019-03-15", 1.1),
    (7,  "Cajun Chicken Burrito",        "Entree",  11.99, 3.70, True,  "2020-02-01", 1.2),
    (8,  "Carne Asada Burrito",          "Entree",  12.49, 4.30, False, "2019-03-15", 1.1),
    (9,  "Brisket Enchiladas",           "Entree",  13.99, 4.80, False, "2021-06-01", 0.9),
    (10, "Cheese Enchiladas",            "Entree",  10.99, 2.90, False, "2019-03-15", 0.8),
    (11, "Fried Shrimp Po' Boy",         "Entree",  13.49, 4.70, False, "2019-03-15", 1.0),
    (12, "Crawfish Boil Platter",        "Entree",  18.99, 7.20, True,  "2022-03-01", 0.5),
    (13, "Red Beans & Rice Bowl",        "Entree",   9.99, 2.40, False, "2019-03-15", 0.7),
    (14, "Queso Fundido Nachos",         "Entree",  10.49, 3.10, False, "2020-09-15", 0.8),
    (15, "Chicken Tinga Quesadilla",     "Entree",  10.99, 3.30, True,  "2021-01-10", 0.9),
    (16, "Veggie Fajita Bowl",           "Entree",  10.49, 2.80, False, "2023-01-09", 0.6),
    (17, "Boudin Quesadilla",            "Entree",  12.49, 3.80, True,  "2026-05-01", 4.5),
    (18, "Chips & Queso",                "Side",     5.49, 1.20, False, "2019-03-15", 1.4),
    (19, "Chips & Salsa",                "Side",     3.99, 0.70, False, "2019-03-15", 1.2),
    (20, "Mexican Street Corn",          "Side",     4.49, 1.10, True,  "2020-05-01", 1.0),
    (21, "Cajun Fries",                  "Side",     3.99, 0.80, True,  "2019-03-15", 1.3),
    (22, "Hushpuppies",                  "Side",     4.49, 0.90, False, "2019-03-15", 0.9),
    (23, "Dirty Rice",                   "Side",     3.99, 0.90, True,  "2019-03-15", 0.8),
    (24, "Charro Beans",                 "Side",     3.49, 0.60, False, "2019-03-15", 0.6),
    (25, "Boudin Balls",                 "Side",     6.49, 1.80, True,  "2021-10-01", 0.9),
    (26, "Fountain Drink",               "Drink",    2.49, 0.30, False, "2019-03-15", 1.8),
    (27, "Sweet Tea",                    "Drink",    2.49, 0.25, False, "2019-03-15", 1.5),
    (28, "Horchata",                     "Drink",    3.49, 0.60, False, "2019-03-15", 0.9),
    (29, "Agua Fresca",                  "Drink",    3.49, 0.60, False, "2020-05-01", 0.8),
    (30, "Mexican Coke",                 "Drink",    3.29, 1.00, False, "2019-03-15", 0.9),
    (31, "Abita Root Beer",              "Drink",    3.49, 1.10, False, "2019-03-15", 0.6),
    (32, "Beignets",                     "Dessert",  4.99, 0.90, False, "2019-03-15", 1.4),
    (33, "Tres Leches Cake",             "Dessert",  5.49, 1.30, False, "2019-03-15", 1.0),
    (34, "Churros",                      "Dessert",  4.49, 0.80, False, "2019-03-15", 1.1),
    (35, "Pecan Praline",                "Dessert",  2.99, 0.60, False, "2020-11-01", 0.6),
]

BOUDIN_QUESADILLA_ID = 17   # story event 7
TACO_IDS = [1, 2, 3]        # Taco Tuesday BOGO
CRAWFISH_IDS = [4, 12]      # Crawfish Fridays
GUMBO_ID = 5                # Mardi Gras

# DQ: these menu rows get the price written as "$12.49" instead of "12.49"
PRICE_DOLLAR_DQ = [6, 21, 33]

# --------------------------------------------------------------------------
# Campaigns (Supabase). `lift` multiplies order volume on eligible
# day/location cells; `share` is the probability an eligible order uses the
# promo code. Both are internal knobs (not exported).
# --------------------------------------------------------------------------
HOUSTON_IDS = [1, 2, 3, 4, 5, 6, 20]

CAMPAIGNS = [
    dict(campaign_id=1, campaign_name="New Year, New Bites", promo_code="NEWYEAR10",
         channel="email", start_date="2026-01-02", end_date="2026-01-31", budget=4000,
         target_locations="ALL", days_of_week=None, offer="10% off entire order",
         lift=1.04, share=0.07, order_channel=None),
    dict(campaign_id=2, campaign_name="Mardi Gras Gumbo Week", promo_code="MARDIGRAS",
         channel="social", start_date="2026-02-10", end_date="2026-02-17", budget=3000,
         target_locations="ALL", days_of_week=None, offer="$3 off Shrimp & Andouille Gumbo",
         lift=1.06, share=0.10, order_channel=None),
    dict(campaign_id=3, campaign_name="Taco Tuesday BOGO", promo_code="TACOBOGO",
         channel="social", start_date="2026-03-01", end_date="2026-03-31", budget=12000,
         target_locations="ALL", days_of_week="Tue", offer="Buy one taco plate, get one free",
         lift=1.80, share=0.52, order_channel=None),
    dict(campaign_id=4, campaign_name="Crawfish Fridays", promo_code="CRAWFRI",
         channel="sms", start_date="2026-04-03", end_date="2026-05-29", budget=9000,
         target_locations=",".join(str(i) for i in HOUSTON_IDS), days_of_week="Fri",
         offer="$5 off any crawfish entree", lift=1.55, share=0.42, order_channel=None),
    dict(campaign_id=5, campaign_name="Boudin Quesadilla Launch", promo_code="BOUDIN20",
         channel="email", start_date="2026-05-01", end_date="2026-05-31", budget=5000,
         target_locations="ALL", days_of_week=None, offer="20% off the new Boudin Quesadilla",
         lift=1.05, share=0.08, order_channel=None),
    dict(campaign_id=6, campaign_name="Summer Delivery Days", promo_code="DELIVER15",
         channel="sms", start_date="2026-06-01", end_date="2026-06-30", budget=6000,
         target_locations="ALL", days_of_week=None, offer="15% off delivery orders",
         lift=1.08, share=0.22, order_channel="delivery"),
]

# --------------------------------------------------------------------------
# Name pools (Texas mix: Anglo, Hispanic, Cajun, Vietnamese, Indian, ...)
# --------------------------------------------------------------------------
FIRST_NAMES = [
    "James", "Maria", "Robert", "Jennifer", "Michael", "Linda", "David", "Sarah",
    "Jose", "Ana", "Juan", "Carmen", "Luis", "Sofia", "Carlos", "Isabella",
    "Emily", "Daniel", "Ashley", "Matthew", "Jessica", "Andrew", "Olivia", "Joshua",
    "Madison", "Ethan", "Chloe", "Noah", "Ava", "Liam", "Mia", "Lucas",
    "Camille", "Remy", "Celeste", "Andre", "Margot", "Pierre", "Josette", "Lucien",
    "Minh", "Linh", "Tuan", "Mai", "Priya", "Arjun", "Anika", "Rohan",
    "Destiny", "Jamal", "Aaliyah", "Marcus", "Brianna", "Tyrone", "Kayla", "Darnell",
    "Hannah", "Caleb", "Grace", "Wyatt", "Abigail", "Colton", "Harper", "Austin",
    "Valeria", "Diego", "Ximena", "Mateo", "Lucia", "Santiago",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson",
    "Garcia", "Martinez", "Rodriguez", "Hernandez", "Lopez", "Gonzalez", "Perez", "Sanchez",
    "Ramirez", "Torres", "Flores", "Rivera", "Gomez", "Diaz", "Reyes", "Morales",
    "Boudreaux", "Thibodeaux", "Hebert", "Landry", "Broussard", "Guidry", "LeBlanc", "Fontenot",
    "Arceneaux", "Robichaux", "Comeaux", "Doucet", "Nguyen", "Tran", "Le", "Pham",
    "Patel", "Shah", "Reddy", "Kumar", "Jackson", "Thomas", "Harris", "Walker",
    "Robinson", "Lewis", "Young", "King", "Wright", "Hill", "Scott", "Green",
    "Baker", "Adams", "Nelson", "Carter", "Mitchell", "Roberts", "Turner", "Phillips",
    "O'Brien", "McAllister",
]

EMAIL_DOMAINS = ["example.com", "example.net", "example.org"]

# --------------------------------------------------------------------------
# Review text templates. {item} is replaced with a menu item name.
# --------------------------------------------------------------------------
REVIEW_POSITIVE = [
    "Loved the {item}! Will definitely be back.",
    "The {item} was fantastic and the line moved fast.",
    "Best Tex-Mex and Cajun combo in town. Get the {item}.",
    "Friendly staff, clean dining room, and the {item} was on point.",
    "{item} was fresh and hot. Great value for the money.",
    "Our go-to spot. The {item} never disappoints.",
    "Huge portions and the {item} had real kick. Five stars.",
    "Quick pickup, order was right, {item} was delicious.",
]
REVIEW_NEUTRAL = [
    "Decent meal. The {item} was fine but nothing special.",
    "Food was okay, a little pricey for the portion size.",
    "{item} was good, but the dining room was messy.",
    "Average visit. Would try something other than the {item} next time.",
]
REVIEW_NEGATIVE = [
    "The {item} was bland and overpriced.",
    "Wrong order and nobody apologized.",
    "Not impressed. The {item} was soggy.",
    "Dirty tables and the drink machine was broken.",
]
# Problem location (Lakewood) from April: slow / cold food / wait
REVIEW_PROBLEM_NEGATIVE = [
    "Waited 45 minutes for our order. Service is so slow now.",
    "Cold food again. The {item} was barely warm.",
    "Long wait at the counter and cold food when it finally came.",
    "Slow service, cold food, and a 30 minute wait for takeout.",
    "Used to love this place but the wait is ridiculous and the {item} was cold.",
    "Staff seems overwhelmed. Slow line and my {item} came out cold.",
    "Drive-thru wait was over 20 minutes. Food was cold by the time we got home.",
]
REVIEW_PROBLEM_NEUTRAL = [
    "Food is still decent but the wait has gotten really long.",
    "{item} was fine, service was slow.",
    "Okay meal, but the wait was longer than it used to be.",
]
