"""Canonical Wii Sports Resort (RZTE01) Archipelago data.

This module is the single source of truth for item/location names, IDs, save
offsets, access requirements, and goal definitions. It is deliberately free of
any Archipelago imports so the external Dolphin bridge client can load it
directly (without Archipelago installed) and stay perfectly in sync with the
generated world.

All memory offsets are relative to the resolved save buffer unless noted.
Unlock flags use the game's 3-state convention:

    0x00 = Unlocked (already seen)
    0x01 = Unlocked and New
    0x02 = Locked
"""

from __future__ import annotations

# --- ID namespaces ----------------------------------------------------------
BASE_ID = 57530000
LOCATION_BASE_ID = BASE_ID + 100000

# --- Unlock flag values -----------------------------------------------------
UNLOCK_LOCKED = 0x02
UNLOCK_NEW = 0x01
UNLOCK_SEEN = 0x00

# --- Progressive filler item addresses (NOT save-buffer relative) -----------
# Cycling stamina drain coefficient (absolute MEM address, big-endian float).
CYCLING_DRAIN_ADDRESS = 0x806FC820
CYCLING_DRAIN_DEFAULT = 20.0
MAX_CYCLING_STAMINA_UPGRADES = 10
# Showdown starting-heart mailbox consumed by the installed Gecko hook.
SHOWDOWN_HEART_MAILBOX_ADDRESS = 0x817FFFF0
MAX_SHOWDOWN_HEART_UPGRADES = 7
# Table Tennis Return Challenge can score value (absolute MEM address, u32).
CAN_SCORE_ADDRESS = 0x806F2304
BASE_CAN_SCORE = 3
SCORE_PER_CAN_SCORE_UPGRADE = 1
MAX_CAN_SCORE_UPGRADES = 7
# Island Flyover no-plane-crash mailbox consumed by the installed Gecko hook.
# 1 = upgrade received (no longer crashes the plane on hard landings).
NO_PLANE_CRASH_MAILBOX_ADDRESS = 0x817FFFF1

PROGRESSIVE_CYCLING_ITEM = "Progressive Cycling Stamina Upgrade"
PROGRESSIVE_HEARTS_ITEM = "Progressive Swordplay Showdown Heart Upgrade"
PROGRESSIVE_CAN_SCORE_ITEM = "Progressive Table Tennis Can Score Upgrade"
NO_PLANE_CRASH_ITEM = "Island Flyover No Plane Crash Upgrade"
FILLER_ITEM = "Nothing"

VICTORY_ITEM = "Victory"
VICTORY_LOCATION = "Goal"


# --- Gamemode unlock flags (the 17 goal-relevant modes) ---------------------
GAMEMODES: list[tuple[str, int]] = [
    ("Swordplay Showdown", 0x009B),
    ("Swordplay Duel", 0x009F),
    ("Swordplay Speed Slice", 0x00A3),
    ("Power Cruising", 0x00A7),
    ("Frisbee Dog", 0x00B3),
    ("Basketball 3-Point Contest", 0x00B7),
    ("Basketball Pickup Game", 0x00BB),
    ("Bowling Standard Game", 0x00BF),
    ("Bowling 100-Pin Game", 0x00C3),
    ("Bowling Spin Control", 0x00C7),
    ("Canoeing Speed Challenge", 0x00CF),
    ("Table Tennis Return Challenge", 0x00D3),
    ("Table Tennis Match", 0x00D7),
    ("Island Flyover", 0x00DF),
    ("Frisbee Golf", 0x00EB),
    ("Cycling Road Race", 0x00F3),
    ("Skydiving", 0x00F7),
]

# Modes the client must keep at 0x02 (Locked) at all times.
ALWAYS_LOCKED_GAMEMODES: list[tuple[str, int]] = [
    ("Power Cruising VS", 0x00AB),
    ("Canoeing VS", 0x00CB),
    ("Air Sports Dogfight", 0x00E3),
    ("Cycling VS", 0x00EF),
]

GAMEMODE_ITEMS = [name for name, _ in GAMEMODES]


