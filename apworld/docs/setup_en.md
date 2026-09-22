# Wii Sports Resort Setup Guide

This guide walks you through everything you need to play **Wii Sports Resort**
(NTSC-U, game ID `RZTE01`) in an Archipelago multiworld, from installing the
world to connecting the client.

# IMPORTANT!!! Information about Gecko Codes and Mii Data
Unless you want to cheat or lose some functionality of the archipelago, please install
The following gecko codes and make sure cheats are enabled in Dolphin:

Archipelago - Progressive Showdown Hearts
C2639FA0 00000004
3D808180 888CFFF0
28040007 40810008
38800000 38840003
60000000 00000000

Archipelago - Swordplay Showdown Next Stage Opens Change Stage
04278908 418200E8

Alternatively run WSR Dolphin Setup.exe to install everything
automatically. The helper opens a folder picker. Select either your Dolphin user
folder (usually `Documents/Dolphin Emulator`) or the `User` folder inside a
portable Dolphin install. If you select a portable Dolphin folder that contains
`Dolphin.exe`, the helper uses its `User` folder automatically.

The helper writes `RZTE01.ini` to `GameSettings`, enables cheats in
`Config/Dolphin.ini`, and installs `RFL_DB.dat` to
`Wii/shared2/menu/FaceLib`. If an existing `RFL_DB.dat` is found, the helper asks
before replacing it and creates a timestamped backup first. We recommend a
portable Dolphin install so you do not accidentally overwrite Mii data you care
about. You can make one by creating an empty `portable.txt` file next to
`Dolphin.exe` before launching Dolphin.

## Required Software

