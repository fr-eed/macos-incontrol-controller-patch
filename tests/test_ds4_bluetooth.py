"""
Tests for ds4_bluetooth.py against a fake game .app bundle.
"""

import logging
import tempfile
import unittest
from pathlib import Path

import ds4_bluetooth
import patch

FIXTURES = Path(__file__).parent / "fixtures"

ORIGINAL_PLUGIN = b"original InControlNative"
DS4_PLUGIN = b"replacement InControlNative"


def setUpModule() -> None:
    logging.disable(logging.CRITICAL)


def tearDownModule() -> None:
    logging.disable(logging.NOTSET)


class Ds4BluetoothTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        work_dir = Path(self.tmp.name)

        app = work_dir / "Human.app"
        self.dll = app / patch.DLL_RELATIVE_PATH
        self.game_plugin = app / ds4_bluetooth.PLUGIN_RELATIVE_PATH
        self.dll.parent.mkdir(parents=True)
        self.game_plugin.parent.mkdir(parents=True)

        # Controller names from the fixture plus the native input switch of Human Fall Flat
        self.original_dll = (FIXTURES / "Assembly-CSharp-v1.dll").read_bytes() + ds4_bluetooth.NATIVE_INPUT_OFF
        self.dll.write_bytes(self.original_dll)
        self.game_plugin.write_bytes(ORIGINAL_PLUGIN)

        self.plugin = work_dir / "InControlNative"
        self.plugin.write_bytes(DS4_PLUGIN)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_install_enables_native_input_and_replaces_plugin(self) -> None:
        ok = ds4_bluetooth.install(self.dll, self.plugin)
        data = self.dll.read_bytes()

        self.assertTrue(ok)
        self.assertTrue(ds4_bluetooth.is_native_input_enabled(data))
        self.assertNotIn(ds4_bluetooth.NATIVE_INPUT_OFF, data)
        self.assertEqual(self.game_plugin.read_bytes(), DS4_PLUGIN)

    def test_install_creates_backups_of_originals(self) -> None:
        ds4_bluetooth.install(self.dll, self.plugin)

        self.assertEqual(self.dll.with_suffix(".dll.bak").read_bytes(), self.original_dll)
        self.assertEqual(self.game_plugin.with_suffix(".orig").read_bytes(), ORIGINAL_PLUGIN)

    def test_install_twice_keeps_original_backups(self) -> None:
        ds4_bluetooth.install(self.dll, self.plugin)
        ok = ds4_bluetooth.install(self.dll, self.plugin)

        self.assertTrue(ok)
        self.assertEqual(self.dll.with_suffix(".dll.bak").read_bytes(), self.original_dll)
        self.assertEqual(self.game_plugin.with_suffix(".orig").read_bytes(), ORIGINAL_PLUGIN)

    def test_unsupported_game_is_rejected(self) -> None:
        other_game = (FIXTURES / "Assembly-CSharp-v1.dll").read_bytes()
        self.dll.write_bytes(other_game)

        ok = ds4_bluetooth.install(self.dll, self.plugin)

        self.assertFalse(ok)
        self.assertEqual(self.dll.read_bytes(), other_game)
        self.assertEqual(self.game_plugin.read_bytes(), ORIGINAL_PLUGIN)

    def test_install_replaces_steam_input_patch(self) -> None:
        patch.patch_dll(self.dll, patch.PATCHES + patch.NATIVE_PROFILE_PATCHES)

        ok = ds4_bluetooth.install(self.dll, self.plugin)
        data = self.dll.read_bytes()

        self.assertTrue(ok)
        self.assertFalse(patch.is_patched(data))
        self.assertTrue(ds4_bluetooth.is_native_input_enabled(data))

    def test_restore_brings_back_original_files(self) -> None:
        ds4_bluetooth.install(self.dll, self.plugin)

        self.assertTrue(ds4_bluetooth.restore_plugin(self.dll))
        self.assertTrue(patch.restore_dll(self.dll))
        self.assertEqual(self.dll.read_bytes(), self.original_dll)
        self.assertEqual(self.game_plugin.read_bytes(), ORIGINAL_PLUGIN)
        self.assertFalse(self.game_plugin.with_suffix(".orig").exists())

    def test_restore_plugin_without_backup_does_nothing(self) -> None:
        self.assertFalse(ds4_bluetooth.restore_plugin(self.dll))
        self.assertEqual(self.game_plugin.read_bytes(), ORIGINAL_PLUGIN)


if __name__ == "__main__":
    unittest.main()