def _sequential(prefix: str, base: int, names: list[str], step: int) -> list[tuple[str, int]]:
    return [(f"{prefix}: {name}", base + step * i) for i, name in enumerate(names)]


# --- Swordplay Showdown stage unlocks (profile slot 1) ----------------------
_SHOWDOWN_NORMAL = [
    "Bridge", "Lighthouse", "Beach", "Mountain", "Forest",
    "Ruins", "Waterfall", "Cliffs", "Castle", "Volcano",
]
_SHOWDOWN_STAGE_NAMES = _SHOWDOWN_NORMAL + [f"{n} Reverse" for n in _SHOWDOWN_NORMAL]
SHOWDOWN_STAGES = _sequential("Swordplay Showdown", 0x9088, _SHOWDOWN_STAGE_NAMES, 1)

SHOWDOWN_STAGE_ITEMS = [name for name, _ in SHOWDOWN_STAGES]
SHOWDOWN_NORMAL_ITEMS = SHOWDOWN_STAGE_ITEMS[:10]
SHOWDOWN_VOLCANO_ITEM = "Swordplay Showdown: Volcano"
SHOWDOWN_VOLCANO_REVERSE_ITEM = "Swordplay Showdown: Volcano Reverse"

# --- Island Flyover time-of-day unlocks -------------------------------------
ISLAND_TIMES = _sequential("Island Flyover", 0x8EE4, ["Daytime", "Evening", "Night"], 1)
ISLAND_TIME_ITEMS = [name for name, _ in ISLAND_TIMES]

# --- Cycling Road Race stage unlocks ----------------------------------------
_CYCLING_NAMES = [
    "Around the Island", "To the Beach", "Across the Bridge", "Over Talon Rock",
    "Up the Volcano", "Into Maka Wuhu", "3-Stage Race A", "3-Stage Race B",
    "6-Stage Race",
]
CYCLING_STAGES = _sequential("Cycling Road Race", 0x07DF, _CYCLING_NAMES, 4)
CYCLING_STAGE_ITEMS = [name for name, _ in CYCLING_STAGES]
CYCLING_1STAGE_ITEMS = CYCLING_STAGE_ITEMS[:6]
CYCLING_3STAGE_ITEMS = CYCLING_STAGE_ITEMS[6:8]
CYCLING_6STAGE_ITEMS = CYCLING_STAGE_ITEMS[8:9]

# --- Wakeboarding difficulty unlocks ----------------------------------------
WAKEBOARDING = _sequential("Wakeboarding", 0x05FF, ["Beginner", "Intermediate", "Expert"], 4)
WAKEBOARDING_ITEMS = [name for name, _ in WAKEBOARDING]
WAKEBOARDING_EXPERT_ITEM = "Wakeboarding: Expert"

# --- Canoeing Speed Challenge difficulty unlocks ----------------------------
CANOEING_SPEED = _sequential(
    "Canoeing Speed Challenge", 0x050F, ["Beginner", "Intermediate", "Expert"], 4
)
CANOEING_SPEED_ITEMS = [name for name, _ in CANOEING_SPEED]

# --- Archery difficulty unlocks ---------------------------------------------
ARCHERY = _sequential("Archery", 0x028F, ["Beginner", "Intermediate", "Expert"], 4)
ARCHERY_ITEMS = [name for name, _ in ARCHERY]

# --- Power Cruising slalom course unlocks -----------------------------------
POWER_CRUISING = _sequential(
    "Power Cruising", 0x01EF,
    ["Beach", "Lagoon", "Lighthouse", "Marina", "Cavern", "Shoals"], 4,
)
POWER_CRUISING_ITEMS = [name for name, _ in POWER_CRUISING]
POWER_CRUISING_SHOALS_ITEM = "Power Cruising: Shoals"

