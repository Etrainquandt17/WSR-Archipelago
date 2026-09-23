# Wii Sports Resort Archipelago

An external-memory Archipelago integration for **Wii Sports Resort (NTSC-U,
RZTE01)** running in Dolphin.

The project randomizes gamemodes, stages, courses, difficulties, and Island
Flyover times. Checks come from 100 Stamps, 80 Island Flyover iPoints, and 20
live Swordplay Showdown clears.

## Downloads

From a release, download:

- `wii_sports_resort.apworld` to install into Archipelago.
- The source archive when using the external Dolphin bridge client.

See [the setup guide](apworld/docs/setup_en.md) for player setup.

## Repository Layout

- `apworld/`: Canonical Archipelago world source and player documentation.
- `pc-client/`: External Dolphin bridge and standalone memory test clients.
- `helpers/`: Dolphin Gecko-code and Mii database installer.
- `scripts/build_apworld.py`: Builds the distributable `.apworld` archive.
- `scripts/build_executables.py`: Builds double-clickable Windows bridge/setup
   executables with PyInstaller.

The reverse-engineering symbol reference is available at
`apworld/docs/RZTE01.map` and is included in the `.apworld` archive.

## Build Without an Archipelago Clone

You do **not** need to clone the full Archipelago repository to modify or build
the distributable world. With Python 3.10+:

```powershell
python apworld/data.py
python -m unittest discover -s pc-client -p "test_*.py"
python scripts/build_apworld.py
```

This writes `dist/wii_sports_resort.apworld`. It packages only the canonical
world code, manifest, and Markdown docs. The optional PowerShell builder remains
available for local Windows use, but the Python builder avoids execution-policy
configuration.

To build the Windows executables locally, install PyInstaller and run:

```powershell
python -m pip install pyinstaller
python scripts/build_executables.py
```

This produces `WSR.Dolphin.Bridge.exe` and `WSR.Dolphin.Setup.exe` in `dist/`.
The bridge opens a connection dialog when double-clicked. The setup executable
opens the Dolphin folder picker described in the setup guide. `RFL_DB.dat` is
embedded inside the setup executable, and `RZTE01.ini` is generated in the
selected Dolphin user folder.

`RFL_DB.dat` is intentionally excluded from source control. Release builds
bundle it only in `WSR Dolphin Setup.exe` from chunked GitHub repository
secrets. The build uses 23 secrets named `RFL_DB_DAT_BASE64_01` through
`RFL_DB_DAT_BASE64_23`; this is necessary because one Base64 encoding exceeds
GitHub's 48 KB secret limit. The publishing setup creates those secrets from
the local file automatically.

Do not commit `RFL_DB.dat` or print the secret chunks in terminal output.

## Client Dependencies

```powershell
python -m pip install -r pc-client/requirements.txt
```

Players should use the release `WSR.Dolphin.Bridge.exe`: double-click it and
enter the server address, slot name, and optional password in the dialog. Keep
its console open while playing.

For source/developer use, run the bridge after starting Dolphin and loading Wii
Sports Resort:

```powershell
python pc-client/dolphin_bridge.py --server ADDRESS:PORT --name YourName
```

Never use `0.0.0.0` as `ADDRESS`; use `127.0.0.1`, a LAN IP, or the address
printed by the server.

The project code is available under the [MIT License](LICENSE).