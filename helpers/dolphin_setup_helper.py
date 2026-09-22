"""GUI helper for installing Wii Sports Resort Archipelago Dolphin setup files."""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path
from tkinter import Tk, filedialog, messagebox


GAME_ID = "RZTE01"
SCRIPT_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
RFL_SOURCE = SCRIPT_DIR / "RFL_DB.dat"

GECKO_CODES = {
	"Archipelago - Progressive Showdown Hearts": [
		"C2639FA0 00000004",
		"3D808180 888CFFF0",
		"28040007 40810008",
		"38800000 38840003",
		"60000000 00000000",
	],
	"Archipelago - Swordplay Showdown Next Stage Opens Change Stage": [
		"04278908 418200E8",
	],
}


def resolve_user_directory(selection: Path) -> Path:
	if selection.name.lower() == "user":
		return selection
	if (selection / "User").exists():
		return selection / "User"
	if (selection / "Dolphin.exe").exists():
		return selection / "User"
	return selection


def read_text(path: Path) -> str:
	if not path.exists():
		return ""
	return path.read_text(encoding="utf-8")


def remove_gecko_code(text: str, code_name: str) -> str:
	lines = text.splitlines()
	output: list[str] = []
	in_gecko = False
	skipping_code = False

	for line in lines:
		stripped = line.strip()
		if stripped.startswith("[") and stripped.endswith("]"):
			in_gecko = stripped == "[Gecko]"
			skipping_code = False
			output.append(line)
			continue

		if in_gecko and stripped.startswith("$"):
			skipping_code = stripped == f"${code_name}"
			if skipping_code:
				continue

		if in_gecko and skipping_code:
			continue

		output.append(line)

	return "\n".join(output).rstrip()


def remove_enabled_code(text: str, code_name: str) -> str:
	lines = text.splitlines()
	output: list[str] = []
	in_enabled = False

	for line in lines:
		stripped = line.strip()
		if stripped.startswith("[") and stripped.endswith("]"):
			in_enabled = stripped == "[Gecko_Enabled]"
			output.append(line)
			continue
		if in_enabled and stripped == f"${code_name}":
			continue
		output.append(line)

	return "\n".join(output).rstrip()


def insert_section_lines(text: str, section_name: str, new_lines: list[str]) -> str:
	lines = text.splitlines()
	section_header = f"[{section_name}]"
	section_start: int | None = None
	insert_at: int | None = None

	for index, line in enumerate(lines):
		stripped = line.strip()
		if stripped == section_header:
			section_start = index
			insert_at = len(lines)
			continue
		if section_start is not None and index > section_start and stripped.startswith("[") and stripped.endswith("]"):
			insert_at = index
			break

	if section_start is None:
		if lines and lines[-1].strip():
			lines.append("")
		lines.extend([section_header, *new_lines])
	else:
		assert insert_at is not None
		if insert_at > 0 and lines[insert_at - 1].strip():
			new_lines = ["", *new_lines]
		lines[insert_at:insert_at] = new_lines

	return "\n".join(lines).rstrip() + "\n"


def set_ini_value(text: str, section_name: str, key: str, value: str) -> str:
	lines = text.splitlines()
	section_header = f"[{section_name}]"
	section_start: int | None = None
	insert_at: int | None = None

	for index, line in enumerate(lines):
		stripped = line.strip()
		if stripped == section_header:
			section_start = index
			insert_at = len(lines)
			continue
		if section_start is not None and index > section_start:
			if stripped.startswith("[") and stripped.endswith("]"):
				insert_at = index
				break
			if stripped.split("=", 1)[0].strip() == key:
				lines[index] = f"{key} = {value}"
				return "\n".join(lines).rstrip() + "\n"

	if section_start is None:
		if lines and lines[-1].strip():
			lines.append("")
		lines.extend([section_header, f"{key} = {value}"])
	else:
		assert insert_at is not None
		lines.insert(insert_at, f"{key} = {value}")

	return "\n".join(lines).rstrip() + "\n"


