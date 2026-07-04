#!/usr/bin/env python3
"""
Steam Input Controller Patch for InControl Games

Patches Assembly-CSharp.dll to recognize Steam Input's virtual controllers
("Microsoft GamePad-1", "Microsoft GamePad-2", etc.) as Xbox 360 controllers.

Supported games: Tricky Towers, Overcooked! 2

Usage:
    python3 patch.py [--restore] [path/to/Assembly-CSharp.dll]
"""

import argparse
import logging
import shutil
import sys
from pathlib import Path
from typing import List, Tuple

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

STEAM_LIBRARY_PATH = Path.home() / "Library/Application Support/Steam/steamapps/common"
DLL_RELATIVE_PATH = Path("Contents/Resources/Data/Managed/Assembly-CSharp.dll")

GAMES: List[Tuple[str, Path]] = [
    ("Tricky Towers", STEAM_LIBRARY_PATH / "Tricky Towers" / "TrickyTowers.app" / DLL_RELATIVE_PATH),
    ("Overcooked! 2", STEAM_LIBRARY_PATH / "Overcooked! 2" / "Overcooked2.app" / DLL_RELATIVE_PATH),
]

PATCHES: List[Tuple[str, str]] = [
    ("Microsoft Wireless 360 Controller", "Microsoft GamePad-1"),
    ("Mad Catz, Inc. Mad Catz FPS Pro GamePad", "Microsoft GamePad-2"),
    ("Mad Catz, Inc. MadCatz Call of Duty GamePad", "Microsoft GamePad-3"),
    ("\xa9Microsoft Corporation Controller", "Microsoft GamePad-4"),
]

# JoystickNames of every InControl OS X profile. Steam Input cannot hide
# physical HID devices on macOS, so a pad recognized by one of these profiles
# attaches twice: as its Steam virtual controller and as the physical device.
# Neutering the names forces all input through Steam Input.
NATIVE_PROFILE_PATCHES: List[Tuple[str, str]] = [
    ("BDA PS3 Airflo wired controller", "UnusedPad-01"),
    (" USB,2-axis 8-button gamepad", "UnusedPad-02"),
    ("Zeroplus PS Vibration Feedback Converter", "UnusedPad-03"),
    ("Zeroplus PS Vibration Feedback Converter ", "UnusedPad-04"),
    ("Logitech Logitech Dual Action", "UnusedPad-05"),
    ("Logitech Gamepad F310", "UnusedPad-06"),
    ("Logitech Logitech RumblePad 2 USB", "UnusedPad-07"),
    ("Logitech Rumble Gamepad F510", "UnusedPad-08"),
    ("Logitech Logitech Cordless RumblePad 2", "UnusedPad-09"),
    ("Unknown Moga Pro HID", "UnusedPad-10"),
    ("Unknown Gamepad", "UnusedPad-11"),
    ("Sony PLAYSTATION(R)3 Controller", "UnusedPad-12"),
    ("SHENGHIC 2009/0708ZXW-V1Inc. PLAYSTATION(R)3Conteroller", "UnusedPad-13"),
    ("SZMY-POWER CO.,LTD. GAMEPAD 3 TURBO", "UnusedPad-14"),
    ("Gasia Co.,Ltd PS(R) Gamepad", "UnusedPad-15"),
    ("Unknown Wireless Controller", "UnusedPad-16"),
    ("Sony Computer Entertainment Wireless Controller", "UnusedPad-17"),
    ("Sony Interactive Entertainment Wireless Controller", "UnusedPad-18"),
    ("Razer Razer Serval", "UnusedPad-19"),
    ("Unknown Razer Serval", "UnusedPad-20"),
    ("DragonRise Inc.   Generic   USB  Joystick  ", "UnusedPad-21"),
    ("Unknown Zeemote: SteelSeries FREE", "UnusedPad-22"),
    ("Microsoft Xbox One Wired Controller", "UnusedPad-23"),
    ("\xa9Microsoft Corporation Xbox Original Wired Controller", "UnusedPad-24"),
    ("Sony Interactive Entertainment DUALSHOCK\xae4 USB Wireless Adaptor", "UnusedPad-25"),
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


def patch_dll(dll_path: Path, patches: List[Tuple[str, str]] = PATCHES) -> bool:
    backup = dll_path.with_suffix(".dll.bak")

    if not dll_path.exists():
        log.error("DLL not found: %s", dll_path)
        return False

    try:
        if not backup.exists():
            shutil.copy2(dll_path, backup)
            log.info("Backup: %s", backup.name)

        data = bytearray(dll_path.read_bytes())

        patched = sum(1 for old, new in patches if patch_string(data, old, new))

        if patched == 0:
            log.error("No strings found to patch")
            return False

        dll_path.write_bytes(data)
        log.info("Patched %d/%d controller names", patched, len(patches))
        return True

    except PermissionError:
        log.error("Permission denied: Unable to read/write to %s. Try checking folder permissions.", dll_path.name)
        return False
    except Exception as e:
        log.error("An unexpected error occurred while patching: %s", str(e))
        return False


def restore_dll(dll_path: Path) -> bool:
    backup = dll_path.with_suffix(".dll.bak")
    if not backup.exists():
        log.error("No backup found for %s", dll_path.name)
        return False

    try:
        shutil.copy2(backup, dll_path)
        log.info("Restored from backup successfully")
        return True
    except PermissionError:
        log.error("Permission denied: Unable to restore file %s", dll_path.name)
        return False


def find_installed_games() -> List[Tuple[str, Path]]:
    """Return list of (name, dll_path) for games that are installed."""
    return [(name, dll_path) for name, dll_path in GAMES if dll_path.exists()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Steam Input Controller Patch for InControl Games")
    parser.add_argument("custom_path", nargs="?", type=Path, help="Optional specific path to Assembly-CSharp.dll")
    parser.add_argument("--restore", action="store_true", help="Restore the DLL from backup")
    parser.add_argument(
        "--disable-native-profiles",
        action="store_true",
        help="Experimental: also neuter every built-in macOS controller profile so physical "
             "pads cannot attach alongside their Steam Input virtual controllers",
    )

    args = parser.parse_args()

    patches = PATCHES + (NATIVE_PROFILE_PATCHES if args.disable_native_profiles else [])

    if args.restore:
        process_game = restore_dll
    else:
        def process_game(dll_path: Path) -> bool:
            return patch_dll(dll_path, patches)

    if args.custom_path:
        games_to_process = [("", args.custom_path)]
    else:
        games_to_process = find_installed_games()

    if not games_to_process:
        log.error("No supported games found automatically. Provide a direct path to Assembly-CSharp.dll.")
        return 1

    all_succeeded = True
    for game_name, dll_path in games_to_process:
        if game_name:
            log.info("\n%s", game_name)
        log.info("DLL: %s", dll_path)

        if not process_game(dll_path):
            all_succeeded = False

    if all_succeeded and not args.restore:
        log.info("\nSuccess! Now enable Steam Input in each game's Steam properties.")

    return 0 if all_succeeded else 1


if __name__ == "__main__":
    sys.exit(main())
