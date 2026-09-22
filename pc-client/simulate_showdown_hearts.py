"""
Live test client for Progressive Swordplay Showdown Hearts.

The client automatically:

1. Installs an enabled Gecko hook into:
       <Dolphin User>/GameSettings/RZTE01.ini

2. Launches Dolphin with cheats enabled.

3. Continuously writes the simulated Archipelago item count, 0-7, to:
    0x817FFFF0

The Gecko hook reads that count whenever a Showdown player object is
initialized and sets:

    starting_hearts = 3 + received_upgrade_count

This hook is specific to Wii Sports Resort NTSC-U, game ID RZTE01.
"""

from __future__ import annotations

import argparse
import subprocess
import threading
from pathlib import Path

import dolphin_memory_engine as dme


GAME_ID = b"RZTE01"
GAME_ID_ADDRESS = 0x80000000

# AP-controlled mailbox consumed by the Gecko hook.
SHOWDOWN_HEART_UPGRADE_ADDRESS = 0x817FFFF0

MAX_SHOWDOWN_HEART_UPGRADES = 7
BASE_SHOWDOWN_HEARTS = 3

ENFORCEMENT_INTERVAL_SECONDS = 0.25

GECKO_NAME = "Archipelago - Progressive Showdown Hearts"

# The generated Gecko hook must load the mailbox from 0x817FFFF0.
# The logic is the same:
#
#   u8 upgrades = *(u8*)0x817FFFF0;
#   if (upgrades > 7) upgrades = 7;
#   starting_hearts = 3 + upgrades;
#
# We still install the block in RZTE01.ini and enable it on launch.
GECKO_CODE_LINES = (
    "C2639FA0 00000004",
    "3D808180 888CFFF0",
    "28040007 40810008",
    "38800000 38840003",
    "60000000 00000000",
)

GECKO_BLOCK_MARKER = "WSR-ARCHIPELAGO-SHOWDOWN-HEARTS"
ENABLED_BLOCK_MARKER = "WSR-ARCHIPELAGO-SHOWDOWN-HEARTS-ENABLED"


class DolphinUnavailableError(RuntimeError):
    """Dolphin is unavailable, stale, or running the wrong game."""


def remove_managed_block(text: str, marker: str) -> str:
    """Remove one block previously managed by this script."""
    begin = f"# BEGIN {marker}"
    end = f"# END {marker}"

    output: list[str] = []
    inside_block = False

    for line in text.splitlines():
        if line.strip() == begin:
            inside_block = True
            continue

        if line.strip() == end:
            inside_block = False
            continue

        if not inside_block:
            output.append(line)

    return "\n".join(output).rstrip()


def insert_section_block(
    text: str,
    section_name: str,
    marker: str,
    block_lines: list[str],
) -> str:
    """
    Insert a managed block at the end of an INI section.

    Existing unrelated codes and settings are preserved.
    """
    text = remove_managed_block(text, marker)

    lines = text.splitlines()
    section_header = f"[{section_name}]"

    section_start: int | None = None
    insertion_index: int | None = None

    for index, line in enumerate(lines):
        stripped = line.strip()

        if stripped == section_header:
            section_start = index
            insertion_index = len(lines)
            continue

        if (
            section_start is not None
            and index > section_start
            and stripped.startswith("[")
            and stripped.endswith("]")
        ):
            insertion_index = index
            break

    managed_block = [
        f"# BEGIN {marker}",
        *block_lines,
        f"# END {marker}",
    ]

    if section_start is None:
        if lines and lines[-1].strip():
            lines.append("")

        lines.extend(
            [
                section_header,
                *managed_block,
            ]
        )
    else:
        assert insertion_index is not None

        if insertion_index > 0 and lines[insertion_index - 1].strip():
            managed_block.insert(0, "")

        lines[insertion_index:insertion_index] = managed_block

    return "\n".join(lines).rstrip() + "\n"