def install_gecko_codes(user_directory: Path) -> Path:
	game_settings = user_directory / "GameSettings"
	game_settings.mkdir(parents=True, exist_ok=True)
	ini_path = game_settings / f"{GAME_ID}.ini"

	text = read_text(ini_path) or "# RZTE01 - Wii Sports Resort (NTSC-U)\n"
	text = set_ini_value(text, "Core", "EnableCheats", "True")

	for name, lines in GECKO_CODES.items():
		text = remove_gecko_code(text, name)
		text = remove_enabled_code(text, name)
		text = insert_section_lines(text, "Gecko", [f"${name}", *lines])
		text = insert_section_lines(text, "Gecko_Enabled", [f"${name}"])

	ini_path.write_text(text, encoding="utf-8")
	return ini_path


def enable_global_cheats(user_directory: Path) -> Path:
	config_dir = user_directory / "Config"
	config_dir.mkdir(parents=True, exist_ok=True)
	dolphin_ini = config_dir / "Dolphin.ini"

	text = read_text(dolphin_ini)
	text = set_ini_value(text, "Core", "EnableCheats", "True")
	dolphin_ini.write_text(text, encoding="utf-8")
	return dolphin_ini


def install_rfl_database(user_directory: Path) -> tuple[Path, Path | None, bool]:
	if not RFL_SOURCE.exists():
		raise FileNotFoundError(f"Missing bundled Mii database: {RFL_SOURCE}")

	target_dir = user_directory / "Wii" / "shared2" / "menu" / "FaceLib"
	target_dir.mkdir(parents=True, exist_ok=True)
	target = target_dir / "RFL_DB.dat"

	if target.exists() and target.read_bytes() == RFL_SOURCE.read_bytes():
		return target, None, False

	backup: Path | None = None
	if target.exists():
		replace = messagebox.askyesno(
			"Replace Dolphin Mii database?",
			"An existing RFL_DB.dat was found. The helper can back it up and "
			"replace it with the Archipelago-compatible Mii database.\n\n"
			"Choose Yes to back up and replace it, or No to leave your current "
			"Mii database untouched.",
		)
		if not replace:
			return target, None, True
		stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
		backup = target.with_name(f"RFL_DB.dat.wsr-ap-backup-{stamp}")
		shutil.copy2(target, backup)

	shutil.copy2(RFL_SOURCE, target)
	return target, backup, False


def install_to_user_directory(user_directory: Path) -> str:
	ini_path = install_gecko_codes(user_directory)
	dolphin_ini = enable_global_cheats(user_directory)
	rfl_path, backup_path, skipped_rfl = install_rfl_database(user_directory)

	lines = [
		"Wii Sports Resort Archipelago Dolphin setup complete.",
		"",
		f"Dolphin user folder: {user_directory}",
		f"Installed Gecko codes: {ini_path}",
		f"Enabled cheats in: {dolphin_ini}",
	]
	if skipped_rfl:
		lines.append(f"Left existing Mii database unchanged: {rfl_path}")
	else:
		lines.append(f"Installed Mii database: {rfl_path}")
	if backup_path is not None:
		lines.append(f"Backed up old Mii database: {backup_path}")
	return "\n".join(lines)


def main() -> None:
	root = Tk()
	root.withdraw()
	root.update()

	selection = filedialog.askdirectory(
		title="Select Dolphin user folder (Dolphin Emulator or portable User folder)",
		mustexist=False,
	)
	if not selection:
		messagebox.showinfo("Setup cancelled", "No Dolphin folder was selected.")
		return

	user_directory = resolve_user_directory(Path(selection))
	try:
		summary = install_to_user_directory(user_directory)
	except Exception as error:  # noqa: BLE001 - show GUI error to the user
		messagebox.showerror("Setup failed", str(error))
		raise
	else:
		messagebox.showinfo("Setup complete", summary)
		print(summary)


if __name__ == "__main__":
	main()
