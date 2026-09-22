"""Print Swordplay Showdown completions from a live Dolphin instance.

Run with Wii Sports Resort (RZTE01) loaded in Dolphin after installing the
dependency from ``pc-client/requirements.txt``::

    python pc-client/showdown_client.py

The script only observes Dolphin memory. It does not read save data or make
Archipelago connections.
"""

from __future__ import annotations

import struct
import time
from dataclasses import dataclass
from typing import Protocol


SESSION_SLOT = 0x806F5FF0
STAGE_NAMES = {
    0: "Bridge",
    1: "Lighthouse",
    2: "Beach",
    3: "Mountain",
    4: "Forest",
    5: "Ruins",
    6: "Waterfall",
    7: "Cliffs",
    8: "Castle",
    9: "Volcano",
    10: "Bridge Reverse",
    11: "Lighthouse Reverse",
    12: "Beach Reverse",
    13: "Mountain Reverse",
    14: "Forest Reverse",
    15: "Ruins Reverse",
    16: "Waterfall Reverse",
    17: "Cliffs Reverse",
    18: "Castle Reverse",
    19: "Volcano Reverse",
}
POLL_INTERVAL_SECONDS = 0.1
MAX_ENEMIES = 100
COMPLETION_MESSAGE = "[COMPLETE] Swordplay Showdown - {stage_name} ({defeated}/{total} defeated)"
PROGRESS_MESSAGE = "[PROGRESS] Swordplay Showdown - {stage_name} ({defeated}/{total} defeated)"
POINTERS_VALID_MESSAGE = "[INFO] Dolphin pointers valid (progress=0x{progress:08X})"


class MemoryAdapter(Protocol):
    """The memory operations required by the detector."""

    def read_bytes(self, address: int, size: int) -> bytes:
        ...


class DolphinMemoryAdapter:
    """Adapter for the installed dolphin-memory-engine package."""

    def __init__(self) -> None:
        import dolphin_memory_engine as dme

        self._dme = dme
        self._dme.hook()

    def read_bytes(self, address: int, size: int) -> bytes:
        return self._dme.read_bytes(address, size)


def read_u32_be(memory: MemoryAdapter, address: int) -> int:
    data = memory.read_bytes(address, 4)
    if len(data) != 4:
        raise ValueError(f"expected 4 bytes at 0x{address:08X}, got {len(data)}")
    return struct.unpack(">I", data)[0]


def is_valid_pointer(address: int) -> bool:
    return (
        0x80000000 <= address < 0x81800000
        or 0x90000000 <= address < 0x94000000
    )


def resolve_progress(memory: MemoryAdapter) -> int:
    session = read_u32_be(memory, SESSION_SLOT)
    if not is_valid_pointer(session):
        raise ValueError("invalid session pointer")

    progress = read_u32_be(memory, session + 0x184)
    if not is_valid_pointer(progress):
        raise ValueError("invalid progress pointer")
    return progress


def stage_name(stage_index: int) -> str:
    return STAGE_NAMES.get(stage_index, f"Unknown ({stage_index})")


def format_completion(stage_index: int, total: int, defeated: int) -> str:
    return COMPLETION_MESSAGE.format(
        stage_name=stage_name(stage_index), total=total, defeated=defeated
    )


def format_progress(stage_index: int, total: int, defeated: int) -> str:
    return PROGRESS_MESSAGE.format(
        stage_name=stage_name(stage_index), total=total, defeated=defeated
    )


@dataclass
class CompletionDetector:
    """Turn successive progress snapshots into at-most-once completions."""

    progress_address: int | None = None
    attempt_stage_index: int | None = None
    saw_incomplete: bool = False
    previous_complete_snapshot: tuple[int, int, int] | None = None
    reported: bool = False

    def reset(self) -> None:
        self.progress_address = None
        self.attempt_stage_index = None
        self.saw_incomplete = False
        self.previous_complete_snapshot = None
        self.reported = False

    def observe(
        self, progress_address: int, stage_index: int, total: int, defeated: int
    ) -> str | None:
        if (
            progress_address != self.progress_address
            or stage_index != self.attempt_stage_index
        ):
            self.progress_address = progress_address
            self.attempt_stage_index = stage_index
            self.saw_incomplete = False
            self.previous_complete_snapshot = None
            self.reported = False

        snapshot = (stage_index, total, defeated)
        complete = total > 0 and defeated == total
        if not complete:
            if total > 0 and defeated < total:
                self.reported = False
                self.saw_incomplete = True
            self.previous_complete_snapshot = None
            return None

        if self.reported or not self.saw_incomplete:
            return None

        if self.previous_complete_snapshot == snapshot:
            self.reported = True
            if stage_index not in STAGE_NAMES:
                return None
            return format_completion(stage_index, total, defeated)

        self.previous_complete_snapshot = snapshot
        return None


def read_snapshot(memory: MemoryAdapter) -> tuple[int, int, int, int]:
    progress = resolve_progress(memory)
    total = read_u32_be(memory, progress + 0x20)
    defeated = read_u32_be(memory, progress + 0x2C)
    stage_index = read_u32_be(memory, progress + 0x3C)
    validate_counters(total, defeated)
    return progress, stage_index, total, defeated


def validate_counters(total: int, defeated: int) -> None:
    if total > MAX_ENEMIES:
        raise ValueError(f"invalid total enemy count: {total}")
    if defeated > total:
        raise ValueError(f"invalid defeated enemy count: {defeated}/{total}")


def read_snapshot_consistent(
    memory: MemoryAdapter, attempts: int = 3
) -> tuple[int, int, int, int]:
    if attempts < 1:
        raise ValueError("attempts must be at least 1")

    for _ in range(attempts):
        first = read_snapshot(memory)
        second = read_snapshot(memory)
        if first == second:
            return first

    raise ValueError("progress snapshot did not stabilize")


def diagnostic_messages(
    snapshot: tuple[int, int, int, int],
    previous_snapshot: tuple[int, int, int, int] | None,
    pointers_valid: bool,
) -> list[str]:
    progress, stage_index, total, defeated = snapshot
    messages = []
    if not pointers_valid or (
        previous_snapshot is not None and progress != previous_snapshot[0]
    ):
        messages.append(POINTERS_VALID_MESSAGE.format(progress=progress))
    if previous_snapshot != snapshot:
        messages.append(format_progress(stage_index, total, defeated))
    return messages


def run(memory: MemoryAdapter, poll_interval: float = POLL_INTERVAL_SECONDS) -> None:
    detector = CompletionDetector()
    last_error_log = 0.0
    pointers_valid = False
    previous_progress: tuple[int, int, int, int] | None = None

    while True:
        try:
            snapshot = read_snapshot_consistent(memory)
            for diagnostic in diagnostic_messages(
                snapshot, previous_progress, pointers_valid
            ):
                print(diagnostic, flush=True)
            pointers_valid = True
            previous_progress = snapshot
            message = detector.observe(*snapshot)
            if message is not None:
                print(message, flush=True)
        except (OSError, RuntimeError, ValueError, struct.error) as error:
            detector.reset()
            pointers_valid = False
            previous_progress = None
            now = time.monotonic()
            if now - last_error_log >= 5.0:
                print(f"[INFO] Waiting for Dolphin: {error}", flush=True)
                last_error_log = now
        time.sleep(poll_interval)


def main() -> None:
    try:
        run(DolphinMemoryAdapter())
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()