"""Wii Sports Resort (RZTE01) Archipelago Dolphin bridge client.

This connects a running Dolphin instance (with Wii Sports Resort loaded) to an
Archipelago server. It:

  * receives items and applies them to the save buffer / live memory,
  * scans the save buffer for badge (stamp) and iPoint completion,
  * detects Swordplay Showdown stage clears live,
  * reports the configured goal when it is met.

It reuses the canonical ``apworld/data.py`` module (loaded directly, without
Archipelago installed) so item/location IDs always match the generated world.

Run:
    python pc-client/dolphin_bridge.py --server localhost:38281 --name YourSlot

Dependencies: see pc-client/requirements.txt (dolphin-memory-engine, websockets).
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import ssl
import struct
import sys
import time
import uuid
from collections import Counter
from pathlib import Path

import dolphin_memory_engine as dme
import websockets

import showdown_client


# --- Load the shared data module without importing the AP package -----------
def _load_data():
    if getattr(sys, "frozen", False):
        data_path = Path(sys._MEIPASS) / "apworld" / "data.py"
    else:
        data_path = Path(__file__).resolve().parent.parent / "apworld" / "data.py"
    spec = importlib.util.spec_from_file_location("wsr_data", data_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


data = _load_data()


# --- Fixed RZTE01 addresses -------------------------------------------------
GAME_ID = b"RZTE01"
GAME_ID_ADDRESS = 0x80000000

SAVE_OBJECT_GLOBAL = 0x806F4CC0
SAVE_DESCRIPTOR_OFFSET = 0x28
SAVE_BUFFER_OFFSET = 0x08
SAVE_MAGIC = b"WSP2"

BOOT_GRACE_SECONDS = 10.0
POLL_INTERVAL_SECONDS = 0.2

CLIENT_STATUS_GOAL = 30
AP_VERSION = {"major": 0, "minor": 5, "build": 0, "class": "Version"}
ITEMS_HANDLING_ALL_REMOTE = 0b111


class DolphinUnavailableError(RuntimeError):
    """Dolphin is closed, hook is stale, or the wrong game is running."""


# ---------------------------------------------------------------------------
# Memory interface
# ---------------------------------------------------------------------------
class MemoryInterface:
    """All Dolphin memory access, with stale-hook self-healing."""

    def __init__(self) -> None:
        self._game_id_verified_at: float | None = None

    # -- hook management ----------------------------------------------------

    def ensure_hooked(self) -> bool:
        if dme.is_hooked():
            return True
        try:
            dme.hook()
        except RuntimeError:
            return False
        return dme.is_hooked()

    def _invalidate(self) -> None:
        try:
            dme.un_hook()
        except RuntimeError:
            pass
        self._game_id_verified_at = None

    # -- primitive reads/writes --------------------------------------------

    def read_bytes(self, address: int, size: int) -> bytes:
        try:
            return dme.read_bytes(address, size)
        except RuntimeError as error:
            self._invalidate()
            raise DolphinUnavailableError(f"stale hook: {error}") from error

    def write_byte(self, address: int, value: int) -> None:
        try:
            dme.write_byte(address, value & 0xFF)
        except RuntimeError as error:
            self._invalidate()
            raise DolphinUnavailableError(f"stale hook: {error}") from error

    def write_bytes(self, address: int, data_bytes: bytes) -> None:
        try:
            dme.write_bytes(address, data_bytes)
        except RuntimeError as error:
            self._invalidate()
            raise DolphinUnavailableError(f"stale hook: {error}") from error

    def read_u8(self, address: int) -> int:
        return self.read_bytes(address, 1)[0]

    def read_u32_be(self, address: int) -> int:
        return struct.unpack(">I", self.read_bytes(address, 4))[0]

    def read_float(self, address: int) -> float:
        try:
            return dme.read_float(address)
        except RuntimeError as error:
            self._invalidate()
            raise DolphinUnavailableError(f"stale hook: {error}") from error

    def write_float(self, address: int, value: float) -> None:
        try:
            dme.write_float(address, value)
        except RuntimeError as error:
            self._invalidate()
            raise DolphinUnavailableError(f"stale hook: {error}") from error

    # -- validation ---------------------------------------------------------

    @staticmethod
    def is_valid_pointer(address: int) -> bool:
        return 0x80000000 <= address < 0x81800000 or 0x90000000 <= address < 0x94000000

    def game_is_ready(self) -> bool:
        """True only once RZTE01 is loaded and the boot grace has elapsed."""
        if self.read_bytes(GAME_ID_ADDRESS, len(GAME_ID)) != GAME_ID:
            self._game_id_verified_at = None
            return False
        now = time.monotonic()
        if self._game_id_verified_at is None:
            self._game_id_verified_at = now
            return False
        return (now - self._game_id_verified_at) >= BOOT_GRACE_SECONDS

    def resolve_save_buffer(self) -> int | None:
        owner = self.read_u32_be(SAVE_OBJECT_GLOBAL)
        if not self.is_valid_pointer(owner):
            return None
        descriptor = self.read_u32_be(owner + SAVE_DESCRIPTOR_OFFSET)
        if not self.is_valid_pointer(descriptor):
            return None
        save_buffer = self.read_u32_be(descriptor + SAVE_BUFFER_OFFSET)
        if not self.is_valid_pointer(save_buffer):
            return None
        if self.read_bytes(save_buffer, len(SAVE_MAGIC)) != SAVE_MAGIC:
            return None
        return save_buffer


class _ShowdownAdapter:
    """Adapts MemoryInterface to the showdown_client MemoryAdapter protocol."""

    def __init__(self, memory: MemoryInterface) -> None:
        self._memory = memory

    def read_bytes(self, address: int, size: int) -> bytes:
        return self._memory.read_bytes(address, size)


# ---------------------------------------------------------------------------
# Item application
# ---------------------------------------------------------------------------
class GameStateApplier:
    """Applies received AP items into game memory (async-safe)."""

    def __init__(self, memory: MemoryInterface) -> None:
        self._memory = memory

    def apply(self, save_buffer: int, received_counts: Counter) -> None:
        self._enforce_locked_modes(save_buffer)
        self._apply_unlocks(save_buffer, received_counts)
        self._apply_cycling(received_counts)
        self._apply_hearts(received_counts)
        self._apply_can_score(received_counts)
        self._apply_no_plane_crash(received_counts)

    def _enforce_locked_modes(self, save_buffer: int) -> None:
        for _name, offset in data.ALWAYS_LOCKED_GAMEMODES:
            if self._memory.read_u8(save_buffer + offset) != data.UNLOCK_LOCKED:
                self._memory.write_byte(save_buffer + offset, data.UNLOCK_LOCKED)

    def _apply_unlocks(self, save_buffer: int, received_counts: Counter) -> None:
        for name, offset in data.UNLOCK_ITEM_OFFSETS.items():
            current = self._memory.read_u8(save_buffer + offset)
            if received_counts.get(name, 0) > 0:
                # Only write when currently Locked, so we never override the
                # game's 0x01 -> 0x00 transition once the player has viewed it.
                if current == data.UNLOCK_LOCKED:
                    self._memory.write_byte(save_buffer + offset, data.UNLOCK_NEW)
            else:
                # Not received yet: continuously force Locked so the game's own
                # vanilla auto-unlock behavior (e.g. clearing a Showdown stage
                # normally unlocks the next one) never grants early access.
                if current != data.UNLOCK_LOCKED:
                    self._memory.write_byte(save_buffer + offset, data.UNLOCK_LOCKED)

    def _apply_cycling(self, received_counts: Counter) -> None:
        count = min(received_counts.get(data.PROGRESSIVE_CYCLING_ITEM, 0),
                    data.MAX_CYCLING_STAMINA_UPGRADES)
        step = data.CYCLING_DRAIN_DEFAULT / data.MAX_CYCLING_STAMINA_UPGRADES
        target = data.CYCLING_DRAIN_DEFAULT - count * step
        current = self._memory.read_float(data.CYCLING_DRAIN_ADDRESS)
        if not _is_finite(current):
            return
        # Only patch recognised drain values to avoid stomping unrelated memory.
        if not _is_known_cycling_value(current):
            return
        if abs(current - target) > 0.001:
            self._memory.write_float(data.CYCLING_DRAIN_ADDRESS, target)

    def _apply_hearts(self, received_counts: Counter) -> None:
        count = min(received_counts.get(data.PROGRESSIVE_HEARTS_ITEM, 0),
                    data.MAX_SHOWDOWN_HEART_UPGRADES)
        if self._memory.read_u8(data.SHOWDOWN_HEART_MAILBOX_ADDRESS) != count:
            self._memory.write_byte(data.SHOWDOWN_HEART_MAILBOX_ADDRESS, count)

    def _apply_can_score(self, received_counts: Counter) -> None:
        count = min(received_counts.get(data.PROGRESSIVE_CAN_SCORE_ITEM, 0),
                    data.MAX_CAN_SCORE_UPGRADES)
        value = data.BASE_CAN_SCORE + count * data.SCORE_PER_CAN_SCORE_UPGRADE
        if self._memory.read_u32_be(data.CAN_SCORE_ADDRESS) != value:
            self._memory.write_bytes(data.CAN_SCORE_ADDRESS, value.to_bytes(4, "big"))

    def _apply_no_plane_crash(self, received_counts: Counter) -> None:
        if received_counts.get(data.NO_PLANE_CRASH_ITEM, 0) <= 0:
            return
        if self._memory.read_u8(data.NO_PLANE_CRASH_MAILBOX_ADDRESS) != 1:
            self._memory.write_byte(data.NO_PLANE_CRASH_MAILBOX_ADDRESS, 1)


def _is_finite(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))


def _safe_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_known_cycling_value(value: float) -> bool:
    step = data.CYCLING_DRAIN_DEFAULT / data.MAX_CYCLING_STAMINA_UPGRADES
    for count in range(data.MAX_CYCLING_STAMINA_UPGRADES + 1):
        if abs(value - (data.CYCLING_DRAIN_DEFAULT - count * step)) <= 0.001:
            return True
    return False


# ---------------------------------------------------------------------------
# Location scanning
# ---------------------------------------------------------------------------
class LocationScanner:
    """Reads the save buffer and live memory to find newly checked locations."""

    def __init__(self, memory: MemoryInterface, active_names: set[str]) -> None:
        self._memory = memory
        self._active = active_names
        self._showdown_detector = showdown_client.CompletionDetector()
        self._showdown_adapter = _ShowdownAdapter(memory)

    def scan_save(self, save_buffer: int) -> set[int]:
        found: set[int] = set()
        for entry in data.LOCATION_TABLE:
            name = entry["name"]
            if name not in self._active:
                continue
            detect = entry["detect"]
            if detect == "word_nonzero":
                if self._memory.read_u32_be(save_buffer + entry["offset"]) != 0:
                    found.add(entry["id"])
            elif detect == "byte_not_ff":
                if self._memory.read_u8(save_buffer + entry["offset"]) != 0xFF:
                    found.add(entry["id"])
        return found

    def scan_showdown(self) -> set[int]:
        found: set[int] = set()
        try:
            snapshot = showdown_client.read_snapshot_consistent(self._showdown_adapter)
        except (DolphinUnavailableError, ValueError):
            return found
        message = self._showdown_detector.observe(*snapshot)
        if message is None:
            return found
        _progress, stage_index, _total, _defeated = snapshot
        name = data.SHOWDOWN_CLEARS[stage_index][0]
        location_id = data.LOCATION_NAME_TO_ID.get(name)
        if location_id is not None and name in self._active:
            found.add(location_id)
        return found

    def reset_showdown(self) -> None:
        self._showdown_detector.reset()


# ---------------------------------------------------------------------------
# Goal evaluation
# ---------------------------------------------------------------------------
def goal_is_met(goal: str, stamp_category: str, memory: MemoryInterface,
                save_buffer: int, checked_ids: set[int]) -> bool:
    if goal == data.GOAL_ALL_GAMEMODES:
        return all(
            memory.read_u8(save_buffer + offset) != data.UNLOCK_LOCKED
            for _name, offset in data.GAMEMODES
        )
    if goal == data.GOAL_ALL_SHOWDOWN_STAGES:
        return _all_checked(data.SHOWDOWN_CLEAR_LOCATION_NAMES, checked_ids)
    if goal == data.GOAL_ALL_IPOINTS:
        return _all_checked(data.IPOINT_LOCATION_NAMES, checked_ids)
    if goal == data.GOAL_ALL_STAMPS:
        return _all_checked(data.STAMP_LOCATION_NAMES, checked_ids)
    if goal == data.GOAL_STAMP_CATEGORY:
        names = [
            data.stamp_location_name(cat, stamp)
            for cat, _base, stamps in data.STAMP_CATEGORIES if cat == stamp_category
            for stamp in stamps
        ]
        return _all_checked(names, checked_ids)
    return False


def _all_checked(location_names: list[str], checked_ids: set[int]) -> bool:
    return all(
        data.LOCATION_NAME_TO_ID[name] in checked_ids for name in location_names
    )


# ---------------------------------------------------------------------------
# Archipelago client
# ---------------------------------------------------------------------------
class ArchipelagoBridge:
    def __init__(self, server: str, slot_name: str, password: str | None) -> None:
        self.server = server
        self.slot_name = slot_name
        self.password = password

        self.memory = MemoryInterface()
        self.applier = GameStateApplier(self.memory)

        self.slot_data: dict = {}
        self.active_location_names: set[str] = set()
        self.scanner: LocationScanner | None = None
        self.player_names: dict[int, str] = {}

        self.received_counts: Counter = Counter()
        self.checked_locations: set[int] = set()
        self.sent_locations: set[int] = set()
        self.goal_reported = False
        self._ws = None
        self._last_status = 0.0

    async def run(self) -> None:
        self._ws = await self._connect()
        try:
            await asyncio.gather(self._network_loop(), self._memory_loop())
        finally:
            await self._ws.close()

    # -- connection ---------------------------------------------------------

    _UNROUTABLE_HOSTS = {"0.0.0.0", "::", "[::]", "0000:0000:0000:0000:0000:0000:0000:0000"}

    @staticmethod
    def _extract_host(address: str) -> str:
        without_scheme = address.split("://", 1)[-1]
        host = without_scheme.rsplit(":", 1)[0] if ":" in without_scheme else without_scheme
        return host.strip("[]")

    async def _connect(self):
        address = self.server
        host = self._extract_host(address)
        if host in self._UNROUTABLE_HOSTS:
            raise ConnectionError(
                f"'{host}' is a bind address, not something a client can connect to. "
                "Use '127.0.0.1' if the server is on this machine, your LAN IP if it's "
                "on your network, or the address the server printed on startup "
                "(e.g. \"Hosting game at 1.2.3.4:38281\")."
            )

        if address.startswith(("ws://", "wss://")):
            candidates = [address]
        else:
            candidates = [f"wss://{address}", f"ws://{address}"]

        last_error: Exception | None = None
        for uri in candidates:
            ssl_context = None
            if uri.startswith("wss://"):
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            try:
                connection = await websockets.connect(
                    uri, ssl=ssl_context, max_size=None, ping_interval=None
                )
                print(f"[NET] Connected to {uri}")
                return connection
            except Exception as error:  # noqa: BLE001 - try next transport
                last_error = error
        raise ConnectionError(f"Could not connect to {self.server}: {last_error}")

    async def _send(self, payload: list[dict]) -> None:
        await self._ws.send(json.dumps(payload))

    # -- network ------------------------------------------------------------

    async def _network_loop(self) -> None:
        async for raw in self._ws:
            for message in json.loads(raw):
                await self._handle_message(message)

    async def _handle_message(self, message: dict) -> None:
        cmd = message.get("cmd")
        if cmd == "RoomInfo":
            await self._send_connect()
        elif cmd == "Connected":
            self._on_connected(message)
        elif cmd == "ConnectionRefused":
            errors = ", ".join(message.get("errors", []))
            raise ConnectionError(f"Connection refused: {errors}")
        elif cmd == "ReceivedItems":
            self._on_received_items(message)
        elif cmd == "RoomUpdate":
            for location_id in message.get("checked_locations", []):
                self.checked_locations.add(location_id)
        elif cmd == "PrintJSON":
            self._print_json(message)

    async def _send_connect(self) -> None:
        await self._send([{
            "cmd": "Connect",
            "password": self.password,
            "game": "Wii Sports Resort",
            "name": self.slot_name,
            "uuid": uuid.getnode(),
            "version": AP_VERSION,
            "items_handling": ITEMS_HANDLING_ALL_REMOTE,
            "tags": [],
            "slot_data": True,
        }])

    def _on_connected(self, message: dict) -> None:
        self.slot_data = message.get("slot_data", {}) or {}
        self.player_names = self._read_player_names(message.get("slot_info", {}))
        self.checked_locations.update(message.get("checked_locations", []))
        self.active_location_names = self._resolve_active_locations()
        self.scanner = LocationScanner(self.memory, self.active_location_names)
        goal = self.slot_data.get("goal", data.GOAL_ALL_GAMEMODES)
        print(f"[NET] Connected as {self.slot_name}. Goal: {goal}. "
              f"{len(self.active_location_names)} active checks.")

    @staticmethod
    def _read_player_names(slot_info: dict) -> dict[int, str]:
        names: dict[int, str] = {}
        for slot_id, slot in slot_info.items():
            player_id = _safe_int(slot_id)
            if player_id is None:
                continue
            name = slot.get("name") if isinstance(slot, dict) else getattr(slot, "name", None)
            if name:
                names[player_id] = name
        return names

    def _resolve_active_locations(self) -> set[str]:
        names = set(data.STAMP_LOCATION_NAMES)
        if self.slot_data.get("include_ipoints", True):
            names.update(data.IPOINT_LOCATION_NAMES)
        if self.slot_data.get("include_showdown_clears", True):
            names.update(data.SHOWDOWN_CLEAR_LOCATION_NAMES)
        return names

    def _on_received_items(self, message: dict) -> None:
        items = message.get("items", [])
        if message.get("index", 0) == 0:
            self.received_counts = Counter()
        for entry in items:
            name = data.ITEM_ID_TO_NAME.get(entry.get("item"))
            if name is not None:
                self.received_counts[name] += 1

    def _print_json(self, message: dict) -> None:
        text = "".join(self._format_print_json_part(part) for part in message.get("data", []))
        if text.strip():
            print(f"[AP] {text}")

    def _format_print_json_part(self, part: dict) -> str:
        text = part.get("text", "")
        part_type = part.get("type")
        if part_type == "item_id":
            return data.ITEM_ID_TO_NAME.get(_safe_int(text), text)
        if part_type == "location_id":
            return data.LOCATION_ID_TO_NAME.get(_safe_int(text), text)
        if part_type in {"player_id", "player_name"}:
            return self.player_names.get(_safe_int(text), text)
        return text

    # -- memory loop --------------------------------------------------------

    async def _memory_loop(self) -> None:
        while True:
            try:
                await self._memory_tick()
            except DolphinUnavailableError as error:
                self._throttled_status(f"waiting for Dolphin: {error}")
                if self.scanner is not None:
                    self.scanner.reset_showdown()
            except Exception as error:  # noqa: BLE001 - keep the loop alive
                self._throttled_status(f"memory loop error: {error}")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    async def _memory_tick(self) -> None:
        if self.scanner is None:
            return
        if not self.memory.ensure_hooked():
            self._throttled_status("Dolphin not running")
            return
        if not self.memory.game_is_ready():
            self._throttled_status("waiting for RZTE01 save to load")
            return
        save_buffer = self.memory.resolve_save_buffer()
        if save_buffer is None:
            self._throttled_status("save buffer not ready")
            return

        self.applier.apply(save_buffer, self.received_counts)

        found = self.scanner.scan_save(save_buffer)
        found |= self.scanner.scan_showdown()
        await self._report_locations(found)

        await self._maybe_report_goal(save_buffer)

    async def _report_locations(self, found: set[int]) -> None:
        self.checked_locations |= found
        pending = {
            loc for loc in (self.checked_locations - self.sent_locations)
            if loc in data.LOCATION_ID_TO_NAME
        }
        if not pending:
            return
        await self._send([{"cmd": "LocationChecks", "locations": sorted(pending)}])
        for loc in sorted(pending):
            print(f"[CHECK] {data.LOCATION_ID_TO_NAME[loc]}")
        self.sent_locations |= pending

    async def _maybe_report_goal(self, save_buffer: int) -> None:
        if self.goal_reported:
            return
        goal = self.slot_data.get("goal", data.GOAL_ALL_GAMEMODES)
        category = self.slot_data.get("goal_stamp_category", data.STAMP_CATEGORY_NAMES[0])
        if goal_is_met(goal, category, self.memory, save_buffer, self.checked_locations):
            await self._send([{"cmd": "StatusUpdate", "status": CLIENT_STATUS_GOAL}])
            self.goal_reported = True
            print("[GOAL] Goal complete! Reported to server.")

    def _throttled_status(self, text: str) -> None:
        now = time.monotonic()
        if now - self._last_status >= 5.0:
            print(f"[INFO] {text}")
            self._last_status = now


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wii Sports Resort AP Dolphin bridge")
    parser.add_argument("--server",
                        help="Archipelago server, e.g. localhost:38281 or archipelago.gg:12345")
    parser.add_argument("--name", help="Your slot name")
    parser.add_argument("--password", default=None, help="Server password, if any")
    return parser.parse_args()


def prompt_connection_details() -> tuple[str, str, str | None] | None:
    from tkinter import Tk, simpledialog

    root = Tk()
    root.withdraw()
    root.update()
    server = simpledialog.askstring("WSR Dolphin Bridge", "Server address and port:", parent=root)
    if not server:
        return None
    name = simpledialog.askstring("WSR Dolphin Bridge", "Archipelago slot name:", parent=root)
    if not name:
        return None
    password = simpledialog.askstring(
        "WSR Dolphin Bridge", "Password (leave blank if none):", parent=root, show="*"
    )
    return server.strip(), name.strip(), password or None


def main() -> None:
    args = parse_args()
    if not args.server or not args.name:
        details = prompt_connection_details()
        if details is None:
            return
        server, name, password = details
    else:
        server, name, password = args.server, args.name, args.password
    bridge = ArchipelagoBridge(server, name, password)
    try:
        asyncio.run(bridge.run())
    except KeyboardInterrupt:
        print("\nStopped.")
    except ConnectionError as error:
        print(f"[NET] {error}")


if __name__ == "__main__":
    main()
