"""Player options for the Wii Sports Resort Archipelago world."""

from __future__ import annotations

from dataclasses import dataclass

from Options import Choice, DefaultOnToggle, OptionSet, PerGameCommonOptions, StartInventoryPool, Toggle

from . import data


class Goal(Choice):
    """Completion condition that releases all of your remaining checks.

    - all_gamemodes: unlock all 17 gamemode variations (default).
    - all_showdown_stages: unlock every Swordplay Showdown stage.
    - all_ipoints: be able to collect every Island Flyover iPoint.
    - stamp_category: earn every stamp in the category chosen by
      goal_stamp_category.
    - all_stamps: be able to earn all 100 stamps.
    """

    display_name = "Goal"
    option_all_gamemodes = 0
    option_all_showdown_stages = 1
    option_all_ipoints = 2
    option_stamp_category = 3
    option_all_stamps = 4
    default = 0


class GoalStampCategory(Choice):
    """Which stamp category to complete when Goal is set to stamp_category."""

    display_name = "Goal Stamp Category"
    option_swordplay_showdown = 0
    option_swordplay_duel = 1
    option_swordplay_speed_slice = 2
    option_power_cruising = 3
    option_archery = 4
    option_frisbee_dog = 5
    option_basketball_3_point_contest = 6
    option_basketball_pickup_game = 7
    option_bowling_standard_game = 8
    option_bowling_100_pin_game = 9
    option_bowling_spin_control = 10
    option_canoeing_speed_challenge = 11
    option_table_tennis_return_challenge = 12
    option_table_tennis_match = 13
    option_wakeboarding = 14
    option_island_flyover = 15
    option_golf = 16
    option_frisbee_golf = 17
    option_cycling_road_race = 18
    option_skydiving = 19
    default = 0

    def to_category_name(self) -> str:
        return data.STAMP_CATEGORY_NAMES[self.value]


class IncludeShowdownClears(DefaultOnToggle):
    """Include the 20 'clear a Swordplay Showdown stage' checks in the pool.

    When disabled, clearing stages does nothing and those 20 locations are
    removed.
    """

    display_name = "Include Swordplay Showdown Clears"


class IncludeIpoints(DefaultOnToggle):
    """Include the 80 Island Flyover iPoint checks in the pool.

    When disabled, collecting iPoints does nothing and those 80 locations are
    removed.
    """

    display_name = "Include Island Flyover iPoints"


class JunkCuratedStamps(Toggle):
    """Force a curated set of grindy stamps to only hold junk.

    These stamps remain checks but never contain progression or useful items,
    keeping them out of the critical path for a faster async.
    """

    display_name = "Junk Curated Stamps"


class JunkStampCategories(OptionSet):
    """Force every stamp in the listed categories to only hold junk.

    Entries are stamp category names, e.g. ``Bowling Spin Control`` or
    ``Cycling Road Race``. Those stamps stay as checks but never hold
    progression or useful items.
    """

    display_name = "Junk Stamp Categories"
    valid_keys = frozenset(data.STAMP_CATEGORY_NAMES)


class JunkStamps(OptionSet):
    """Force specific individual stamps to only hold junk.

    Entries are full stamp names in the form ``<Category> - <Stamp>``, e.g.
    ``Golf - Hole in One``. (The generic ``exclude_locations`` option works
    too; this is a convenience with validated names.)
    """

    display_name = "Junk Stamps"
    valid_keys = frozenset(data.STAMP_LOCATION_NAMES)


@dataclass
class WiiSportsResortOptions(PerGameCommonOptions):
    goal: Goal
    goal_stamp_category: GoalStampCategory
    include_showdown_clears: IncludeShowdownClears
    include_ipoints: IncludeIpoints
    junk_curated_stamps: JunkCuratedStamps
    junk_stamp_categories: JunkStampCategories
    junk_stamps: JunkStamps
    start_inventory_from_pool: StartInventoryPool
