# Wii Sports Resort — Technical Notes

Developer reference for how the Dolphin bridge reads and writes Wii Sports
Resort (`RZTE01`, NTSC-U) memory. All numeric values are hexadecimal unless
stated otherwise. Multi-byte reads are **big-endian** (the Wii is PowerPC).

## Memory map overview

Two independent pointer systems are used:

1. The **save buffer**, which holds unlock flags, stamps, and iPoints.
2. The **live Swordplay Showdown session**, used to detect stage clears in real
   time.

Everything the world randomizes lives in the save buffer except live Showdown
clears and the two progressive-upgrade addresses.

## Resolving the save buffer

The save buffer address is not fixed; it is resolved through a pointer chain
every poll, so nothing is hardcoded:

```
SAVE_OBJECT_GLOBAL      = 0x806F4CC0   # fixed global slot
SAVE_DESCRIPTOR_OFFSET  = 0x28
SAVE_BUFFER_OFFSET      = 0x08
SAVE_MAGIC              = "WSP2"

owner       = read_u32(0x806F4CC0)
descriptor  = read_u32(owner + 0x28)
save_buffer = read_u32(descriptor + 0x08)
assert read_bytes(save_buffer, 4) == "WSP2"
```

Each hop is validated to point into MEM1 (`0x80000000`–`0x817FFFFF`) or MEM2
(`0x90000000`–`0x93FFFFFF`). The `WSP2` magic check is important: during boot
the buffer is uninitialized, and the magic only matches once the save has
actually loaded. If any step fails, the bridge simply retries next poll.

Every offset in the tables below is **relative to `save_buffer`**.

## Boot-safety (async) rules

The save is in a default state right after boot, which would cause false reads
and unwanted writes. The bridge guards against this:

1. It does nothing until the **Game ID** at `0x80000000` reads `RZTE01`.
2. After the Game ID first appears, it waits **~30 seconds** before touching
   memory, giving the save time to load.
3. The `WSP2` magic check must also pass before any read/write.

This combination means boot defaults (zeros / `0xFF`) are never mistaken for
progress, and unlocks are never written into a not-yet-loaded save.

## Unlock flags (items)

Gamemode, stage, course, difficulty, and time-of-day unlocks are single bytes
using a 3-state convention:

| Value | Meaning |
| --- | --- |
| `0x00` | Unlocked (already seen) |
| `0x01` | Unlocked and New |
| `0x02` | Locked |

### Applying an unlock

When the player receives an unlock item, the bridge writes `0x01` **only if the
byte is currently `0x02` (Locked)**. It never overwrites `0x00` or `0x01`. This
is what makes async play safe:

- After a reboot, the save resets a granted unlock back to `0x02`; the bridge
  sees `0x02` and re-applies `0x01`.
- Once the player views the "New" badge in-game, the game sets the flag to
  `0x00`; the bridge leaves it alone from then on.

The four VS / Dogfight modes are never randomized and are forced back to `0x02`
whenever they are readable.

### Starting state

At generation, one random gamemode is granted as a starting item. If it needs a
sub-unlock to be playable, one compatible stage, course, difficulty, or time is
also chosen at random. Both arrive through the normal item stream, so the bridge
unlocks them like any other received item.

## Stamps (100 locations)

Stamps live at `0x8CEC`–`0x8EC8` in the save buffer, grouped as 20 categories of
5, each entry a **4-byte word**, `0x04` apart. Detection rule:

```
earned = read_u32(save_buffer + stamp_offset) != 0
```

Any non-zero value means the stamp is earned. Category base offsets are not
perfectly contiguous (there are small gaps between categories), so each category
has its own base address.

## Island Flyover iPoints (80 locations)

iPoints live at `0x8EE8`–`0x8F37`, one **byte** each, `0x01` apart. Detection
rule:

```
collected = read_u8(save_buffer + ipoint_offset) != 0xFF
```