# --- Golf course unlocks ----------------------------------------------------
_GOLF_COURSE_NAMES = [
    "Resort A (3-Hole)", "Resort B (3-Hole)", "Resort C (3-Hole)",
    "Classic A (3-Hole)", "Classic B (3-Hole)", "Classic C (3-Hole)",
    "Special (3-Hole)", "Resort (9-Hole)", "Classic (9-Hole)", "18-Hole",
]
GOLF = _sequential("Golf", 0x06EF, _GOLF_COURSE_NAMES, 4)
GOLF_ITEMS = [name for name, _ in GOLF]
GOLF_NINE_HOLE_ITEMS = ["Golf: Resort (9-Hole)", "Golf: Classic (9-Hole)"]
GOLF_18_ITEM = "Golf: 18-Hole"

# --- Frisbee Golf course unlocks --------------------------------------------
FRISBEE_GOLF = _sequential("Frisbee Golf", 0x073F, _GOLF_COURSE_NAMES, 4)
FRISBEE_GOLF_ITEMS = [name for name, _ in FRISBEE_GOLF]
FRISBEE_GOLF_RESORT_C_ITEM = "Frisbee Golf: Resort C (3-Hole)"
FRISBEE_GOLF_RESORT_NINE_ITEM = "Frisbee Golf: Resort (9-Hole)"
FRISBEE_GOLF_18_ITEM = "Frisbee Golf: 18-Hole"
FRISBEE_GOLF_LUCKY_SKIP_ITEMS = [
    FRISBEE_GOLF_RESORT_C_ITEM,
    FRISBEE_GOLF_RESORT_NINE_ITEM,
    FRISBEE_GOLF_18_ITEM,
]

# Every save-flag unlock item (name -> save offset).
UNLOCK_ITEM_OFFSETS: dict[str, int] = {}
for _name, _off in GAMEMODES:
    UNLOCK_ITEM_OFFSETS[_name] = _off
for _group in (
    SHOWDOWN_STAGES, ISLAND_TIMES, CYCLING_STAGES, WAKEBOARDING,
    CANOEING_SPEED, ARCHERY, POWER_CRUISING, GOLF, FRISBEE_GOLF,
):
    for _name, _off in _group:
        UNLOCK_ITEM_OFFSETS[_name] = _off


# --- Stamps -- 20 categories x 5 = 100 location checks ----------------------
# Category key aligns with the gamemode item name where one exists so access
# rules can reference it directly.
STAMP_CATEGORIES: list[tuple[str, int, list[str]]] = [
    ("Swordplay Showdown", 0x8CEC,
     ["Not a Scratch", "Sword Fighter", "Perfect 10", "Swordmaster", "Untouchable"]),
    ("Swordplay Duel", 0x8D00,
     ["Cliff-hanger", "Straight to the Point", "Met Your Match", "One-Hit Wonder", "Last Mii Standing"]),
    ("Swordplay Speed Slice", 0x8D14,
     ["Slice and Dice", "Slicing Machine", "Psychic Slice", "Double Time", "A Cut Above"]),
    ("Power Cruising", 0x8D28,
     ["Ringmaster", "5,000-pointer", "Power Cruiser", "Power Jumper", "Leisure Cruiser"]),
    ("Archery", 0x8D50,
     ["Bull Stampede", "Sure Shot", "Century Shot", "A Secret to Everybody", "Sharpshooter"]),
    ("Frisbee Dog", 0x8D64,
     ["Good Dog", "Balloon Animal", "A for Effort", "Perfect Target", "Golden Arm"]),
    ("Basketball 3-Point Contest", 0x8D78,
     ["Hot Streak", "Bonus Plumber", "Quick Draw", "Hot Hand", "Pure Shooter"]),
    ("Basketball Pickup Game", 0x8D8C,
     ["Triple Dip", "Rim Rattler", "Lights Out", "Buzzer Beater", "Hoop Hero"]),
    ("Bowling Standard Game", 0x8DA0,
     ["Gobble Gobble", "Split Spare", "High Roller", "Pin Dropper", "Perfect Game"]),
    ("Bowling 100-Pin Game", 0x8DB4,
     ["Super Strike", "Split Spare", "Off the Wall", "Secret Strike", "Pin Dropper"]),
    ("Bowling Spin Control", 0x8DC8,
     ["One for All", "Split Spare", "Head First", "English Major", "Pin Dropper"]),
    ("Canoeing Speed Challenge", 0x8DF0,
     ["Beginner License", "Intermediate License", "Expert License", "Ducks in a Row", "Cut the Red Tape"]),
    ("Table Tennis Return Challenge", 0x8E04,
     ["50-pointer", "100-pointer", "200-pointer", "Recycler", "Save Face"]),
    ("Table Tennis Match", 0x8E18,
     ["In Your Face", "Back from the Brink", "Epic Rally", "Perfectly Matched", "Table Titan"]),
    ("Wakeboarding", 0x8E2C,
     ["Huge Air", "Bag of Tricks", "Smooth Landing", "Master Carver", "The Long Way Home"]),
    ("Island Flyover", 0x8E40,
     ["Island Hopper", "Pop Frenzy", "Follow That Plane", "Wuhu Tour Guide", "Balloonatic"]),
    ("Golf", 0x8E68,
     ["Under Par", "Chip In", "King of Clubs", "Ace of Clubs", "Hole in One"]),
    ("Frisbee Golf", 0x8E7C,
     ["Under Par", "Lucky Skip", "On a Roll", "Hole in One", "Straight and Narrow"]),
    ("Cycling Road Race", 0x8EA4,
     ["Last Gasp", "First of Many", "1-Stage Master", "3-Stage Master", "6-Stage Master"]),
    ("Skydiving", 0x8EB8,
     ["High Five", "For the Birds", "Friends in High Places", "Camera Shy", "200-Point Dive"]),
]