def install_gecko_code(dolphin_user_directory: Path) -> Path:
    """
    Install and enable the Showdown heart hook in RZTE01.ini.

    Dolphin reads per-game user codes from:
        <user directory>/GameSettings/RZTE01.ini
    """
    game_settings_directory = dolphin_user_directory / "GameSettings"
    game_settings_directory.mkdir(parents=True, exist_ok=True)

    ini_path = game_settings_directory / "RZTE01.ini"

    if ini_path.exists():
        text = ini_path.read_text(encoding="utf-8")
    else:
        text = "# RZTE01 - Wii Sports Resort (NTSC-U)\n"

    text = insert_section_block(
        text=text,
        section_name="Gecko",
        marker=GECKO_BLOCK_MARKER,
        block_lines=[
            f"${GECKO_NAME}",
            *GECKO_CODE_LINES,
        ],
    )

    text = insert_section_block(
        text=text,
        section_name="Gecko_Enabled",
        marker=ENABLED_BLOCK_MARKER,
        block_lines=[f"${GECKO_NAME}"],
    )

    ini_path.write_text(text, encoding="utf-8")
    return ini_path


def launch_dolphin(
    dolphin_executable: Path,
    dolphin_user_directory: Path,
    game_path: Path,
) -> subprocess.Popen[bytes]:
    """
    Launch Dolphin with the chosen user directory and cheats enabled.

    The Gecko code must be installed before this function is called.
    """
    command = [
        str(dolphin_executable),
        "--user",
        str(dolphin_user_directory),
        "--config",
        "Dolphin.Core.EnableCheats=True",
        "--exec",
        str(game_path),
    ]

    return subprocess.Popen(command)


class ShowdownHeartController:
    """Continuously enforces a simulated AP upgrade count."""

    def __init__(self, initial_count: int = 0) -> None:
        self._received_count = self._clamp_count(initial_count)
        self._last_status = "not started"

        self._state_lock = threading.Lock()
        self._dme_lock = threading.Lock()

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @staticmethod
    def _clamp_count(count: int) -> int:
        return max(0, min(int(count), MAX_SHOWDOWN_HEART_UPGRADES))

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._enforcement_loop,
            name="showdown-heart-enforcer",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

        if self._thread is not None:
            self._thread.join(timeout=2.0)

        self._thread = None

        with self._dme_lock:
            self._invalidate_hook_locked()

    def set_received_count(self, count: int) -> None:
        with self._state_lock:
            self._received_count = self._clamp_count(count)

        # Do not wait for the next periodic tick.
        self._enforce_safely()

    def receive_item(self) -> None:
        with self._state_lock:
            new_count = self._received_count + 1

        self.set_received_count(new_count)

    def remove_item(self) -> None:
        with self._state_lock:
            new_count = self._received_count - 1

        self.set_received_count(new_count)

    def status_text(self) -> str:
        with self._state_lock:
            count = self._received_count
            status = self._last_status

        hooked = dme.is_hooked()

        return (
            f"Hooked to Dolphin : {hooked}\n"
            f"Upgrade items     : {count}/{MAX_SHOWDOWN_HEART_UPGRADES}\n"
            f"Starting hearts   : {BASE_SHOWDOWN_HEARTS + count}\n"
            f"Mailbox address   : 0x{SHOWDOWN_HEART_UPGRADE_ADDRESS:08X}\n"
            f"Status            : {status}"
        )

    def _set_status(self, status: str) -> None:
        with self._state_lock:
            self._last_status = status

    def _invalidate_hook_locked(self) -> None:
        try:
            dme.un_hook()
        except RuntimeError:
            pass

    def _try_hook_locked(self) -> bool:
        if dme.is_hooked():
            return True

        try:
            dme.hook()
        except RuntimeError:
            return False

        return dme.is_hooked()

    def _read_game_id_locked(self) -> bytes:
        try:
            return dme.read_bytes(GAME_ID_ADDRESS, len(GAME_ID))
        except RuntimeError as error:
            self._invalidate_hook_locked()
            raise DolphinUnavailableError(
                "Dolphin hook became stale; waiting to re-hook"
            ) from error

    def _write_upgrade_count_locked(self, count: int) -> None:
        try:
            dme.write_byte(SHOWDOWN_HEART_UPGRADE_ADDRESS, count)
        except RuntimeError as error:
            self._invalidate_hook_locked()
            raise DolphinUnavailableError(
                "Dolphin hook became stale during write; waiting to re-hook"
            ) from error

    def _read_upgrade_count_locked(self) -> int:
        try:
            return dme.read_byte(SHOWDOWN_HEART_UPGRADE_ADDRESS)
        except RuntimeError as error:
            self._invalidate_hook_locked()
            raise DolphinUnavailableError(
                "Dolphin hook became stale during verification"
            ) from error

    def _enforce_once(self) -> None:
        with self._state_lock:
            count = self._received_count

        with self._dme_lock:
            if not self._try_hook_locked():
                raise DolphinUnavailableError(
                    "Dolphin is not running or emulation has not started"
                )

            running_game_id = self._read_game_id_locked()

            if running_game_id != GAME_ID:
                readable_id = running_game_id.decode("ascii", errors="replace")
                raise DolphinUnavailableError(
                    f"Expected RZTE01, found {readable_id!r}"
                )

            current_value = self._read_upgrade_count_locked()

            if current_value != count:
                self._write_upgrade_count_locked(count)

                written_value = self._read_upgrade_count_locked()
                if written_value != count:
                    raise DolphinUnavailableError(
                        f"Mailbox verification failed: wrote {count}, "
                        f"read back {written_value}"
                    )

        self._set_status(
            f"in sync: {count} upgrades, "
            f"{BASE_SHOWDOWN_HEARTS + count} starting hearts"
        )

    def _enforce_safely(self) -> None:
        try:
            self._enforce_once()
        except DolphinUnavailableError as error:
            self._set_status(f"waiting: {error}")
        except RuntimeError as error:
            self._set_status(f"Dolphin memory error: {error}")

    def _enforcement_loop(self) -> None:
        while not self._stop_event.is_set():
            self._enforce_safely()
            self._stop_event.wait(ENFORCEMENT_INTERVAL_SECONDS)


