"""
Live Dolphin test client for the Cycling Stamina Upgrade progression item.

This hooks to a running Dolphin instance and continuously enforces the real
Wii Sports Resort Cycling stamina-drain coefficient:

    0x806FC820: float, default 20.0 / 0x41A00000

Every received Cycling Stamina Upgrade reduces stamina drain by 10%.

    0 upgrades  -> 20.0 -> 100% drain
    1 upgrade   -> 18.0 ->  90% drain
    ...
    9 upgrades  ->  2.0 ->  10% drain
    10 upgrades ->  0.0 ->   0% drain

This version runs a background enforcement loop so the patch survives:
  - Dolphin being closed and reopened
  - the game being reset or rebooted
  - loading a different profile/save
  - Dolphin momentarily losing/regaining the memory hook

Run:
    python pc-client/simulate_cycling_stamina.py

Type "set N" or "+"/"-" to simulate the AP-received item count while the
background loop keeps applying it, even across game restarts.
"""

from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass

import dolphin_memory_engine as dme


# RZTE01 Wii Sports Resort Cycling drain coefficient.
# Verified from:
#   lfs f0, -0x1860(r2) at 0x803AF6D0
#   lfs f1, -0x1860(r2) at 0x803AF6F0
CYCLING_DRAIN_ADDRESS = 0x806FC820

DEFAULT_DRAIN_VALUE = 20.0
MAX_UPGRADES = 10
DRAIN_REDUCTION_PER_UPGRADE = DEFAULT_DRAIN_VALUE / MAX_UPGRADES  # 2.0

# How often the background thread checks/reapplies the value.
# This does not need to be 60 Hz; the value only needs to be corrected
# before the player notices a restored default, so a few times per second
# is enough and keeps CPU/dme traffic low.
ENFORCEMENT_INTERVAL_SECONDS = 0.5


class DolphinNotReadyError(RuntimeError):
    """Raised when Dolphin or the intended game memory is not available."""


def drain_value_for_upgrades(upgrade_count: int) -> float:
    """Return the in-game drain coefficient for 0-10 received upgrades."""
    clamped_count = max(0, min(upgrade_count, MAX_UPGRADES))
    return DEFAULT_DRAIN_VALUE - (
        clamped_count * DRAIN_REDUCTION_PER_UPGRADE
    )


def is_a_known_drain_value(value: float) -> bool:
    """
    True if value matches the vanilla default or any of this project's
    10%-increment values. Used to avoid patching unrelated/garbage memory.
    """
    valid_values = (
        drain_value_for_upgrades(count)
        for count in range(MAX_UPGRADES + 1)
    )
    return any(math.isclose(value, valid, abs_tol=0.001) for valid in valid_values)


def try_hook_dolphin() -> bool:
    """Attempt to hook Dolphin. Returns whether hooking is currently active."""
    if not dme.is_hooked():
        try:
            dme.hook()
        except RuntimeError:
            return False

    return dme.is_hooked()


def read_live_drain_value() -> float:
    """Read the actual big-endian float from emulated Wii memory."""
    if not dme.is_hooked():
        raise DolphinNotReadyError("Dolphin is not currently hooked.")

    try:
        value = dme.read_float(CYCLING_DRAIN_ADDRESS)
    except RuntimeError as error:
        # is_hooked() can still report True after Dolphin closes/restarts;
        # force a fresh hook attempt on the next cycle.
        dme.un_hook()
        raise DolphinNotReadyError(f"Dolphin hook is stale: {error}") from error

    if not math.isfinite(value):
        raise DolphinNotReadyError(
            f"Unexpected non-finite value at 0x{CYCLING_DRAIN_ADDRESS:08X}: "
            f"{value!r}"
        )

    return value


def write_live_drain_value(value: float) -> None:
    """Write the actual Cycling drain coefficient to Dolphin memory."""
    if not dme.is_hooked():
        raise DolphinNotReadyError("Dolphin is not currently hooked.")

    if not math.isfinite(value) or not 0.0 <= value <= DEFAULT_DRAIN_VALUE:
        raise ValueError(f"Refusing invalid Cycling drain value: {value}")

    try:
        dme.write_float(CYCLING_DRAIN_ADDRESS, value)
    except RuntimeError as error:
        dme.un_hook()
        raise DolphinNotReadyError(f"Dolphin hook is stale: {error}") from error