def stamp_location_name(category: str, stamp: str) -> str:
    return f"{category} - {stamp}"


# category -> list of (location_name, offset)
STAMPS: list[tuple[str, str, int]] = []
for _category, _base, _stamps in STAMP_CATEGORIES:
    for _i, _stamp in enumerate(_stamps):
        STAMPS.append((_category, stamp_location_name(_category, _stamp), _base + 4 * _i))


# --- Island Flyover iPoints -- 80 location checks ---------------------------
_IPOINT_NAMES = [
    "Red Iron Bridge", "Cocoba Hotel", "Cabana Lagoon", "The Queen Peach",
    "The Nineteenth Hole Hotel", "Summerstone Castle", "The Candle",
    "Mysterious Ruins", "Wind Orchard", "Swaying Bridge", "Summerstone Falls",
    "Crab Rock", "Starboard Harbor", "Silk Sands", "Evergreen Grove",
    "Mountain Monument", "Gateway to Wuhu", "Sugarsand Beach", "Hillside Cabins",
    "Talon Rock", "Power-Cruising Area", "Camel Rock", "Duckling Lake",
    "Basketball Court", "Bowling Alley", "Swordplay Colosseum", "Pool Patio",
    "Frisbee Dog Park", "Wishing Fountain", "Serpent's Mouth",
    "Beginner's Wakeboarding Area", "Forest Monument", "Golf Area A",
    "Golf Area B", "Golf Area C", "Off-Road Vehicle", "Toppled Monument",
    "Hilltop Overlook", "Maka Wuhu", "Heart of Maka Wuhu", "Pirate's Eye",
    "Island Loop Tunnel #1", "Lava Tube", "Sea Serpent Cavern",
    "Miguel's Guide Plane", "Broken Clock Tower", "Palm Boulevard",
    "Heartbreak Peak", "Weathered Monument", "Lone Cedar",
    "Firework Launch Zone 1", "Firework Launch Zone 2", "Sweet Beach",
    "Starry Beach", "Tennis Courts", "Beginner's Archery Area",
    "Needlepoint Spire", "Dead-End Point", "Cliffside Ruins",
    "Entrance to the Mysterious Ruins", "Barnacle Arch", "Private Island",
    "Deserted Island", "Island Loop Tunnel #2", "Stillwater Grotto",
    "Lava Monument", "Mountain Hikers", "Sundown Point", "Runner's Circle",
    "Footbridge", "Cedar-Tree Tunnel", "Wedge Island Marina", "Whale Watchers",
    "Diving Spot", "Sportfishing Spot", "Extreme Canoeist",
    "Undersea-Cable Inspectors", "The Whale Shark", "Seaplane Team",
    "The Sea Caddy",
]
IPOINTS: list[tuple[str, int]] = [
    (f"iPoint: {name}", 0x8EE8 + i) for i, name in enumerate(_IPOINT_NAMES)
]


