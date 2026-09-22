"""Item definitions for the Wii Sports Resort Archipelago world."""

from __future__ import annotations

from BaseClasses import Item, ItemClassification

from . import data


_CLASSIFICATION = {
    "progression": ItemClassification.progression,
    "useful": ItemClassification.useful,
    "filler": ItemClassification.filler,
}


class WiiSportsResortItem(Item):
    game = "Wii Sports Resort"


item_name_to_id: dict[str, int] = dict(data.ITEM_NAME_TO_ID)


def create_item(player: int, name: str) -> WiiSportsResortItem:
    entry = data.ITEM_BY_NAME[name]
    classification = _CLASSIFICATION[entry["classification"]]
    return WiiSportsResortItem(name, classification, entry["id"], player)


# Item groups for universal tracker / plando convenience.
item_name_groups: dict[str, set[str]] = {
    "Gamemodes": set(data.GAMEMODE_ITEMS),
    "Swordplay Showdown Stages": set(data.SHOWDOWN_STAGE_ITEMS),
    "Cycling Stages": set(data.CYCLING_STAGE_ITEMS),
    "Golf Courses": set(data.GOLF_ITEMS),
    "Frisbee Golf Courses": set(data.FRISBEE_GOLF_ITEMS),
    "Power Cruising Courses": set(data.POWER_CRUISING_ITEMS),
    "Archery": set(data.ARCHERY_ITEMS),
    "Wakeboarding": set(data.WAKEBOARDING_ITEMS),
    "Canoeing Speed Challenge": set(data.CANOEING_SPEED_ITEMS),
    "Island Flyover Times": set(data.ISLAND_TIME_ITEMS),
}
