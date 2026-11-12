# Steam Input Controller Patch for InControl Games (macOS)

[![Downloads](https://img.shields.io/github/downloads/fr-eed/macos-incontrol-controller-patch/total?style=for-the-badge&logo=github&logoColor=66C0F4&label=DOWNLOADS&labelColor=171A21&color=66C0F4)](https://github.com/fr-eed/macos-incontrol-controller-patch/releases)

Fixes controller support on macOS by patching games to recognize Steam Input's virtual controllers.

> [!TIP]
> **[Download the latest release](https://github.com/fr-eed/macos-incontrol-controller-patch/releases/latest)** and run the patcher app. No Python required.

## Supported Games

- Tricky Towers
- Overcooked! 2
- Human Fall Flat
- Any other Unity game that used InControl package

## Problem

These games use InControl for input handling. On macOS, Steam Input presents controllers as "Microsoft GamePad-1", "Microsoft GamePad-2", etc. These names don't match any built-in InControl profile, causing controllers to appear as "Unknown Device".

## Solution

Patches `Assembly-CSharp.dll` to replace Xbox360MacProfile's JoystickNames with Steam Input controller names:

| Original | Replacement |
|----------|-------------|
| Microsoft Wireless 360 Controller | Microsoft GamePad-1 |
| Mad Catz, Inc. Mad Catz FPS Pro GamePad | Microsoft GamePad-2 |
| Mad Catz, Inc. MadCatz Call of Duty GamePad | Microsoft GamePad-3 |
| ©Microsoft Corporation Controller | Microsoft GamePad-4 |

### Disable native controller profiles

It is recommended to use all controller sthrough steam input as some controllers can be registered twice by the game which causes double inputs. 

tick "Disable native controller profiles" in the GUI (or use `--disable-native-profiles`). This will null out all profile names except Steam input controllers, basically disabling any controller that doesn't go through Steam input

To undo, click Restore and patch again without it.

## Usage

### GUI (recommended)

```bash
python3 patch_gui.py
```

Automatically detects supported games in the default Steam library folder; games installed in other Steam library locations must be selected or provided manually.

### Command Line

```bash
python3 patch.py                        # Patch all installed games
python3 patch.py /path/to/dll           # Patch specific DLL
python3 patch.py --restore              # Restore all installed games
python3 patch.py --restore /path/to/dll # Restore specific DLL
python3 patch.py --disable-native-profiles  # Also disable native pad profiles (experimental)
```

### After Patching

Enable Steam Input:
1. Steam -> Right-click the game -> Properties -> Controller
2. Select "Enable Steam Input"

## Tested With

- Tricky Towers (unity.WeirdBeard.Tricky Towers)
- Unity Player 5.5.1p3 (828893732fe0)
- Overcooked! 2

## Notes

- Supports up to 4 controllers
- Backup created automatically (`Assembly-CSharp.dll.bak`)
- Game updates will overwrite the patch
- See `docs/` for technical details

## Star History

<a href="https://www.star-history.com/?repos=fr-eed%2Fmacos-incontrol-controller-patch&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=fr-eed/macos-incontrol-controller-patch&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=fr-eed/macos-incontrol-controller-patch&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=fr-eed/macos-incontrol-controller-patch&type=date&legend=top-left" />
 </picture>
</a>