# --- Swordplay Showdown stage-clear locations -- 20 live checks --------------
SHOWDOWN_CLEARS: list[tuple[str, int]] = [
    (f"Swordplay Showdown Clear: {name}", index)
    for index, name in enumerate(_SHOWDOWN_STAGE_NAMES)
]


# ---------------------------------------------------------------------------
# Access requirements
#
# A requirement is a list of clauses. Each clause is either:
#   ("all", [item, ...])  -> must have every listed item
#   ("any", [item, ...])  -> must have at least one listed item
# A location is reachable when every clause is satisfied.
# ---------------------------------------------------------------------------
_STAMP_BASE_REQUIREMENT: dict[str, list[tuple[str, list[str]]]] = {}
for _category, _base, _stamps in STAMP_CATEGORIES:
    if _category == "Archery":
        _STAMP_BASE_REQUIREMENT[_category] = [("any", ARCHERY_ITEMS)]
    elif _category == "Wakeboarding":
        _STAMP_BASE_REQUIREMENT[_category] = [("any", WAKEBOARDING_ITEMS)]
    elif _category == "Golf":
        _STAMP_BASE_REQUIREMENT[_category] = [("any", GOLF_ITEMS)]
    elif _category == "Frisbee Golf":
        _STAMP_BASE_REQUIREMENT[_category] = [("all", ["Frisbee Golf"]), ("any", FRISBEE_GOLF_ITEMS)]
    elif _category == "Island Flyover":
        _STAMP_BASE_REQUIREMENT[_category] = [("all", ["Island Flyover"]), ("any", ISLAND_TIME_ITEMS)]
    elif _category == "Canoeing Speed Challenge":
        _STAMP_BASE_REQUIREMENT[_category] = [("all", ["Canoeing Speed Challenge"]), ("any", CANOEING_SPEED_ITEMS)]
    elif _category == "Cycling Road Race":
        _STAMP_BASE_REQUIREMENT[_category] = [("all", ["Cycling Road Race"]), ("any", CYCLING_STAGE_ITEMS)]
    elif _category == "Power Cruising":
        _STAMP_BASE_REQUIREMENT[_category] = [("all", ["Power Cruising"]), ("any", POWER_CRUISING_ITEMS)]
    elif _category == "Swordplay Showdown":
        _STAMP_BASE_REQUIREMENT[_category] = [("all", ["Swordplay Showdown"]), ("any", SHOWDOWN_NORMAL_ITEMS)]
    else:
        _STAMP_BASE_REQUIREMENT[_category] = [("all", [_category])]