- **Dolphin Emulator** 5.0 or newer ([download](https://dolphin-emu.org/download/)).
- A legal dump of **Wii Sports Resort (NTSC-U / `RZTE01`)**.
- **Python 3.10 or newer** ([download](https://www.python.org/downloads/)).
- The **`wii_sports_resort.apworld`** package (from this project's releases).
- The **`pc-client/`** Dolphin bridge from this repository.

## Optional Software

- An Archipelago install for local generation/hosting
  ([releases](https://github.com/ArchipelagoMW/Archipelago/releases)), if you
  are not generating on the website.
- The [Archipelago Text Client](https://github.com/ArchipelagoMW/Archipelago/releases)
  for chatting and hints while you play.

## Installation

1. **Install the apworld.** Double-click `wii_sports_resort.apworld` to let the
   Archipelago Launcher install it, or copy it into your Archipelago
   installation's `custom_worlds/` folder.
2. **Install the client dependencies.** In a terminal, from this repository:
   ```bash
   pip install -r pc-client/requirements.txt
   ```

## Creating Your YAML

Every player fills out a YAML config. A minimal example:

```yaml
name: YourName
game: Wii Sports Resort
Wii Sports Resort:
  goal: all_gamemodes
  goal_stamp_category: swordplay_showdown
  include_showdown_clears: true
  include_ipoints: true
  junk_curated_stamps: false
  junk_stamp_categories: []
  junk_stamps: []
```

### Goal options (`goal`)

| Value | Completion condition |
| --- | --- |
| `all_gamemodes` *(default)* | Unlock all 17 gamemodes. |
| `all_showdown_stages` | Unlock all 20 Swordplay Showdown stages. |
| `all_ipoints` | Be able to collect every Island Flyover iPoint. |
| `stamp_category` | Earn every stamp in the category set by `goal_stamp_category`. |
| `all_stamps` | Be able to earn all 100 stamps. |

### Goal stamp categories (`goal_stamp_category`)

Used only when `goal: stamp_category`. One of:

```
swordplay_showdown          swordplay_duel               swordplay_speed_slice
power_cruising              archery                      frisbee_dog
basketball_3_point_contest  basketball_pickup_game       bowling_standard_game
bowling_100_pin_game        bowling_spin_control         canoeing_speed_challenge
table_tennis_return_challenge  table_tennis_match        wakeboarding
island_flyover              golf                         frisbee_golf
cycling_road_race           skydiving
```

### Location options

| Option | Default | Effect |
| --- | --- | --- |
| `include_showdown_clears` | `true` | Include the 20 "clear a Swordplay Showdown stage" checks. |
| `include_ipoints` | `true` | Include the 80 Island Flyover iPoint checks. |

### Junking stamps

You can force grindy or unwanted stamps to only ever hold junk. They stay as
checks but never hold progression, so they are safe to skip.

| Option | Type | Effect |
| --- | --- | --- |
| `junk_curated_stamps` | yes/no | Junk a built-in curated list of grindy stamps (default `no`). |
| `junk_stamp_categories` | list of categories | Junk **every** stamp in the listed categories. |
| `junk_stamps` | list of stamp names | Junk **specific** stamps, named `<Category> - <Stamp>`. |

`junk_curated_stamps` affects the following stamps (including all three listed
Bowling Pin Droppers and both listed Hole in Ones):

```text
Skydiving - Friends in High Places
Skydiving - 200-Point Dive
Island Flyover - Wuhu Tour Guide
Island Flyover - Balloonatic
Archery - A Secret to Everybody
Archery - Sharpshooter
Basketball 3-Point Contest - Hot Hand
Basketball 3-Point Contest - Pure Shooter
Basketball Pickup Game - Hoop Hero
Bowling Standard Game - High Roller
Bowling Standard Game - Pin Dropper
Bowling 100-Pin Game - Pin Dropper
Bowling Spin Control - Pin Dropper
Bowling Standard Game - Perfect Game
Bowling Spin Control - English Major
Canoeing Speed Challenge - Cut the Red Tape
Cycling Road Race - Last Gasp
Frisbee Dog - Perfect Target
Frisbee Dog - Golden Arm
Frisbee Golf - On a Roll
Golf - Hole in One
Frisbee Golf - Hole in One
Frisbee Golf - Straight and Narrow
Golf - King of Clubs
Golf - Ace of Clubs
Swordplay Duel - Met Your Match
Swordplay Duel - Last Mii Standing
Swordplay Speed Slice - A Cut Above
Swordplay Showdown - Sword Fighter
Swordplay Showdown - Untouchable
Table Tennis Match - Perfectly Matched
Table Tennis Match - Table Titan
Table Tennis Return Challenge - Recycler
Table Tennis Return Challenge - Save Face
```

These stamps are always junked regardless of every junk option, because AP
upgrades can make them impossible or inconsistent with randomized play:

```text
Swordplay Showdown - Not a Scratch
Swordplay Showdown - Perfect 10
Swordplay Showdown - Untouchable
Cycling Road Race - Last Gasp
```

Example:

```yaml
Wii Sports Resort:
  junk_curated_stamps: true
  junk_stamp_categories:
    - Bowling Spin Control
    - Cycling Road Race
  junk_stamps:
    - Golf - Hole in One
    - Frisbee Golf - Hole in One
```

Category names are the human-readable names (e.g. `Bowling Spin Control`).
Individual stamp names are `Category - Stamp`, exactly as they appear as
locations (e.g. `Swordplay Showdown - Sword Fighter`). The built-in
`exclude_locations` option also works if you prefer.

> Junked stamps hold junk or useful filler (like the progressive upgrades),
> never logic-required progression.

## Generating and Hosting

- **Website:** upload your YAML at
  [archipelago.gg](https://archipelago.gg/), generate, and host the room.
- **Locally:** drop your YAML in `Archipelago/Players/`, run
  `python Generate.py`, then host the output with `python MultiServer.py` or on
  the website.

## Preparing Dolphin

1. Open Dolphin and enable **Config → General → Enable Cheats**.
2. install the Gecko hook that reads the heart mailbox as well as the
   gecko code that redirects the next stage in Swordplay Showdown to change
   stage. For the codes themselves look above at information about gecko
   codes.
3. Boot **Wii Sports Resort (`RZTE01`)** and load your fresh save file.

## Connecting the Client

With Dolphin running and the game loaded, start the bridge:

```bash
python pc-client/dolphin_bridge.py --server ADDRESS:PORT --name YourName
```

Add `--password YOURPASSWORD` if the room requires one.

`ADDRESS:PORT` must be an address a client can actually reach:

- **Playing on the website:** use the address/port shown on your room page.
- **Hosting locally, playing on the same PC:** use `127.0.0.1:PORT` (or
  `localhost:PORT`).
- **Hosting locally, playing over LAN/internet:** use the address the server
  printed on startup, e.g. `Hosting game at 1.2.3.4:38281` → use `1.2.3.4:38281`.

Do **not** use `0.0.0.0` — that is only a server *bind* address ("listen on
every interface") and is never something a client can connect to.

The bridge will:

- unlock the gamemodes, stages, courses, and difficulties you receive,
- keep the always-locked VS / Dogfight modes disabled,
- apply Cycling Stamina, Swordplay Showdown Heart, and Table Tennis Can Score upgrades,
- send checks for stamps, iPoints, and live Swordplay Showdown clears,
- report your goal to the server when it is met.

## How Checks Work

- **Stamps (100):** sent when the game marks a stamp earned in your save.
- **iPoints (80):** sent when you visit an Island Flyover iPoint.
- **Swordplay Showdown clears (20):** detected **live** as you finish a stage.

## Troubleshooting

- **"'0.0.0.0' is a bind address..." / `WinError 1214`:** you passed the
  server's bind address instead of a reachable one — see "Connecting the
  Client" above for what to use instead.
- **"Waiting for Dolphin" / not connecting:** make sure Wii Sports Resort is
  actually running (not just Dolphin). The bridge re-hooks automatically when
  Dolphin restarts.
- **Nothing happens right after boot:** the bridge waits ~10 seconds after the
  game boots for the save to finish loading, so it never misreads boot defaults.
  (IMPORTANT NOTE: Please do not sit on the strap screen for too long, else
  things might mess up.)
- **A stage clear didn't count:** clears are detected live only. If you clear a
  stage while the bridge is disconnected, that check is not recovered later —
  clear it again while connected.
- **Heart upgrades not applying:** confirm cheats are enabled and the Gecko hook
  is installed, then start a **new** Showdown match (the hook runs at match
  start).

## Good to Know

- You always begin with one random gamemode already unlocked. If that mode
  needs a stage, course, difficulty, or time unlock, you receive one random
  compatible unlock too.
- Keep the bridge open the whole session; it self-heals across Dolphin restarts,
  game resets, and save reloads.
