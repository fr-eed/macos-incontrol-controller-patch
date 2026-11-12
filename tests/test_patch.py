"""
Tests for patch.py against a fake Assembly-CSharp.dll.

"""

import logging
import tempfile
import unittest
from pathlib import Path

import patch

ALL_PATCHES = patch.PATCHES + patch.NATIVE_PROFILE_PATCHES

FIXTURES = Path(__file__).parent / "fixtures"

# Same decoys as in fixtures/FakeProfiles.cs
DECOYS = [
    "Unknown Gamepad Pro",
    "Microsoft Wireless 360 Controller for Windows",
    "Press Start",
]


def fake_dll(game_version: str) -> bytes:
    """Build DLL bytes holding every original controller name.
    """
    fixture = FIXTURES / f"Assembly-CSharp-{game_version}.dll"

    return fixture.read_bytes()


def has_string(data: bytes, text: str) -> bool:
    pattern = patch.user_string_pattern(text)

    return pattern in data


def natives_disabled(data: bytes) -> bool:
    return has_string(data, "UnusedPad-01")


class PatchDllTest(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)

        self.tmp = tempfile.TemporaryDirectory()
        work_dir = Path(self.tmp.name)

        self.dll = work_dir / "Assembly-CSharp.dll"
        self.backup = work_dir / "Assembly-CSharp.dll.bak"
        self.v1 = fake_dll("v1")
        self.dll.write_bytes(self.v1)

    def tearDown(self) -> None:
        self.tmp.cleanup()
        logging.disable(logging.NOTSET)

    def test_fresh_patch_renames_steam_input_names(self) -> None:
        ok = patch.patch_dll(self.dll, patch.PATCHES)
        data = self.dll.read_bytes()

        self.assertTrue(ok)
        self.assertTrue(patch.is_patched(data))
        self.assertTrue(has_string(data, "Microsoft GamePad-1"))
        self.assertTrue(has_string(data, "Microsoft GamePad-4"))
        self.assertFalse(has_string(data, "Microsoft Wireless 360 Controller"))

    def test_fresh_patch_keeps_native_profiles(self) -> None:
        patch.patch_dll(self.dll, patch.PATCHES)
        data = self.dll.read_bytes()

        self.assertFalse(natives_disabled(data))

    def test_decoys_are_untouched(self) -> None:
        patch.patch_dll(self.dll, ALL_PATCHES)
        data = self.dll.read_bytes()

        for decoy in DECOYS:
            with self.subTest(decoy=decoy):
                self.assertTrue(has_string(data, decoy))

    def test_size_is_untouched(self) -> None:
        patch.patch_dll(self.dll, ALL_PATCHES)
        data = self.dll.read_bytes()

        self.assertEqual(len(data), len(self.v1))

    def test_fresh_patch_backs_up_original(self) -> None:
        patch.patch_dll(self.dll, patch.PATCHES)

        self.assertEqual(self.backup.read_bytes(), self.v1)

    def test_disable_native_profiles_renames_all_of_them(self) -> None:
        patch.patch_dll(self.dll, ALL_PATCHES)
        data = self.dll.read_bytes()

        for old, new in patch.NATIVE_PROFILE_PATCHES:
            with self.subTest(profile=old):
                self.assertFalse(has_string(data, old))
                self.assertTrue(has_string(data, new))

    def test_repatch_with_tick_disables_natives(self) -> None:
        patch.patch_dll(self.dll, patch.PATCHES)
        patch.patch_dll(self.dll, ALL_PATCHES)
        data = self.dll.read_bytes()

        self.assertTrue(natives_disabled(data))
        self.assertEqual(self.backup.read_bytes(), self.v1)

    def test_repatch_without_tick_brings_natives_back(self) -> None:
        patch.patch_dll(self.dll, ALL_PATCHES)
        patch.patch_dll(self.dll, patch.PATCHES)
        data = self.dll.read_bytes()

        self.assertFalse(natives_disabled(data))
        self.assertTrue(patch.is_patched(data))

    def test_patch_then_ticked_then_unticked(self) -> None:
        patch.patch_dll(self.dll, patch.PATCHES)
        first_unticked = self.dll.read_bytes()

        patch.patch_dll(self.dll, ALL_PATCHES)
        ticked = self.dll.read_bytes()

        patch.patch_dll(self.dll, patch.PATCHES)
        last_unticked = self.dll.read_bytes()

        self.assertTrue(natives_disabled(ticked))
        self.assertEqual(last_unticked, first_unticked)
        self.assertEqual(self.backup.read_bytes(), self.v1)

    def test_game_update_refreshes_backup(self) -> None:
        patch.patch_dll(self.dll, patch.PATCHES)

        v2 = fake_dll("v2")
        self.dll.write_bytes(v2)
        patch.patch_dll(self.dll, patch.PATCHES)

        self.assertEqual(self.backup.read_bytes(), v2)
        self.assertTrue(patch.is_patched(self.dll.read_bytes()))

    def test_restore_returns_original(self) -> None:
        patch.patch_dll(self.dll, ALL_PATCHES)

        ok = patch.restore_dll(self.dll)

        self.assertTrue(ok)
        self.assertEqual(self.dll.read_bytes(), self.v1)

    def test_restore_after_game_update_returns_new_version(self) -> None:
        patch.patch_dll(self.dll, patch.PATCHES)
        v2 = fake_dll("v2")
        self.dll.write_bytes(v2)
        patch.patch_dll(self.dll, patch.PATCHES)

        patch.restore_dll(self.dll)

        self.assertEqual(self.dll.read_bytes(), v2)

    def test_restore_without_backup_fails(self) -> None:
        ok = patch.restore_dll(self.dll)

        self.assertFalse(ok)
        self.assertEqual(self.dll.read_bytes(), self.v1)

    def test_missing_dll_fails(self) -> None:
        self.dll.unlink()

        ok = patch.patch_dll(self.dll, patch.PATCHES)

        self.assertFalse(ok)

    def test_dll_without_controller_names_fails(self) -> None:
        self.dll.write_bytes(b"NOT AN INCONTROL GAME")

        ok = patch.patch_dll(self.dll, patch.PATCHES)

        self.assertFalse(ok)


class PatchStringTest(unittest.TestCase):
    def test_longer_replacement_is_rejected(self) -> None:
        logging.disable(logging.CRITICAL)
        data = bytearray(fake_dll("v1"))

        ok = patch.patch_string(data, "Unknown Gamepad", "A name that is far too long")

        logging.disable(logging.NOTSET)
        self.assertFalse(ok)

    def test_shorter_replacement_is_zero_padded(self) -> None:
        old = "Microsoft Wireless 360 Controller"
        new = "Microsoft GamePad-1"
        data = bytearray(patch.user_string_pattern(old) + b"\x01")

        patch.patch_string(data, old, new)

        expected_text = patch.user_string_pattern(new)
        padding_size = len(data) - len(expected_text)
        padding = bytes(padding_size)
        self.assertEqual(bytes(data), expected_text + padding)


if __name__ == "__main__":
    unittest.main()