# Strict stamp overrides that replace the category base requirement.
_STAMP_OVERRIDES: dict[str, list[tuple[str, list[str]]]] = {
    "Swordplay Showdown - Sword Fighter": [("all", ["Swordplay Showdown"] + SHOWDOWN_NORMAL_ITEMS)],
    "Swordplay Showdown - Perfect 10": [("all", ["Swordplay Showdown", SHOWDOWN_VOLCANO_ITEM])],
    "Swordplay Showdown - Swordmaster": [("all", ["Swordplay Showdown", SHOWDOWN_VOLCANO_REVERSE_ITEM])],
    "Swordplay Showdown - Untouchable": [("all", ["Swordplay Showdown", SHOWDOWN_VOLCANO_REVERSE_ITEM])],
    "Power Cruising - Power Cruiser": [("all", ["Power Cruising"] + POWER_CRUISING_ITEMS)],
    "Power Cruising - Power Jumper": [("all", ["Power Cruising", POWER_CRUISING_SHOALS_ITEM])],
    "Archery - A Secret to Everybody": [("all", ARCHERY_ITEMS)],
    "Canoeing Speed Challenge - Beginner License":
        [("all", ["Canoeing Speed Challenge", "Canoeing Speed Challenge: Beginner"])],
    "Canoeing Speed Challenge - Intermediate License":
        [("all", ["Canoeing Speed Challenge", "Canoeing Speed Challenge: Intermediate"])],
    "Canoeing Speed Challenge - Expert License":
        [("all", ["Canoeing Speed Challenge", "Canoeing Speed Challenge: Expert"])],
    "Canoeing Speed Challenge - Cut the Red Tape":
        [("all", ["Canoeing Speed Challenge"] + CANOEING_SPEED_ITEMS)],
    "Frisbee Golf - Lucky Skip": [
        ("all", ["Frisbee Golf"]), ("any", FRISBEE_GOLF_LUCKY_SKIP_ITEMS)
    ],
    "Frisbee Golf - Straight and Narrow": [("all", ["Frisbee Golf", FRISBEE_GOLF_18_ITEM])],
    "Golf - King of Clubs": [("any", [GOLF_18_ITEM] + GOLF_NINE_HOLE_ITEMS)],
    "Golf - Ace of Clubs": [("all", [GOLF_18_ITEM])],
    "Cycling Road Race - 1-Stage Master": [("all", ["Cycling Road Race"] + CYCLING_1STAGE_ITEMS)],
    "Cycling Road Race - 3-Stage Master": [("all", ["Cycling Road Race"] + CYCLING_3STAGE_ITEMS)],
    "Cycling Road Race - 6-Stage Master": [("all", ["Cycling Road Race"] + CYCLING_6STAGE_ITEMS)],
    "Island Flyover - Wuhu Tour Guide": [("all", ["Island Flyover"] + ISLAND_TIME_ITEMS)],
    "Island Flyover - Balloonatic": [("all", ["Island Flyover"] + ISLAND_TIME_ITEMS)],
    "Wakeboarding - Master Carver": [("all", [WAKEBOARDING_EXPERT_ITEM])],
}


def stamp_requirement(category: str, location_name: str) -> list[tuple[str, list[str]]]:
    return _STAMP_OVERRIDES.get(location_name, _STAMP_BASE_REQUIREMENT[category])


# location name -> requirement clauses
LOCATION_REQUIREMENTS: dict[str, list[tuple[str, list[str]]]] = {}
for _category, _loc_name, _off in STAMPS:
    LOCATION_REQUIREMENTS[_loc_name] = stamp_requirement(_category, _loc_name)
for _loc_name, _off in IPOINTS:
    LOCATION_REQUIREMENTS[_loc_name] = [("all", ["Island Flyover"]), ("any", ISLAND_TIME_ITEMS)]
for _index, _stage in enumerate(_SHOWDOWN_STAGE_NAMES):
    _loc_name = f"Swordplay Showdown Clear: {_stage}"
    LOCATION_REQUIREMENTS[_loc_name] = [("all", ["Swordplay Showdown", SHOWDOWN_STAGE_ITEMS[_index]])]


# --- Goals ------------------------------------------------------------------
GOAL_ALL_GAMEMODES = "all_gamemodes"
GOAL_ALL_SHOWDOWN_STAGES = "all_showdown_stages"
GOAL_ALL_IPOINTS = "all_ipoints"
GOAL_STAMP_CATEGORY = "stamp_category"
GOAL_ALL_STAMPS = "all_stamps"

STAMP_CATEGORY_NAMES = [category for category, _base, _stamps in STAMP_CATEGORIES]


def category_goal_items(category: str) -> list[str]:
    """All unlock items required to make every stamp in a category reachable."""
    required: set[str] = set()
    for _cat, loc_name, _off in STAMPS:
        if _cat != category:
            continue
        for _kind, items in stamp_requirement(category, loc_name):
            required.update(items)
    return sorted(item for item in required if item in UNLOCK_ITEM_OFFSETS)