def print_help() -> None:
    print(
        """
Commands:
  +             Simulate receiving one Showdown Heart Upgrade
  -             Remove one simulated upgrade
  set N         Set the received count to 0-7
  status        Display the desired progression and hook status
  help          Display this help
  quit          Exit the test client

The selected value is continuously enforced. Start a NEW Swordplay Showdown
match after changing the count because the Gecko hook runs when the match's
player state is initialized.
""".strip()
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test progressive Swordplay Showdown hearts in Dolphin."
    )

    parser.add_argument(
        "--dolphin",
        required=True,
        type=Path,
        help="Path to Dolphin.exe.",
    )
    parser.add_argument(
        "--user",
        required=True,
        type=Path,
        help="Path to the Dolphin user directory.",
    )
    parser.add_argument(
        "--game",
        required=True,
        type=Path,
        help="Path to the RZTE01 game image.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=0,
        help="Initial simulated upgrade count, from 0 through 7.",
    )
    parser.add_argument(
        "--no-launch",
        action="store_true",
        help="Install the code but attach to an already running Dolphin.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    ini_path = install_gecko_code(args.user)
    print(f"Installed Gecko hook in: {ini_path}")

    if not args.no_launch:
        print("Launching Dolphin with cheats enabled...")
        launch_dolphin(
            dolphin_executable=args.dolphin,
            dolphin_user_directory=args.user,
            game_path=args.game,
        )
    else:
        print("Not launching Dolphin; waiting for an existing process.")

    controller = ShowdownHeartController(args.count)
    controller.start()

    print("\nSwordplay Showdown Progressive Hearts Test")
    print_help()

    try:
        while True:
            try:
                command = input("\nshowdown> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                break

            if command in {"quit", "exit", "q"}:
                break

            if command in {"help", "h", "?"}:
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
                    count = int(raw_count)
                except ValueError:
                    print("Usage: set N, where N is an integer from 0 through 7.")
                    continue

                controller.set_received_count(count)
                print(controller.status_text())

            elif command == "status":
                print(controller.status_text())

            elif command == "":
                continue

            else:
                print("Unknown command. Type 'help' for available commands.")
    finally:
        print("\nStopping Showdown heart controller...")
        controller.stop()


if __name__ == "__main__":
    main()