@dataclass
class CyclingStaminaUpgradeController:
    """
    Tracks the AP-received item count and continuously enforces the
    corresponding in-game drain coefficient.

    In the real AP client, call set_received_count() whenever the local
    ReceivedItems cache changes. A background thread re-applies the value
    on an interval so it survives game/emulator restarts without needing
    the AP client to notice the restart itself.
    """

    received_count: int = 0

    _enforcement_thread: threading.Thread | None = None
    _stop_event: threading.Event | None = None
    _lock: threading.Lock = None  # type: ignore[assignment]
    _last_status: str = "not started"

    def __post_init__(self) -> None:
        self._lock = threading.Lock()

    # -- Public control -----------------------------------------------

    def start(self) -> None:
        """Start the background enforcement loop. Safe to call once."""
        if self._enforcement_thread is not None:
            return

        self._stop_event = threading.Event()
        self._enforcement_thread = threading.Thread(
            target=self._enforcement_loop,
            name="cycling-stamina-enforcer",
            daemon=True,
        )
        self._enforcement_thread.start()

    def stop(self) -> None:
        """Stop the background loop, e.g. on client shutdown."""
        if self._stop_event is not None:
            self._stop_event.set()

        if self._enforcement_thread is not None:
            self._enforcement_thread.join(timeout=2.0)

        self._enforcement_thread = None
        self._stop_event = None

    def set_received_count(self, count: int) -> None:
        """Set the number of received AP progression items."""
        with self._lock:
            self.received_count = max(0, min(count, MAX_UPGRADES))

    def receive_item(self) -> None:
        """Simulate receiving one Cycling Stamina Upgrade from Archipelago."""
        with self._lock:
            self.set_received_count(self.received_count + 1)

    def remove_item(self) -> None:
        """Testing helper: remove one simulated upgrade."""
        with self._lock:
            self.set_received_count(self.received_count - 1)

    def status_text(self) -> str:
        """Human-readable snapshot combining desired state and live memory."""
        with self._lock:
            target_count = self.received_count
            last_status = self._last_status

        hooked = dme.is_hooked()
        live_text = "unavailable"

        if hooked:
            try:
                live_value = read_live_drain_value()
                percent = live_value / DEFAULT_DRAIN_VALUE * 100.0
                live_text = f"{live_value:.1f}  ({percent:.0f}% of normal)"
            except (DolphinNotReadyError, RuntimeError):
                live_text = "unreadable"

        return (
            f"Hooked to Dolphin : {hooked}\n"
            f"Target upgrades   : {target_count}/{MAX_UPGRADES}\n"
            f"Live drain value  : {live_text}\n"
            f"Enforcement status: {last_status}\n"
            f"Target address    : 0x{CYCLING_DRAIN_ADDRESS:08X}\n"
        )

    # -- Background enforcement ----------------------------------------

    def _enforcement_loop(self) -> None:
        """
        Runs continuously in the background so that:
          - closing/reopening Dolphin
          - resetting or reloading the game
          - Dolphin briefly losing the memory hook
        all self-heal without any manual intervention.
        """
        assert self._stop_event is not None

        while not self._stop_event.is_set():
            try:
                self._enforce_once()
            except DolphinNotReadyError as error:
                self._set_status(f"waiting: {error}")
            except RuntimeError as error:
                self._set_status(f"dolphin error: {error}")

            self._stop_event.wait(ENFORCEMENT_INTERVAL_SECONDS)

    def _enforce_once(self) -> None:
        if not try_hook_dolphin():
            self._set_status("Dolphin not found; retrying")
            return

        with self._lock:
            target_count = self.received_count

        target_value = drain_value_for_upgrades(target_count)

        try:
            current_value = read_live_drain_value()
        except DolphinNotReadyError:
            # Hooked, but the game/memory isn't ready yet (e.g. between
            # boot and the save/profile finishing initialization).
            self._set_status("hooked, game memory not ready yet")
            return

        if math.isclose(current_value, target_value, abs_tol=0.001):
            self._set_status(f"in sync at {target_value:.1f}")
            return

        if not is_a_known_drain_value(current_value):
            # Something else is at this address right now (different
            # game/revision loaded, or memory not initialized). Do not
            # stomp on it; wait for a recognizable value to appear.
            self._set_status(
                f"unexpected value {current_value:.6g}; not patching"
            )
            return

        # This is the key behavior for async play: whenever the game
        # (re)boots, the game code resets this address back to the
        # vanilla 20.0 default. This loop notices the mismatch and
        # reapplies the player's current upgrade count automatically,
        # without needing an explicit "the game restarted" signal.
        write_live_drain_value(target_value)
        self._set_status(f"reapplied {target_value:.1f} after mismatch")

    def _set_status(self, status: str) -> None:
        with self._lock:
            self._last_status = status


def print_help() -> None:
    print(
        """
Commands:
  +             Simulate receiving one Cycling Stamina Upgrade.
  -             Remove one simulated upgrade.
  set N         Set the simulated received count to N, from 0 through 10.
  status        Show the target count and the live in-game value.
  help          Show this help.
  quit          Stop the background loop and exit.

The background loop keeps running the whole time this program is open. It
will automatically re-detect Dolphin and reapply your current upgrade count
whenever the game restarts, Dolphin restarts, or the hook drops.
""".strip()
    )


def main() -> None:
    controller = CyclingStaminaUpgradeController()
    controller.start()

    print("Wii Sports Resort — Cycling Stamina Upgrade Live Test")
    print(f"Target coefficient: 0x{CYCLING_DRAIN_ADDRESS:08X}")
    print("Background enforcement loop is running.")
    print_help()

    try:
        while True:
            try:
                command = input("\ncycling> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                break

            if command in {"q", "quit", "exit"}:
                break

            elif command in {"help", "h", "?"}:
                print_help()

            elif command == "+":
                controller.receive_item()
                print(controller.status_text())

            elif command == "-":
                controller.remove_item()
                print(controller.status_text())

            elif command.startswith("set "):
                try:
                    _, raw_count = command.split(maxsplit=1)
                    controller.set_received_count(int(raw_count))
                except ValueError:
                    print("Use: set N, where N is an integer from 0 through 10.")
                    continue
                print(controller.status_text())

            elif command == "status":
                print(controller.status_text())

            elif command == "":
                continue

            else:
                print("Unknown command. Type 'help' for available commands.")
    finally:
        print("\nStopping background enforcement loop...")
        controller.stop()


if __name__ == "__main__":
    main()