def goal_requirement(goal: str, stamp_category: str) -> list[tuple[str, list[str]]]:
    if goal == GOAL_ALL_GAMEMODES:
        return [("all", GAMEMODE_ITEMS)]
    if goal == GOAL_ALL_SHOWDOWN_STAGES:
        return [("all", ["Swordplay Showdown"] + SHOWDOWN_STAGE_ITEMS)]
    if goal == GOAL_ALL_IPOINTS:
        return [("all", ["Island Flyover"] + ISLAND_TIME_ITEMS)]
    if goal == GOAL_STAMP_CATEGORY:
        return [("all", category_goal_items(stamp_category))]
    if goal == GOAL_ALL_STAMPS:
        every_item = sorted(UNLOCK_ITEM_OFFSETS)
        return [("all", every_item)]
    raise ValueError(f"unknown goal: {goal}")


# --- Always-junk stamps -----------------------------------------------------
# AP upgrades can make these impossible or inconsistent with randomized play.
ALWAYS_JUNK_STAMPS = [
    "Swordplay Showdown - Not a Scratch",
    "Swordplay Showdown - Perfect 10",
    "Swordplay Showdown - Untouchable",
    "Cycling Road Race - Last Gasp",
]


# --- Curated junk stamp list (default off) ----------------------------------
CURATED_JUNK_STAMPS = [
    "Skydiving - Friends in High Places",
    "Skydiving - 200-Point Dive",
    "Island Flyover - Wuhu Tour Guide",
    "Island Flyover - Balloonatic",
    "Archery - A Secret to Everybody",
    "Archery - Sharpshooter",
    "Basketball 3-Point Contest - Hot Hand",
    "Basketball 3-Point Contest - Pure Shooter",
    "Basketball Pickup Game - Hoop Hero",
    "Bowling Standard Game - High Roller",
    "Bowling Standard Game - Pin Dropper",
    "Bowling 100-Pin Game - Pin Dropper",
    "Bowling Spin Control - Pin Dropper",
    "Bowling Standard Game - Perfect Game",
    "Bowling Spin Control - English Major",
    "Canoeing Speed Challenge - Cut the Red Tape",
    "Cycling Road Race - Last Gasp",
    "Frisbee Dog - Perfect Target",
    "Frisbee Dog - Golden Arm",
    "Frisbee Golf - On a Roll",
    "Golf - Hole in One",
    "Frisbee Golf - Hole in One",
    "Frisbee Golf - Straight and Narrow",
    "Golf - King of Clubs",
    "Golf - Ace of Clubs",
    "Swordplay Duel - Met Your Match",
    "Swordplay Duel - Last Mii Standing",
    "Swordplay Speed Slice - A Cut Above",
    "Swordplay Showdown - Sword Fighter",
    "Swordplay Showdown - Untouchable",
    "Table Tennis Match - Perfectly Matched",
    "Table Tennis Match - Table Titan",
    "Table Tennis Return Challenge - Recycler",
    "Table Tennis Return Challenge - Save Face",
]


# ---------------------------------------------------------------------------
# Item / location tables (deterministic IDs shared with the client)
# ---------------------------------------------------------------------------
ITEM_TABLE: list[dict] = []


def _add_item(name: str, kind: str, classification: str, offset: int | None = None) -> None:
    ITEM_TABLE.append({
        "name": name,
        "id": BASE_ID + len(ITEM_TABLE),
        "kind": kind,
        "classification": classification,
        "offset": offset,
    })


for _name, _off in GAMEMODES:
    _add_item(_name, "gamemode", "progression", _off)
for _group in (
    SHOWDOWN_STAGES, ISLAND_TIMES, CYCLING_STAGES, WAKEBOARDING,
    CANOEING_SPEED, ARCHERY, POWER_CRUISING, GOLF, FRISBEE_GOLF,
):
    for _name, _off in _group:
        _add_item(_name, "unlock", "progression", _off)
