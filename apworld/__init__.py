"""Wii Sports Resort (RZTE01) Archipelago world definition."""

from __future__ import annotations

from BaseClasses import ItemClassification, LocationProgressType, Region, Tutorial

from worlds.AutoWorld import WebWorld, World

from . import data
from .items import (
    WiiSportsResortItem,
    create_item as _create_item,
    item_name_groups,
    item_name_to_id,
)
from .locations import (
    WiiSportsResortLocation,
    location_name_groups,
    location_name_to_id,
)
from .options import WiiSportsResortOptions
from .rules import set_rules

# Starting gamemodes that need an accompanying unlock to be playable.
STARTER_SUBUNLOCKS = {
    "Swordplay Showdown": data.SHOWDOWN_STAGE_ITEMS,
    "Power Cruising": data.POWER_CRUISING_ITEMS,
    "Canoeing Speed Challenge": data.CANOEING_SPEED_ITEMS,
    "Island Flyover": data.ISLAND_TIME_ITEMS,
    "Frisbee Golf": data.FRISBEE_GOLF_ITEMS,
    "Cycling Road Race": data.CYCLING_STAGE_ITEMS,
}


class WiiSportsResortWeb(WebWorld):
    theme = "ocean"
    game_info_languages = ["en"]
    tutorials = [
        Tutorial(
            "Multiworld Setup Guide",
            "A guide to playing Wii Sports Resort with Archipelago.",
            "English",
            "setup_en.md",
            "setup/en",
            ["WSR-Archipelago"],
        )
    ]


class WiiSportsResortWorld(World):
    """Wii Sports Resort multiworld: unlock modes, earn stamps, collect iPoints."""

    game = "Wii Sports Resort"
    web = WiiSportsResortWeb()

    options_dataclass = WiiSportsResortOptions
    options: WiiSportsResortOptions

    item_name_to_id = item_name_to_id
    location_name_to_id = location_name_to_id
    item_name_groups = item_name_groups
    location_name_groups = location_name_groups

    def __init__(self, multiworld, player):
        super().__init__(multiworld, player)
        self.goal_name: str = data.GOAL_ALL_GAMEMODES
        self.goal_stamp_category_name: str = data.STAMP_CATEGORY_NAMES[0]
        self.active_location_names: set[str] = set()
        self.starting_items: list[str] = []

    # -- Item helpers -------------------------------------------------------

    def create_item(self, name: str) -> WiiSportsResortItem:
        return _create_item(self.player, name)

    def get_filler_item_name(self) -> str:
        return data.FILLER_ITEM

    # -- Generation stages --------------------------------------------------

    def generate_early(self) -> None:
        goal_map = {
            self.options.goal.option_all_gamemodes: data.GOAL_ALL_GAMEMODES,
            self.options.goal.option_all_showdown_stages: data.GOAL_ALL_SHOWDOWN_STAGES,
            self.options.goal.option_all_ipoints: data.GOAL_ALL_IPOINTS,
            self.options.goal.option_stamp_category: data.GOAL_STAMP_CATEGORY,
            self.options.goal.option_all_stamps: data.GOAL_ALL_STAMPS,
        }
        self.goal_name = goal_map[self.options.goal.value]
        self.goal_stamp_category_name = self.options.goal_stamp_category.to_category_name()

        self.active_location_names = set(data.STAMP_LOCATION_NAMES)
        if self.options.include_ipoints:
            self.active_location_names.update(data.IPOINT_LOCATION_NAMES)
        if self.options.include_showdown_clears:
            self.active_location_names.update(data.SHOWDOWN_CLEAR_LOCATION_NAMES)

        starting_gamemode = self.random.choice(data.GAMEMODE_ITEMS)
        self.starting_items = [starting_gamemode]
        sub_unlocks = STARTER_SUBUNLOCKS.get(starting_gamemode)
        if sub_unlocks is not None:
            self.starting_items.append(self.random.choice(sub_unlocks))

    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)
        self.multiworld.regions.append(menu)

        for location_name in data.LOCATION_NAME_TO_ID:
            if location_name not in self.active_location_names:
                continue
            location = WiiSportsResortLocation(
                self.player, location_name,
                data.LOCATION_NAME_TO_ID[location_name], menu,
            )
            menu.locations.append(location)

        victory = WiiSportsResortLocation(
            self.player, data.VICTORY_LOCATION, None, menu
        )
        victory.place_locked_item(
            WiiSportsResortItem(
                data.VICTORY_ITEM, ItemClassification.progression, None, self.player
            )
        )
        menu.locations.append(victory)

    def create_items(self) -> None:
        for name in self.starting_items:
            self.multiworld.push_precollected(self.create_item(name))

        precollected = list(self.starting_items)
        pool: list[WiiSportsResortItem] = []

        for name in data.UNLOCK_ITEM_OFFSETS:
            if name in precollected:
                precollected.remove(name)
                continue
            pool.append(self.create_item(name))

        for _ in range(data.MAX_CYCLING_STAMINA_UPGRADES):
            pool.append(self.create_item(data.PROGRESSIVE_CYCLING_ITEM))
        for _ in range(data.MAX_SHOWDOWN_HEART_UPGRADES):
            pool.append(self.create_item(data.PROGRESSIVE_HEARTS_ITEM))
        for _ in range(data.MAX_CAN_SCORE_UPGRADES):
            pool.append(self.create_item(data.PROGRESSIVE_CAN_SCORE_ITEM))
        pool.append(self.create_item(data.NO_PLANE_CRASH_ITEM))

        total_locations = len(self.active_location_names)
        while len(pool) < total_locations:
            pool.append(self.create_item(data.FILLER_ITEM))
        # If somehow over-full, trim filler first.
        if len(pool) > total_locations:
            pool.sort(key=lambda item: item.classification == ItemClassification.filler)
            pool = pool[:total_locations]

        self.multiworld.itempool += pool
        self._apply_stamp_junk(total_locations)

    def _collect_junk_stamp_names(self) -> set[str]:
        junk: set[str] = set(data.ALWAYS_JUNK_STAMPS)
        if self.options.junk_curated_stamps:
            junk.update(data.CURATED_JUNK_STAMPS)
        for category in self.options.junk_stamp_categories.value:
            junk.update(
                data.stamp_location_name(category, stamp)
                for cat, _base, stamps in data.STAMP_CATEGORIES if cat == category
                for stamp in stamps
            )
        junk.update(self.options.junk_stamps.value)
        return junk & self.active_location_names

    def _apply_stamp_junk(self, total_locations: int) -> None:
        junk_names = self._collect_junk_stamp_names()
        if not junk_names:
            return

        progression_count = sum(
            1 for item in self.multiworld.itempool
            if item.player == self.player
            and item.classification == ItemClassification.progression
        )
        max_excludable = total_locations - progression_count
        if max_excludable <= 0:
            return

        for name in sorted(junk_names)[:max_excludable]:
            location = self.multiworld.get_location(name, self.player)
            location.progress_type = LocationProgressType.EXCLUDED

    def set_rules(self) -> None:
        set_rules(self)

    def fill_slot_data(self) -> dict:
        return {
            "goal": self.goal_name,
            "goal_stamp_category": self.goal_stamp_category_name,
            "include_ipoints": bool(self.options.include_ipoints),
            "include_showdown_clears": bool(self.options.include_showdown_clears),
            "starting_items": self.starting_items,
            "version": 1,
        }