`0xFF` means "not collected". Because uninitialized memory reads as `0x00`
(which is *not* `0xFF`), the boot-safety rules above are essential here — without
them, a booting game would look like every iPoint was collected.

## Swordplay Showdown

### Live stage-clear detection

Stage clears are not stored in a reliable save flag once the game's normal
"beating unlocks the next stage" behavior is disabled by the randomizer.
Instead, clears are read live from the active session:

```
SESSION_SLOT = 0x806F5FF0

session   = read_u32(0x806F5FF0)
progress  = read_u32(session + 0x184)

total     = read_u32(progress + 0x20)   # total enemies
defeated  = read_u32(progress + 0x2C)   # defeated enemies
stage_idx = read_u32(progress + 0x3C)   # 0..19
```

Stage index maps to the 20 stages in order (`0` = Bridge … `9` = Volcano,
`10` = Bridge Reverse … `19` = Volcano Reverse).

A stage is "cleared" when `total > 0 and defeated == total`. To avoid false
positives from attaching mid-results-screen or reading a half-updated frame, the
detector requires:

- the same progress object to have been seen **incomplete** first,
- two **identical consecutive** complete snapshots,
- a known stage index.

Because this is live-only, clearing a stage while the bridge is disconnected is
not recovered later.

### Starting hearts (progressive item)

Showdown normally starts you with 3 hearts. Each **Progressive Swordplay
Showdown Heart Upgrade** adds one, up to 7 extra (10 total). The bridge writes
the received count to a mailbox byte:

```
SHOWDOWN_HEART_MAILBOX_ADDRESS = 0x817FFFF0
```

An installed Gecko hook reads that mailbox when a Showdown player object is
initialized and sets `starting_hearts = 3 + min(count, 7)`. The mailbox write
alone does nothing without the hook, which is why the hook must be installed
(see `pc-client/simulate_showdown_hearts.py`).

## Cycling Road Race stamina

The Cycling stamina-drain coefficient is a **big-endian float** at a fixed
address:

```
CYCLING_DRAIN_ADDRESS = 0x806FC820
default value         = 20.0   (0x41A00000)
```

Each **Progressive Cycling Stamina Upgrade** reduces drain by 10% of the
default:

```
target = 20.0 - received_count * 2.0     # count clamped to 0..10
```

| Upgrades | Drain | % of normal |
| --- | --- | --- |
| 0 | 20.0 | 100% |
| 1 | 18.0 | 90% |
| … | … | … |
| 9 | 2.0 | 10% |
| 10 | 0.0 | 0% |

To avoid stomping unrelated memory, the bridge only writes when the current
value is a recognized drain value (the default or one of the 10 upgrade steps).
The game rewrites `20.0` on load, so the bridge re-applies the player's target
whenever it sees a mismatch — no explicit "game restarted" signal is needed.

## Table Tennis Return Challenge can score

The can's point value in Table Tennis Return Challenge is a **big-endian u32**
at a fixed address:

```
CAN_SCORE_ADDRESS = 0x806F2304
BASE_CAN_SCORE = 3
```

Each **Progressive Table Tennis Can Score Upgrade** adds 1 point, up to 7
upgrades total:

```
target = 3 + received_count       # count clamped to 0..7
```

The bridge continuously writes the target value while connected so game reloads
or mode transitions do not restore the default.

## Stamp logic notes

- **Frisbee Golf - Lucky Skip** requires **Frisbee Golf: Resort C (3-Hole)**,
  **Frisbee Golf: Resort (9-Hole)**, or **Frisbee Golf: 18-Hole**. Other
  Frisbee Golf courses are not considered reasonably completable for this stamp.

## IDs and data source

Item/location names, IDs, save offsets, and access rules all live in a single
`data.py` module with no Archipelago imports. The generated world and the
Dolphin bridge both consume it (the bridge loads it directly), so IDs and
offsets can never drift between the two.