_add_item(PROGRESSIVE_CYCLING_ITEM, "progressive_cycling", "useful")
_add_item(PROGRESSIVE_HEARTS_ITEM, "progressive_hearts", "useful")
_add_item(PROGRESSIVE_CAN_SCORE_ITEM, "progressive_can_score", "useful")
_add_item(NO_PLANE_CRASH_ITEM, "no_plane_crash", "useful")
_add_item(FILLER_ITEM, "filler", "filler")

ITEM_NAME_TO_ID = {entry["name"]: entry["id"] for entry in ITEM_TABLE}
ITEM_ID_TO_NAME = {entry["id"]: entry["name"] for entry in ITEM_TABLE}
ITEM_BY_NAME = {entry["name"]: entry for entry in ITEM_TABLE}


LOCATION_TABLE: list[dict] = []


def _add_location(name: str, category: str, detect: str, offset: int | None = None,
                  stage_index: int | None = None) -> None:
    LOCATION_TABLE.append({
        "name": name,
        "id": LOCATION_BASE_ID + len(LOCATION_TABLE),
        "category": category,
        "detect": detect,
        "offset": offset,
        "stage_index": stage_index,
    })


for _category, _loc_name, _off in STAMPS:
    _add_location(_loc_name, "stamp", "word_nonzero", offset=_off)
for _loc_name, _off in IPOINTS:
    _add_location(_loc_name, "ipoint", "byte_not_ff", offset=_off)
for _index, (_loc_name, _stage_index) in enumerate(SHOWDOWN_CLEARS):
    _add_location(_loc_name, "showdown_clear", "showdown_live", stage_index=_stage_index)

LOCATION_NAME_TO_ID = {entry["name"]: entry["id"] for entry in LOCATION_TABLE}
LOCATION_ID_TO_NAME = {entry["id"]: entry["name"] for entry in LOCATION_TABLE}
LOCATION_BY_NAME = {entry["name"]: entry for entry in LOCATION_TABLE}

STAMP_LOCATION_NAMES = [name for _cat, name, _off in STAMPS]
IPOINT_LOCATION_NAMES = [name for name, _off in IPOINTS]
SHOWDOWN_CLEAR_LOCATION_NAMES = [name for name, _idx in SHOWDOWN_CLEARS]


def _self_check() -> None:
    assert len(GAMEMODES) == 17, len(GAMEMODES)
    assert len(UNLOCK_ITEM_OFFSETS) == 84, len(UNLOCK_ITEM_OFFSETS)
    assert len(STAMPS) == 100, len(STAMPS)
    assert len(IPOINTS) == 80, len(IPOINTS)
    assert len(SHOWDOWN_CLEARS) == 20, len(SHOWDOWN_CLEARS)
    assert len(LOCATION_TABLE) == 200, len(LOCATION_TABLE)
    assert len(ITEM_NAME_TO_ID) == len(ITEM_TABLE), "duplicate item name"
    assert len(LOCATION_NAME_TO_ID) == len(LOCATION_TABLE), "duplicate location name"
    for name in ALWAYS_JUNK_STAMPS:
        assert name in LOCATION_NAME_TO_ID, f"always junk stamp not found: {name}"
    for name in CURATED_JUNK_STAMPS:
        assert name in LOCATION_NAME_TO_ID, f"curated junk stamp not found: {name}"
    for name, req in LOCATION_REQUIREMENTS.items():
        assert name in LOCATION_NAME_TO_ID, f"requirement for unknown location: {name}"
        for _kind, items in req:
            for item in items:
                assert item in ITEM_NAME_TO_ID, f"requirement references unknown item: {item}"


if __name__ == "__main__":
    _self_check()
    print(f"items={len(ITEM_TABLE)} locations={len(LOCATION_TABLE)} "
          f"unlocks={len(UNLOCK_ITEM_OFFSETS)} stamps={len(STAMPS)} "
          f"ipoints={len(IPOINTS)} clears={len(SHOWDOWN_CLEARS)} "
          f"curated_junk={len(CURATED_JUNK_STAMPS)}")
    print("data.py self-check OK")
