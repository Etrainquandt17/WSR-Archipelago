"""Location definitions for the Wii Sports Resort Archipelago world."""

from __future__ import annotations

from BaseClasses import Location

from . import data


class WiiSportsResortLocation(Location):
    game = "Wii Sports Resort"


location_name_to_id: dict[str, int] = dict(data.LOCATION_NAME_TO_ID)


location_name_groups: dict[str, set[str]] = {
    "Stamps": set(data.STAMP_LOCATION_NAMES),
    "iPoints": set(data.IPOINT_LOCATION_NAMES),
    "Swordplay Showdown Clears": set(data.SHOWDOWN_CLEAR_LOCATION_NAMES),
}
for _category, _base, _stamps in data.STAMP_CATEGORIES:
    location_name_groups[f"{_category} Stamps"] = {
        data.stamp_location_name(_category, stamp) for stamp in _stamps
    }
