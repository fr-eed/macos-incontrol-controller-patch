"""
Bluetooth DualShock 4 mode for Human Fall Flat.

macOS switches DualShock 4 controllers connected over Bluetooth to their
extended input report (0x11), which InControl cannot read. Steam Input works
around that, but all Steam virtual pads share the HID Location ID 0x0, so two
controllers overwrite each other's input in local co-op.

This mode instead:
  1. replaces the game's InControlNative plugin with native/InControlNative,
     which decodes DS4 reports (USB 0x01 and Bluetooth 0x11) itself and gives
     every controller its own device, and
  2. patches Assembly-CSharp.dll so InControl always uses native input.

Steam Input must be turned OFF for the game in this mode.
"""

import logging
import shutil
import sys
from pathlib import Path
from typing import Optional

import patch

log = logging.getLogger(__name__)

PLUGIN_RELATIVE_PATH = Path("Contents/Plugins/InControlNative.bundle/Contents/MacOS/InControlNative")

# InControlManager.OnEnable: `ldarg.0; ldfld enableNativeInput; call InputManager::set_EnableNativeInput`.
# Replacing the field load with `ldc.i4.1; nop x5` turns native input on. Token values are those
# of Human Fall Flat's Assembly-CSharp.dll, so other games are rejected.
NATIVE_INPUT_OFF = bytes.fromhex("027be702000428" "3c040006")
NATIVE_INPUT_ON = bytes.fromhex("17000000000028" "3c040006")


def bundled_plugin() -> Optional[Path]:
    """Path of the built plugin, inside the PyInstaller bundle or next to this file."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    plugin = base / "native" / "InControlNative"

    return plugin if plugin.exists() else None


def game_plugin_path(dll_path: Path) -> Optional[Path]:
    """Path of the game's InControlNative plugin for a given Assembly-CSharp.dll."""
    for parent in dll_path.parents:
        if parent.suffix == ".app":
            return parent / PLUGIN_RELATIVE_PATH

    return None


def is_native_input_enabled(data: bytes) -> bool:
    return NATIVE_INPUT_ON in data


def enable_native_input(data: bytearray) -> bool:
    """Patch the native input switch in place. Returns False if the game is not supported."""
    if data.count(NATIVE_INPUT_ON) == 1:
        return True

    if data.count(NATIVE_INPUT_OFF) != 1:
        return False

    pos = data.find(NATIVE_INPUT_OFF)
    data[pos:pos + len(NATIVE_INPUT_ON)] = NATIVE_INPUT_ON

    return True


def install(dll_path: Path, plugin: Optional[Path] = None) -> bool:
    """Enable native input in a clean copy of the DLL and install the DS4 plugin.

    Uses the same .dll.bak backup as patch_dll, so restore_dll undoes the DLL change.
    The original plugin is kept as InControlNative.orig.
    """
    plugin = plugin or bundled_plugin()
    if not plugin:
        log.error("DS4 plugin not found. Build it first: sh native/build.sh")
        return False

    game_plugin = game_plugin_path(dll_path)
    if not game_plugin or not game_plugin.exists():
        log.error("InControlNative plugin not found in the game's .app bundle")
        return False

    backup = dll_path.with_suffix(".dll.bak")

    try:
        current = dll_path.read_bytes()
        already_patched = patch.is_patched(current) or is_native_input_enabled(current)

        if not (already_patched and backup.exists()):
            shutil.copy2(dll_path, backup)
            log.info("Backup created: %s", backup.name)

        data = bytearray(backup.read_bytes())

        if not enable_native_input(data):
            log.error("Native input switch not found. Bluetooth DS4 mode only supports Human Fall Flat.")
            return False

        dll_path.write_bytes(data)
        log.info("Native input enabled")

        plugin_backup = game_plugin.with_suffix(".orig")
        if not plugin_backup.exists():
            shutil.copy2(game_plugin, plugin_backup)
            log.info("Backup created: %s", plugin_backup.name)

        shutil.copy2(plugin, game_plugin)
        log.info("DS4 Bluetooth plugin installed")
        return True

    except PermissionError:
        log.error("Permission denied: Unable to modify files in %s", dll_path.parent)
        return False


def restore_plugin(dll_path: Path) -> bool:
    """Put the original InControlNative plugin back, if it was replaced."""
    game_plugin = game_plugin_path(dll_path)
    if not game_plugin:
        return False

    plugin_backup = game_plugin.with_suffix(".orig")
    if not plugin_backup.exists():
        return False

    try:
        shutil.move(plugin_backup, game_plugin)
        log.info("Original InControlNative plugin restored")
        return True
    except PermissionError:
        log.error("Permission denied: Unable to restore %s", game_plugin.name)
        return False
