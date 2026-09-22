"""Access rules for the Wii Sports Resort Archipelago world."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from BaseClasses import CollectionState
from worlds.generic.Rules import set_rule

from . import data

if TYPE_CHECKING:
    from . import WiiSportsResortWorld


def _clause_checker(
    clauses: list[tuple[str, list[str]]], player: int
) -> Callable[[CollectionState], bool]:
    def rule(state: CollectionState) -> bool:
        for kind, items in clauses:
            if not items:
                continue
            if kind == "all":
                if not state.has_all(items, player):
                    return False
            elif kind == "any":
                if not state.has_any(items, player):
                    return False
        return True

    return rule


def set_rules(world: "WiiSportsResortWorld") -> None:
    player = world.player
    multiworld = world.multiworld

    for location_name, clauses in data.LOCATION_REQUIREMENTS.items():
        if location_name not in world.active_location_names:
            continue
        location = multiworld.get_location(location_name, player)
        set_rule(location, _clause_checker(clauses, player))

    goal_clauses = data.goal_requirement(
        world.goal_name, world.goal_stamp_category_name
    )
    victory = multiworld.get_location(data.VICTORY_LOCATION, player)
    set_rule(victory, _clause_checker(goal_clauses, player))

    multiworld.completion_condition[player] = (
        lambda state, p=player: state.has(data.VICTORY_ITEM, p)
    )
