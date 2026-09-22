"""Build double-clickable Windows executables for the Dolphin bridge and setup helper."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = REPOSITORY_ROOT / "dist"


def run_pyinstaller(arguments: list[str]) -> None:
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", *arguments], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Wii Sports Resort Windows executables")
    parser.add_argument("--output-directory", type=Path, default=OUTPUT_DIRECTORY)
    parser.add_argument("--skip-helper", action="store_true")
    args = parser.parse_args()

    output_directory = args.output_directory.resolve()
    work_directory = output_directory / "pyinstaller-work"
    specification_directory = output_directory / "pyinstaller-spec"
    output_directory.mkdir(parents=True, exist_ok=True)

    run_pyinstaller([
        "--onefile",
        "--console",
        "--name", "WSR Dolphin Bridge",
        "--distpath", str(output_directory),
        "--workpath", str(work_directory),
        "--specpath", str(specification_directory),
        "--add-data", f"{REPOSITORY_ROOT / 'apworld' / 'data.py'};apworld",
        "--paths", str(REPOSITORY_ROOT / "pc-client"),
        str(REPOSITORY_ROOT / "pc-client" / "dolphin_bridge.py"),
    ])

    if args.skip_helper:
        return

    database = REPOSITORY_ROOT / "helpers" / "RFL_DB.dat"
    if not database.is_file():
        raise FileNotFoundError(
            "Missing helpers/RFL_DB.dat. Provide it locally or through CI before "
            "building the setup helper executable."
        )

    run_pyinstaller([
        "--onefile",
        "--windowed",
        "--name", "WSR Dolphin Setup",
        "--distpath", str(output_directory),
        "--workpath", str(work_directory),
        "--specpath", str(specification_directory),
        "--add-data", f"{database};.",
        str(REPOSITORY_ROOT / "helpers" / "dolphin_setup_helper.py"),
    ])


if __name__ == "__main__":
    main()