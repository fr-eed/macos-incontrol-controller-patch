#!/usr/bin/env python3
"""
Steam Input Controller Patch for InControl Games

Patches Assembly-CSharp.dll to recognize Steam Input's virtual controllers
("Microsoft GamePad-1", "Microsoft GamePad-2", etc.) as Xbox 360 controllers.

Supported games: Tricky Towers, Overcooked! 2

Usage:
    python3 patch.py [--restore] [path/to/Assembly-CSharp.dll]
"""

import logging
import shutil
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

STEAM_LIBRARY_PATH = Path.home() / "Library/Application Support/Steam/steamapps/common"
DLL_RELATIVE_PATH = Path("Contents/Resources/Data/Managed/Assembly-CSharp.dll")

GAMES = [
    ("Tricky Towers", STEAM_LIBRARY_PATH / "Tricky Towers" / "TrickyTowers.app" / DLL_RELATIVE_PATH),
    ("Overcooked! 2", STEAM_LIBRARY_PATH / "Overcooked! 2" / "Overcooked2.app" / DLL_RELATIVE_PATH),
]

# Xbox360MacProfile JoystickNames to replace with Steam Input controller names
# Each original string must be >= length of replacement (will be null-padded)
# Note: © = \xa9 (copyright symbol) prefixes some strings in the DLL
PATCHES = [
    ("Microsoft Wireless 360 Controller", "Microsoft GamePad-1"),
    ("Mad Catz, Inc. Mad Catz FPS Pro GamePad", "Microsoft GamePad-2"),
    ("Mad Catz, Inc. MadCatz Call of Duty GamePad", "Microsoft GamePad-3"),
    ("\xa9Microsoft Corporation Controller", "Microsoft GamePad-4"),
]


def patch_string(data: bytearray, old_str: str, new_str: str) -> bool:
    """Replace a .NET User String in the DLL."""
    old_utf16 = old_str.encode("utf-16-le")
    new_utf16 = new_str.encode("utf-16-le")

    if len(new_utf16) > len(old_utf16):
        log.error("'%s' is longer than '%s'", new_str, old_str)
        return False

    old_length_byte = len(old_utf16) + 1
    new_length_byte = len(new_utf16) + 1

    pattern = bytes([old_length_byte]) + old_utf16
    pos = data.find(pattern)

    if pos == -1:
        new_pattern = bytes([new_length_byte]) + new_utf16
        if new_pattern in data:
            log.info("  Already patched: '%s'", new_str)
            return True
        return False

    data[pos] = new_length_byte
    data[pos + 1:pos + 1 + len(new_utf16)] = new_utf16
    for i in range(len(new_utf16), len(old_utf16) + 1):
        data[pos + 1 + i] = 0x00

    log.info("  Patched: '%s' -> '%s'", old_str, new_str)
    return True


def patch_dll(dll_path: Path) -> bool:
    backup = dll_path.with_suffix(".dll.bak")

    if not dll_path.exists():
        log.error("DLL not found: %s", dll_path)
        return False

    if not backup.exists():
        shutil.copy2(dll_path, backup)
        log.info("Backup: %s", backup.name)

    data = bytearray(dll_path.read_bytes())

    patched = sum(1 for old, new in PATCHES if patch_string(data, old, new))

    if patched == 0:
        log.error("No strings found to patch")
        return False

    dll_path.write_bytes(data)
    log.info("Patched %d/%d controller names", patched, len(PATCHES))
    return True


def restore_dll(dll_path: Path) -> bool:
    backup = dll_path.with_suffix(".dll.bak")
    if not backup.exists():
        log.error("No backup found")
        return False
    shutil.copy2(backup, dll_path)
    log.info("Restored from backup")
    return True


def find_installed_games():
    """Return list of (name, dll_path) for games that are installed."""
    return [(name, dll_path) for name, dll_path in GAMES if dll_path.exists()]


def main() -> int:
    custom_paths = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    should_restore = "--restore" in sys.argv
    process_game = restore_dll if should_restore else patch_dll

    if custom_paths:
        games_to_process = [("", Path(custom_paths[0]))]
    else:
        games_to_process = find_installed_games()

    if not games_to_process:
        log.error("No supported games found. Provide a path to Assembly-CSharp.dll.")
        return 1

    all_succeeded = True
    for game_name, dll_path in games_to_process:
        if game_name:
            log.info("\n%s", game_name)
        log.info("DLL: %s", dll_path)
        if not process_game(dll_path):
            all_succeeded = False

    if all_succeeded and not should_restore:
        log.info("\nEnable Steam Input in each game's Steam properties.")

    return 0 if all_succeeded else 1


if __name__ == "__main__":
    sys.exit(main())
