"""Build the Wii Sports Resort .apworld archive without an Archipelago checkout."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
WORLD_SOURCE = REPOSITORY_ROOT / "apworld"


def build(output_directory: Path) -> Path:
    manifest = WORLD_SOURCE / "archipelago.json"
    if not manifest.is_file():
        raise FileNotFoundError(f"Missing manifest: {manifest}")

    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / "wii_sports_resort.apworld"

    with zipfile.ZipFile(
        output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for source in WORLD_SOURCE.glob("*.py"):
            archive.write(source, Path("wii_sports_resort") / source.name)
        archive.write(manifest, "wii_sports_resort/archipelago.json")
        for source in (WORLD_SOURCE / "docs").glob("*.md"):
            archive.write(source, Path("wii_sports_resort") / "docs" / source.name)
        symbol_map = WORLD_SOURCE / "docs" / "RZTE01.map"
        if symbol_map.is_file():
            archive.write(symbol_map, "wii_sports_resort/docs/RZTE01.map")

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Wii Sports Resort apworld")
    parser.add_argument("--output-directory", type=Path, default=REPOSITORY_ROOT / "dist")
    args = parser.parse_args()
    print(f"Built {build(args.output_directory.resolve())}")


if __name__ == "__main__":
    main()